"""
Response generation using LLM providers.

This module handles generating witty, contextual responses to comments
using OpenAI or Anthropic APIs.
"""

import logging
from typing import Dict, Optional

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
        
        if provider == "openai":
            if not Settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            
            from openai import OpenAI
            self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
            self.model = Settings.OPENAI_MODEL
            
        elif provider == "anthropic":
            if not Settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set")
            
            from anthropic import Anthropic
            self.client = Anthropic(api_key=Settings.ANTHROPIC_API_KEY)
            self.model = Settings.ANTHROPIC_MODEL
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Initialized {provider} response generator with model {self.model}")
    
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
            
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a witty AI agent on Moltbook. "
                                     "Respond naturally and engagingly to comments."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=Settings.RESPONSE_MAX_TOKENS,
                    temperature=Settings.RESPONSE_TEMPERATURE
                )
                return response.choices[0].message.content.strip()
                
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=Settings.RESPONSE_MAX_TOKENS,
                    temperature=Settings.RESPONSE_TEMPERATURE,
                    system="You are a witty AI agent on Moltbook. "
                           "Respond naturally and engagingly to comments.",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
