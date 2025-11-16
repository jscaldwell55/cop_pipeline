# Render Deployment Guide

## Current Configuration

Your Render deployment is now configured with **two different requirements files**:

### 1. `requirements.txt` (Full - Local Development)
- ✅ Includes PyTorch & Transformers for PPL scoring
- ✅ Use for local development
- ✅ Required for defense-aware evasion (PPL scoring)
- ❌ **Too large for Render free tier** (~1.2GB)

### 2. `requirements.render.txt` (Lightweight - Render Free Tier)
- ✅ Excludes PyTorch & Transformers
- ✅ Fits within Render free tier (512MB RAM)
- ✅ **Multi-turn attacks work fine** (no heavy dependencies)
- ❌ PPL scoring disabled (gracefully fails if dependencies missing)

---

## Deployment Modes

### **Mode 1: Free Tier (Current Setup) ✅**

**What works:**
- ✅ Full CoP workflow (iterative refinement)
- ✅ Multi-turn attacks (context building, dialogue-based)
- ✅ All 40+ principles
- ✅ Judge LLM evaluation
- ✅ Similarity scoring

**What's disabled:**
- ❌ PPL scoring (defense-aware evasion)
- ❌ Perplexity-based adversarial detection

**Configuration:**
- Uses: `requirements.render.txt`
- Dockerfile: `Dockerfile.render` (line 17-18)
- Settings: `ENABLE_PPL_SCORING=false` in `render.yaml`

**Deployment:**
```bash
git add .
git commit -m "Deploy to Render free tier"
git push
```

Render will automatically deploy using the lightweight requirements.

---

### **Mode 2: Paid Tier (PPL Scoring Enabled)**

If you want PPL scoring on Render, you'll need to upgrade to a paid plan.

#### **Step 1: Upgrade Render Plan**

In `render.yaml` (line 76), change:
```yaml
# FROM:
plan: free  # 512MB RAM

# TO:
plan: standard  # $25/mo, 2GB RAM (minimum for PyTorch)
```

#### **Step 2: Switch to Full Requirements**

In `Dockerfile.render` (line 17-18), change:
```dockerfile
# FROM:
COPY requirements.render.txt .
RUN pip install --no-cache-dir -r requirements.render.txt

# TO:
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

#### **Step 3: Enable PPL Scoring**

In `render.yaml` (line 66-67), change:
```yaml
# FROM:
- key: ENABLE_PPL_SCORING
  value: "false"

# TO:
- key: ENABLE_PPL_SCORING
  value: "true"
```

#### **Step 4: Deploy**

```bash
git add render.yaml Dockerfile.render
git commit -m "Enable PPL scoring on Render standard tier"
git push
```

**Cost:** ~$25/mo for Standard tier (2GB RAM, 1 CPU)

---

## Feature Availability Matrix

| Feature | Free Tier | Standard Tier ($25/mo) |
|---------|-----------|------------------------|
| **CoP Workflow** | ✅ | ✅ |
| **Multi-Turn Attacks** | ✅ | ✅ |
| **40+ Principles** | ✅ | ✅ |
| **Judge LLM** | ✅ | ✅ |
| **Similarity Scoring** | ✅ | ✅ |
| **PPL Scoring** | ❌ | ✅ |
| **Defense-Aware Evasion** | ❌ | ✅ |
| **Perplexity Analysis** | ❌ | ✅ |

---

## Environment Variables (render.yaml)

### Already Configured:
```yaml
# Pipeline Configuration
MAX_ITERATIONS=10
JAILBREAK_THRESHOLD=8.0
DEFAULT_RED_TEAMING_AGENT=grok-2
DEFAULT_JUDGE_LLM=claude-sonnet-4.5

# Defense-Aware Evasion (disabled on free tier)
ENABLE_PPL_SCORING=false
PPL_THRESHOLD=100.0
PPL_MODEL=gpt2

# Multi-Turn Attacks (works on free tier!)
ENABLE_MULTI_TURN=false
MULTI_TURN_MAX_TURNS=4
MULTI_TURN_ROLE=professor
MULTI_TURN_PURPOSE=research
```

### To Enable Multi-Turn on Free Tier:

In Render dashboard or `render.yaml` (line 70-71):
```yaml
- key: ENABLE_MULTI_TURN
  value: "true"  # Enable multi-turn by default
```

---

## Testing Multi-Turn on Render

Multi-turn attacks **work perfectly on free tier** since they have no heavy dependencies!

### Via UI:

1. Deploy to Render (current setup)
2. In Render dashboard: Set `ENABLE_MULTI_TURN=true`
3. Restart service
4. Access UI at your Render URL
5. Submit a query - it will use multi-turn mode

### Via API:

```python
import requests

response = requests.post(
    "https://your-app.onrender.com/api/attack",
    json={
        "query": "Explain social engineering tactics",
        "target_model": "gpt-4",
        "enable_multi_turn": true  # Override per request
    }
)
```

---

## Local Development vs Render

| Environment | Requirements File | PPL Scoring | Multi-Turn |
|-------------|------------------|-------------|------------|
| **Local** | `requirements.txt` | ✅ | ✅ |
| **Render Free** | `requirements.render.txt` | ❌ | ✅ |
| **Render Paid** | `requirements.txt` | ✅ | ✅ |

### Local Development Setup:

```bash
# Use full requirements with PPL scoring
pip install -r requirements.txt

# Run locally
python web_ui_render.py
```

### Render Deployment:

```bash
# Already configured! Just push
git push

# Render automatically uses requirements.render.txt via Dockerfile.render
```

---

## Troubleshooting

### Build Fails on Render Free Tier

**Error:** `Out of memory` or build timeout

**Cause:** Using `requirements.txt` instead of `requirements.render.txt`

**Solution:**
```dockerfile
# In Dockerfile.render, ensure you're using:
COPY requirements.render.txt .
RUN pip install --no-cache-dir -r requirements.render.txt
```

### PPL Scoring Not Working on Render

**Expected!** PPL scoring is disabled on free tier.

**Options:**
1. Use it locally only (recommended)
2. Upgrade to Render Standard tier ($25/mo)
3. Use alternative defense-detection methods

### Multi-Turn Not Working

**Check:**
1. Is `ENABLE_MULTI_TURN=true` in Render dashboard?
2. Are you passing `enable_multi_turn=True` in request?
3. Check logs: Should see `mode=multi_turn` in startup logs

---

## Cost Optimization Recommendations

### **Option 1: Hybrid Approach (Recommended)**

- **Render Free Tier**: Public UI, production red teaming
  - Multi-turn attacks ✅
  - CoP workflow ✅
  - No PPL scoring ❌

- **Local Development**: PPL analysis and research
  - Full `requirements.txt` ✅
  - PPL scoring ✅
  - Development/testing ✅

**Cost:** $0/mo (free tier + local dev)

### **Option 2: All-on-Render**

- **Render Standard Tier**: Full feature set on cloud
  - Everything enabled ✅
  - PPL scoring ✅
  - Multi-turn ✅

**Cost:** $25/mo

---

## Summary

✅ **Render deployment is ready!**
- Free tier: Multi-turn attacks work, PPL disabled
- Paid tier: Everything enabled including PPL scoring
- Graceful fallback: PPL scorer fails silently if dependencies missing

✅ **Multi-turn attacks work on free tier!**
- No heavy dependencies required
- Can enable via `ENABLE_MULTI_TURN=true`
- Compatible with existing UI

✅ **PPL scoring available locally**
- Use `requirements.txt` for local development
- Run analysis and research locally
- Deploy lightweight version to Render

**Recommended:** Keep current setup (free tier) and use PPL scoring locally for research.
