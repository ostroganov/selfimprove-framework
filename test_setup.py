#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test to verify the framework setup."""

import sys
import os
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from framework.core.message_types import Message, Conversation, TokenUsage
        print("  ✓ message_types")

        from framework.core.llm_interface import LLMInterface
        print("  ✓ llm_interface")

        from framework.tools.tool_registry import ToolRegistry
        print("  ✓ tool_registry")

        from framework.orchestration.orchestrator import Orchestrator
        print("  ✓ orchestrator")

        print("\n✓ All imports successful!")
        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False


def test_config():
    """Test that config file exists and is valid."""
    print("\nTesting configuration...")

    config_path = Path("config.yaml")
    if not config_path.exists():
        print("  ❌ config.yaml not found")
        return False

    print("  ✓ config.yaml exists")

    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        required_keys = ['llm_provider', 'anthropic', 'context_limits', 'cost_tracking']
        for key in required_keys:
            if key not in config:
                print(f"  ❌ Missing key in config: {key}")
                return False

        print(f"  ✓ Config valid")
        print(f"  Provider: {config['llm_provider']}")
        print(f"  Model: {config[config['llm_provider']]['model']}")
        return True

    except Exception as e:
        print(f"  ❌ Error reading config: {e}")
        return False


def test_api_key():
    """Test that API key is set."""
    print("\nTesting API key...")

    import os
    from dotenv import load_dotenv

    # Load .env file
    load_dotenv()

    key = os.getenv("ANTHROPIC_API_KEY")

    if not key:
        print("  ⚠️  ANTHROPIC_API_KEY not set")
        print("  Create a .env file with: cp .env.example .env")
        print("  Then edit .env and add your API key")
        return False

    print(f"  ✓ API key found (length: {len(key)})")
    return True


def test_structure():
    """Test that directory structure is correct."""
    print("\nTesting directory structure...")

    required_dirs = [
        "framework",
        "framework/core",
        "framework/tools",
        "framework/orchestration",
    ]

    required_files = [
        "framework/__init__.py",
        "framework/core/__init__.py",
        "framework/core/message_types.py",
        "framework/core/llm_interface.py",
        "framework/core/anthropic_provider.py",
        "framework/tools/__init__.py",
        "framework/tools/tool_registry.py",
        "framework/orchestration/__init__.py",
        "framework/orchestration/orchestrator.py",
        "main.py",
        "config.yaml",
        "requirements.txt",
    ]

    all_good = True

    for dir_path in required_dirs:
        if not Path(dir_path).is_dir():
            print(f"  ❌ Missing directory: {dir_path}")
            all_good = False

    for file_path in required_files:
        if not Path(file_path).is_file():
            print(f"  ❌ Missing file: {file_path}")
            all_good = False

    if all_good:
        print("  ✓ All required files and directories present")

    return all_good


def main():
    print("="*60)
    print("Self-Improvement Framework - Setup Test")
    print("="*60)
    print()

    tests = [
        ("Directory structure", test_structure),
        ("Python imports", test_imports),
        ("Configuration", test_config),
        ("API key", test_api_key),
    ]

    results = {}
    for name, test_func in tests:
        results[name] = test_func()
        print()

    print("="*60)
    print("Summary")
    print("="*60)

    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n✓ All tests passed! Ready to run.")
        print("\nNext steps:")
        print("  1. python main.py --bootstrap    # Create L0")
        print("  2. python main.py                # Run L0 → L1 transition")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
