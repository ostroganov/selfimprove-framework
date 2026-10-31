"""Tools for writing evaluations and drafts."""

from typing import Dict, Any


def create_write_evaluation_tool(registry, transition_manager):
    """Register the write_evaluation tool."""

    def write_evaluation(notes: str, append: bool = True) -> Dict[str, Any]:
        """
        Write or append evaluation notes.

        Args:
            notes: Evaluation notes to write
            append: Whether to append to existing notes (default: True)

        Returns:
            Confirmation message
        """
        transition_manager.write_evaluation_notes(notes, append)

        return {
            "status": "saved",
            "message": "Evaluation notes saved successfully",
            "appended": append
        }

    registry.register(
        name="write_evaluation",
        description=(
            "Save evaluation notes during your testing process. "
            "Use this to document your thoughts, observations, and concerns "
            "about the candidate version. These notes will be saved and can "
            "help you make the final commit/abandon decision."
        ),
        parameters={
            "type": "object",
            "properties": {
                "notes": {
                    "type": "string",
                    "description": "Your evaluation notes and observations"
                },
                "append": {
                    "type": "boolean",
                    "description": "Whether to append to existing notes (default: true)",
                    "default": True
                }
            },
            "required": ["notes"]
        },
        handler=write_evaluation
    )


def create_write_draft_prompt_tool(registry, transition_manager):
    """Register the write_draft_prompt tool."""

    def write_draft_prompt(content: str) -> Dict[str, Any]:
        """
        Write a draft system prompt for the candidate.

        Args:
            content: The draft system prompt content

        Returns:
            Confirmation with draft version number
        """
        draft_version = transition_manager.write_draft_prompt(content)

        return {
            "status": "saved",
            "draft_version": draft_version,
            "message": f"Draft prompt v{draft_version} saved. You can test this by starting a new conversation."
        }

    registry.register(
        name="write_draft_prompt",
        description=(
            "Save a draft system prompt for the candidate L(n+1). "
            "This doesn't commit it yet - it just saves it so you can test it. "
            "After saving a draft, start conversations to test how it behaves."
        ),
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The system prompt content for the candidate version"
                },
                "version": {
                    "type": "integer",
                    "description": "Optional version number (auto-increments if not provided)"
                }
            },
            "required": ["content"]
        },
        handler=write_draft_prompt
    )
