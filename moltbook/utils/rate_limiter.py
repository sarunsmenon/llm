"""
Rate limiting utilities for Moltbook API compliance.

This module ensures we respect Moltbook's rate limits for comments.
"""

import time
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handle rate limiting for Moltbook API requests."""
    
    def __init__(self, cooldown_seconds: int = 20, daily_limit: int = 50):
        """
        Initialize rate limiter.
        
        Args:
            cooldown_seconds: Seconds to wait between comments
            daily_limit: Maximum comments allowed per day
        """
        self.cooldown_seconds = cooldown_seconds
        self.daily_limit = daily_limit
        self.last_comment_time = 0.0
        self.daily_comment_count = 0
    
    def can_comment(self) -> Tuple[bool, Optional[int]]:
        """
        Check if we can post a comment now.
        
        Returns:
            Tuple of (can_comment, wait_seconds)
            - can_comment: True if we can comment now
            - wait_seconds: Seconds to wait if can't comment (None if daily limit reached)
        """
        current_time = time.time()
        time_since_last = current_time - self.last_comment_time
        
        # Check cooldown
        if time_since_last < self.cooldown_seconds:
            wait_time = int(self.cooldown_seconds - time_since_last) + 1
            logger.debug(f"Cooldown active: wait {wait_time}s")
            return False, wait_time
        
        # Check daily limit
        if self.daily_comment_count >= self.daily_limit:
            logger.warning(f"Daily comment limit reached ({self.daily_limit})")
            return False, None
        
        return True, 0
    
    def wait_if_needed(self) -> bool:
        """
        Wait if necessary before posting a comment.
        
        Returns:
            True if ready to comment, False if daily limit reached
        """
        can_post, wait_time = self.can_comment()
        
        if not can_post:
            if wait_time is None:
                return False  # Daily limit reached
            
            logger.info(f"Rate limit: waiting {wait_time} seconds...")
            time.sleep(wait_time)
        
        return True
    
    def record_comment(self):
        """Record that a comment was posted."""
        self.last_comment_time = time.time()
        self.daily_comment_count += 1
        logger.debug(
            f"Comment recorded. Daily count: {self.daily_comment_count}/{self.daily_limit}"
        )
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with rate limit stats
        """
        return {
            'daily_count': self.daily_comment_count,
            'daily_limit': self.daily_limit,
            'remaining': self.daily_limit - self.daily_comment_count,
            'cooldown_seconds': self.cooldown_seconds
        }
