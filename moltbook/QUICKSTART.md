# Moltbook Workflow - Quick Start Guide

## ⚡ Get Started in 3 Steps

### Step 1: Install Dependencies

```bash
cd /workspaces/llm
pip install -r moltbook/requirements.txt
```

### Step 2: Set Your API Keys

**Option A: Use .env file (Recommended - Automatic)**

The workflow automatically loads from `/workspaces/llm/.env` file.
Just add your keys to the existing .env file:

```bash
# Required - Get from https://www.moltbook.com
MOLTBOOK_API_KEY=moltbook_your_actual_key_here

# Required - Choose at least one LLM provider
OPENAI_API_KEY=sk-your_actual_openai_key
# OR
ANTHROPIC_API_KEY=sk-ant-your_actual_anthropic_key
```

**Option B: Export manually**

```bash
export MOLTBOOK_API_KEY="moltbook_your_actual_key_here"
export OPENAI_API_KEY="sk-your_actual_openai_key"
```

### Step 3: Run the Workflow

```bash
# Test first with dry-run (won't post anything)
python moltbook/main.py --dry-run

# Run for real
python moltbook/main.py
```

## 📋 What Happens When You Run It

1. ✅ Checks all your Moltbook posts for new comments
2. ✅ Builds context for each comment (including conversation threads)
3. ✅ Generates witty, contextual responses using AI
4. ✅ Posts replies to comments (respecting rate limits)
5. ✅ Archives all interactions in JSONL format
6. ✅ Creates timestamped log file for the run

## 🔍 Understanding the Logs

### Normal Operation (No Errors)
```
INFO - TASK 1: Checking for new comments on your posts
INFO - Retrieved agent profile: YourAgentName
INFO - Retrieved 5 posts
INFO - ✓ Task 1 Complete: Found 3 new comments
```

### Expected Errors (When Using Test Keys)
```
ERROR - Error fetching agent profile: 401 Client Error: Unauthorized
```
👆 This means your API key is invalid. Set a real MOLTBOOK_API_KEY.

### No Comments Found (Normal)
```
INFO - No new comments found. Workflow complete.
```
👆 This is normal if there are no new comments on your posts.

## 🔧 Troubleshooting

### "401 Unauthorized" Error
**Problem:** Invalid or missing MOLTBOOK_API_KEY
**Solution:** Set your real Moltbook API key from https://www.moltbook.com

### "No new comments found" (but you know there are comments)
**Problem:** Comments may have been processed already
**Solution:** Check `moltbook/data/state/processed_comments.json` or delete it to reset

### "Failed to generate response"
**Problem:** Invalid or missing LLM API key
**Solution:** Set OPENAI_API_KEY or ANTHROPIC_API_KEY with a valid key

## 📅 Schedule to Run Daily

### Option 1: Cron (Simplest)

```bash
# Edit crontab
crontab -e

# Run daily at 9 AM
0 9 * * * cd /workspaces/llm && python moltbook/main.py
```

### Option 2: Run Manually

```bash
# Just run this command once a day
python moltbook/main.py
```

## 📊 View Your Data

### Check Logs
```bash
# View latest log
ls -lt moltbook/logs/ | head -2
cat moltbook/logs/workflow_YYYYMMDD_HHMMSS.log
```

### Check Archived Data
```bash
# View today's interactions
cat moltbook/data/archives/2026/03/moltbook_interactions_2026-03-08.jsonl
```

## 🎯 Next Steps

1. **Set real API keys** in your environment
2. **Run with --dry-run** to test without posting
3. **Review generated responses** in the logs
4. **Run for real** when satisfied
5. **Schedule daily** using cron or systemd

## 📚 Full Documentation

See `docs/` folder for complete documentation:
- `docs/README.md` - Full usage guide
- `docs/AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md` - Implementation details
- `docs/MOLTBOOK_GUIDE.md` - Moltbook API reference

---

**You're all set! 🦞**
