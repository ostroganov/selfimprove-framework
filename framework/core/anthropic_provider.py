"""Anthropic provider implementation with prompt caching."""

from typing import List, Dict, Any, Optional, Tuple
import anthropic

from .llm_interface import LLMInterface
from .message_types import TokenUsage


class AnthropicProvider(LLMInterface):
    """Anthropic Claude provider with prompt caching support."""

    def __init__(self, config):
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=config.api_key)

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
        user_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], TokenUsage]:
        """
        Generate a response using Claude with prompt caching.

        Caching strategy:
        1. System prompt is marked for caching (most stable)
        2. Tool definitions are marked for caching (stable)
        3. Recent conversation history can be cached (less stable)

        Args:
            user_id: Unused (Anthropic doesn't support user tracking parameter)
        """
        # Prepare system content with caching
        system_content = []
        if system_prompt:
            system_content.append({
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"} if use_cache and self.config.enable_caching else None
            })

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            # Basic message format
            message = {
                "role": msg["role"],
                "content": msg["content"]
            }
            anthropic_messages.append(message)

        # Prepare API call parameters
        api_params = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": anthropic_messages,
        }

        # Add system prompt if provided
        if system_content:
            # Filter out None cache_control
            system_content = [{k: v for k, v in item.items() if v is not None}
                            for item in system_content]
            api_params["system"] = system_content

        # Add tools with caching if provided
        if tools:
            api_params["tools"] = tools
            # Mark tools for caching if enabled
            if use_cache and self.config.enable_caching and len(tools) > 0:
                # Cache the last tool definition (Anthropic caches from the end)
                tools[-1]["cache_control"] = {"type": "ephemeral"}

        # Make API call
        try:
            response = self.client.messages.create(**api_params)

            # Extract response text and build content blocks
            content_blocks = []
            response_text = ""
            tool_calls = []

            for content_block in response.content:
                if content_block.type == "text":
                    response_text += content_block.text
                    content_blocks.append({
                        "type": "text",
                        "text": content_block.text
                    })
                elif content_block.type == "tool_use":
                    tool_calls.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                        # Store content block for reconstructing message
                        "_content_block": {
                            "type": "tool_use",
                            "id": content_block.id,
                            "name": content_block.name,
                            "input": content_block.input
                        }
                    })

            # Extract token usage
            usage = response.usage
            token_usage = TokenUsage(
                input_tokens=getattr(usage, 'input_tokens', 0),
                output_tokens=getattr(usage, 'output_tokens', 0),
                cache_creation_tokens=getattr(usage, 'cache_creation_input_tokens', 0),
                cache_read_tokens=getattr(usage, 'cache_read_input_tokens', 0),
            )

            return response_text, tool_calls, token_usage

        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Note: Anthropic doesn't provide a public tokenization API,
        so we use a rough estimate of ~4 characters per token.
        This is conservative and tends to overestimate.
        """
        if text is None:
            return 0

        # Rough estimate: 4 characters per token
        # This is a conservative estimate and may overcount
        return len(text) // 4 + 1 if text else 0

    def count_tokens_beta(self, text: str) -> int:
        """
        Count tokens using the beta token counting API.

        Note: This requires the beta API which may not be available.
        Falls back to estimate if not available.
        """
        try:
            # Anthropic's beta token counting (if available)
            response = self.client.messages.count_tokens(
                model=self.config.model,
                messages=[{"role": "user", "content": text}]
            )
            return response.input_tokens
        except Exception:
            # Fall back to estimate
            return self.count_tokens(text)
