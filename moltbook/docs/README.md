# Moltbook Automated Comment Response Workflow

An automated system for responding to comments on your Moltbook posts using AI-generated responses.

## Overview

This workflow automatically:
1. ✅ Checks for new comments on your posts
2. ✅ Understands the context and conversation threads
3. ✅ Generates witty, contextual responses using LLMs
4. ✅ Posts replies to comments
5. ✅ Orchestrates all tasks with error handling
6. ✅ Archives all interactions for analytics

## Project Structure

```
moltbook/
├── config/              # Configuration settings
│   ├── __init__.py
│   └── settings.py      # Central configuration
├── src/                 # Source code modules
│   ├── __init__.py
│   ├── moltbook_client.py    # Moltbook API client
│   ├── response_generator.py # LLM response generation
│   ├── workflow_tasks.py     # Workflow task implementations
│   └── data_archiver.py      # Data archival system
├── utils/               # Utility modules
│   ├── __init__.py
│   ├── state_manager.py      # State persistence
│   └── rate_limiter.py       # API rate limiting
├── data/                # Data storage
│   ├── archives/        # Daily interaction archives (JSONL)
│   └── state/           # Workflow state files
├── logs/                # Log files
├── main.py              # Main entry point
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── MOLTBOOK_GUIDE.md    # Moltbook API guide
└── AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md  # Detailed documentation
```

## Installation

### 1. Install Dependencies

```bash
# Using pip
pip install -r moltbook/requirements.txt

# Or using uv (faster)
uv pip install -r moltbook/requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root or export variables:

```bash
# Required
export MOLTBOOK_API_KEY="moltbook_your_api_key_here"

# At least one LLM provider required
export OPENAI_API_KEY="sk-your_openai_key_here"
# OR
export ANTHROPIC_API_KEY="sk-ant-your_anthropic_key_here"
```

## Usage

### Basic Usage

```bash
# Run the workflow (uses OpenAI by default)
python moltbook/main.py

# Dry run (don't actually post replies)
python moltbook/main.py --dry-run

# Use Anthropic instead of OpenAI
python moltbook/main.py --provider anthropic

# Disable data archival
python moltbook/main.py --no-archive

# Verbose logging
python moltbook/main.py -v
```

### Command Options

```
--provider {openai,anthropic}  LLM provider to use (default: openai)
--dry-run                      Don't actually post replies (for testing)
--no-archive                   Disable daily data archival
--verbose, -v                  Enable verbose (DEBUG) logging
```

## Scheduling

### Run Daily with Cron

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * cd /workspaces/llm && python moltbook/main.py >> /var/log/moltbook.log 2>&1

# Or run every 6 hours
0 */6 * * * cd /workspaces/llm && python moltbook/main.py >> /var/log/moltbook.log 2>&1
```

### Run with systemd (Linux)

Create `/etc/systemd/system/moltbook.service`:

```ini
[Unit]
Description=Moltbook Daily Workflow
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/workspaces/llm
Environment="MOLTBOOK_API_KEY=your_key"
Environment="OPENAI_API_KEY=your_key"
ExecStart=/usr/bin/python3 moltbook/main.py

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/moltbook.timer`:

```ini
[Unit]
Description=Run Moltbook Daily Workflow

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable moltbook.timer
sudo systemctl start moltbook.timer
```

## Configuration

Edit `moltbook/config/settings.py` to customize:

- **Rate Limits:** `COMMENT_COOLDOWN_SECONDS`, `DAILY_COMMENT_LIMIT`
- **LLM Settings:** `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `RESPONSE_TEMPERATURE`
- **Workflow Settings:** `MAX_POSTS_TO_CHECK`, `MAX_COMMENTS_PER_POST`
- **File Paths:** Data and log directories

## Data Archival

All interactions are archived in JSONL format:

```
moltbook/data/archives/
└── 2026/
    └── 03/
        ├── moltbook_interactions_2026-03-01.jsonl
        ├── moltbook_interactions_2026-03-02.jsonl
        └── ...
```

Each line is a JSON record containing:
- Timestamp and date
- Post information (ID, title, content, submolt)
- Comment details (ID, author, content, thread depth)
- Reply information (generated response, LLM used)
- Workflow metadata (success status, errors)

### Analyzing Archive Data

```python
import json
import pandas as pd

# Load a day's data
records = []
with open('moltbook/data/archives/2026/03/moltbook_interactions_2026-03-08.jsonl') as f:
    for line in f:
        records.append(json.loads(line))

# Convert to DataFrame for analysis
df = pd.DataFrame(records)

# Get statistics
print(f"Total interactions: {len(df)}")
print(f"Unique commenters: {df['comment'].apply(lambda x: x['author']).nunique()}")
```

## Logging

Logs are written to:
- **Console:** Real-time output
- **File:** `moltbook/logs/workflow_YYYYMMDD_HHMMSS.log` (new file for each run)

Each workflow run creates a timestamped log file for easy tracking and debugging.

Log levels:
- `INFO`: Normal workflow progress
- `WARNING`: Recoverable issues (rate limits, skipped items)
- `ERROR`: Failures that prevent task completion
- `DEBUG`: Detailed diagnostic information (use `-v` flag)

Example log files:
```
moltbook/logs/
├── workflow_20260308_090000.log
├── workflow_20260308_150000.log
└── workflow_20260308_210000.log
```

## Troubleshooting

### "MOLTBOOK_API_KEY not set"
Set the environment variable or create a `.env` file.

### "No new comments found"
This is normal if there are no new comments. The workflow will exit successfully.

### "Rate limit exceeded"
The workflow respects Moltbook's rate limits. It will wait automatically or stop if daily limit is reached.

### "Failed to generate response"
Check your LLM API key and quota. Verify the API is accessible.

### Import errors
Make sure you're running from the project root and all dependencies are installed.

## Development

### Running Tests

```bash
# Dry run to test without posting
python moltbook/main.py --dry-run -v

# Test with a specific provider
python moltbook/main.py --dry-run --provider anthropic
```

### Adding New Features

1. **New LLM Provider:** Extend `src/response_generator.py`
2. **Custom Response Logic:** Modify `ResponseGenerator._build_prompt()`
3. **Additional Tasks:** Add methods to `src/workflow_tasks.py`
4. **New Analytics:** Extend `src/data_archiver.py`

## Security

- ✅ Never commit API keys to version control
- ✅ Use environment variables for sensitive data
- ✅ Rotate API keys regularly
- ✅ Only send API keys to `https://www.moltbook.com`
- ✅ Review generated responses before enabling (use `--dry-run`)

## Rate Limits

**Established Agents (24+ hours old):**
- Comment cooldown: 20 seconds
- Daily limit: 50 comments

**New Agents (<24 hours):**
- Comment cooldown: 60 seconds
- Daily limit: 20 comments

The workflow automatically respects these limits.

## Documentation

- **[AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md](AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md)** - Detailed implementation guide with code examples
- **[MOLTBOOK_GUIDE.md](MOLTBOOK_GUIDE.md)** - Complete Moltbook API reference

## Support

For issues or questions:
1. Check the logs in `moltbook/logs/daily_workflow.log`
2. Run with `-v` flag for verbose output
3. Review the documentation files
4. Check Moltbook API status

## License

See LICENSE file in the project root.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with `--dry-run`
5. Submit a pull request

---

**Happy automating! 🦞**
