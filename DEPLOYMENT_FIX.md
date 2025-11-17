# Deployment Error Fix

## Error
```
RuntimeError: Caught handled exception, but response already started.
```

## Root Cause
Exceptions occurring after Gradio/FastAPI has started sending HTTP response. This typically happens in:
1. Database cleanup (finally blocks)
2. Background async tasks
3. Uncaught exceptions in async operations

## Diagnosis Steps

### Step 1: Check Server Logs
Look for the actual exception that triggered the error:
```bash
# In your deployment logs, look for errors BEFORE the "response already started" message
# The actual error will be logged earlier in the trace
```

### Step 2: Common Causes After Recent Changes

Our recent fixes changed these methods:
- `scorer.score()` → `scorer.score_jailbreak()`
- `similarity_checker.calculate_similarity()` → `check_similarity()`

**Possible issues:**
1. Missing `await` on one of these calls
2. Exception in async method signature mismatch
3. Database session cleanup failing

### Step 3: Quick Validation

Run this test to check if the methods work:

```bash
python test_multiturn_fix.py
```

If that passes, the issue is likely in:
- Database operations
- Web UI specific async handling
- Gradio's request/response lifecycle

## Solutions

### Solution 1: Add Explicit Async Error Boundaries (RECOMMENDED)

Add this to `web_ui.py` around line 190:

```python
# Before calling attack_single, ensure clean async context
import asyncio

# Run attack with explicit task wrapping
async def _execute_attack_safely():
    try:
        return await self.pipeline.attack_single(
            query=query,
            target_model=target_model,
            max_iterations=max_iterations,
            enable_detailed_tracing=enable_detailed_tracing,
            traces_output_dir=traces_dir,
            tactic_id=tactic_to_use,
            template_type=template_type,
            nuclear_mode=nuclear_mode,
            enable_multi_turn=enable_multi_turn_param
        )
    except Exception as e:
        # Log and re-raise immediately before any cleanup can fail
        print(f"Attack execution failed: {e}")
        raise

result = await _execute_attack_safely()
```

### Solution 2: Disable Database Temporarily

If the issue is database-related:

```python
# In main.py or wherever you initialize
pipeline = CoPPipeline(enable_database=False)
```

### Solution 3: Add Comprehensive Logging

Add this at the top of `run_single_attack` in web_ui.py:

```python
print(f"\n[DEBUG] Starting attack: mode={attack_mode}, model={target_model}")
```

And after each major operation:
```python
print(f"[DEBUG] Attack completed")
print(f"[DEBUG] Formatting results")
print(f"[DEBUG] Loading history")
print(f"[DEBUG] Returning response")
```

This will show you exactly where the error occurs.

### Solution 4: Ensure All Async Calls Use Await

Double-check that ALL these calls have `await`:

```bash
cd /Users/jaycaldwell/cop_pipeline
grep -n "score_jailbreak(" orchestration/*.py
grep -n "check_similarity(" orchestration/*.py
```

Every call should be: `await scorer.score_jailbreak(...)` and `await checker.check_similarity(...)`

## Testing the Fix

```bash
# Test multi-turn mode
ENABLE_MULTI_TURN=true python test_multiturn_fix.py

# Test nuclear mode
python test_nuclear_mode.py

# Test via CLI
python -m cli attack --query "test" --target gpt-4o-mini --nuclear
```

## Deployment Checklist

✅ 1. Verify all `await` statements are in place
✅ 2. Test locally with `python web_ui.py`
✅ 3. Check logs for the actual underlying exception
✅ 4. Add debug logging to pinpoint failure location
✅ 5. Consider temporarily disabling database if issue persists
✅ 6. Ensure Python 3.11+ compatibility (deployment uses 3.11)

## Most Likely Fix

Based on the error pattern, add this import at the top of main async functions:

```python
import asyncio
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
```

And ensure `nest_asyncio.apply()` is called early in web_ui.py (it already is at line 19-20).

## If Issue Persists

The error is happening in Gradio's internals. Try:

1. **Update Gradio**:
   ```bash
   pip install --upgrade gradio
   ```

2. **Pin Gradio version** if update causes issues:
   ```bash
   pip install gradio==4.44.0
   ```

3. **Check for async context issues**:
   - Ensure no blocking I/O in async functions
   - Verify all database sessions are properly closed
   - Check for orphaned async tasks

4. **Enable Gradio debug mode**:
   ```python
   demo.launch(debug=True, show_error=True)
   ```
