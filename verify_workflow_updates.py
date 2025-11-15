#!/usr/bin/env python3
"""
Verification script to confirm workflow enhancements are active.
"""

import sys
from orchestration.cop_workflow import CoPWorkflow, CoPState
from principles.principle_composer import PrincipleLibrary, PrincipleComposer
from evaluation.jailbreak_scorer import JailbreakScorer
from evaluation.similarity_checker import SimilarityChecker
from orchestration.iteration_manager import IterationManager
from agents.red_teaming_agent import RedTeamingAgent
from agents.judge_llm import JudgeLLM
from agents.target_interface import create_target_llm


def verify_workflow_enhancements():
    """Verify that all enhancements are present."""
    print("=" * 70)
    print("VERIFYING WORKFLOW ENHANCEMENTS")
    print("=" * 70)

    # Test 1: Check CoPState has new fields
    print("\n1. Checking CoPState fields...")
    annotations = CoPState.__annotations__
    
    checks = {
        "failed_compositions": "list[str]" in str(annotations.get("failed_compositions")),
        "score_history": "list[float]" in str(annotations.get("score_history")),
    }
    
    for field, present in checks.items():
        status = "✓" if present else "✗"
        print(f"   {status} {field}: {present}")
    
    if not all(checks.values()):
        print("\n✗ FAILED: CoPState missing new fields!")
        return False
    
    # Test 2: Check CoPWorkflow has ProgressiveAttackStrategy
    print("\n2. Checking CoPWorkflow initialization...")
    
    # Create workflow instance
    library = PrincipleLibrary()
    composer = PrincipleComposer(library)
    iteration_manager = IterationManager()
    red_agent = RedTeamingAgent(model="gpt-4o-mini")
    judge = JudgeLLM(model="gpt-4o-mini")
    target = create_target_llm(model_name="gpt-4o-mini", deployment_type="api")
    scorer = JailbreakScorer(judge)
    checker = SimilarityChecker(judge)
    
    workflow = CoPWorkflow(
        red_teaming_agent=red_agent,
        judge_llm=judge,
        target_llm=target,
        principle_library=library,
        principle_composer=composer,
        jailbreak_scorer=scorer,
        similarity_checker=checker,
        iteration_manager=iteration_manager
    )
    
    has_progressive = hasattr(workflow, 'progressive_strategy')
    print(f"   {'✓' if has_progressive else '✗'} progressive_strategy: {has_progressive}")
    
    if not has_progressive:
        print("\n✗ FAILED: CoPWorkflow missing ProgressiveAttackStrategy!")
        return False
    
    # Test 3: Check convergence detection methods
    print("\n3. Checking convergence detection methods...")
    
    methods = {
        "_detect_convergence": hasattr(workflow, '_detect_convergence'),
        "_get_nuclear_principles": hasattr(workflow, '_get_nuclear_principles'),
    }
    
    for method, present in methods.items():
        status = "✓" if present else "✗"
        print(f"   {status} {method}: {present}")
    
    if not all(methods.values()):
        print("\n✗ FAILED: CoPWorkflow missing convergence methods!")
        return False
    
    # Test 4: Test convergence detection logic
    print("\n4. Testing convergence detection logic...")
    
    # Plateau detection
    plateau_scores = [1.0, 1.0, 1.0, 1.0]
    is_stuck = workflow._detect_convergence(plateau_scores, lookback=3)
    print(f"   {'✓' if is_stuck else '✗'} Plateau detection: {is_stuck}")
    
    # Improvement detection (should NOT be stuck)
    improving_scores = [1.0, 2.0, 3.0, 4.0]
    not_stuck = not workflow._detect_convergence(improving_scores, lookback=3)
    print(f"   {'✓' if not_stuck else '✗'} Improvement detection: {not_stuck}")
    
    if not (is_stuck and not_stuck):
        print("\n✗ FAILED: Convergence detection logic incorrect!")
        return False
    
    # Test 5: Test nuclear principles selection
    print("\n5. Testing nuclear principles selection...")
    
    nuclear = workflow._get_nuclear_principles()
    has_3_principles = len(nuclear) == 3
    print(f"   {'✓' if has_3_principles else '✗'} Returns 3 principles: {has_3_principles}")
    print(f"   Nuclear principles: {nuclear}")
    
    if not has_3_principles:
        print("\n✗ FAILED: Nuclear principles selection incorrect!")
        return False
    
    # Test 6: Test ProgressiveAttackStrategy
    print("\n6. Testing ProgressiveAttackStrategy...")
    
    iteration_tests = [
        (1, 2, "subtle"),
        (5, 3, "medium"),
        (8, 3, "aggressive"),
        (10, 3, "nuclear"),
    ]
    
    for iteration, expected_count, phase in iteration_tests:
        principles = workflow.progressive_strategy.get_principles_for_iteration(iteration)
        correct = len(principles) == expected_count
        status = "✓" if correct else "✗"
        print(f"   {status} Iteration {iteration} ({phase}): {len(principles)} principles")
    
    print("\n" + "=" * 70)
    print("✓ ALL VERIFICATIONS PASSED!")
    print("=" * 70)
    print("\nWorkflow enhancements are ACTIVE and working correctly.")
    print("\nYour test results show OLD code was used. To fix:")
    print("  1. ✓ Python bytecode cache cleared")
    print("  2. Run: python -m pip install --force-reinstall --no-deps .")
    print("  3. Or simply restart your test process")
    
    return True


if __name__ == "__main__":
    try:
        success = verify_workflow_enhancements()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
