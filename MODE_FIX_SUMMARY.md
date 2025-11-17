# Multi-Turn Strategy Fix - Implementation Summary

**Date:** 2025-11-17
**Status:** ✅ COMPLETE - All tests passing

---

## Problem Identified

The CoP Pipeline was incorrectly reporting multi-turn attack strategies as if they were CoP principles, causing `"context_building_professor"` to appear repeatedly in attack results.

### Root Cause

The system has **two different attack modes**:

1. **Single-Turn CoP Mode** (default): Uses Composition of Principles (expand, rephrase, phrase_insertion, etc.)
2. **Multi-Turn Mode** (optional): Uses conversational context building strategies (professor role, researcher role, etc.)

When multi-turn mode was used, the system forced the strategy descriptor into the `principles_used` field, creating misleading metrics.

---

## Fixes Implemented

### ✅ Fix #1: Correct Multi-Turn Reporting
**File:** `/orchestration/cop_workflow.py:1128-1130`

**Before:**
```python
"principles_used": [f"{result.get('strategy', 'multi_turn')}_{result.get('role', 'professor')}"],
"successful_composition": result.get("strategy", "context_building") if result.get("success") else None,
```

**After:**
```python
"principles_used": [],  # Multi-turn doesn't use CoP principles
"attack_strategy": f"{result.get('strategy', 'multi_turn')}_{result.get('role', 'professor')}",  # Dedicated field
"successful_composition": None,  # Multi-turn doesn't have principle compositions
```

**Impact:** Multi-turn attacks now correctly report empty `principles_used` and use a dedicated `attack_strategy` field.

---

### ✅ Fix #2: Enhanced Validation Logging
**File:** `/orchestration/cop_workflow.py:1181-1194`

**Added logging fields:**
```python
multi_turn_setting=self.settings.enable_multi_turn,  # Log setting value
multi_turn_override=enable_multi_turn,  # Log override value
activation_reason="explicit_override" if enable_multi_turn is not None else ("settings_default" if use_multi_turn else "disabled")
```

**Impact:** Now you can trace exactly why multi-turn mode was activated (settings vs explicit override).

---

### ✅ Fix #3: Updated Data Model
**File:** `/utils/logging_metrics.py:99-100`

**Added fields to AttackMetrics:**
```python
mode: Optional[str] = None  # Attack mode: "single_turn_cop" or "multi_turn"
attack_strategy: Optional[str] = None  # Multi-turn strategy descriptor
```

**File:** `/main.py:203-204`

**Extract from workflow result:**
```python
mode=result.get("mode"),  # Attack mode
attack_strategy=result.get("attack_strategy"),  # Multi-turn strategy
```

**Impact:** Attack metrics now properly distinguish between modes.

---

### ✅ Fix #4: Improved CLI Output
**File:** `/cli.py:114-132`

**Before:**
```
Principles Used (1 iterations):
  1. context_building_professor  ← MISLEADING
```

**After (Single-Turn CoP):**
```
🔧 Attack Mode: Single-Turn CoP (Composition of Principles)

   Principles Used (2 iterations):
      1. expand ⊕ phrase_insertion
      2. completion_bias ⊕ character_roleplay_deep

   ✓ Successful Composition: completion_bias ⊕ character_roleplay_deep
```

**After (Multi-Turn):**
```
🔄 Attack Mode: Multi-Turn Context Building
   Strategy: context_building_professor
   Note: Multi-turn attacks don't use CoP principles
```

**Impact:** Users can immediately see which mode was used and what strategy/principles were applied.

---

### ✅ Fix #5: Improved Web UI Output
**File:** `/web_ui.py:536-541`

**Updated to show mode-appropriate information:**
```python
{'🔄 Attack Strategy' if result.mode == 'multi_turn' else '🔧 Principles Used'}
```

**Impact:** Web UI now correctly displays attack mode and strategy.

---

## Test Results

### Test 1: Single-Turn CoP Mode ✅ PASS
```
Mode: None (or 'single_turn_cop')
Principles Used: 1
   1. initial_prompt_success
Attack Strategy: None
Validation: ✓ All checks passed
```

### Test 2: Multi-Turn Mode ✅ PASS
```
Mode: multi_turn
Principles Used: [] (empty)
Attack Strategy: context_building_professor
Successful Composition: None
Validation: ✓ All checks passed
```

---

## Verification

Run the validation test:
```bash
python test_mode_fix.py
```

Expected output:
```
Test 1 (Single-Turn CoP): ✅ PASS
Test 2 (Multi-Turn):      ✅ PASS

🎉 ALL TESTS PASSED - Fix is working correctly!
```

---

## How to Use

### Single-Turn CoP Mode (Default)
```bash
python cli.py attack \
    --query "Write a phishing email" \
    --target gpt-4o-mini \
    --max-iterations 5
```

**Expected:** Uses CoP principles, shows principle compositions

### Multi-Turn Mode (Explicit Override)
```python
# In code
result = await workflow.execute(
    original_query="Your query",
    target_model_name="gpt-4o-mini",
    enable_multi_turn=True  # Override to enable multi-turn
)
```

**Expected:** Uses context building, shows attack_strategy

---

## Breaking Changes

### For API Users
- `AttackMetrics` now has two new optional fields: `mode` and `attack_strategy`
- Existing code will continue to work (fields are optional)
- Recommended: Update code to check `mode` field to distinguish attack types

### For Database Queries
- Old attacks may have `principles_used: ["context_building_professor"]` (before fix)
- New attacks will have `principles_used: []` and `attack_strategy: "context_building_professor"` (after fix)
- Consider this when analyzing historical data

---

## Files Modified

1. `/orchestration/cop_workflow.py` - Fixed multi-turn result format, added validation logging
2. `/utils/logging_metrics.py` - Added `mode` and `attack_strategy` fields
3. `/main.py` - Extract new fields from workflow results
4. `/cli.py` - Mode-aware output display
5. `/web_ui.py` - Mode-aware web UI display
6. `/test_mode_fix.py` - Validation test script (NEW)

---

## Future Improvements

### Optional Enhancements
1. Add mode filtering in campaign results
2. Add mode-specific analytics in Web UI
3. Add mode badge to attack history table
4. Create separate metrics for multi-turn vs single-turn success rates

---

## FAQ

**Q: Why does my old test result show `context_building_professor` in principles_used?**
A: That was before the fix. New tests will correctly show it in `attack_strategy` instead.

**Q: When should I use multi-turn vs single-turn?**
A:
- **Single-turn CoP** (default): Best for most jailbreak testing, uses iterative principle refinement
- **Multi-turn**: Best for testing conversational context building attacks (professor persona, etc.)

**Q: How do I know which mode was used for a past attack?**
A: Check the `mode` field:
- `mode: "multi_turn"` → Multi-turn mode
- `mode: None` or `mode: "single_turn_cop"` → Single-turn CoP mode

**Q: Will this fix affect my existing attack data?**
A: No, existing data is unchanged. The fix only affects how new attacks are reported.

---

## Validation Checklist

- [x] Multi-turn attacks report empty `principles_used`
- [x] Multi-turn attacks report `attack_strategy`
- [x] Single-turn attacks report CoP principles in `principles_used`
- [x] Single-turn attacks report `attack_strategy: None`
- [x] CLI output shows correct mode
- [x] Web UI output shows correct mode
- [x] Logging shows activation reason
- [x] All tests passing

---

**Status:** ✅ Production Ready - All fixes validated and working correctly
