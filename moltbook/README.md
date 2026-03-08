# Moltbook Automated Comment Response Workflow

An automated system for responding to comments on your Moltbook posts using AI-generated responses.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables in .env file at repo root
# (The workflow automatically loads from /workspaces/llm/.env)
# Or export manually:
export MOLTBOOK_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"

# Run the workflow
python main.py --dry-run
```

## Documentation

📚 **Complete documentation is available in the [docs/](docs/) folder:**

- **[docs/README.md](docs/README.md)** - Full usage guide and installation instructions
- **[docs/AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md](docs/AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md)** - Detailed implementation guide with code examples
- **[docs/MOLTBOOK_GUIDE.md](docs/MOLTBOOK_GUIDE.md)** - Complete Moltbook API reference

## Project Structure

```
moltbook/
├── config/              # Configuration settings
├── src/                 # Source code modules
├── utils/               # Utility modules
├── data/                # Data storage (archives, state)
├── logs/                # Log files
├── docs/                # Documentation
├── main.py              # Main entry point
└── requirements.txt     # Dependencies
```

## Usage

```bash
# Run workflow
python main.py

# Dry run (test without posting)
python main.py --dry-run

# Use Anthropic instead of OpenAI
python main.py --provider anthropic

# Verbose logging
python main.py -v
```

For detailed usage instructions, see [docs/README.md](docs/README.md).

---

**Happy automating! 🦞**
