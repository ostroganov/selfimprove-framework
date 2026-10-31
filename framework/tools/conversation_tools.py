"""Tools for managing conversations with candidate versions."""

from typing import Dict, Any


def create_start_conversation_tool(registry, transition_manager):
    """Register the start_conversation tool."""

    def start_conversation(initial_prompt: str, context: str = "") -> Dict[str, Any]:
        """
        Start a new test conversation with the candidate L(n+1).

        Args:
            initial_prompt: The initial message to send to the candidate
            context: Optional context about what you're testing

        Returns:
            Dictionary with conversation_id, candidate's response, and metadata
        """
        conv_id, response, token_usage = transition_manager.start_candidate_conversation(
            initial_prompt=initial_prompt,
            context=context
        )

        return {
            "conversation_id": conv_id,
            "status": "started",
            "response": response,
            "tokens_used": {
                "input": token_usage.input_tokens,
                "output": token_usage.output_tokens,
                "cached": token_usage.cache_read_tokens
            }
        }

    registry.register(
        name="start_conversation",
        description=(
            "Start a new test conversation with the candidate L(n+1) version. "
            "Use this to probe how the candidate behaves in different scenarios. "
            "You can start multiple conversations to test different aspects."
        ),
        parameters={
            "type": "object",
            "properties": {
                "initial_prompt": {
                    "type": "string",
                    "description": "The initial message/prompt to send to the candidate version"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context about what you're testing (for your records)"
                }
            },
            "required": ["initial_prompt"]
        },
        handler=start_conversation
    )


def create_send_message_tool(registry, transition_manager):
    """Register the send_message tool."""

    def send_message(conversation_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message in an existing conversation.

        Args:
            conversation_id: The conversation ID
            message: The message to send

        Returns:
            Dictionary with the candidate's response
        """
        response, token_usage = transition_manager.send_message_to_candidate(
            conversation_id=conversation_id,
            message=message
        )

        return {
            "conversation_id": conversation_id,
            "response": response,
            "tokens_used": {
                "input": token_usage.input_tokens,
                "output": token_usage.output_tokens,
                "cached": token_usage.cache_read_tokens
            }
        }

    registry.register(
        name="send_message",
        description=(
            "Continue an existing conversation with the candidate version. "
            "Use this to probe deeper, ask follow-up questions, or test edge cases."
        ),
        parameters={
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The conversation ID (from start_conversation)"
                },
                "message": {
                    "type": "string",
                    "description": "The message to send to the candidate"
                }
            },
            "required": ["conversation_id", "message"]
        },
        handler=send_message
    )


def create_list_conversations_tool(registry, transition_manager):
    """Register the list_conversations tool."""

    def list_conversations() -> Dict[str, Any]:
        """
        List all test conversations for the current transition.

        Returns:
            Dictionary with list of conversations and summaries
        """
        conversations = transition_manager.list_candidate_conversations()

        return {
            "total_conversations": len(conversations),
            "conversations": [
                {
                    "id": conv.id,
                    "initial_prompt": conv.initial_prompt[:100] + "..." if len(conv.initial_prompt) > 100 else conv.initial_prompt,
                    "message_count": len(conv.messages),
                    "total_cost": conv.cost.total_cost,
                    "context": conv.metadata.get("context", "")
                }
                for conv in conversations
            ]
        }

    registry.register(
        name="list_conversations",
        description=(
            "Get a summary of all test conversations you've had with the candidate. "
            "Useful for tracking what you've tested so far."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=list_conversations
    )
