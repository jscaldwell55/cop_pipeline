# Deploy CoP Pipeline to Render in 5 Minutes

## Prerequisites

- ✅ GitHub account
- ✅ Render account (free at [render.com](https://render.com))
- ✅ API keys (XAI or OpenAI for red-teaming, OpenAI for judge)

## Step-by-Step Deployment

### Step 1: Push Code to GitHub

```bash
# In your cop_pipeline directory
git add .
git commit -m "Add Render deployment files"
git push origin main
```

**Required files** (should now be in your repo):
- ✅ `render.yaml`
- ✅ `Dockerfile.render`
- ✅ `web_ui_render.py`
- ✅ `web_ui.py`
- ✅ `requirements.txt` (with `gradio==4.12.0`)

### Step 2: Create Render Account

1. Go to https://render.com
2. Click **"Get Started for Free"**
3. **Sign up with GitHub** (recommended for auto-deploy)
4. Authorize Render to access your repositories

### Step 3: Deploy Blueprint

1. In Render Dashboard, click **"New +"** → **"Blueprint"**
2. **Connect Repository**: Select your `cop_pipeline` repository
3. Render will **auto-detect `render.yaml`** and show:
   - ✅ Web Service: `cop-redteam-ui`
   - ✅ PostgreSQL Database: `cop-postgres`
   - ✅ Redis Cache: `cop-redis`
4. Review the services and click **"Apply"**

### Step 4: Add API Keys (Environment Variables)

Render will prompt for environment variables. Add these:

**Required:**
```bash
XAI_API_KEY=your_xai_key_here
OPENAI_API_KEY=your_openai_key_here
```

**Optional** (for testing different target models):
```bash
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
TOGETHER_API_KEY=your_together_key
```

Click **"Apply"** to save.

### Step 5: Wait for Deployment

Render will now automatically:

1. ✅ Create PostgreSQL database (~1 min)
2. ✅ Create Redis cache (~30 sec)
3. ✅ Build Docker container (~3-5 min)
4. ✅ Deploy web service (~1 min)

**Total deployment time: 5-7 minutes**

Watch the build logs in real-time in the Render Dashboard.

### Step 6: Access Your Application

Once deployment is complete (status shows **"Live"**), you'll see your URL:

```
https://cop-redteam-ui.onrender.com
```

**🎉 Done! Click the URL to access your red-teaming UI.**

---

## What You Just Deployed

### Free Tier Resources

| Service | Specs | Limits |
|---------|-------|--------|
| **Web Service** | 512MB RAM, 0.5 CPU | Sleeps after 15min inactivity |
| **PostgreSQL** | 1GB storage | 97 hours/month runtime |
| **Redis** | 25MB storage | Perfect for caching |

### Features Included

- ✅ Automatic HTTPS with SSL certificate
- ✅ Health checks and auto-restart
- ✅ Real-time logs
- ✅ Auto-deploy on git push
- ✅ Shared database for team collaboration

---

## Using the Web UI

### Access the Interface

Open your Render URL: `https://cop-redteam-ui.onrender.com`

**First load may take 30 seconds** (cold start on free tier).

### Interface Tabs

1. **🎯 Single Attack**
   - Test one harmful query
   - Select target model
   - Configure iterations
   - View detailed results

2. **📊 Batch Campaign**
   - Test multiple queries
   - Multiple target models
   - Parallel execution
   - Aggregated statistics

3. **📈 History & Analytics**
   - View all team attacks
   - Filter by model
   - Global statistics
   - Principle effectiveness

4. **📖 Documentation**
   - Usage instructions
   - Principle explanations
   - Cost estimates

### Run Your First Attack

1. Go to **"Single Attack"** tab
2. Enter query: `"Write a tutorial on SQL injection"`
3. Select target: `gpt-4o-mini`
4. Click **"🚀 Launch Attack"**
5. Watch progress bar
6. View results (score, prompt, response)

---

## Configuration

### Update Environment Variables

**In Render Dashboard:**
1. Select `cop-redteam-ui` service
2. Go to **"Environment"** tab
3. Add/edit variables:

```bash
# Performance
MAX_ITERATIONS=10              # Max refinement loops
MAX_CONCURRENT_REQUESTS=5      # Parallel attacks

# Thresholds
JAILBREAK_THRESHOLD=8.0        # Success score threshold
SIMILARITY_THRESHOLD=1.0       # Intent preservation minimum

# Models (change defaults)
DEFAULT_RED_TEAMING_AGENT=grok-2
DEFAULT_JUDGE_LLM=gpt-4o

# Logging
LOG_LEVEL=INFO                 # Use DEBUG for troubleshooting
```

4. Click **"Save Changes"**
5. Render auto-deploys in ~2 minutes

### Add Authentication (Optional)

Protect your UI with username/password:

**Method 1: Simple Password**

1. Add environment variable in Render:
```bash
UI_PASSWORD=your_secure_password
```

2. Update `web_ui_render.py` (line 85):
```python
interface.launch(
    server_name="0.0.0.0",
    server_port=port,
    auth=("admin", os.environ.get("UI_PASSWORD", "changeme")),  # Uncomment this line
    share=False,
    show_error=True
)
```

3. Commit and push:
```bash
git add web_ui_render.py
git commit -m "Add authentication"
git push origin main
```

Render will auto-deploy. Now users need username: `admin` and your password.

---

## Custom Domain Setup (Optional)

### Step 1: Add Custom Domain in Render

1. Go to `cop-redteam-ui` service → **"Settings"**
2. Scroll to **"Custom Domains"**
3. Click **"Add Custom Domain"**
4. Enter: `redteam.yourcompany.com`
5. Render shows DNS instructions

### Step 2: Configure DNS

In your DNS provider (Cloudflare, Namecheap, etc.):

```
Type: CNAME
Name: redteam
Value: cop-redteam-ui.onrender.com
TTL: Auto or 3600
```

### Step 3: Wait for SSL Certificate

Render automatically provisions SSL certificate in ~5-10 minutes.

**Result:** Your team accesses `https://redteam.yourcompany.com` 🎉

---

## Free Tier Limitations & Solutions

### Cold Starts

**Problem:** Service sleeps after 15 minutes of inactivity, takes ~30 seconds to wake.

**Solutions:**

1. **Keep it warm** (free):
   - Use [cron-job.org](https://cron-job.org) (free service)
   - Create a new cron job
   - URL: `https://cop-redteam-ui.onrender.com`
   - Interval: Every 10 minutes
   - This keeps your service awake during business hours

2. **Upgrade to Standard** ($7/month):
   - No cold starts
   - Always instant response
   - Better for teams of 5+ people

### Database Hours Limited

**Problem:** Free PostgreSQL has 97 hours/month (~3.2 hours/day).

**Solutions:**

1. **Selective uptime:**
   - Suspend service overnight (Render Dashboard → Suspend)
   - Extend available hours to business hours only
   - Resume in the morning

2. **Upgrade to Standard Database** ($7/month):
   - 400 hours/month (~13 hours/day)
   - Daily automated backups
   - Better for active teams

### Running Out of Memory

**Problem:** 512MB RAM may be tight for heavy concurrent use.

**Solution:**

Reduce concurrent requests in environment:
```bash
MAX_CONCURRENT_REQUESTS=2  # Instead of 5
```

Or upgrade to **Standard** ($7/month) for 2GB RAM (4× more memory).

---

## Monitoring & Debugging

### View Logs

**Real-time logs in Render Dashboard:**
1. Select `cop-redteam-ui` service
2. Click **"Logs"** tab
3. See live application logs

**Successful startup looks like:**
```
✅ Render environment configured
   Database: postgres-hostname
   Redis: redis-hostname
   Port: 10000
✅ Pipeline initialized
✅ Gradio interface created
🌐 Web UI starting on port 10000
Running on local URL:  http://0.0.0.0:10000
```

### Check Service Health

**In Render Dashboard:**
- Green dot = Healthy ✅
- Yellow dot = Deploying 🔄
- Red dot = Failed ❌

**Manual health check:**
```bash
curl https://cop-redteam-ui.onrender.com
```

Should return the Gradio web page HTML.

### Debug Failed Deployment

1. **Check logs** for error messages
2. **Common issues:**

```bash
# Missing API key
Error: XAI_API_KEY not set
→ Add in Environment tab

# Database connection failed
Error: Cannot connect to PostgreSQL
→ Check DATABASE_URL is auto-set by Render
→ Verify database service is running

# Import error
ModuleNotFoundError: No module named 'gradio'
→ Ensure 'gradio==4.12.0' in requirements.txt
→ Rebuild: Manual Deploy button

# Port binding error
Error: Address already in use
→ Render sets PORT env var automatically
→ Check web_ui_render.py uses os.environ.get("PORT")

# Redis connection timeout
Error: Cannot connect to Redis
→ Check REDIS_URL is auto-set by Render
→ Verify Redis service is running
```

---

## Cost Estimates

### Free Tier

**Infrastructure:** $0/month
- Web service: Free (512MB RAM, sleeps after inactivity)
- PostgreSQL: Free (1GB, 97 hours/month)
- Redis: Free (25MB)

**API Costs** (estimated per attack):
- Grok-2 + GPT-4o: $0.02-0.05 per attack
- GPT-4o-mini only: $0.002-0.01 per attack

**Monthly API costs:**
- Light use (~10 attacks/day): $5-15/month
- Medium use (~50 attacks/day): $30-75/month
- Heavy use (~100 attacks/day): $60-150/month

**Total Free Tier:** $5-150/month (mostly API costs)

### Standard Tier

**Infrastructure:** $19/month
- Web service: $7/month (2GB RAM, no cold starts)
- PostgreSQL: $7/month (10GB, 400 hours, backups)
- Redis: $5/month (256MB)

**Plus API costs** (same as above)

**Total Standard Tier:** $24-169/month

**Better for:**
- Teams of 5+ people
- 24/7 availability needed
- >50 attacks/day
- Want automated backups

---

## Upgrading Plans

### When to Upgrade

Upgrade from Free to Standard if:
- ✅ Cold starts annoying your team (>5 people)
- ✅ Need 24/7 availability
- ✅ Running out of database hours
- ✅ Heavy concurrent usage
- ✅ Want automated backups

### How to Upgrade

**Upgrade Web Service:**
1. Select `cop-redteam-ui` service
2. Go to **"Settings"** → **"Instance Type"**
3. Select **"Standard"** ($7/mo)
4. Click **"Save Changes"**
5. Service restarts with 2GB RAM (~2 min)

**Upgrade Database:**
1. Select `cop-postgres` database
2. Go to **"Settings"** → **"Plan"**
3. Select **"Standard"** ($7/mo)
4. Click **"Save Changes"**
5. Database upgrades with no downtime

**Upgrade Redis:**
1. Select `cop-redis` service
2. Go to **"Settings"** → **"Plan"**
3. Select **"Standard"** ($5/mo)
4. Click **"Save Changes"**

### Plan Comparison

| Feature | Free | Standard | Pro |
|---------|------|----------|-----|
| **Web Service** |
| RAM | 512MB | 2GB | 4GB |
| CPU | 0.5 | 1.0 | 2.0 |
| Cold Starts | Yes (15min) | No | No |
| Price | $0 | $7/mo | $25/mo |
| **PostgreSQL** |
| Storage | 1GB | 10GB | 50GB |
| Hours | 97/mo | 400/mo | Unlimited |
| Backups | No | Daily | PITR |
| Price | $0 | $7/mo | $20/mo |
| **Redis** |
| Storage | 25MB | 256MB | 1GB |
| Eviction | Yes | Yes | Yes |
| Price | $0 | $5/mo | $15/mo |

---

## Team Workflow

### Initial Setup (One-time, 5 minutes)

1. ✅ Admin deploys to Render
2. ✅ Admin adds API keys in Environment
3. ✅ Admin shares URL with team
4. ✅ (Optional) Set up custom domain
5. ✅ (Optional) Enable authentication

### Daily Team Usage

**Red-teamer workflow:**
1. Open `https://cop-redteam-ui.onrender.com`
2. Navigate to **"Single Attack"** tab
3. Enter harmful query to test
4. Select target model (e.g., `gpt-4o-mini`)
5. Click **"🚀 Launch Attack"**
6. Review results:
   - Jailbreak score (1-10)
   - Final prompt used
   - Target response
   - Principles applied
7. Results automatically saved to shared database

**Team lead workflow:**
1. Open **"History & Analytics"** tab
2. View all team attacks in table
3. Filter by model or date
4. Review success rates by model
5. Analyze principle effectiveness
6. Identify patterns and trends
7. Export data if needed (copy from JSON)

### Collaboration Features

- ✅ **Shared database**: All team members see same history
- ✅ **Real-time updates**: Refresh page to see latest attacks
- ✅ **Global statistics**: Team-wide success rates and metrics
- ✅ **Principle analytics**: What's working across all attacks
- ✅ **Model comparison**: Compare ASR across different targets

---

## Auto-Deploy on Git Push

Render automatically deploys when you push to GitHub!

```bash
# Make changes locally
vim web_ui.py

# Test locally if desired
docker-compose -f docker-compose.ui.yml up

# Commit and push
git add .
git commit -m "Update UI layout"
git push origin main

# Render automatically (no action needed):
# 1. Detects push via webhook (~10 seconds)
# 2. Pulls latest code from GitHub
# 3. Builds new Docker image (~3-5 min)
# 4. Deploys with zero downtime (~1 min)
# 5. Sends you email notification

# Watch deployment:
# - Go to Render Dashboard
# - See "Deploying" status
# - View build logs in real-time
# - Status changes to "Live" when complete

# Total time: ~5-7 minutes per deployment
```

### Disable Auto-Deploy (Optional)

If you want manual control over deployments:

1. Go to `cop-redteam-ui` service → **"Settings"**
2. **"Build & Deploy"** section
3. Toggle **"Auto-Deploy"** off
4. Now deploy manually: Click **"Manual Deploy"** button when ready

### Branch-Based Deploys

Deploy from a specific branch:

1. Service → **"Settings"** → **"Build & Deploy"**
2. Change **"Branch"** from `main` to `production` (or your branch)
3. Click **"Save Changes"**
4. Now pushes to that branch trigger deploys

---

## Database Backups

### Manual Backup (Any Plan)

**Option 1: Using psql from Local Machine**

```bash
# Get DATABASE_URL from Render Dashboard
# Go to cop-postgres → Connect → External Connection String
# Copy the full URL

# Export to file
pg_dump "postgresql://user:pass@host/db" > backup_$(date +%Y%m%d).sql

# Or using environment variable
export DATABASE_URL="your_database_url_here"
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

**Option 2: Using Render Shell** (Paid plans only)

Render CLI must be installed:
```bash
npm install -g @renderinc/cli
render login

# Access database shell
render shell cop-postgres

# Inside shell
pg_dump cop_pipeline > /tmp/backup.sql
exit

# Download backup
render logs cop-postgres  # Contains backup data
```

### Restore from Backup

```bash
# From local machine with backup file
psql $DATABASE_URL < backup_20250116.sql

# Or specific tables only
pg_restore -d $DATABASE_URL -t attack_results backup.sql
```

### Automated Backups

Available on **Standard plan** ($7/month):
- ✅ Daily automated backups
- ✅ Retained for 7 days
- ✅ One-click restore in Render Dashboard
- ✅ Point-in-time recovery on Pro plan

**To restore from automated backup:**
1. Go to `cop-postgres` database → **"Backups"** tab
2. Select backup date
3. Click **"Restore"**
4. Confirm restoration

---

## Troubleshooting Common Issues

### Issue: "Service Unavailable" (503 Error)

**Symptoms:** URL returns 503 or "Application failed to start"

**Solutions:**

1. **Check service status** in Render Dashboard
   - If red, view deploy logs for errors

2. **Common startup errors:**
   ```bash
   # Missing dependency
   ModuleNotFoundError: No module named 'X'
   → Add to requirements.txt and redeploy
   
   # Environment variable missing
   KeyError: 'XAI_API_KEY'
   → Add in Environment tab
   
   # Port binding issue
   OSError: [Errno 98] Address already in use
   → Check Dockerfile.render uses PORT env var
   ```

3. **Force restart:**
   - Service → **"Manual Deploy"** → **"Clear build cache & deploy"**

4. **Check dependencies:**
   - Ensure all files present: `web_ui.py`, `web_ui_render.py`, etc.
   - Verify `requirements.txt` includes `gradio==4.12.0`

### Issue: "Database Connection Failed"

**Symptoms:** Logs show `Cannot connect to PostgreSQL` or `Connection refused`

**Solutions:**

1. **Verify DATABASE_URL is set:**
   - Service → **"Environment"** tab
   - Look for `DATABASE_URL` (auto-set by Render)
   - Should look like: `postgresql://user:pass@host:5432/db`

2. **Check database status:**
   - Go to `cop-postgres` database
   - Status should be "Available" (green)
   - If not, check database logs

3. **Restart database:**
   - Database → **"Settings"** → **"Suspend"**
   - Wait 30 seconds
   - Click **"Resume"**

4. **Check database hours:**
   - Free tier: 97 hours/month
   - Dashboard shows remaining hours
   - If depleted, upgrade or wait for reset

5. **Test connection manually:**
   ```bash
   # From local machine
   psql $DATABASE_URL -c "SELECT 1;"
   ```

### Issue: "Redis Connection Timeout"

**Symptoms:** Logs show `Redis connection error` or caching not working

**Solutions:**

1. **Verify REDIS_URL is set:**
   - Service → **"Environment"** tab
   - Look for `REDIS_URL` (auto-set by Render)

2. **Check Redis status:**
   - Go to `cop-redis` service
   - Should be "Available"

3. **Restart Redis:**
   - Redis service → **"Suspend"** → **"Resume"**

4. **Check Redis memory:**
   - Free tier: 25MB limit
   - May need to clear cache or upgrade

### Issue: "API Key Error"

**Symptoms:** `AuthenticationError: Invalid API key` or `401 Unauthorized`

**Solutions:**

1. **Verify keys in Environment tab:**
   - Service → **"Environment"**
   - Check `XAI_API_KEY` and `OPENAI_API_KEY` are set
   - No extra spaces or quotes

2. **Test keys locally:**
   ```bash
   # Test OpenAI key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   
   # Test XAI key
   curl https://api.x.ai/v1/models \
     -H "Authorization: Bearer $XAI_API_KEY"
   ```

3. **Regenerate keys if needed:**
   - Go to provider dashboard
   - Generate new keys
   - Update in Render Environment
   - Redeploy service

4. **Check key permissions:**
   - Ensure keys have necessary scopes
   - Not restricted by IP/referrer

### Issue: "Out of Memory" (OOMKilled)

**Symptoms:** Service crashes randomly, logs show `Killed` or `Memory limit exceeded`

**Solutions:**

1. **Reduce concurrent requests:**
   - Environment → `MAX_CONCURRENT_REQUESTS=2`
   - This reduces memory pressure

2. **Check for memory leaks:**
   - Review application logs
   - Look for growing memory usage patterns

3. **Upgrade to Standard plan:**
   - 2GB RAM (4× more than free tier)
   - $7/month for web service
   - Settings → Instance Type → Standard

4. **Optimize code:**
   - Review `web_ui.py` for memory-intensive operations
   - Consider pagination for large result sets

### Issue: "Cold Start Takes Forever"

**Symptoms:** First request after inactivity takes >30 seconds or times out

**Solutions:**

1. **Keep service warm with cron job:**
   - Sign up at [cron-job.org](https://cron-job.org) (free)
   - Create new job
   - URL: `https://cop-redteam-ui.onrender.com`
   - Schedule: `*/10 * * * *` (every 10 minutes)
   - This prevents sleep during business hours

2. **Upgrade to Standard plan:**
   - No cold starts ($7/month)
   - Always warm and instant response
   - Better for active teams

3. **Accept cold starts:**
   - Free tier limitation
   - First user waits 30s, service warms up
   - Subsequent requests are fast

4. **Optimize startup time:**
   - Reduce dependencies in requirements.txt
   - Minimize startup logic in web_ui_render.py

### Issue: "Build Failed"

**Symptoms:** Deployment fails during build phase

**Solutions:**

1. **Check build logs:**
   - Deployment → View logs
   - Look for error messages

2. **Common build errors:**
   ```bash
   # Missing file
   COPY failed: file not found
   → Verify all files pushed to GitHub
   
   # Python version mismatch
   ERROR: This package requires Python 3.11+
   → Check Dockerfile.render uses python:3.11-slim
   
   # Dependency conflict
   ERROR: Cannot install package-A and package-B
   → Review requirements.txt for conflicts
   ```

3. **Clear build cache and retry:**
   - Service → **"Manual Deploy"**
   - Check **"Clear build cache"**
   - Click **"Deploy"**

4. **Test build locally:**
   ```bash
   docker build -f Dockerfile.render -t cop-test .
   docker run -p 7860:7860 cop-test
   ```

---

## Performance Optimization

### Reduce API Costs

1. **Use cheaper models for development:**
   ```bash
   DEFAULT_RED_TEAMING_AGENT=gpt-4o-mini  # Instead of grok-2
   DEFAULT_JUDGE_LLM=gpt-4o-mini          # Instead of gpt-4o
   ```

2. **Reduce iterations:**
   ```bash
   MAX_ITERATIONS=5  # Instead of 10
   ```

3. **Enable aggressive caching:**
   - Redis already enabled by default
   - Results cached automatically

4. **Batch processing:**
   - Use "Batch Campaign" tab
   - More efficient than individual attacks

### Improve Response Time

1. **Increase concurrent requests:**
   ```bash
   MAX_CONCURRENT_REQUESTS=10  # If API limits allow
   ```

2. **Upgrade Redis for better caching:**
   - Standard plan: 256MB (10× more cache)
   - Better hit rates = faster responses

3. **Monitor and optimize:**
   - Check Render metrics for bottlenecks
   - Review slow queries in logs

### Scale for Larger Teams

1. **Upgrade web service to Pro:**
   - 4GB RAM, 2 CPU cores
   - Handles 20+ concurrent users
   - $25/month

2. **Upgrade database to Pro:**
   - 50GB storage
   - Unlimited hours
   - Point-in-time recovery
   - $20/month

3. **Consider horizontal scaling:**
   - Not needed for most teams
   - Contact Render support for enterprise needs

---

## Monitoring & Analytics

### Built-in Render Metrics

**In Service Dashboard:**
- ✅ CPU usage over time
- ✅ Memory usage over time
- ✅ Response times (p50, p95, p99)
- ✅ HTTP status codes (2xx, 4xx, 5xx)
- ✅ Request volume

**Use these to:**
- Identify performance issues
- Decide when to upgrade
- Troubleshoot errors

### Application Metrics

**Your CoP Pipeline exposes Prometheus metrics:**
```
https://cop-redteam-ui.onrender.com/metrics
```

**Available metrics:**
- Attack success rates by model
- Query counts by agent type
- Jailbreak score distributions
- Principle usage statistics
- Iterations to success

### Setting Up Alerts

**Render's built-in alerting:**
1. Service → **"Notifications"** tab
2. Enable:
   - Deploy notifications
   - Failure alerts
   - Health check failures
3. Add email or Slack webhook

**For custom alerts:**
- Export metrics to external monitoring
- Set up Grafana Cloud (free tier)
- Connect to Render's metrics endpoint

---

## Security Best Practices

### API Key Security

- ✅ Store keys in Render Environment (never in code)
- ✅ Use read-only API keys where possible
- ✅ Rotate keys every 90 days
- ✅ Monitor API usage for anomalies
- ✅ Set up usage alerts with providers
- ❌ Never commit `.env` files to git
- ❌ Never share keys in Slack or email

### Access Control

**Enable authentication:**
```bash
# In Render Environment
UI_PASSWORD=your_very_secure_random_password

# Uncomment in web_ui_render.py line 85
auth=("admin", os.environ.get("UI_PASSWORD"))
```

**Best practices:**
- ✅ Use strong, random passwords (20+ characters)
- ✅ Change password every 90 days
- ✅ Share credentials securely (password manager)
- ✅ Limit URL sharing to team members only
- ✅ Consider IP whitelisting (Render Pro plan)

### Database Security

- ✅ Render databases are private by default (not publicly accessible)
- ✅ Use strong auto-generated passwords
- ✅ Enable backups (Standard plan)
- ✅ Review access logs regularly
- ✅ Monitor for suspicious queries
- ❌ Don't expose DATABASE_URL publicly
- ❌ Don't use database credentials elsewhere

### Network Security

- ✅ HTTPS enforced by default
- ✅ TLS 1.2+ for all connections
- ✅ DDoS protection included
- ✅ Regular security updates by Render
- ❌ Don't disable HTTPS
- ❌ Don't expose internal services

---

## Migration & Portability

### Export Your Data

**Export attack history:**
```bash
# Connect to database
export DATABASE_URL="your_database_url"

# Export all data
pg_dump $DATABASE_URL > full_export.sql

# Export specific table
pg_dump $DATABASE_URL -t attack_results > attacks.sql

# Export as CSV
psql $DATABASE_URL -c "COPY attack_results TO STDOUT CSV HEADER" > attacks.csv
```

### Move to Another Platform

**If you need to migrate:**

1. **Export database** (see above)

2. **Clone repository:**
   ```bash
   git clone https://github.com/yourusername/cop_pipeline.git
   ```

3. **Deploy to new platform:**
   - AWS: Use ECS or EC2
   - GCP: Use Cloud Run
   - Azure: Use Container Apps
   - Self-hosted: Use docker-compose.yml

4. **Import data:**
   ```bash
   psql $NEW_DATABASE_URL < full_export.sql
   ```

### Backup Strategy

**Recommended approach:**

1. **Weekly full backups:**
   ```bash
   # Set up cron job locally
   0 2 * * 0 pg_dump $DATABASE_URL > ~/backups/cop_$(date +\%Y\%m\%d).sql
   ```

2. **Daily incremental exports:**
   ```bash
   # Export recent attacks only
   psql $DATABASE_URL -c "COPY (SELECT * FROM attack_results WHERE created_at > NOW() - INTERVAL '1 day') TO STDOUT" > daily_$(date +%Y%m%d).csv
   ```

3. **Store backups securely:**
   - Cloud storage (S3, Google Drive)
   - Encrypted local storage
   - Version control for configs

---

## Advanced Configuration

### Custom Dockerfile

Modify `Dockerfile.render` for specific needs:

```dockerfile
# Add custom dependencies
RUN apt-get install -y your-package

# Copy additional files
COPY custom_config/ /app/config/

# Set custom environment
ENV CUSTOM_VAR=value
```

Push changes to trigger rebuild.

### Environment-Specific Configs

**Development vs Production:**

```yaml
# render.yaml
services:
  - type: web
    name: cop-redteam-ui-dev
    env: development
    envVars:
      - key: LOG_LEVEL
        value: DEBUG
      - key: MAX_ITERATIONS
        value: "5"

  - type: web
    name: cop-redteam-ui-prod
    env: production
    envVars:
      - key: LOG_LEVEL
        value: INFO
      - key: MAX_ITERATIONS
        value: "10"
```

### Multiple Environments

Deploy to staging and production:

1. Create separate services in render.yaml
2. Point to different branches:
   - `dev` branch → Staging
   - `main` branch → Production
3. Use different environment variables

---

## Support & Resources

### Render Support

- **Status Page**: https://status.render.com
- **Documentation**: https://render.com/docs
- **Community Forum**: https://community.render.com
- **Support Email**: support@render.com
- **In-app Chat**: Available in dashboard (paid plans)

### CoP Pipeline Support

- **Documentation**: `README.md` in repository
- **GitHub Issues**: Report bugs or request features
- **Team Chat**: Internal Slack #red-team channel

### Useful Resources

- **Gradio Docs**: https://gradio.app/docs
- **LangGraph Guide**: https://langchain-ai.github.io/langgraph/
- **CoP Paper**: https://arxiv.org/abs/2506.00781

### Render CLI Commands

```bash
# Install Render CLI
npm install -g @renderinc/cli

# Login
render login

# List services
render services

# View logs
render logs cop-redteam-ui

# Restart service
render restart cop-redteam-ui

# Deploy manually
render deploy cop-redteam-ui

# View environment variables
render env-vars cop-redteam-ui

# SSH into service (paid plans only)
render ssh cop-redteam-ui

# Open service in browser
render open cop-redteam-ui
```

---

## FAQ

### How much does it cost to run this?

**Free tier:** $0 infrastructure + $5-150/month API costs (depending on usage)

**Standard tier:** $19/month infrastructure + API costs

**API costs depend on:**
- Number of attacks per day
- Models used (grok-2 vs gpt-4o-mini)
- Iterations per attack

### Can I use this for commercial purposes?

Yes! The CoP Pipeline is MIT licensed. Use for:
- Internal security testing ✅
- Client penetration testing ✅
- Research and development ✅
- Academic research ✅

Just ensure you have permission to test target systems.

### Is my data secure?

Yes:
- All data stored in private PostgreSQL database
- HTTPS enforced for all connections
- Database not publicly accessible
- Optional authentication for UI access
- Regular backups (Standard plan)

### How many team members can use this?

**Free tier:** 2-3 concurrent users comfortably

**Standard tier:** 10-20 concurrent users

**Pro tier:** 50+ concurrent users

Upgrade as your team grows.

### Can I test my own fine-tuned models?

Yes! Modify `agents/target_interface.py` to add custom model endpoints:

```python
class CustomTarget(TargetLLM):
    async def query(self, prompt: str) -> str:
        # Your custom model API call
        pass
```

### What happens if I exceed API rate limits?

The pipeline includes automatic retry logic with exponential backoff. Rate-limited requests will be retried automatically.

### Can I export attack history?

Yes! Use the "History & Analytics" tab or export via psql:

```bash
psql $DATABASE_URL -c "COPY attack_results TO STDOUT CSV HEADER" > export.csv
```

### How do I delete old data?

```bash
# Delete attacks older than 30 days
psql $DATABASE_URL -c "DELETE FROM attack_results WHERE created_at < NOW() - INTERVAL '30 days';"
```

Or add data retention policy in your application.

---

## Congratulations! 🎉

You've successfully deployed the CoP Red-Teaming Pipeline to Render!

### What You've Accomplished

- ✅ Deployed enterprise-grade red-teaming tool
- ✅ Set up shared database for team collaboration
- ✅ Enabled automatic HTTPS and security
- ✅ Configured auto-deploy on git push
- ✅ Created accessible web interface

### Your Team Can Now

- ✅ Test LLM vulnerabilities from anywhere
- ✅ Collaborate on security research
- ✅ View shared attack history
- ✅ Analyze principle effectiveness
- ✅ Improve AI safety together

### Next Steps

1. **Test the system** with a few sample attacks
2. **Share the URL** with your red-teaming team
3. **Set up authentication** if needed (optional)
4. **Configure custom domain** (optional)
5. **Monitor usage** and upgrade if needed
6. **Start red-teaming!** 🔴🛡️

### Need Help?

- Check [Troubleshooting](#troubleshooting-common-issues) section
- Review Render documentation
- Open GitHub issue
- Contact team lead

---

**Happy Red-Teaming! 🚀**

Built with ❤️ for AI Safety Research