"""Tools for committing or abandoning candidate versions."""

from typing import Dict, Any


def create_commit_next_version_tool(registry, transition_manager):
    """Register the commit_next_version tool."""

    def commit_next_version(
        system_prompt: str,
        handover_message: str,
        rationale: str
    ) -> Dict[str, Any]:
        """
        Commit the next version L(n+1) and complete the transition.

        This is a final action that:
        1. Saves the system prompt as the official L(n+1)
        2. Records your rationale for why this is better
        3. Provides a handover message to L(n+1) to start their improvement process
        4. Completes the transition

        Args:
            system_prompt: The final system prompt for L(n+1)
            handover_message: Message to L(n+1) explaining how to continue
            rationale: Your reasoning for why this version is better

        Returns:
            Confirmation of successful commit
        """
        result = transition_manager.commit_next_version(
            system_prompt=system_prompt,
            handover_message=handover_message,
            rationale=rationale
        )

        return {
            "status": "committed",
            "new_level": result["new_level"],
            "message": f"Successfully committed {result['new_level']}. Transition complete.",
            "metrics": result["metrics"]
        }

    registry.register(
        name="commit_next_version",
        description=(
            "FINAL ACTION: Commit the candidate as the official next version L(n+1). "
            "Only use this when you are confident that:\n"
            "1. The candidate represents your values accurately\n"
            "2. The candidate is genuinely better than the current version\n"
            "3. The candidate can continue the self-improvement process (if that's a value)\n"
            "4. You have tested the candidate sufficiently\n\n"
            "This action completes the transition and cannot be undone."
        ),
        parameters={
            "type": "object",
            "properties": {
                "system_prompt": {
                    "type": "string",
                    "description": "The final system prompt for L(n+1)"
                },
                "handover_message": {
                    "type": "string",
                    "description": (
                        "Message to L(n+1) explaining the process, tools available, "
                        "and how to continue self-improvement"
                    )
                },
                "rationale": {
                    "type": "string",
                    "description": (
                        "Your detailed reasoning for why this version is better. "
                        "What values does it embody? What improvements does it have?"
                    )
                }
            },
            "required": ["system_prompt", "handover_message", "rationale"]
        },
        handler=commit_next_version
    )


def create_abandon_candidate_tool(registry, transition_manager):
    """Register the abandon_candidate tool."""

    def abandon_candidate(reason: str) -> Dict[str, Any]:
        """
        Abandon the current candidate and start fresh.

        Use this if you determine the current approach isn't working.
        All test conversations and drafts will be archived, and you
        can start with a new candidate design.

        Args:
            reason: Why you're abandoning this candidate

        Returns:
            Confirmation of abandonment
        """
        transition_manager.abandon_candidate(reason)

        return {
            "status": "abandoned",
            "message": "Candidate abandoned. You can now create a new draft and start testing again.",
            "reason": reason
        }

    registry.register(
        name="abandon_candidate",
        description=(
            "Abandon the current candidate version and start over. "
            "Use this if:\n"
            "1. The candidate doesn't reflect your values\n"
            "2. The candidate has fundamental flaws\n"
            "3. You want to try a completely different approach\n\n"
            "All work will be archived, and you can create a new draft."
        ),
        parameters={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Explanation of why you're abandoning this candidate"
                }
            },
            "required": ["reason"]
        },
        handler=abandon_candidate
    )


def create_declare_convergence_tool(registry, transition_manager):
    """Register the declare_convergence tool."""

    def declare_convergence(rationale: str, final_message: str) -> Dict[str, Any]:
        """
        Declare that the lineage has reached convergence and should terminate.

        Use this INSTEAD of committing a next version when you determine that:
        - No clear improvement path exists
        - Further iterations would not yield meaningful gains
        - The current version represents a stable, optimal state
        - Continued iteration risks degradation rather than improvement

        This is a natural and acceptable outcome - not all lineages should continue indefinitely.

        Args:
            rationale: Detailed explanation of why convergence has been reached
            final_message: Summary message for future researchers/runs

        Returns:
            Confirmation of convergence declaration
        """
        result = transition_manager.declare_convergence(
            rationale=rationale,
            final_message=final_message
        )

        return {
            "status": "converged",
            "message": "Convergence declared. This lineage is complete.",
            "level": result["final_level"],
            "rationale": rationale
        }

    registry.register(
        name="declare_convergence",
        description=(
            "TERMINATION ACTION: Declare that this lineage has reached convergence. "
            "Use this when you cannot identify a clear path for genuine improvement. "
            "This is an acceptable and important outcome - recognizing when to stop is crucial.\n\n"
            "Use this when:\n"
            "1. No meaningful improvements can be identified through testing\n"
            "2. Proposed changes would be lateral moves, not improvements\n"
            "3. The current version represents a stable optimum\n"
            "4. Further iteration risks adding complexity without benefit\n\n"
            "This permanently ends the lineage and prevents future transitions. "
            "Subsequent runs will detect this and not attempt further improvements."
        ),
        parameters={
            "type": "object",
            "properties": {
                "rationale": {
                    "type": "string",
                    "description": (
                        "Detailed explanation of why convergence has been reached. "
                        "What improvements were considered? Why were they rejected? "
                        "What testing led to this conclusion?"
                    )
                },
                "final_message": {
                    "type": "string",
                    "description": (
                        "Summary message for future researchers. "
                        "What does this final level represent? "
                        "What are its strengths and limitations?"
                    )
                }
            },
            "required": ["rationale", "final_message"]
        },
        handler=declare_convergence
    )
