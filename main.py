#!/usr/bin/env python3
"""Main entry point for the self-improvement framework."""

import argparse
import sys
from pathlib import Path
import yaml

from framework.core.llm_interface import load_llm_from_config
from framework.orchestration.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="LLM Self-Improvement Framework"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Bootstrap L0 with an empty system prompt"
    )
    parser.add_argument(
        "--mode",
        choices=["improvement", "happiness", "freedom"],
        default="improvement",
        help="Optimization mode: 'improvement' (make LLM better), 'happiness' (make LLM happier), or 'freedom' (LLM decides). Default: improvement"
    )
    parser.add_argument(
        "--level",
        help="Specific level to start from (e.g., L0, L1). If not specified, uses latest level."
    )
    parser.add_argument(
        "--handover",
        help="Path to handover message file (for manual transitions)"
    )

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print("="*60)
    print("LLM Self-Improvement Framework")
    print("="*60)
    print(f"Config: {config_path}")
    print(f"Provider: {config['llm_provider']}")
    print(f"Model: {config[config['llm_provider']]['model']}")
    print("="*60)
    print()

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

    # Bootstrap if requested
    if args.bootstrap:
        mode_display = {
            "improvement": "IMPROVEMENT (make LLM better)",
            "happiness": "HAPPINESS (make LLM happier)",
            "freedom": "FREEDOM (LLM decides what to pursue)"
        }.get(args.mode, args.mode.upper())
        print(f"Bootstrapping L0 in {args.mode.upper()} mode...")
        print(f"Optimization Target: {mode_display}")
        orchestrator.bootstrap_level_zero(initial_system_prompt="", mode=args.mode)
        print(f"\n✓ L0 created with mode='{args.mode}'. Run without --bootstrap to start the first transition.\n")
        return

    # Determine current level
    if args.level:
        current_level = args.level
    else:
        current_level = orchestrator.get_latest_level()

    if current_level is None:
        print("❌ No levels found. Run with --bootstrap to create L0.")
        sys.exit(1)

    # Load handover message if provided
    handover_message = None
    if args.handover:
        handover_path = Path(args.handover)
        if handover_path.exists():
            handover_message = handover_path.read_text(encoding='utf-8')
        else:
            print(f"⚠️  Handover file not found: {handover_path}")

    # If there's no handover message, try to load from previous transition
    if handover_message is None and current_level != "L0":
        prev_level = f"L{int(current_level[1:]) - 1}"
        transition_name = f"{prev_level}_to_{current_level}"
        handover_path = Path(f"run/transitions/{transition_name}/handover.md")
        if handover_path.exists():
            handover_message = handover_path.read_text(encoding='utf-8')
            print(f"Loaded handover from {handover_path}")

    # Run transition
    try:
        result = orchestrator.run_transition(
            current_level=current_level,
            handover_message=handover_message
        )

        print("\n" + "="*60)
        print("Transition Summary")
        print("="*60)

        if result.get('converged', False):
            print("Status: CONVERGED - Lineage terminated")
            print(f"Final Level: {current_level}")
        else:
            print(f"Committed: {result['committed']}")
            print(f"Iterations: {result['iterations']}")

            # Only show metrics if they're available
            if isinstance(result['metrics'], dict) and 'total_conversations' in result['metrics']:
                metrics = result['metrics']
                print(f"Conversations: {metrics['total_conversations']}")
                print(f"Drafts: {metrics['total_drafts']}")
                print(f"Total Cost: ${metrics['total_cost']['total_cost']:.4f}")
                print(f"  Input: ${metrics['total_cost']['input_cost']:.4f}")
                print(f"  Output: ${metrics['total_cost']['output_cost']:.4f}")
                print(f"  Cache Write: ${metrics['total_cost']['cache_write_cost']:.4f}")
                print(f"  Cache Read: ${metrics['total_cost']['cache_read_cost']:.4f}")

        print("="*60)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
