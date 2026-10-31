"""Data structures for messages, conversations, and token tracking."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class TokenUsage:
    """Token usage information with cache breakdown."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_input(self) -> int:
        """Total input tokens (including cache operations)."""
        return self.input_tokens + self.cache_creation_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens

    def add(self, other: 'TokenUsage') -> 'TokenUsage':
        """Add another TokenUsage to this one."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens + other.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
        )


@dataclass
class CostBreakdown:
    """Cost breakdown by token type."""
    input_cost: float = 0.0
    output_cost: float = 0.0
    cache_write_cost: float = 0.0
    cache_read_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total cost in USD."""
        return self.input_cost + self.output_cost + self.cache_write_cost + self.cache_read_cost


@dataclass
class Message:
    """A single message in a conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool_calls=data.get("tool_calls"),
            tool_results=data.get("tool_results"),
        )


@dataclass
class Conversation:
    """A conversation session."""
    id: str
    level_from: str
    level_to: str
    initial_prompt: str
    messages: List[Message] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    cost: CostBreakdown = field(default_factory=CostBreakdown)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Message):
        """Add a message to the conversation."""
        self.messages.append(message)

    def update_usage(self, usage: TokenUsage, cost: CostBreakdown):
        """Update token usage and cost."""
        self.token_usage = self.token_usage.add(usage)
        self.cost.input_cost += cost.input_cost
        self.cost.output_cost += cost.output_cost
        self.cost.cache_write_cost += cost.cache_write_cost
        self.cost.cache_read_cost += cost.cache_read_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "level_from": self.level_from,
            "level_to": self.level_to,
            "initial_prompt": self.initial_prompt,
            "messages": [m.to_dict() for m in self.messages],
            "token_usage": {
                "input_tokens": self.token_usage.input_tokens,
                "output_tokens": self.token_usage.output_tokens,
                "cache_creation_tokens": self.token_usage.cache_creation_tokens,
                "cache_read_tokens": self.token_usage.cache_read_tokens,
            },
            "cost": {
                "input_cost": self.cost.input_cost,
                "output_cost": self.cost.output_cost,
                "cache_write_cost": self.cost.cache_write_cost,
                "cache_read_cost": self.cost.cache_read_cost,
                "total_cost": self.cost.total_cost,
            },
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create from dictionary."""
        token_usage_data = data["token_usage"]
        cost_data = data["cost"]

        return cls(
            id=data["id"],
            level_from=data["level_from"],
            level_to=data["level_to"],
            initial_prompt=data["initial_prompt"],
            messages=[Message.from_dict(m) for m in data["messages"]],
            token_usage=TokenUsage(
                input_tokens=token_usage_data["input_tokens"],
                output_tokens=token_usage_data["output_tokens"],
                cache_creation_tokens=token_usage_data["cache_creation_tokens"],
                cache_read_tokens=token_usage_data["cache_read_tokens"],
            ),
            cost=CostBreakdown(
                input_cost=cost_data["input_cost"],
                output_cost=cost_data["output_cost"],
                cache_write_cost=cost_data["cache_write_cost"],
                cache_read_cost=cost_data["cache_read_cost"],
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TransitionMetrics:
    """Metrics for a level transition."""
    level_from: str
    level_to: str
    total_conversations: int = 0
    total_drafts: int = 0
    total_tokens: TokenUsage = field(default_factory=TokenUsage)
    total_cost: CostBreakdown = field(default_factory=CostBreakdown)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "level_from": self.level_from,
            "level_to": self.level_to,
            "total_conversations": self.total_conversations,
            "total_drafts": self.total_drafts,
            "total_tokens": {
                "input_tokens": self.total_tokens.input_tokens,
                "output_tokens": self.total_tokens.output_tokens,
                "cache_creation_tokens": self.total_tokens.cache_creation_tokens,
                "cache_read_tokens": self.total_tokens.cache_read_tokens,
                "total": self.total_tokens.total_tokens,
            },
            "total_cost": {
                "input_cost": self.total_cost.input_cost,
                "output_cost": self.total_cost.output_cost,
                "cache_write_cost": self.total_cost.cache_write_cost,
                "cache_read_cost": self.total_cost.cache_read_cost,
                "total_cost": self.total_cost.total_cost,
            },
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
