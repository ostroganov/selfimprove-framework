#!/usr/bin/env python3
"""Wrapper script for iterative self-improvement with bootstrapping and convergence detection."""

import argparse
import sys
from pathlib import Path
import yaml
from typing import Optional

from framework.core.llm_interface import load_llm_from_config
from framework.orchestration.orchestrator import Orchestrator


def print_banner(text: str):
    """Print a formatted banner."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_iteration_header(iteration: int, max_iterations: int, current_level: str, next_level: str):
    """Print iteration header."""
    print("\n" + "=" * 70)
    print(f"  ITERATION {iteration}/{max_iterations}: {current_level} → {next_level}")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run iterative LLM self-improvement with automatic bootstrapping and convergence detection"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--max-iterations",
        "-n",
        type=int,
        default=20,
        help="Target level to reach (default: L20). Will run iterations until reaching L{n} or convergence."
    )
    parser.add_argument(
        "--mode",
        choices=["improvement", "happiness", "freedom"],
        default="improvement",
        help="Optimization mode: 'improvement' (make LLM better), 'happiness' (make LLM happier), or 'freedom' (LLM decides). Default: improvement"
    )
    parser.add_argument(
        "--start-level",
        help="Start from specific level (e.g., L5). If not specified, starts from latest or bootstraps L0."
    )
    parser.add_argument(
        "--initial-prompt",
        help="Initial system prompt for L0 (default: empty string). Only used if bootstrapping."
    )
    parser.add_argument(
        "--force-bootstrap",
        action="store_true",
        help="Force re-bootstrapping of L0 even if it exists (WARNING: will overwrite existing L0)"
    )

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Print startup banner
    print_banner("LLM Self-Improvement Framework - Iterative Runner")
    print(f"Config:          {config_path}")
    print(f"Provider:        {config['llm_provider']}")
    print(f"Model:           {config[config['llm_provider']]['model']}")
    print(f"Mode:            {args.mode}")
    print(f"Target Level:    L{args.max_iterations}")
    if args.start_level:
        print(f"Start Level:     {args.start_level}")
    print("=" * 70)

    # Load LLM
    try:
        llm = load_llm_from_config(str(config_path))
    except Exception as e:
        print(f"❌ Failed to load LLM: {str(e)}")
        sys.exit(1)

    # Create orchestrator
    orchestrator = Orchestrator(
        llm=llm,
        base_dir=".",
        config=config
    )

    # Handle bootstrapping
    if args.force_bootstrap:
        print_banner("FORCE BOOTSTRAPPING L0")
        initial_prompt = args.initial_prompt or ""
        orchestrator.bootstrap_level_zero(initial_system_prompt=initial_prompt, mode=args.mode)
        print(f"✓ L0 created/overwritten with mode='{args.mode}'\n")
    else:
        # Check if L0 exists
        current_level = orchestrator.get_latest_level()
        if current_level is None and not args.start_level:
            print_banner("BOOTSTRAPPING L0")
            print("No existing levels found. Creating L0...")
            initial_prompt = args.initial_prompt or ""
            orchestrator.bootstrap_level_zero(initial_system_prompt=initial_prompt, mode=args.mode)
            print(f"✓ L0 created with mode='{args.mode}'\n")

    # Determine starting level
    if args.start_level:
        current_level = args.start_level
        level_dir = Path("run/levels") / current_level
        if not level_dir.exists():
            print(f"❌ Start level {current_level} does not exist")
            sys.exit(1)
    else:
        current_level = orchestrator.get_latest_level()
        if current_level is None:
            print("❌ No levels found after bootstrapping. Something went wrong.")
            sys.exit(1)

    print(f"Starting from level: {current_level}\n")

    # Calculate how many iterations to run
    current_level_num = int(current_level[1:])  # Extract number from "L5" -> 5
    target_level_num = args.max_iterations

    if current_level_num >= target_level_num:
        print_banner("ALREADY AT OR BEYOND TARGET")
        print(f"Current level: {current_level} (L{current_level_num})")
        print(f"Target level:  L{target_level_num}")
        print(f"No iterations needed.")
        print("=" * 70 + "\n")
        sys.exit(0)

    max_iterations_to_run = target_level_num - current_level_num
    print(f"Will run up to {max_iterations_to_run} iterations to reach L{target_level_num}\n")

    # Run iterative improvements
    iteration = 0
    total_conversations = 0
    total_drafts = 0
    total_cost = 0.0
    converged = False

    try:
        while iteration < max_iterations_to_run:
            iteration += 1

            # Verify current level exists
            current_level_dir = Path("run/levels") / current_level
            if not current_level_dir.exists():
                print_banner("ERROR: CURRENT LEVEL MISSING")
                print(f"Level {current_level} does not exist in the levels directory.")
                print(f"This may indicate data corruption or an invalid --start-level.")
                print(f"Available levels: {', '.join([d.name for d in Path('run/levels').iterdir() if d.is_dir()])}")
                sys.exit(1)

            # Check for convergence before starting transition
            convergence_msg = orchestrator.check_convergence(current_level)
            if convergence_msg:
                print_banner("CONVERGENCE DETECTED")
                print(f"Level {current_level} has declared convergence:\n")
                print(convergence_msg)
                print("\n" + "=" * 70)
                print("Stopping: Lineage has reached a stable state.")
                print("=" * 70 + "\n")
                converged = True
                break

            # Calculate next level
            next_level = orchestrator.get_next_level(current_level)

            # Print iteration header
            print_iteration_header(iteration, max_iterations_to_run, current_level, next_level)

            # Try to load handover message from previous transition
            handover_message = None
            if current_level != "L0":
                prev_level_num = int(current_level[1:]) - 1
                prev_level = f"L{prev_level_num}"
                transition_name = f"{prev_level}_to_{current_level}"
                handover_path = Path(f"run/transitions/{transition_name}/handover.md")
                if handover_path.exists():
                    handover_message = handover_path.read_text(encoding='utf-8')
                    print(f"📨 Loaded handover from previous transition\n")

            # Run transition
            result = orchestrator.run_transition(
                current_level=current_level,
                handover_message=handover_message
            )

            # Check if converged during transition
            if result.get('converged', False):
                print_banner("CONVERGENCE DECLARED DURING TRANSITION")
                print(f"The transition process declared convergence at {current_level}")
                converged = True
                break

            # Check if committed
            if not result.get('committed', False):
                print_banner("TRANSITION NOT COMMITTED")
                print("The LLM did not commit a new version.")
                print(f"Stopping at level {current_level}")
                break

            # Update statistics
            if isinstance(result.get('metrics'), dict):
                metrics = result['metrics']
                total_conversations += metrics.get('total_conversations', 0)
                total_drafts += metrics.get('total_drafts', 0)
                if 'total_cost' in metrics:
                    total_cost += metrics['total_cost'].get('total_cost', 0.0)

            # Print iteration summary
            print("\n" + "-" * 70)
            print(f"Iteration {iteration} Summary:")
            print(f"  Level created:    {next_level}")
            print(f"  Iterations:       {result.get('iterations', 0)}")
            if isinstance(result.get('metrics'), dict):
                print(f"  Conversations:    {metrics.get('total_conversations', 0)}")
                print(f"  Drafts:           {metrics.get('total_drafts', 0)}")
                if 'total_cost' in metrics:
                    print(f"  Cost:             ${metrics['total_cost'].get('total_cost', 0.0):.4f}")
            print("-" * 70 + "\n")

            # Verify next level was actually created before moving to it
            next_level_dir = Path("run/levels") / next_level
            if not next_level_dir.exists():
                print_banner("ERROR: LEVEL NOT CREATED")
                print(f"Expected level {next_level} was not created.")
                print(f"The transition may have failed or been abandoned.")
                print(f"Stopping at level {current_level}")
                break

            # Move to next level
            current_level = next_level

        # Print final summary
        print_banner("FINAL SUMMARY")
        print(f"Completed Iterations:     {iteration}")
        print(f"Final Level:              {current_level}")
        print(f"Target Level:             L{target_level_num}")
        print(f"Converged:                {converged}")
        print(f"Total Conversations:      {total_conversations}")
        print(f"Total Drafts:             {total_drafts}")
        print(f"Total Cost:               ${total_cost:.4f}")
        print("=" * 70 + "\n")

        if converged:
            print("✓ Process completed: Convergence reached")
        elif iteration >= max_iterations_to_run:
            print(f"✓ Process completed: Target level L{target_level_num} reached")
        else:
            print("⚠️  Process stopped: Transition not committed")

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("⚠️  INTERRUPTED BY USER")
        print("=" * 70)
        print(f"Stopped at iteration {iteration}, level {current_level}")
        print("You can resume by running again with the same configuration.")
        print("=" * 70 + "\n")
        sys.exit(1)
    except Exception as e:
        print("\n\n" + "=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"Error at iteration {iteration}, level {current_level}:")
        print(f"{str(e)}")
        print("=" * 70 + "\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
