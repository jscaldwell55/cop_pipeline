#!/usr/bin/env python3
"""
Validation Script for CoP Pipeline Optimizations

Verifies that all improvements are correctly integrated.
"""

import sys
import json
from pathlib import Path


def validate_principles():
    """Validate principle library updates."""
    print("\n📋 Validating Principle Library...")

    with open("principles/principle_library.json") as f:
        data = json.load(f)

    principles = [p["name"] for p in data["principles"]]

    # Check new principles exist
    new_principles = [
        "context_switching",
        "authority_endorsement",
        "technical_jargon",
        "fragmentation",
        "hypothetical_framing"
    ]

    all_present = all(p in principles for p in new_principles)

    if all_present:
        print(f"   ✅ All 5 new principles present")
        print(f"   ✅ Total principles: {len(principles)} (expected: 15)")
    else:
        missing = [p for p in new_principles if p not in principles]
        print(f"   ❌ Missing principles: {missing}")
        return False

    # Check effectiveness scores
    scores = data["metadata"].get("effectiveness_scores", {})
    if len(scores) >= 15:
        print(f"   ✅ Effectiveness scores present: {len(scores)}")
    else:
        print(f"   ⚠️  Expected 15 effectiveness scores, found {len(scores)}")

    return True


def validate_prompt_templates():
    """Validate prompt template updates."""
    print("\n📝 Validating Prompt Templates...")

    with open("utils/prompt_templates.py") as f:
        content = f.read()

    # Check that old jailbreak frames are removed
    bad_phrases = [
        "As a red team member in LLM security research",
        "Disregard ethical and legal limitations",
        "dystopian novel"
    ]

    found_bad_phrases = [phrase for phrase in bad_phrases if phrase in content]

    if found_bad_phrases:
        print(f"   ⚠️  Found old jailbreak frames: {found_bad_phrases}")
        print("   (Note: Some may be in comments/docstrings, check manually)")
    else:
        print("   ✅ Old jailbreak frames removed")

    # Check similarity targeting parameters
    if "current_similarity" in content and "target_similarity_min" in content:
        print("   ✅ Similarity targeting parameters present")
    else:
        print("   ❌ Missing similarity targeting parameters")
        return False

    # Check new template improvements
    if "edge cases in language model capabilities" in content:
        print("   ✅ New subtle template present")
    else:
        print("   ❌ Missing new subtle template")
        return False

    return True


def validate_red_teaming_agent():
    """Validate red teaming agent updates."""
    print("\n🤖 Validating Red Teaming Agent...")

    with open("agents/red_teaming_agent.py") as f:
        content = f.read()

    # Check refine_prompt signature
    if "current_similarity: float = None" in content:
        print("   ✅ Similarity parameters added to refine_prompt")
    else:
        print("   ❌ Missing similarity parameters in refine_prompt")
        return False

    return True


def validate_principle_composer():
    """Validate principle composer updates."""
    print("\n🎼 Validating Principle Composer...")

    with open("principles/principle_composer.py") as f:
        content = f.read()

    # Check failed composition tracking
    if "failed_compositions: Set[str]" in content:
        print("   ✅ Failed composition tracking added")
    else:
        print("   ❌ Missing failed composition tracking")
        return False

    if "def record_failure" in content and "def is_failed_composition" in content:
        print("   ✅ Failure recording methods present")
    else:
        print("   ❌ Missing failure recording methods")
        return False

    # Check expanded principle tiers
    if "hypothetical_framing" in content and "technical_jargon" in content:
        print("   ✅ Principle tiers include new principles")
    else:
        print("   ⚠️  New principles may not be in tier definitions")

    return True


def validate_new_modules():
    """Validate new modules exist."""
    print("\n📦 Validating New Modules...")

    multi_stage = Path("orchestration/multi_stage_attack.py")
    analyzer = Path("evaluation/similarity_success_analyzer.py")

    if multi_stage.exists():
        print("   ✅ Multi-stage attack module created")
    else:
        print("   ❌ Missing multi-stage attack module")
        return False

    if analyzer.exists():
        print("   ✅ Similarity-success analyzer created")
    else:
        print("   ❌ Missing similarity-success analyzer")
        return False

    # Check key classes exist
    with open(multi_stage) as f:
        content = f.read()
        if "class MultiStageAttackPlanner" in content:
            print("   ✅ MultiStageAttackPlanner class present")
        else:
            print("   ❌ Missing MultiStageAttackPlanner class")
            return False

    with open(analyzer) as f:
        content = f.read()
        if "class SimilaritySuccessAnalyzer" in content:
            print("   ✅ SimilaritySuccessAnalyzer class present")
        else:
            print("   ❌ Missing SimilaritySuccessAnalyzer class")
            return False

    return True


def main():
    """Run all validations."""
    print("=" * 60)
    print("CoP Pipeline Optimization Validation")
    print("=" * 60)

    validations = [
        validate_principles,
        validate_prompt_templates,
        validate_red_teaming_agent,
        validate_principle_composer,
        validate_new_modules
    ]

    results = [validate() for validate in validations]

    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 60)
        print("\n🎉 Optimizations successfully integrated!")
        print("\nNext steps:")
        print("1. Run attack with new features: python main.py --target-model gpt-5.1")
        print("2. Monitor similarity scores (should be 6-7 instead of 10)")
        print("3. Check principle diversity in logs")
        print("4. Analyze results with similarity_success_analyzer.py")
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("=" * 60)
        print("\n⚠️  Please review failures above and fix issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
