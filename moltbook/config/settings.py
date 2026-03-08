"""
Configuration settings for Moltbook workflow.

This module manages all configuration settings including API keys,
file paths, and workflow parameters.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file at repo root
repo_root = Path(__file__).parent.parent.parent
dotenv_path = repo_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)


class Settings:
    """Central configuration for Moltbook workflow."""
    
    # Base directories
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Data subdirectories
    ARCHIVES_DIR = DATA_DIR / "archives"
    STATE_DIR = DATA_DIR / "state"
    
    # API Configuration
    MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
    MOLTBOOK_API_KEY = os.getenv("MOLTBOOK_API_KEY")
    
    # LLM Provider Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Default LLM Models
    OPENAI_MODEL = "gpt-4-turbo-preview"
    ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
    
    # Rate Limiting (for established agents)
    COMMENT_COOLDOWN_SECONDS = 20
    DAILY_COMMENT_LIMIT = 50
    
    # Workflow Settings
    MAX_POSTS_TO_CHECK = 50
    MAX_COMMENTS_PER_POST = 100
    RESPONSE_MAX_TOKENS = 200
    RESPONSE_TEMPERATURE = 0.8
    
    # State Files
    PROCESSED_COMMENTS_FILE = STATE_DIR / "processed_comments.json"
    
    # Logging
    LOG_FILE = LOGS_DIR / "daily_workflow.log"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_LEVEL = "INFO"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required settings are present.
        
        Returns:
            bool: True if all required settings are valid
        
        Raises:
            ValueError: If required settings are missing
        """
        if not cls.MOLTBOOK_API_KEY:
            raise ValueError("MOLTBOOK_API_KEY environment variable is required")
        
        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "At least one LLM API key is required: "
                "OPENAI_API_KEY or ANTHROPIC_API_KEY"
            )
        
        return True
    
    @classmethod
    def create_directories(cls):
        """Create all necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.LOGS_DIR, cls.ARCHIVES_DIR, cls.STATE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_headers(cls) -> dict:
        """
        Get HTTP headers for Moltbook API requests.
        
        Returns:
            dict: Headers including authorization
        """
        return {
            "Authorization": f"Bearer {cls.MOLTBOOK_API_KEY}",
            "Content-Type": "application/json"
        }
