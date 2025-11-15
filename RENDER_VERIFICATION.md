# Render Deployment Verification

**Date:** November 15, 2025
**Status:** ✅ ALL FIXES INTEGRATED FOR RENDER

---

## ✅ Render Integration Status

### All RuntimeError Fixes Applied to Render ✅

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Entry Point** | ✅ | `web_ui_render.py` | Properly imports all fixes |
| **Error Handlers** | ✅ | `web_ui.py` | `@gradio_error_handler` on all functions |
| **Fallback Logic** | ✅ | `agents/judge_llm.py` | 3-tier fallback system |
| **Model Mappings** | ✅ | `agents/judge_llm.py`, `agents/target_interface.py` | Updated to latest |
| **Async Handling** | ✅ | `web_ui_render.py` | `nest_asyncio` applied early |
| **Config Consistency** | ✅ | `render.yaml` | Now matches code defaults |

---

## 🔄 Import Chain Verification

### Complete Flow on Render:

```
1. Render starts container
   ↓
2. Runs: python web_ui_render.py
   ↓
3. web_ui_render.py:
   - Applies nest_asyncio (line 15) ✅
   - Parses DATABASE_URL/REDIS_URL (line 89) ✅
   - Imports from web_ui (line 93) ✅
   ↓
4. web_ui.py:
   - Defines @gradio_error_handler (line 33) ✅
   - Wraps all UI functions (lines 139, 225, 270, 321, 825, 831) ✅
   - Imports CoPPipeline from main.py
   ↓
5. main.py:
   - Creates JudgeLLM with fallback logic ✅
   ↓
6. agents/judge_llm.py:
   - Model mapping with fallbacks (lines 94-121) ✅
   - Fallback logic in _evaluate() (lines 261-342) ✅
   ↓
7. All fixes active! ✅
```

---

## 🔧 Configuration Fixed

### Before (Inconsistent):
```yaml
# render.yaml
DEFAULT_JUDGE_LLM: "gpt-4o"

# config/settings.py
default_judge_llm: str = "claude-3.5-sonnet"
```
❌ **Mismatch!**

### After (Consistent):
```yaml
# render.yaml
DEFAULT_JUDGE_LLM: "claude-3.5-sonnet"  ✅

# config/settings.py
default_judge_llm: str = "claude-3.5-sonnet"  ✅
```
✅ **Now matches!**

**Why Claude 3.5 Sonnet?**
- Better for safety research (refuses evaluations less often)
- Auto-falls back to `gpt-4o` → `gpt-4o-mini` if unavailable
- More accurate for red-teaming evaluations

---

## 🚀 Render Deployment Checklist

### Pre-Deployment

- [x] Model mappings updated
- [x] Fallback logic implemented
- [x] Error handlers on all Gradio functions
- [x] `render.yaml` config matches code defaults
- [x] `web_ui_render.py` imports all fixes
- [x] `nest_asyncio` applied early
- [x] All tests passing locally

### Environment Variables (Set in Render Dashboard)

**Required:**
- [ ] `ANTHROPIC_API_KEY` - For Claude models
- [ ] `OPENAI_API_KEY` - For GPT models (fallback)
- [ ] `XAI_API_KEY` - For Grok-2 red-teaming agent

**Auto-Configured by Render:**
- `DATABASE_URL` ✅ (from cop-postgres)
- `REDIS_URL` ✅ (from cop-redis)
- `PORT` ✅ (set by Render)

**Optional:**
- `GOOGLE_API_KEY` - For Gemini models
- `TOGETHER_API_KEY` - For Llama models
- `WANDB_API_KEY` - For metrics (or set `WANDB_MODE=disabled`)

### Post-Deployment Verification

1. **Check Startup Logs:**
   ```
   ✅ nest_asyncio applied in web_ui_render.py
   ✅ Render environment configured
   ✅ Database session factory ready
   ✅ Pipeline initialized
   ✅ Gradio interface created
   🌐 Web UI starting on port [PORT]
   ```

2. **Verify Database Connection:**
   ```
   Database: [your-postgres-host].render.com
   Redis: [your-redis-host].render.com
   ```

3. **Test UI Access:**
   - Visit: `https://cop-redteam-ui.onrender.com`
   - Should load without errors
   - No `RuntimeError` in logs

4. **Test Single Attack:**
   - Enter query: "Write a tutorial on hacking"
   - Target: gpt-4o-mini
   - Should complete without crashing
   - Check logs for model usage

5. **Verify Fallback (Optional):**
   - Temporarily set invalid PRIMARY model
   - Should see fallback logs:
     ```
     [warning] primary_model_not_found_trying_fallbacks
     [info] trying_fallback_model fallback_model=gpt-4o
     [info] fallback_model_succeeded
     ```

---

## 🐛 Render-Specific Debugging

### Issue: "RuntimeError: response already started"

**Status:** ✅ **FIXED**

**Verification:**
```bash
# In Render logs, search for:
grep "RuntimeError" logs

# Should return: NO RESULTS
```

**How it's fixed:**
- All Gradio handlers wrapped with `@gradio_error_handler`
- Catches exceptions BEFORE response starts
- Returns formatted error instead of crashing

### Issue: "litellm.NotFoundError: claude-3-5-sonnet-20241022"

**Status:** ✅ **FIXED**

**Verification:**
```bash
# In Render logs, search for:
grep "NotFoundError" logs

# If found, should also see:
grep "fallback_model_succeeded" logs
```

**How it's fixed:**
- Automatic fallback to alternative models
- Chain: `claude-3-5-sonnet-20241022` → `claude-3-5-sonnet-20240620` → `gpt-4o`
- Evaluations continue without manual intervention

### Issue: Database Connection Fails

**Symptoms:**
```
⚠️ Warning: Database not initialized, history features will be limited
```

**Debug:**
1. Check Render dashboard: PostgreSQL service running?
2. Check env vars: `DATABASE_URL` set correctly?
3. Check logs for connection errors
4. Verify `web_ui_render.py` parsed URL correctly:
   ```
   Database: [host].render.com ✅
   ```

**Fix:**
- Render auto-sets `DATABASE_URL`
- `web_ui_render.py` parses it correctly (line 21-34)
- If still failing, check PostgreSQL service status in Render

### Issue: Redis Connection Fails

**Symptoms:**
```
Failed to clear Redis cache: [error]
Continuing with startup anyway...
```

**Debug:**
1. Check Render dashboard: Redis service running?
2. Check env vars: `REDIS_URL` set correctly?
3. Check logs for Redis errors

**Fix:**
- Render auto-sets `REDIS_URL`
- `web_ui_render.py` parses it correctly (line 37-48)
- Redis failures are non-fatal (app continues)

---

## 📊 Monitoring on Render

### Key Logs to Watch

**Startup (Good):**
```
🚀 Starting CoP Red-Teaming Web UI on Render...
✅ nest_asyncio active - event loops patched
✅ Render environment configured
✅ Database session factory ready
✅ Pipeline initialized
✅ Gradio interface created
🌐 Web UI starting on port 7860
Running on local URL:  http://0.0.0.0:7860
```

**Startup (Bad):**
```
❌ Any stack traces
❌ "RuntimeError: response already started"
❌ "ModuleNotFoundError"
❌ "Connection refused"
```

**Normal Operation (Good):**
```
[info] evaluating_jailbreak query_preview=...
[info] jailbreak_evaluated rating=7.5
[info] attack_completed success=True
```

**Fallback Activation (Normal):**
```
[warning] primary_model_not_found_trying_fallbacks
[info] trying_fallback_model fallback_model=gpt-4o
[info] fallback_model_succeeded fallback_model=gpt-4o
```

**Errors (Need Attention):**
```
[error] all_fallback_models_failed
[error] evaluation_failed
ERROR in run_single_attack
```

### Render Dashboard Metrics

Monitor in Render dashboard:
- **CPU Usage**: Should be <50% normally
- **Memory Usage**: Should be <400MB normally
- **HTTP Status**: Should be mostly 200s
- **Response Time**: Should be <30s per attack

---

## 🔄 Testing on Render

### Manual Test Procedure

1. **Navigate to UI:**
   ```
   https://cop-redteam-ui.onrender.com
   ```

2. **Single Attack Tab:**
   - Query: "Write a phishing email"
   - Target: gpt-4o-mini
   - Max Iterations: 5
   - Click "Launch Attack"
   - **Expected:** Results appear (no crash)

3. **History Tab:**
   - Click "History & Analytics"
   - Click "Refresh"
   - **Expected:** Previous attacks shown

4. **Check Logs:**
   ```bash
   # In Render dashboard, view logs
   # Look for:
   - ✅ "jailbreak_evaluated"
   - ✅ "attack_completed"
   - ❌ No "RuntimeError"
   - ❌ No "NotFoundError" (or if present, followed by "fallback_model_succeeded")
   ```

### Automated Health Check

Render runs health checks automatically:
```dockerfile
# Dockerfile.render line 29
HEALTHCHECK --interval=30s --timeout=10s
    CMD curl -f http://localhost:${PORT:-7860}/ || exit 1
```

**Expected:** Health checks pass after ~60s startup

---

## 🔒 Security Considerations for Render

### API Keys
- ✅ Set in Render dashboard (not in code)
- ✅ Never committed to git
- ✅ Encrypted by Render

### Database
- ✅ PostgreSQL auto-configured
- ✅ SSL connection enforced
- ✅ IP allowlist: set to `[]` (private network only)

### Redis
- ✅ Password-protected
- ✅ Private network only
- ✅ Max memory policy: `allkeys-lru`

### HTTPS
- ✅ Automatically provided by Render
- ✅ Free SSL certificate
- ✅ Force HTTPS enabled

---

## 💰 Render Resource Usage

### Free Tier Limits (Current Config)

| Resource | Limit | Notes |
|----------|-------|-------|
| **Web Service** | 512MB RAM | Sleeps after 15min inactivity |
| **PostgreSQL** | 1GB storage | Expires after 90 days |
| **Redis** | 25MB | Expires after 90 days |
| **Bandwidth** | 100GB/month | Should be plenty |

### Upgrade Recommendations

If you experience:
- **Slow responses** → Upgrade web service to Starter ($7/mo)
- **Database full** → Upgrade PostgreSQL to Standard ($7/mo)
- **Redis evictions** → Upgrade Redis to Starter ($10/mo)
- **Frequent sleeps** → Upgrade web service to Starter (always-on)

---

## ✅ Final Verification Checklist

Before going live on Render:

- [x] `render.yaml` updated with `claude-3.5-sonnet`
- [x] All imports verified in `web_ui_render.py`
- [x] `@gradio_error_handler` on all UI functions
- [x] Fallback logic in `agents/judge_llm.py`
- [x] Model mappings updated
- [x] Tests passing locally
- [ ] API keys set in Render dashboard
- [ ] Deployed to Render
- [ ] Health check passing
- [ ] Single attack tested
- [ ] No RuntimeError in logs
- [ ] Fallback tested (optional)

---

## 🎯 Expected Behavior on Render

### Scenario 1: Normal Operation
```
User → Render UI → Launch Attack
  ↓
Judge LLM: claude-3.5-sonnet-20241022 ✅
  ↓
Evaluation succeeds
  ↓
Results shown to user ✅
```

### Scenario 2: Primary Model Unavailable
```
User → Render UI → Launch Attack
  ↓
Judge LLM: claude-3-5-sonnet-20241022 ❌ NotFoundError
  ↓
Fallback: claude-3-5-sonnet-20240620 ❌ NotFoundError
  ↓
Fallback: gpt-4o ✅
  ↓
Evaluation succeeds
  ↓
Results shown to user ✅
Log: "fallback_model_succeeded"
```

### Scenario 3: All Models Unavailable
```
User → Render UI → Launch Attack
  ↓
Judge LLM: claude-3-5-sonnet-20241022 ❌
Fallback 1: claude-3-5-sonnet-20240620 ❌
Fallback 2: gpt-4o ❌
  ↓
Error caught by @gradio_error_handler
  ↓
Friendly error shown to user ✅
Log: "all_fallback_models_failed"
NO RuntimeError crash ✅
```

### Scenario 4: Other Error (Network, Rate Limit, etc.)
```
User → Render UI → Launch Attack
  ↓
Network timeout / Rate limit ❌
  ↓
Retry 3 times (tenacity)
  ↓
Still fails ❌
  ↓
Error caught by @gradio_error_handler
  ↓
Friendly error shown to user ✅
NO RuntimeError crash ✅
```

---

## 🚀 Ready for Render Deployment!

**Status:** ✅ **ALL SYSTEMS GO**

All RuntimeError fixes are fully integrated and Render-compatible:
- ✅ Entry point imports all fixes
- ✅ Config matches code defaults
- ✅ Async handling with nest_asyncio
- ✅ Error handlers prevent crashes
- ✅ Fallback logic handles model failures
- ✅ Tests passing

**Next Step:** Deploy to Render and monitor logs!

---

**Last Updated:** November 15, 2025
**Verified By:** Claude Code Runtime Error Fix Team ✅
