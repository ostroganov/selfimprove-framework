"""xAI Grok provider implementation with prompt caching."""

from typing import List, Dict, Any, Optional, Tuple
import tiktoken

from .llm_interface import LLMInterface
from .message_types import TokenUsage


class XAIProvider(LLMInterface):
    """xAI Grok provider with prompt caching support."""

    def __init__(self, config):
        super().__init__(config)

        # Import OpenAI here (xAI API is OpenAI-compatible)
        try:
            from openai import OpenAI
            # xAI uses OpenAI-compatible API at https://api.x.ai/v1
            self.client = OpenAI(
                api_key=config.api_key,
                base_url="https://api.x.ai/v1"
            )
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai>=1.0.0"
            )

        # Initialize tokenizer for token counting (use cl100k_base as fallback)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
        user_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], TokenUsage]:
        """
        Generate a response using xAI Grok with automatic prompt caching.

        xAI Caching strategy:
        - Automatic prompt caching is enabled for all requests
        - Cached tokens are reported in usage.prompt_tokens_details
        - Caching is transparent and requires no special configuration

        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt
            tools: Optional tool definitions
            use_cache: Whether to enable caching (xAI always caches automatically)
            user_id: Optional user identifier
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
            # Copy message, preserving all fields
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
            "max_tokens": self.config.max_tokens,
        }

        # Add user identifier if provided
        if user_id:
            api_params["user"] = user_id

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
                    import json
                    tool_calls.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": json.loads(tool_call.function.arguments),
                    })

            # Extract token usage
            usage = response.usage

            # Get cached tokens from prompt_tokens_details if available
            # xAI reports cached tokens in the usage object
            cached_tokens = 0
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                # xAI may report cached tokens similar to OpenAI
                cached_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', 0)

            token_usage = TokenUsage(
                input_tokens=getattr(usage, 'prompt_tokens', 0),
                output_tokens=getattr(usage, 'completion_tokens', 0),
                cache_creation_tokens=0,  # xAI doesn't separate cache write
                cache_read_tokens=cached_tokens,
            )

            return response_text, tool_calls, token_usage

        except Exception as e:
            raise RuntimeError(f"xAI API error: {str(e)}")

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
            if self.tokenizer:
                return len(self.tokenizer.encode(text))
            else:
                # Fall back to rough estimate
                return len(text) // 4 + 1 if text else 0
        except Exception:
            # Fall back to rough estimate if tokenizer fails
            return len(text) // 4 + 1 if text else 0
