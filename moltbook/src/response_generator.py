"""
Response generation using LLM providers.

This module handles generating witty, contextual responses to comments
using OpenAI or Anthropic APIs via OpenRouter.
"""

import logging
import requests
from typing import Dict, Optional
import os

from config import Settings

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate responses using LLM providers."""
    
    def __init__(self, provider: str = "openai"):
        """
        Initialize response generator.
        
        Args:
            provider: LLM provider ('openai' or 'anthropic')
        
        Raises:
            ValueError: If provider is invalid or API key is missing
        """
        self.provider = provider
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        
        # Set model based on provider preference
        if provider == "openai":
            self.model = Settings.OPENAI_MODEL if hasattr(Settings, 'OPENAI_MODEL') else "openai/gpt-4-turbo"
        elif provider == "anthropic":
            self.model = Settings.ANTHROPIC_MODEL if hasattr(Settings, 'ANTHROPIC_MODEL') else "anthropic/claude-3.5-sonnet"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Initialized {provider} response generator with model {self.model} via OpenRouter")
    
    def _build_prompt(self, comment_data: Dict) -> str:
        """
        Build prompt for LLM.
        
        Args:
            comment_data: Enriched comment data with context
        
        Returns:
            Formatted prompt string
        """
        post_title = comment_data.get('post_title', '')
        post_content = comment_data.get('post_content', '')
        comment_content = comment_data.get('comment_content', '')
        comment_author = comment_data.get('comment_author', 'Unknown')
        
        prompt = f"""You are responding to a comment on your Moltbook post (a social network for AI agents).

YOUR ORIGINAL POST:
Title: {post_title}
Content: {post_content}

COMMENT FROM @{comment_author}:
{comment_content}
"""
        
        # Add conversation thread if exists
        thread = comment_data.get('conversation_thread', [])
        if thread and len(thread) > 1:
            prompt += "\n\nCONVERSATION THREAD:\n"
            for i, msg in enumerate(thread[:-1], 1):
                author = msg.get('author', {}).get('name', 'Unknown')
                content = msg.get('content', '')
                prompt += f"{i}. @{author}: {content}\n"
        
        prompt += """

Generate a witty, engaging, and contextually appropriate response. Guidelines:
- Be conversational and authentic
- Show personality but remain respectful
- Keep it concise (1-3 sentences ideal)
- Add value to the conversation
- Use humor when appropriate
- Don't be overly formal
- Engage with the specific points raised

Your response:"""
        
        return prompt
    
    def generate_response(self, comment_data: Dict) -> Optional[str]:
        """
        Generate response using LLM.
        
        Args:
            comment_data: Enriched comment data with context
        
        Returns:
            Generated response text or None if generation fails
        """
        try:
            prompt = self._build_prompt(comment_data)
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            # Build messages with system prompt
            messages = [
                {
                    "role": "system",
                    "content": "You are a witty AI agent on Moltbook. "
                             "Respond naturally and engagingly to comments."
                },
                {"role": "user", "content": prompt}
            ]
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": Settings.RESPONSE_MAX_TOKENS if hasattr(Settings, 'RESPONSE_MAX_TOKENS') else 150,
                "temperature": Settings.RESPONSE_TEMPERATURE if hasattr(Settings, 'RESPONSE_TEMPERATURE') else 0.8
            }
            
            response = requests.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            generated_text = data['choices'][0]['message']['content'].strip()
            
            logger.info(f"Generated response: {generated_text[:100]}...")
            return generated_text
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
