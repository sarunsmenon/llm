"""
Workflow tasks implementation.

This module implements all 6 tasks of the Moltbook automated response workflow.
"""

import logging
from typing import List, Dict
from datetime import datetime, timezone

from src.moltbook_client import MoltbookClient
from src.response_generator import ResponseGenerator
from src.gandalf_poster import GandalfPoster
from utils import StateManager, RateLimiter
from config import Settings

logger = logging.getLogger(__name__)


class WorkflowTasks:
    """Implementation of all workflow tasks."""
    
    def __init__(
        self,
        client: MoltbookClient,
        state_manager: StateManager,
        rate_limiter: RateLimiter
    ):
        """
        Initialize workflow tasks.
        
        Args:
            client: Moltbook API client
            state_manager: State manager for tracking processed comments
            rate_limiter: Rate limiter for API compliance
        """
        self.client = client
        self.state = state_manager
        self.rate_limiter = rate_limiter
    
    def task1_check_new_comments(self) -> List[Dict]:
        """
        Task 1: Check for new comments on your posts.
        
        Returns:
            List of new comment dictionaries with metadata
        """
        logger.info("=" * 80)
        logger.info("TASK 1: Checking for new comments on your posts")
        logger.info("=" * 80)
        
        # Get your posts
        my_posts = self.client.get_my_posts()
        
        new_comments = []
        
        for post in my_posts:
            post_id = post.get('id')
            post_title = post.get('title', '')
            post_content = post.get('content', '')
            submolt = post.get('submolt', {})
            submolt_name = submolt.get('name') if isinstance(submolt, dict) else str(submolt)
            
            # Get comments for this post
            comments = self.client.get_comments_for_post(post_id)
            
            for comment in comments:
                comment_id = comment.get('id')
                author = comment.get('author', {})
                author_name = author.get('name') if isinstance(author, dict) else str(author)
                
                # Skip if this is your own comment
                if author_name == self.client.agent_name:
                    continue
                
                # Skip if already processed
                if self.state.is_processed(comment_id):
                    continue
                
                # This is a new comment!
                new_comments.append({
                    'comment_id': comment_id,
                    'comment_content': comment.get('content', ''),
                    'comment_author': author_name,
                    'parent_id': comment.get('parent_id'),
                    'post_id': post_id,
                    'post_title': post_title,
                    'post_content': post_content,
                    'submolt_name': submolt_name,
                    'created_at': comment.get('created_at'),
                    'upvotes': comment.get('upvotes', 0)
                })
        
        logger.info(f"✓ Task 1 Complete: Found {len(new_comments)} new comments")
        return new_comments
    
    def task2_build_context(self, new_comments: List[Dict]) -> List[Dict]:
        """
        Task 2: Understand what posts are being replied to.
        
        Args:
            new_comments: List of new comments from Task 1
        
        Returns:
            List of comments enriched with full context
        """
        logger.info("=" * 80)
        logger.info("TASK 2: Understanding what posts are being replied to")
        logger.info("=" * 80)
        
        enriched_comments = []
        
        for comment_data in new_comments:
            post_id = comment_data['post_id']
            
            # Get all comments on the post for context
            all_comments = self.client.get_comments_for_post(post_id)
            
            # Find the specific comment in the list
            comment = next(
                (c for c in all_comments if c.get('id') == comment_data['comment_id']),
                None
            )
            
            if not comment:
                logger.warning(f"Could not find comment {comment_data['comment_id']}")
                continue
            
            # Build conversation thread
            thread = self._build_thread(comment, all_comments)
            
            # Enrich comment data
            enriched = comment_data.copy()
            enriched['conversation_thread'] = thread
            enriched['is_direct_reply'] = comment_data['parent_id'] is None
            enriched['thread_depth'] = len(thread)
            
            enriched_comments.append(enriched)
            
            logger.debug(
                f"Comment {comment_data['comment_id']}: "
                f"{'Direct reply' if enriched['is_direct_reply'] else f'Thread depth {enriched['thread_depth']}'}"
            )
        
        logger.info(f"✓ Task 2 Complete: Built context for {len(enriched_comments)} comments")
        return enriched_comments
    
    def _build_thread(self, comment: Dict, all_comments: List[Dict]) -> List[Dict]:
        """
        Build conversation thread for a comment.
        
        Args:
            comment: The comment to build thread for
            all_comments: All comments on the post
        
        Returns:
            List of comments in thread order (oldest to newest)
        """
        thread = []
        current = comment
        
        while current:
            thread.insert(0, current)
            
            parent_id = current.get('parent_id')
            if not parent_id:
                break
            
            current = next(
                (c for c in all_comments if c.get('id') == parent_id),
                None
            )
        
        return thread
    
    def task3_generate_responses(
        self,
        enriched_comments: List[Dict],
        provider: str = "openai"
    ) -> List[Dict]:
        """
        Task 3: Generate contextual responses.
        
        Args:
            enriched_comments: Comments with full context from Task 2
            provider: LLM provider to use
        
        Returns:
            List of comments with generated responses
        """
        logger.info("=" * 80)
        logger.info("TASK 3: Generating contextual responses")
        logger.info("=" * 80)
        
        generator = ResponseGenerator(provider=provider)
        comments_with_responses = []
        
        for comment in enriched_comments:
            logger.info(f"Generating response for comment {comment['comment_id']}...")
            
            response_text = generator.generate_response(comment)
            
            if response_text:
                comment_with_response = comment.copy()
                comment_with_response['generated_response'] = response_text
                comment_with_response['generated_by'] = f"{provider}:{generator.model}"
                comment_with_response['generated_at'] = datetime.now(timezone.utc).isoformat()
                comments_with_responses.append(comment_with_response)
                
                logger.info(f"Generated: {response_text[:100]}...")
            else:
                logger.warning(f"Failed to generate response for {comment['comment_id']}")
        
        logger.info(f"✓ Task 3 Complete: Generated {len(comments_with_responses)} responses")
        return comments_with_responses
    
    def task4_send_replies(
        self,
        comments_with_responses: List[Dict],
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Task 4: Send replies to comments.
        
        Args:
            comments_with_responses: Comments with generated responses from Task 3
            dry_run: If True, don't actually post replies
        
        Returns:
            Dictionary with success/failure counts
        """
        logger.info("=" * 80)
        logger.info("TASK 4: Sending replies to comments")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("DRY RUN MODE - Not actually posting replies")
        
        results = {'success': 0, 'failed': 0}
        
        for comment in comments_with_responses:
            comment_id = comment['comment_id']
            post_id = comment['post_id']
            response_text = comment['generated_response']
            
            logger.info(f"Posting reply to comment {comment_id}...")
            
            if dry_run:
                logger.info(f"Would post: {response_text}")
                results['success'] += 1
                continue
            
            # Check rate limits
            if not self.rate_limiter.wait_if_needed():
                logger.error("Daily comment limit reached")
                results['failed'] += 1
                continue
            
            # Post the reply
            response = self.client.post_comment(
                post_id=post_id,
                content=response_text,
                parent_id=comment_id
            )
            
            if response:
                # Record successful comment
                self.rate_limiter.record_comment()
                self.state.mark_processed(comment_id)
                results['success'] += 1
            else:
                results['failed'] += 1
        
        logger.info(
            f"✓ Task 4 Complete: {results['success']} successful, "
            f"{results['failed']} failed"
        )
        
        return results
    
    def task7_post_gandalf_quote(self, dry_run: bool = False) -> bool:
        """
        Task 7: Generate and post a random Gandalf quote to /m/lotr.
        
        Uses OpenRouter API to generate an authentic Gandalf quote from
        The Hobbit or Lord of the Rings, then posts it to the 'lotr' submolt.
        
        Args:
            dry_run: If True, don't actually post the quote
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("TASK 7: Posting Gandalf quote to /m/lotr")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("DRY RUN MODE - Not actually posting quote")
        
        try:
            # Initialize Gandalf poster
            gandalf = GandalfPoster()
            
            if dry_run:
                # Just generate the quote to test
                quote_data = gandalf.generate_gandalf_quote()
                if quote_data:
                    logger.info(f"Would post: {quote_data['title']}")
                    logger.info(f"Content: {quote_data['content'][:200]}...")
                    logger.info("✓ Task 7 Complete: Successfully generated Gandalf quote (dry run)")
                    return True
                else:
                    logger.warning("✗ Task 7 Failed: Could not generate Gandalf quote")
                    return False
            else:
                # Generate and post quote
                success = gandalf.post_gandalf_quote(self.client)
                
                if success:
                    logger.info("✓ Task 7 Complete: Successfully posted Gandalf quote")
                else:
                    logger.warning("✗ Task 7 Failed: Could not post Gandalf quote")
                
                return success
            
        except Exception as e:
            logger.error(f"✗ Task 7 Failed with error: {e}", exc_info=True)
            return False
