"""Automated test runner for the LLM Memory Mock API.

Loads test prompts from ``config/prompts.toml`` and runs them against the mock API,
reporting per-prompt results and summary statistics. The ``memory`` prompt category
exercises the write-then-recall path in order (store a fact, then ask for it back).
"""

import os
import warnings
from pathlib import Path
from typing import Any, Dict, List

import tomli
from mirascope.core import prompt_template
from mirascope.core.openai import openai_call

# Suppress pydub SyntaxWarnings.
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

# Load model configuration.
config_path = Path(__file__).parent.parent / "config" / "model.toml"
with open(config_path, "rb") as f:
    config = tomli.load(f)

# Load test prompts.
prompts_path = Path(__file__).parent.parent / "config" / "prompts.toml"
with open(prompts_path, "rb") as f:
    prompts_config = tomli.load(f)

# Load client configuration.
client_config_path = Path(__file__).parent.parent / "config" / "client_config.toml"
with open(client_config_path, "rb") as f:
    client_config = tomli.load(f)

os.environ["OPENAI_API_KEY"] = "sk-mock-key"
os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"


@openai_call(model=config["default"]["model"])
@prompt_template("{pre_prompt}\n\n<user>{user_message}</user>")
def llm_client_call(user_message: str, pre_prompt: str):
    """Mirascope OpenAI call wrapper for testing the mock API."""
    ...


def test_prompt(prompt: str, category: str = "test") -> Dict[str, Any]:
    """Test a single prompt and return results.

    Args:
        prompt: The prompt text to test.
        category: Category of the test for reporting purposes. Defaults to "test".

    Returns:
        Dict[str, Any]: Test result dictionary with category, prompt, success flag,
            response content, and error message keys.
    """
    try:
        pre_prompt = client_config["client"].get("pre_prompt", "")
        response = llm_client_call(user_message=prompt, pre_prompt=pre_prompt)
        return {
            "category": category,
            "prompt": prompt,
            "success": True,
            "response": response.content,
            "error": None,
        }
    except Exception as e:
        return {
            "category": category,
            "prompt": prompt,
            "success": False,
            "response": None,
            "error": str(e),
        }


if __name__ == "__main__":
    print("=" * 80)
    print("🧪 Testing Mock LLM Memory API with Configured Prompts")
    print("=" * 80)
    print()

    all_results: List[Dict[str, Any]] = []
    total_tests: int = 0
    passed_tests: int = 0

    # Test all prompt categories.
    for category, prompts in prompts_config["test_prompts"].items():
        if not prompts:  # Skip empty categories.
            continue

        print(f"\n📋 Testing category: {category.upper()}")
        print("-" * 80)

        for i, prompt in enumerate(prompts, 1):
            total_tests += 1
            print(
                f"\n[{i}/{len(prompts)}] Prompt: {prompt[:60]}"
                f"{'...' if len(prompt) > 60 else ''}"
            )

            result = test_prompt(prompt, category)
            all_results.append(result)

            if result["success"]:
                passed_tests += 1
                print("✅ Success")
                response_text = result["response"] or ""
                print(
                    f"Response: {response_text[:100]}"
                    f"{'...' if len(response_text) > 100 else ''}"
                )
            else:
                print(f"❌ Failed: {result['error']}")

    # Print summary.
    print("\n" + "=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {total_tests - passed_tests} ❌")
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    print("=" * 80)

    # Exit with appropriate code.
    exit(0 if passed_tests == total_tests else 1)
