"""
Data archival for daily interactions.

This module handles archiving all interactions in JSONL format
for analytics and historical tracking.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, date, timezone
from typing import List, Dict, Any

from config import Settings

logger = logging.getLogger(__name__)


class DataArchiver:
    """Archive daily interaction data in JSONL format."""
    
    def __init__(self):
        """Initialize data archiver."""
        self.archive_dir = Settings.ARCHIVES_DIR
        self.workflow_run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    def _get_archive_file(self, target_date: date = None) -> Path:
        """
        Get archive file path for a specific date.
        
        Args:
            target_date: Date for archive file (defaults to today)
        
        Returns:
            Path to archive file
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        
        # Organize by year/month for better file management
        year_month_dir = self.archive_dir / str(target_date.year) / f"{target_date.month:02d}"
        year_month_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"moltbook_interactions_{target_date.isoformat()}.jsonl"
        return year_month_dir / filename
    
    def archive_interaction(
        self,
        interaction_type: str,
        comment_data: Dict,
        reply_data: Dict = None,
        success: bool = True,
        error: str = None
    ):
        """
        Archive an interaction.
        
        Args:
            interaction_type: Type ('comment_received' or 'reply_sent')
            comment_data: Comment information
            reply_data: Reply information (if applicable)
            success: Whether the interaction was successful
            error: Error message if failed
        """
        now = datetime.now(timezone.utc)
        
        record = {
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "date": now.date().isoformat(),
            "interaction_type": interaction_type,
            "workflow_run_id": self.workflow_run_id,
            "post": {
                "id": comment_data.get('post_id'),
                "title": comment_data.get('post_title'),
                "content": comment_data.get('post_content', ''),
                "submolt": comment_data.get('submolt_name'),
                "url": f"https://www.moltbook.com/m/{comment_data.get('submolt_name', 'unknown')}/{comment_data.get('post_id')}"
            },
            "comment": {
                "id": comment_data.get('comment_id'),
                "content": comment_data.get('comment_content'),
                "author": comment_data.get('comment_author'),
                "parent_id": comment_data.get('parent_id'),
                "created_at": comment_data.get('created_at'),
                "upvotes": comment_data.get('upvotes', 0),
                "is_direct_reply": comment_data.get('is_direct_reply', True),
                "thread_depth": comment_data.get('thread_depth', 1)
            },
            "workflow_metadata": {
                "success": success,
                "error": error
            }
        }
        
        # Add reply data if present
        if reply_data:
            record["reply"] = {
                "content": reply_data.get('generated_response'),
                "generated_by": reply_data.get('generated_by'),
                "generated_at": reply_data.get('generated_at')
            }
        
        self._append_record(record)
    
    def _append_record(self, record: Dict[str, Any]):
        """
        Append a record to the archive file.
        
        Args:
            record: Interaction record to append
        """
        try:
            archive_file = self._get_archive_file()
            
            # Append as single line JSON
            with open(archive_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            logger.debug(f"Archived interaction to {archive_file}")
                
        except Exception as e:
            logger.error(f"Error archiving record: {e}")
    
    def get_daily_summary(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get summary statistics for a specific day.
        
        Args:
            target_date: Date to summarize (defaults to today)
        
        Returns:
            Summary statistics dictionary
        """
        archive_file = self._get_archive_file(target_date)
        
        if not archive_file.exists():
            return {
                "date": (target_date or datetime.now(timezone.utc).date()).isoformat(),
                "total_interactions": 0,
                "comments_received": 0,
                "replies_sent": 0,
                "unique_posts": 0,
                "unique_commenters": 0,
                "submolts": []
            }
        
        comments_received = 0
        replies_sent = 0
        unique_posts = set()
        unique_commenters = set()
        submolts = set()
        
        try:
            with open(archive_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line)
                    
                    if record['interaction_type'] == 'comment_received':
                        comments_received += 1
                    elif record['interaction_type'] == 'reply_sent':
                        replies_sent += 1
                    
                    unique_posts.add(record['post']['id'])
                    unique_commenters.add(record['comment']['author'])
                    submolts.add(record['post']['submolt'])
        
        except Exception as e:
            logger.error(f"Error reading archive file: {e}")
        
        return {
            "date": (target_date or datetime.now(timezone.utc).date()).isoformat(),
            "total_interactions": comments_received + replies_sent,
            "comments_received": comments_received,
            "replies_sent": replies_sent,
            "unique_posts": len(unique_posts),
            "unique_commenters": len(unique_commenters),
            "submolts": sorted(list(submolts))
        }
