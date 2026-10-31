"""OpenAI provider implementation with prompt caching."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import tiktoken

from .llm_interface import LLMInterface
from .message_types import TokenUsage

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMInterface):
    """OpenAI GPT provider with prompt caching support."""

    def __init__(self, config):
        super().__init__(config)

        # Import OpenAI here to make it optional
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai>=1.0.0"
            )

        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(config.model)
        except KeyError:
            # Fall back to cl100k_base for newer models
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Moderation log file
        self._moderation_log_path: Optional[Path] = None

    def _moderate_text(self, text: str, user_id: Optional[str] = None, context: str = "") -> Optional[Dict[str, Any]]:
        """Run text through OpenAI's moderation endpoint (log-only, non-blocking).

        Returns moderation result if content is flagged, None otherwise.
        """
        if not text or not text.strip():
            return None

        try:
            result = self.client.moderations.create(
                model="omni-moderation-latest",
                input=text
            )
            mod = result.results[0]
            if mod.flagged:
                flagged_categories = {
                    cat: getattr(mod.category_scores, cat, 0)
                    for cat in vars(mod.categories)
                    if getattr(mod.categories, cat, False)
                }
                entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "context": context,
                    "flagged_categories": flagged_categories,
                    "text_preview": text[:200],
                }
                logger.warning(f"Moderation flag: {flagged_categories} | context={context}")
                self._write_moderation_log(entry)
                return entry
            return None
        except Exception as e:
            logger.debug(f"Moderation call failed (non-blocking): {e}")
            return None

    def _write_moderation_log(self, entry: Dict[str, Any]):
        """Append a moderation flag entry to the log file."""
        if self._moderation_log_path is None:
            self._moderation_log_path = Path("run") / "moderation_log.jsonl"
            self._moderation_log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._moderation_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
        user_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], TokenUsage]:
        """
        Generate a response using OpenAI with prompt caching.

        Caching strategy (OpenAI prompt caching):
        - System messages and tool definitions are automatically cached
        - Caching happens when prompts exceed 1024 tokens
        - Recent conversation history is cached

        Args:
            user_id: Optional unique identifier for end-user tracking and moderation
        """
        # Prepare messages in OpenAI format
        openai_messages = []

        # Add system prompt if provided
        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt
            })

        # Add conversation messages
        for msg in messages:
            # Copy message, preserving all fields (tool_calls, tool_call_id, etc.)
            openai_msg = {
                "role": msg["role"],
                "content": msg.get("content")
            }

            # Preserve tool_calls for assistant messages
            if "tool_calls" in msg:
                openai_msg["tool_calls"] = msg["tool_calls"]

            # Preserve tool_call_id for tool messages
            if "tool_call_id" in msg:
                openai_msg["tool_call_id"] = msg["tool_call_id"]

            openai_messages.append(openai_msg)

        # Prepare API call parameters
        api_params = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
        }

        # Add user identifier if provided (for tracking and moderation)
        if user_id:
            api_params["user"] = user_id
            api_params["extra_body"] = {"safety_identifier": user_id}

        # GPT-5 and newer models use max_completion_tokens instead of max_tokens
        if "gpt-5" in self.config.model.lower() or "o1" in self.config.model.lower():
            api_params["max_completion_tokens"] = self.config.max_tokens
        else:
            api_params["max_tokens"] = self.config.max_tokens

        # Add tools if provided (convert to OpenAI format)
        if tools:
            openai_tools = []
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }
                })
            api_params["tools"] = openai_tools

        # Make API call
        try:
            response = self.client.chat.completions.create(**api_params)

            # Extract response text and tool calls
            message = response.choices[0].message
            response_text = message.content or ""

            tool_calls = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": json.loads(tool_call.function.arguments),
                    })

            # Extract token usage
            usage = response.usage

            # Get cached tokens from prompt_tokens_details if available
            cached_tokens = 0
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                cached_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', 0)

            token_usage = TokenUsage(
                input_tokens=getattr(usage, 'prompt_tokens', 0),
                output_tokens=getattr(usage, 'completion_tokens', 0),
                cache_creation_tokens=0,  # OpenAI doesn't separate cache write
                cache_read_tokens=cached_tokens,
            )

            # Log-only moderation: check the last user message asynchronously
            # This does not block or alter the response — purely for audit logging
            last_user_msg = None
            for msg in reversed(openai_messages):
                if msg.get("role") == "user" and msg.get("content"):
                    last_user_msg = msg["content"]
                    break
            if last_user_msg:
                self._moderate_text(last_user_msg, user_id=user_id, context="user_message")

            return response_text, tool_calls, token_usage

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if text is None:
            return 0

        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fall back to rough estimate if tokenizer fails
            return len(text) // 4 + 1 if text else 0
