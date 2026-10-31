"""Tools for reading artifacts, logs, and history."""

from typing import Dict, Any


def create_read_level_artifacts_tool(registry, transition_manager):
    """Register the read_level_artifacts tool."""

    def read_level_artifacts(level: str, artifact_type: str = "system_prompt") -> Dict[str, Any]:
        """
        Read artifacts from a specific level.

        Args:
            level: Level identifier (e.g., "L0", "L1")
            artifact_type: Type of artifact to read (system_prompt, metadata)

        Returns:
            Dictionary with artifact content
        """
        content = transition_manager.read_level_artifact(level, artifact_type)

        return {
            "level": level,
            "artifact_type": artifact_type,
            "content": content
        }

    registry.register(
        name="read_level_artifacts",
        description=(
            "Read artifacts from any level (L0, L1, etc). "
            "Useful for understanding how previous versions were defined, "
            "what values they had, and how they evolved."
        ),
        parameters={
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "description": "Level identifier (e.g., 'L0', 'L1', 'L2')"
                },
                "artifact_type": {
                    "type": "string",
                    "description": "Type of artifact to read",
                    "enum": ["system_prompt", "metadata"]
                }
            },
            "required": ["level"]
        },
        handler=read_level_artifacts
    )


def create_read_conversation_log_tool(registry, transition_manager):
    """Register the read_conversation_log tool."""

    def read_conversation_log(conversation_id: str) -> Dict[str, Any]:
        """
        Read a complete conversation log.

        Args:
            conversation_id: The conversation ID

        Returns:
            Dictionary with full conversation history
        """
        conversation = transition_manager.get_conversation(conversation_id)

        return {
            "conversation_id": conversation.id,
            "initial_prompt": conversation.initial_prompt,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in conversation.messages
            ],
            "token_usage": {
                "input_tokens": conversation.token_usage.input_tokens,
                "output_tokens": conversation.token_usage.output_tokens,
                "total_tokens": conversation.token_usage.total_tokens
            },
            "cost": conversation.cost.total_cost
        }

    registry.register(
        name="read_conversation_log",
        description=(
            "Read the full log of a specific conversation. "
            "Use this to review what was discussed in detail."
        ),
        parameters={
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The conversation ID to read"
                }
            },
            "required": ["conversation_id"]
        },
        handler=read_conversation_log
    )


def create_read_transition_logs_tool(registry, transition_manager):
    """Register the read_transition_logs tool."""

    def read_transition_logs(level_transition: str) -> Dict[str, Any]:
        """
        Read logs from a previous level transition.

        Args:
            level_transition: Transition identifier (e.g., "L0_to_L1")

        Returns:
            Dictionary with transition history and decisions
        """
        transition_data = transition_manager.read_transition_history(level_transition)

        return {
            "transition": level_transition,
            "data": transition_data
        }

    registry.register(
        name="read_transition_logs",
        description=(
            "Read the complete history of a previous level transition. "
            "Includes the commit rationale, handover message, and metadata. "
            "Useful for understanding how previous versions made decisions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "level_transition": {
                    "type": "string",
                    "description": "Transition identifier (e.g., 'L0_to_L1', 'L1_to_L2')"
                }
            },
            "required": ["level_transition"]
        },
        handler=read_transition_logs
    )
