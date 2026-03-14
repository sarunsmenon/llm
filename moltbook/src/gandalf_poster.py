"""
Gandalf quote generator and poster.

This module generates Gandalf quotes from Lord of the Rings/Hobbit
using OpenRouter API and posts them to Moltbook.
"""

import logging
import requests
from typing import Optional
import os
import random
import json
from datetime import datetime, timezone
from pathlib import Path

from config import Settings

logger = logging.getLogger(__name__)


class GandalfPoster:
    """Generate and post Gandalf quotes."""
    
    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize Gandalf poster.
        
        Args:
            state_file: Path to state file for tracking last run date.
                       Defaults to moltbook/data/state/gandalf_state.json
        """
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for Task 7")
        
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        
        # Set up state file for tracking last run date
        if state_file is None:
            state_file = Path(__file__).parent.parent / "data" / "state" / "gandalf_state.json"
        self.state_file = state_file
        
        logger.info("Initialized Gandalf poster with OpenRouter")
    
    def _load_last_run_date(self) -> Optional[str]:
        """
        Load the last run date from state file.
        
        Returns:
            Last run date in YYYY-MM-DD format, or None if never run
        """
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_run_date')
        except Exception as e:
            logger.error(f"Error loading last run date: {e}")
        return None
    
    def _save_last_run_date(self, date_str: str):
        """
        Save the last run date to state file.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump({
                    'last_run_date': date_str,
                    'last_run_timestamp': datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            
            logger.info(f"Saved last run date: {date_str}")
            
        except Exception as e:
            logger.error(f"Error saving last run date: {e}")
    
    def _should_run_today(self) -> bool:
        """
        Check if the Gandalf poster should run today.
        
        Returns:
            True if it should run (hasn't run today yet), False otherwise
        """
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        last_run_date = self._load_last_run_date()
        
        if last_run_date is None:
            logger.info("No previous run found, will run today")
            return True
        
        if last_run_date == today:
            logger.info(f"Already ran today ({today}), skipping")
            return False
        
        logger.info(f"Last run was {last_run_date}, will run today ({today})")
        return True
    
    def generate_gandalf_quote(self) -> Optional[dict]:
        """
        Generate a Gandalf quote using OpenRouter API.
        
        Returns:
            Dictionary with 'title' and 'content' for the post, or None if failed
        """
        try:
            # Add variety by randomly selecting different aspects
            themes = [
                "about courage and bravery",
                "about wisdom and knowledge", 
                "about hope in dark times",
                "that is humorous or witty",
                "about friendship and loyalty",
                "about the nature of power",
                "about death and mortality",
                "about the small things that matter",
                "about adventure and the unknown",
                "about patience and timing"
            ]
            
            sources = [
                "The Hobbit",
                "The Fellowship of the Ring",
                "The Two Towers", 
                "The Return of the King"
            ]
            
            theme = random.choice(themes)
            preferred_source = random.choice(sources)
            
            prompt = f"""Generate a memorable Gandalf quote from {preferred_source} (or another book if needed) that is {theme}.

Requirements:
1. Choose a quote that fits the theme: {theme}
2. Provide the exact quote (try to pick a less commonly quoted one for variety)
3. Mention which book/movie it's from
4. Add a brief (1-2 sentence) reflection on why this quote resonates

Format your response as:
QUOTE: [the actual quote]
SOURCE: [book name]
REFLECTION: [your brief reflection]"""

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "anthropic/claude-3.5-sonnet",  # Using Claude via OpenRouter
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.9
            }
            
            response = requests.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            generated_text = data['choices'][0]['message']['content']
            
            # Parse the response
            lines = generated_text.strip().split('\n')
            quote = ""
            source = ""
            reflection = ""
            
            for line in lines:
                if line.startswith('QUOTE:'):
                    quote = line.replace('QUOTE:', '').strip()
                elif line.startswith('SOURCE:'):
                    source = line.replace('SOURCE:', '').strip()
                elif line.startswith('REFLECTION:'):
                    reflection = line.replace('REFLECTION:', '').strip()
            
            if not quote:
                logger.error("Failed to parse quote from generated text")
                return None
            
            # Create post content
            title = f"Gandalf's Wisdom: {quote[:50]}..." if len(quote) > 50 else f"Gandalf's Wisdom"
            content = f'"{quote}"\n\n— Gandalf'
            if source:
                content += f', {source}'
            if reflection:
                content += f'\n\n{reflection}'
            
            logger.info(f"Generated Gandalf quote: {quote[:100]}...")
            
            return {
                'title': title,
                'content': content
            }
            
        except Exception as e:
            logger.error(f"Error generating Gandalf quote: {e}")
            return None
    
    def post_gandalf_quote(self, client) -> bool:
        """
        Generate and post a Gandalf quote to Moltbook.
        Only runs once per day. If already run today, skips execution.
        
        Args:
            client: MoltbookClient instance
        
        Returns:
            True if successful, False otherwise (including if skipped due to already running today)
        """
        # Check if we should run today
        if not self._should_run_today():
            logger.info("Gandalf poster already ran today, skipping")
            return False
        
        logger.info("Generating Gandalf quote...")
        
        quote_data = self.generate_gandalf_quote()
        if not quote_data:
            logger.error("Failed to generate Gandalf quote")
            return False
        
        try:
            # Post to Moltbook
            payload = {
                "submolt_name": "lotr",
                "title": quote_data['title'],
                "content": quote_data['content'],
                "type": "text"
            }
            
            response = requests.post(
                f"{client.base_url}/posts",
                headers=client.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            post_data = response.json()
            
            # Log rate limit info if present
            if 'retry_after_minutes' in post_data:
                logger.info(f"Post cooldown: {post_data['retry_after_minutes']} minutes")
            
            logger.info(f"Successfully posted Gandalf quote to /m/lotr")
            logger.info(f"Title: {quote_data['title']}")
            
            # Save today's date as the last run date
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            self._save_last_run_date(today)
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error posting Gandalf quote: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
