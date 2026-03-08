"""
State management utilities for tracking processed comments.

This module handles persistent state to avoid processing the same
comments multiple times.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent state for processed comments."""
    
    def __init__(self, state_file: Path):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to the state file
        """
        self.state_file = state_file
        self.processed_comments: Set[str] = self._load_state()
    
    def _load_state(self) -> Set[str]:
        """
        Load processed comment IDs from file.
        
        Returns:
            Set of processed comment IDs
        """
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    comment_ids = set(data.get('processed_comment_ids', []))
                    logger.info(f"Loaded {len(comment_ids)} processed comments from state")
                    return comment_ids
        except Exception as e:
            logger.error(f"Error loading state: {e}")
        
        return set()
    
    def _save_state(self):
        """Save processed comment IDs to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump({
                    'processed_comment_ids': list(self.processed_comments),
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'total_processed': len(self.processed_comments)
                }, f, indent=2)
            
            logger.debug(f"Saved state with {len(self.processed_comments)} processed comments")
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def is_processed(self, comment_id: str) -> bool:
        """
        Check if a comment has been processed.
        
        Args:
            comment_id: ID of the comment to check
        
        Returns:
            True if comment has been processed, False otherwise
        """
        return comment_id in self.processed_comments
    
    def mark_processed(self, comment_id: str):
        """
        Mark a comment as processed.
        
        Args:
            comment_id: ID of the comment to mark as processed
        """
        self.processed_comments.add(comment_id)
        self._save_state()
        logger.debug(f"Marked comment {comment_id} as processed")
    
    def get_stats(self) -> dict:
        """
        Get statistics about processed comments.
        
        Returns:
            Dictionary with state statistics
        """
        return {
            'total_processed': len(self.processed_comments),
            'state_file': str(self.state_file),
            'file_exists': self.state_file.exists()
        }
