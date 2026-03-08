"""
Gandalf quote generator and poster.

This module generates Gandalf quotes from Lord of the Rings/Hobbit
using OpenRouter API and posts them to Moltbook.
"""

import logging
import requests
from typing import Optional
import os

from config import Settings

logger = logging.getLogger(__name__)


class GandalfPoster:
    """Generate and post Gandalf quotes."""
    
    def __init__(self):
        """Initialize Gandalf poster."""
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for Task 7")
        
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        logger.info("Initialized Gandalf poster with OpenRouter")
    
    def generate_gandalf_quote(self) -> Optional[dict]:
        """
        Generate a Gandalf quote using OpenRouter API.
        
        Returns:
            Dictionary with 'title' and 'content' for the post, or None if failed
        """
        try:
            prompt = """Generate a memorable Gandalf quote from either The Hobbit or The Lord of the Rings trilogy.

Requirements:
1. Choose a quote that is wise, inspiring, or humorous
2. Provide the exact quote
3. Mention which book/movie it's from
4. Add a brief (1-2 sentence) reflection on why this quote resonates

Format your response as:
QUOTE: [the actual quote]
SOURCE: [The Hobbit / The Fellowship of the Ring / The Two Towers / The Return of the King]
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
        
        Args:
            client: MoltbookClient instance
        
        Returns:
            True if successful, False otherwise
        """
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
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error posting Gandalf quote: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
