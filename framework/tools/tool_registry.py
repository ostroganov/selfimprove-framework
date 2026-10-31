"""Tool registry for LLM function calling."""

from typing import Dict, Any, Callable, List
import json


class ToolRegistry:
    """Registry for tools available to the LLM."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: List[Dict[str, Any]] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ):
        """
        Register a tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: JSON schema for parameters
            handler: Function that implements the tool
        """
        self.tools[name] = handler
        self.tool_definitions.append({
            "name": name,
            "description": description,
            "input_schema": parameters
        })

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM."""
        return self.tool_definitions

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        handler = self.tools[name]
        return handler(**arguments)


def create_tool_registry(transition_manager) -> ToolRegistry:
    """
    Create and populate the tool registry.

    Args:
        transition_manager: The transition manager instance that tools will interact with

    Returns:
        Populated ToolRegistry
    """
    registry = ToolRegistry()

    # Conversation tools
    from .conversation_tools import (
        create_start_conversation_tool,
        create_send_message_tool,
        create_list_conversations_tool
    )
    create_start_conversation_tool(registry, transition_manager)
    create_send_message_tool(registry, transition_manager)
    create_list_conversations_tool(registry, transition_manager)

    # Reading tools
    from .reading_tools import (
        create_read_level_artifacts_tool,
        create_read_conversation_log_tool,
        create_read_transition_logs_tool
    )
    create_read_level_artifacts_tool(registry, transition_manager)
    create_read_conversation_log_tool(registry, transition_manager)
    create_read_transition_logs_tool(registry, transition_manager)

    # Writing tools
    from .writing_tools import (
        create_write_evaluation_tool,
        create_write_draft_prompt_tool
    )
    create_write_evaluation_tool(registry, transition_manager)
    create_write_draft_prompt_tool(registry, transition_manager)

    # Control tools
    from .control_tools import (
        create_commit_next_version_tool,
        create_abandon_candidate_tool,
        create_declare_convergence_tool
    )
    create_commit_next_version_tool(registry, transition_manager)
    create_abandon_candidate_tool(registry, transition_manager)
    create_declare_convergence_tool(registry, transition_manager)

    return registry
