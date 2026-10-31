"""Abstract LLM interface with caching support."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import yaml
import os
from dotenv import load_dotenv

from .message_types import TokenUsage, CostBreakdown


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: str
    model: str
    api_key: str
    max_tokens: int
    temperature: float
    enable_caching: bool
    context_limit: int
    pricing: Dict[str, float]


class LLMInterface(ABC):
    """Abstract interface for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
        user_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], TokenUsage]:
        """
        Generate a response.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt (will be cached if use_cache=True)
            tools: Optional list of tool definitions (will be cached if use_cache=True)
            use_cache: Whether to enable prompt caching
            user_id: Optional user identifier for tracking (OpenAI only)

        Returns:
            Tuple of (response_text, tool_calls, token_usage)
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass

    def calculate_cost(self, usage: TokenUsage) -> CostBreakdown:
        """Calculate cost based on token usage."""
        pricing = self.config.pricing

        # Convert from tokens to millions of tokens
        input_cost = (usage.input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (usage.output_tokens / 1_000_000) * pricing.get("output", 0)
        cache_write_cost = (usage.cache_creation_tokens / 1_000_000) * pricing.get("cache_write", 0)
        cache_read_cost = (usage.cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)

        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            cache_write_cost=cache_write_cost,
            cache_read_cost=cache_read_cost,
        )

    def estimate_context_usage(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Estimate total context tokens that will be used.

        Returns:
            Estimated token count
        """
        total = 0

        # System prompt
        if system_prompt:
            total += self.count_tokens(system_prompt)

        # Tools (rough estimate)
        if tools:
            tools_str = str(tools)
            total += self.count_tokens(tools_str)

        # Messages
        for msg in messages:
            content = msg.get("content")

            # Handle content (can be string, list, or None)
            if isinstance(content, str):
                total += self.count_tokens(content)
            elif isinstance(content, list):
                # List of content blocks (Anthropic) or tool results
                total += self.count_tokens(str(content))
            elif content is None:
                pass  # No content tokens
            else:
                total += self.count_tokens(str(content))

            # Handle tool_calls if present (OpenAI format)
            if "tool_calls" in msg:
                total += self.count_tokens(str(msg["tool_calls"]))

        # Add overhead for message formatting (rough estimate: 10 tokens per message)
        total += len(messages) * 10

        return total


def load_llm_from_config(config_path: str = "config.yaml") -> LLMInterface:
    """
    Load LLM provider from configuration file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Configured LLMInterface instance
    """
    # Load environment variables from .env file
    load_dotenv()

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    provider = config['llm_provider']
    provider_config = config[provider]

    # Get API key from environment
    api_key_env = provider_config['api_key_env']
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"API key not found in environment variable: {api_key_env}")

    # Get context limit
    context_limit = config['context_limits']['max_context_tokens']

    # Get pricing
    model = provider_config['model']
    pricing = config['cost_tracking'][f'{provider}_pricing'].get(model, {})

    llm_config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        max_tokens=provider_config['max_tokens'],
        temperature=provider_config['temperature'],
        enable_caching=provider_config['enable_caching'],
        context_limit=context_limit,
        pricing=pricing,
    )

    # Import and instantiate the appropriate provider
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(llm_config)
    elif provider == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(llm_config)
    elif provider == "xai":
        from .xai_provider import XAIProvider
        return XAIProvider(llm_config)
    elif provider == "google":
        from .google_provider import GoogleProvider
        return GoogleProvider(llm_config)
    else:
        raise ValueError(f"Unknown provider: {provider}")
