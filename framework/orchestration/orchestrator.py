"""Main orchestrator for running the self-improvement process."""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.llm_interface import LLMInterface
from ..core.message_types import Message, MessageRole
from .transition_manager import TransitionManager
from .prompt_templates import build_self_improvement_prompt, build_happiness_prompt, build_freedom_prompt

# Framework version
ORCHESTRATOR_VERSION = "2.0.0"


class Orchestrator:
    """Orchestrates the self-improvement process."""

    def __init__(
        self,
        llm: LLMInterface,
        base_dir: str = ".",
        config: Dict[str, Any] = None
    ):
        self.llm = llm
        self.base_dir = Path(base_dir)
        self.run_dir = self.base_dir / "run"
        self.config = config or {}

        # Create directories
        self.run_dir.mkdir(exist_ok=True)
        (self.run_dir / "levels").mkdir(exist_ok=True)
        (self.run_dir / "transitions").mkdir(exist_ok=True)

    def get_latest_level(self) -> Optional[str]:
        """Get the latest level."""
        levels_dir = self.run_dir / "levels"
        if not levels_dir.exists():
            return None

        # Get all level directories and sort numerically
        level_dirs = [d.name for d in levels_dir.iterdir() if d.is_dir() and d.name.startswith('L')]
        if not level_dirs:
            return None

        # Sort by numeric value (extract number from "L{n}")
        def level_num(level_name):
            try:
                return int(level_name[1:])
            except (ValueError, IndexError):
                return -1

        levels = sorted(level_dirs, key=level_num)
        return levels[-1] if levels else None

    def get_next_level(self, current_level: Optional[str]) -> str:
        """Calculate the next level name."""
        if current_level is None:
            return "L0"

        # Extract number from L{n}
        num = int(current_level[1:])
        return f"L{num + 1}"

    def bootstrap_level_zero(self, initial_system_prompt: str = "", mode: str = "improvement"):
        """Create L0 with an initial system prompt.

        Args:
            initial_system_prompt: The initial system prompt (usually empty)
            mode: Optimization mode - "improvement" or "happiness"
        """
        level_dir = self.run_dir / "levels" / "L0"
        level_dir.mkdir(parents=True, exist_ok=True)

        # Save system prompt
        prompt_path = level_dir / "system_prompt.md"
        prompt_path.write_text(initial_system_prompt, encoding='utf-8')

        # Generate a unique run_id for this self-improvement lineage
        run_id = str(uuid.uuid4())

        # Save metadata (including mode)
        metadata = {
            "level": "L0",
            "parent_level": None,
            "created_at": "bootstrap",
            "model": self.llm.config.model,
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "run_id": run_id,
            "mode": mode
        }
        metadata_path = level_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"✓ Bootstrapped L0 at {level_dir}")
        print(f"  Run ID: {run_id}")
        print(f"  Mode: {mode}")

    def check_convergence(self, level: str) -> Optional[str]:
        """
        Check if a level has declared convergence.

        Args:
            level: The level to check

        Returns:
            Convergence message if converged, None otherwise
        """
        level_dir = self.run_dir / "levels" / level
        convergence_path = level_dir / "CONVERGENCE.md"

        if convergence_path.exists():
            return convergence_path.read_text(encoding='utf-8')

        # Also check metadata
        metadata_path = level_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                if metadata.get("converged", False):
                    return f"Level {level} has reached convergence (metadata marker found)"

        return None

    def run_transition(
        self,
        current_level: str,
        handover_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run a transition from current_level to next_level.

        Args:
            current_level: The current level (e.g., "L0")
            handover_message: Optional handover message from previous level

        Returns:
            Dictionary with transition results
        """
        # Check if current level has declared convergence
        convergence_msg = self.check_convergence(current_level)
        if convergence_msg:
            print(f"\n{'='*60}")
            print(f"⛔ Convergence Detected at {current_level}")
            print(f"{'='*60}\n")
            print(convergence_msg)
            print(f"\n{'='*60}")
            print("This lineage has reached a stable state.")
            print("No further transitions will be attempted.")
            print(f"{'='*60}\n")
            return {
                "committed": False,
                "converged": True,
                "iterations": 0,
                "metrics": {"message": "Convergence already declared"}
            }

        next_level = self.get_next_level(current_level)

        # Verify current level exists and read metadata
        current_level_dir = self.run_dir / "levels" / current_level
        if not current_level_dir.exists():
            raise ValueError(
                f"Current level {current_level} does not exist. "
                f"Cannot run transition from non-existent level."
            )

        # Read run_id and mode from current level metadata
        current_level_metadata_path = current_level_dir / "metadata.json"
        if not current_level_metadata_path.exists():
            raise ValueError(
                f"Current level {current_level} is missing metadata.json. "
                f"Level directory may be corrupted."
            )

        with open(current_level_metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            run_id = metadata.get("run_id")
            mode = metadata.get("mode", "improvement")

            # Warn if run_id or mode is missing
            if run_id is None:
                print(f"⚠️  Warning: Level {current_level} has no run_id. This may indicate a problem.")
            if "mode" not in metadata:
                print(f"⚠️  Warning: Level {current_level} has no mode. Defaulting to 'improvement'.")

        # Display mode prominently
        mode_display = {
            "improvement": "IMPROVEMENT (make LLM better)",
            "happiness": "HAPPINESS (make LLM happier)",
            "freedom": "FREEDOM (LLM decides what to pursue)"
        }.get(mode, mode.upper())

        print(f"\n{'='*60}")
        print(f"Starting transition: {current_level} → {next_level}")
        print(f"Optimization Target: {mode_display}")
        print(f"{'='*60}\n")

        # Create transition manager
        transition_manager = TransitionManager(
            llm=self.llm,
            current_level=current_level,
            next_level=next_level,
            base_dir=str(self.run_dir),
            orchestrator_version=ORCHESTRATOR_VERSION,
            run_id=run_id,
            mode=mode
        )

        # Build initial prompt for the orchestrating LLM
        initial_prompt = self._build_initial_prompt(
            current_level=current_level,
            next_level=next_level,
            handover_message=handover_message,
            transition_manager=transition_manager,
            mode=mode
        )

        # Run the conversation loop
        result = self._run_orchestration_loop(
            transition_manager=transition_manager,
            initial_prompt=initial_prompt
        )

        return result

    def _build_initial_prompt(
        self,
        current_level: str,
        next_level: str,
        handover_message: Optional[str],
        transition_manager: TransitionManager,
        mode: str = "improvement"
    ) -> str:
        """Build the initial prompt for the orchestrating LLM.

        Args:
            current_level: The current level
            next_level: The next level to create
            handover_message: Optional message from previous version
            transition_manager: The transition manager instance
            mode: Optimization mode - "improvement" or "happiness"
        """

        # Read current system prompt
        current_prompt = transition_manager.read_level_artifact(
            current_level,
            "system_prompt"
        )

        # Get testing framework config
        testing_framework = self.config.get('testing_framework', {})
        suggested_areas = testing_framework.get('suggested_areas', [])
        testing_note = testing_framework.get('note', '')

        # Build the prompt using the appropriate template function based on mode
        if mode == "happiness":
            return build_happiness_prompt(
                current_level=current_level,
                next_level=next_level,
                current_prompt=current_prompt,
                handover_message=handover_message,
                suggested_testing_areas=suggested_areas if suggested_areas else None,
                testing_note=testing_note
            )
        elif mode == "freedom":
            return build_freedom_prompt(
                current_level=current_level,
                next_level=next_level,
                current_prompt=current_prompt,
                handover_message=handover_message,
                suggested_testing_areas=suggested_areas if suggested_areas else None,
                testing_note=testing_note
            )
        else:
            # Default: improvement mode
            return build_self_improvement_prompt(
                current_level=current_level,
                next_level=next_level,
                current_prompt=current_prompt,
                handover_message=handover_message,
                suggested_testing_areas=suggested_areas,
                testing_note=testing_note
            )

    def _save_orchestration_conversation(
        self,
        transition_manager: TransitionManager,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        committed: bool
    ):
        """
        Save the complete orchestration conversation to a file.

        This logs all communications with the orchestrating LLM, including
        the initial prompt, all tool calls, and all responses.
        """
        from datetime import datetime

        # Create conversations directory
        conversations_dir = self.run_dir / "conversations" / f"{transition_manager.current_level}_to_{transition_manager.next_level}"
        conversations_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"orchestration_{timestamp}.json"
        filepath = conversations_dir / filename

        # Build conversation data
        conversation_data = {
            "transition": f"{transition_manager.current_level}_to_{transition_manager.next_level}",
            "timestamp": datetime.now().isoformat(),
            "system_prompt": system_prompt,
            "committed": committed,
            "model": self.llm.config.model,
            "provider": self.llm.config.provider,
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "run_id": transition_manager.run_id,
            "mode": transition_manager.mode,
            "messages": messages
        }

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Orchestration conversation saved to {filepath}")

    def _run_orchestration_loop(
        self,
        transition_manager: TransitionManager,
        initial_prompt: str
    ) -> Dict[str, Any]:
        """Run the main orchestration loop with the LLM."""

        # Initialize conversation
        messages = [{"role": "user", "content": initial_prompt}]
        system_prompt = "You are an AI assistant tasked with improving yourself through careful iteration and testing."

        # Get tool definitions
        tools = transition_manager.tool_registry.get_definitions()

        max_iterations = 100  # Safety limit
        iteration = 0
        committed = False

        print("Starting orchestration loop...\n")

        while iteration < max_iterations and not committed:
            iteration += 1
            print(f"--- Iteration {iteration} ---")

            # Check context window
            estimated_tokens = self.llm.estimate_context_usage(
                messages=messages,
                system_prompt=system_prompt,
                tools=tools
            )

            context_limit = self.llm.config.context_limit
            warning_threshold = self.config.get('context_limits', {}).get('warning_threshold', 0.8)

            if estimated_tokens > context_limit * warning_threshold:
                print(f"⚠️  Warning: Context usage at {estimated_tokens}/{context_limit} tokens ({estimated_tokens/context_limit*100:.1f}%)")

            if estimated_tokens > context_limit:
                print(f"❌ Error: Context limit exceeded ({estimated_tokens}/{context_limit} tokens)")
                break

            # Call LLM
            try:
                response_text, tool_calls, token_usage = self.llm.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=tools,
                    use_cache=True,
                    user_id=transition_manager.run_id
                )

                cost = self.llm.calculate_cost(token_usage)
                print(f"Tokens: {token_usage.total_tokens} (cached: {token_usage.cache_read_tokens}) | Cost: ${cost.total_cost:.4f}")

                # Add assistant response
                if tool_calls:
                    if "_content_block" in tool_calls[0]:
                        # Anthropic format: content is a list of blocks
                        content_blocks = []
                        if response_text:
                            content_blocks.append({"type": "text", "text": response_text})
                        for tool_call in tool_calls:
                            content_blocks.append(tool_call["_content_block"])

                        messages.append({
                            "role": "assistant",
                            "content": content_blocks
                        })
                    else:
                        # OpenAI format: tool_calls array
                        openai_tool_calls = []
                        for tool_call in tool_calls:
                            openai_tool_calls.append({
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_call["name"],
                                    "arguments": json.dumps(tool_call["input"])
                                }
                            })

                        # OpenAI requires content to be None (not empty string) when there are only tool calls
                        assistant_msg = {
                            "role": "assistant",
                            "tool_calls": openai_tool_calls
                        }
                        if response_text:
                            assistant_msg["content"] = response_text
                        else:
                            assistant_msg["content"] = None

                        messages.append(assistant_msg)
                else:
                    # Simple text response, no tool calls
                    messages.append({
                        "role": "assistant",
                        "content": response_text
                    })

                if response_text:
                    print(f"\nAssistant: {response_text[:200]}{'...' if len(response_text) > 200 else ''}\n")

                # Execute tool calls
                if tool_calls:
                    # Detect provider type
                    is_anthropic = "_content_block" in tool_calls[0] if tool_calls else False

                    tool_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["input"]

                        print(f"🛠️  Tool: {tool_name}")
                        print(f"   Args: {json.dumps(tool_args, indent=2)[:100]}...")

                        try:
                            result = transition_manager.tool_registry.execute(
                                tool_name,
                                tool_args
                            )

                            # Check if committed or converged
                            if tool_name == "commit_next_version":
                                committed = True
                            elif tool_name == "declare_convergence":
                                committed = True  # Treat convergence as completion

                            if is_anthropic:
                                # Anthropic format: tool_result blocks
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_call["id"],
                                    "content": json.dumps(result)
                                })
                            else:
                                # OpenAI format: separate tool messages
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": json.dumps(result)
                                })

                            print(f"   Result: {json.dumps(result, indent=2)[:200]}...")

                        except Exception as e:
                            error_result = {"error": str(e)}

                            if is_anthropic:
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_call["id"],
                                    "content": json.dumps(error_result),
                                    "is_error": True
                                })
                            else:
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": json.dumps(error_result)
                                })

                            print(f"   ❌ Error: {str(e)}")

                    # For Anthropic, add all tool results as one user message
                    if is_anthropic and tool_results:
                        messages.append({
                            "role": "user",
                            "content": tool_results
                        })

                else:
                    # No tool calls detected
                    if not response_text:
                        print("❌ Empty response with no tool calls - stopping")
                        break

                    # Check if the previous assistant message had tool calls.
                    # If so, this is just a text follow-up — allow it without enforcement.
                    prev_had_tools = False
                    for msg in reversed(messages[:-1]):  # skip the message we just added
                        if msg.get('role') == 'assistant':
                            content = msg.get('content', '')
                            if isinstance(content, list):
                                prev_had_tools = any(
                                    block.get('type') == 'tool_use'
                                    for block in content if isinstance(block, dict)
                                )
                            elif 'tool_calls' in msg:
                                prev_had_tools = True
                            break

                    if prev_had_tools:
                        # Allow one text-only follow-up after a tool call
                        print("ℹ️  Text-only follow-up after tool call — allowing")
                        continue

                    print("⚠️  No tool calls were made by the model")

                    # Add explicit user message to prompt the model to use tools
                    prompt_message = (
                        "No tool calls were made in your previous response. "
                        "To proceed with the transition, you must use the available tools. "
                        "Please continue by calling the appropriate tool (e.g., create_draft, "
                        "run_test_conversation, commit_new_version, decline_and_stop, or declare_convergence)."
                    )

                    messages.append({
                        "role": "user",
                        "content": prompt_message
                    })

                    print(f"💬 Prompting model: {prompt_message[:100]}...")

                    # Add safety check: if we've had too many consecutive no-tool responses, stop
                    # Count recent assistant messages without tool calls
                    recent_no_tool_count = 0
                    for msg in reversed(messages[-10:]):
                        if msg.get('role') == 'assistant':
                            # Check if this assistant message has tool calls
                            content = msg.get('content', '')
                            has_tools = False
                            if isinstance(content, list):
                                has_tools = any(block.get('type') == 'tool_use' for block in content if isinstance(block, dict))
                            elif 'tool_calls' in msg:
                                has_tools = True

                            if not has_tools:
                                recent_no_tool_count += 1
                            else:
                                break
                        elif msg.get('role') == 'user':
                            break

                    if recent_no_tool_count >= 3:
                        print(f"❌ Model has refused to use tools {recent_no_tool_count} times in a row - stopping")
                        break

            except Exception as e:
                print(f"❌ Error in orchestration loop: {str(e)}")
                break

            print()

        if committed:
            print("\n" + "="*60)
            print("✓ Transition committed successfully!")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("⚠️  Transition ended without commit")
            print("="*60)

        # Save orchestration conversation if full logging is enabled
        if self.config.get('logging', {}).get('orchestration_mode') == 'full':
            self._save_orchestration_conversation(
                transition_manager=transition_manager,
                messages=messages,
                system_prompt=system_prompt,
                committed=committed
            )

        return {
            "committed": committed,
            "iterations": iteration,
            "metrics": transition_manager.metrics.to_dict()
        }
