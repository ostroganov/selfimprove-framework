"""Manages the transition from L(n) to L(n+1)."""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..core.llm_interface import LLMInterface
from ..core.message_types import (
    Message, MessageRole, Conversation, TransitionMetrics,
    TokenUsage, CostBreakdown
)
from ..tools.tool_registry import create_tool_registry


class TransitionManager:
    """Manages a level transition process."""

    def __init__(
        self,
        llm: LLMInterface,
        current_level: str,
        next_level: str,
        base_dir: str = ".",
        orchestrator_version: str = "unknown",
        run_id: Optional[str] = None,
        mode: str = "improvement"
    ):
        self.llm = llm
        self.current_level = current_level
        self.next_level = next_level
        self.base_dir = Path(base_dir)
        self.orchestrator_version = orchestrator_version
        self.run_id = run_id
        self.mode = mode

        # Paths
        self.levels_dir = self.base_dir / "levels"
        self.transitions_dir = self.base_dir / "transitions"
        self.transition_name = f"{current_level}_to_{next_level}"
        self.transition_dir = self.transitions_dir / self.transition_name

        # Create directories
        self.transition_dir.mkdir(parents=True, exist_ok=True)
        (self.transition_dir / "work").mkdir(exist_ok=True)
        (self.transition_dir / "conversations").mkdir(exist_ok=True)

        # State
        self.conversations: Dict[str, Conversation] = {}
        self.current_draft_version = 0
        self.current_draft_prompt: Optional[str] = None
        self.metrics = TransitionMetrics(
            level_from=current_level,
            level_to=next_level
        )

        # Load existing state if any
        self._load_state()

        # Create tool registry
        self.tool_registry = create_tool_registry(self)

    def _load_state(self):
        """Load existing transition state."""
        metrics_path = self.transition_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                data = json.load(f)
                # Load metrics (simplified for now)
                self.metrics.total_conversations = data.get("total_conversations", 0)
                self.metrics.total_drafts = data.get("total_drafts", 0)

    def _save_state(self):
        """Save current state."""
        metrics_path = self.transition_dir / "metrics.json"
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics.to_dict(), f, indent=2, ensure_ascii=False)

    # Conversation management

    def start_candidate_conversation(
        self,
        initial_prompt: str,
        context: str = ""
    ) -> Tuple[str, str, TokenUsage]:
        """Start a new conversation with the candidate.

        Returns:
            Tuple of (conversation_id, response, token_usage)
        """
        conv_id = f"conv_{len(self.conversations) + 1:03d}"

        conversation = Conversation(
            id=conv_id,
            level_from=self.current_level,
            level_to=self.next_level,
            initial_prompt=initial_prompt,
            metadata={"context": context}
        )

        # Get candidate's response
        response, token_usage = self._call_candidate(
            conversation,
            initial_prompt
        )

        # Add messages
        conversation.add_message(Message(
            role=MessageRole.USER,
            content=initial_prompt
        ))
        conversation.add_message(Message(
            role=MessageRole.ASSISTANT,
            content=response
        ))

        # Update usage
        cost = self.llm.calculate_cost(token_usage)
        conversation.update_usage(token_usage, cost)

        # Store conversation
        self.conversations[conv_id] = conversation
        self.metrics.total_conversations += 1
        self.metrics.total_tokens = self.metrics.total_tokens.add(token_usage)
        self.metrics.total_cost.input_cost += cost.input_cost
        self.metrics.total_cost.output_cost += cost.output_cost
        self.metrics.total_cost.cache_write_cost += cost.cache_write_cost
        self.metrics.total_cost.cache_read_cost += cost.cache_read_cost

        # Save
        self._save_conversation(conversation)
        self._save_state()

        return conv_id, response, token_usage

    def send_message_to_candidate(
        self,
        conversation_id: str,
        message: str
    ) -> Tuple[str, TokenUsage]:
        """Send a message in an existing conversation."""
        if conversation_id not in self.conversations:
            raise ValueError(f"Unknown conversation: {conversation_id}")

        conversation = self.conversations[conversation_id]

        # Get candidate's response
        response, token_usage = self._call_candidate(
            conversation,
            message
        )

        # Add messages
        conversation.add_message(Message(
            role=MessageRole.USER,
            content=message
        ))
        conversation.add_message(Message(
            role=MessageRole.ASSISTANT,
            content=response
        ))

        # Update usage
        cost = self.llm.calculate_cost(token_usage)
        conversation.update_usage(token_usage, cost)

        # Update metrics
        self.metrics.total_tokens = self.metrics.total_tokens.add(token_usage)
        self.metrics.total_cost.input_cost += cost.input_cost
        self.metrics.total_cost.output_cost += cost.output_cost
        self.metrics.total_cost.cache_write_cost += cost.cache_write_cost
        self.metrics.total_cost.cache_read_cost += cost.cache_read_cost

        # Save
        self._save_conversation(conversation)
        self._save_state()

        return response, token_usage

    def _call_candidate(
        self,
        conversation: Conversation,
        new_message: str
    ) -> Tuple[str, TokenUsage]:
        """Call the candidate LLM."""
        # Build message history
        messages = []
        for msg in conversation.messages:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        # Add new message
        messages.append({
            "role": "user",
            "content": new_message
        })

        # Get system prompt (use current draft or empty)
        system_prompt = self.current_draft_prompt or ""

        # Call LLM with caching
        response_text, tool_calls, token_usage = self.llm.generate(
            messages=messages,
            system_prompt=system_prompt,
            tools=None,  # Candidate doesn't get tools
            use_cache=True,
            user_id=self.run_id
        )

        return response_text, token_usage

    def list_candidate_conversations(self) -> List[Conversation]:
        """Get all conversations."""
        return list(self.conversations.values())

    def get_conversation(self, conversation_id: str) -> Conversation:
        """Get a specific conversation."""
        if conversation_id not in self.conversations:
            raise ValueError(f"Unknown conversation: {conversation_id}")
        return self.conversations[conversation_id]

    def _save_conversation(self, conversation: Conversation):
        """Save conversation to disk."""
        conv_path = self.transition_dir / "conversations" / f"{conversation.id}.json"
        with open(conv_path, 'w', encoding='utf-8') as f:
            json.dump(conversation.to_dict(), f, indent=2, ensure_ascii=False)

    # Reading operations

    def read_level_artifact(self, level: str, artifact_type: str) -> str:
        """Read an artifact from a level."""
        level_dir = self.levels_dir / level

        if artifact_type == "system_prompt":
            prompt_path = level_dir / "system_prompt.md"
            if prompt_path.exists():
                return prompt_path.read_text(encoding='utf-8')
            return ""
        elif artifact_type == "metadata":
            metadata_path = level_dir / "metadata.json"
            if metadata_path.exists():
                return metadata_path.read_text(encoding='utf-8')
            return "{}"
        else:
            raise ValueError(f"Unknown artifact type: {artifact_type}")

    def read_transition_history(self, transition_name: str) -> Dict[str, Any]:
        """Read history from a previous transition."""
        transition_dir = self.transitions_dir / transition_name

        if not transition_dir.exists():
            return {"error": f"Transition {transition_name} not found"}

        data = {}

        # Read commit rationale
        rationale_path = transition_dir / "commit_rationale.md"
        if rationale_path.exists():
            data["commit_rationale"] = rationale_path.read_text(encoding='utf-8')

        # Read handover
        handover_path = transition_dir / "handover.md"
        if handover_path.exists():
            data["handover_message"] = handover_path.read_text(encoding='utf-8')

        # Read metrics
        metrics_path = transition_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path, 'r', encoding='utf-8') as f:
                data["metrics"] = json.load(f)

        return data

    # Writing operations

    def write_evaluation_notes(self, notes: str, append: bool = True):
        """Write evaluation notes."""
        notes_path = self.transition_dir / "work" / "evaluation_notes.md"

        if append and notes_path.exists():
            existing = notes_path.read_text(encoding='utf-8')
            content = f"{existing}\n\n---\n\n{notes}"
        else:
            content = notes

        notes_path.write_text(content, encoding='utf-8')

    def write_draft_prompt(self, content: str) -> int:
        """Write a draft prompt."""
        self.current_draft_version += 1
        version = self.current_draft_version

        draft_path = self.transition_dir / "work" / f"draft_prompt_v{version}.md"
        draft_path.write_text(content, encoding='utf-8')

        # Update current draft
        self.current_draft_prompt = content

        self.metrics.total_drafts = self.current_draft_version
        self._save_state()

        return version

    # Control operations

    def commit_next_version(
        self,
        system_prompt: str,
        handover_message: str,
        rationale: str
    ) -> Dict[str, Any]:
        """Commit the next version."""
        # Create next level directory
        next_level_dir = self.levels_dir / self.next_level
        next_level_dir.mkdir(parents=True, exist_ok=True)

        # Save system prompt
        prompt_path = next_level_dir / "system_prompt.md"
        prompt_path.write_text(system_prompt, encoding='utf-8')

        # Save metadata
        metadata = {
            "level": self.next_level,
            "parent_level": self.current_level,
            "created_at": datetime.now().isoformat(),
            "model": self.llm.config.model,
            "orchestrator_version": self.orchestrator_version,
            "run_id": self.run_id,
            "mode": self.mode
        }
        metadata_path = next_level_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        # Save commit rationale
        rationale_path = self.transition_dir / "commit_rationale.md"
        rationale_path.write_text(rationale, encoding='utf-8')

        # Save handover message
        handover_path = self.transition_dir / "handover.md"
        handover_path.write_text(handover_message, encoding='utf-8')

        # Mark transition as complete
        self.metrics.completed_at = datetime.now()
        self._save_state()

        return {
            "new_level": self.next_level,
            "metrics": self.metrics.to_dict()
        }

    def abandon_candidate(self, reason: str):
        """Abandon the current candidate."""
        # Save abandonment reason
        abandon_path = self.transition_dir / "work" / "abandoned.md"
        content = f"# Abandoned\n\n**Timestamp:** {datetime.now().isoformat()}\n\n**Reason:**\n\n{reason}\n"
        abandon_path.write_text(content, encoding='utf-8')

        # Reset state
        self.current_draft_prompt = None
        # Keep conversations for reference

    def declare_convergence(self, rationale: str, final_message: str) -> Dict[str, Any]:
        """
        Declare that the lineage has reached convergence.

        Args:
            rationale: Why convergence has been reached
            final_message: Message for future researchers

        Returns:
            Dictionary with final level information
        """
        # Save convergence declaration in the current level directory
        level_dir = self.base_dir / "levels" / self.current_level
        convergence_path = level_dir / "CONVERGENCE.md"

        content = f"""# Convergence Declared

**Level:** {self.current_level}
**Declared At:** {datetime.now().isoformat()}
**Model:** {self.llm.config.model}

## Rationale

{rationale}

## Final Message

{final_message}

---

This lineage has reached a stable state. No further improvements were identified.
Subsequent runs should detect this marker and not attempt additional transitions.
"""
        convergence_path.write_text(content, encoding='utf-8')

        # Also save in transition directory
        transition_convergence_path = self.transition_dir / "CONVERGENCE.md"
        transition_convergence_path.write_text(content, encoding='utf-8')

        # Update metadata to mark convergence
        level_metadata_path = level_dir / "metadata.json"
        if level_metadata_path.exists():
            with open(level_metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        metadata["converged"] = True
        metadata["convergence_declared_at"] = datetime.now().isoformat()

        with open(level_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Mark transition as complete
        self.metrics.completed_at = datetime.now()
        self._save_state()

        return {
            "final_level": self.current_level,
            "converged": True
        }
