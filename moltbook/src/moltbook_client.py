"""
Moltbook API client for interacting with the Moltbook platform.

This module provides a clean interface to the Moltbook API for
fetching posts, comments, and posting replies.
"""

import requests
import logging
from typing import List, Dict, Optional

from config import Settings

logger = logging.getLogger(__name__)


class MoltbookClient:
    """Client for interacting with Moltbook API."""
    
    def __init__(self):
        """Initialize Moltbook client."""
        self.base_url = Settings.MOLTBOOK_BASE_URL
        self.headers = Settings.get_headers()
        self.agent_name: Optional[str] = None
    
    def get_agent_profile(self) -> Dict:
        """
        Get the authenticated agent's profile.
        
        Returns:
            Agent profile dictionary
        
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/agents/me",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            agent_data = response.json()
            
            # The API returns data nested under 'agent' key
            agent_info = agent_data.get('agent', {})
            
            # Try different possible keys for agent name
            self.agent_name = (
                agent_info.get('name') or 
                agent_info.get('username') or 
                agent_info.get('display_name') or
                agent_data.get('name') or  # Fallback to top level
                agent_data.get('username')
            )
            
            if not self.agent_name:
                logger.warning(f"Could not find agent name in response. Keys available: {list(agent_data.keys())}")
                logger.debug(f"Full agent data: {agent_data}")
            
            logger.info(f"Retrieved agent profile: {self.agent_name}")
            return agent_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching agent profile: {e}")
            raise
    
    def get_my_posts_with_activity(self) -> List[Dict]:
        """
        Get posts that have activity (comments) using /home endpoint.
        
        This is the recommended approach per Moltbook API guide.
        
        Returns:
            List of post dictionaries with activity metadata
        """
        try:
            response = requests.get(
                f"{self.base_url}/home",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            home_data = response.json()
            
            # Get activity on your posts
            activity_list = home_data.get('activity_on_your_posts', [])
            
            posts_with_activity = []
            for activity in activity_list:
                # Create a post dict from activity data
                post_dict = {
                    'id': activity.get('post_id'),
                    'title': activity.get('post_title'),
                    'submolt': {'name': activity.get('submolt_name')},
                    'submolt_name': activity.get('submolt_name'),
                    'has_new_comments': activity.get('new_notification_count', 0) > 0,
                    'new_comment_count': activity.get('new_notification_count', 0),
                    'latest_commenters': activity.get('latest_commenters', [])
                }
                posts_with_activity.append(post_dict)
            
            logger.info(f"Retrieved {len(posts_with_activity)} posts with activity from /home")
            return posts_with_activity
            
        except requests.RequestException as e:
            logger.error(f"Error fetching posts from /home: {e}")
            return []
    
    def get_my_posts(self, limit: int = None) -> List[Dict]:
        """
        Retrieve posts created by the authenticated agent.
        
        Args:
            limit: Maximum number of posts to retrieve
        
        Returns:
            List of post dictionaries
        """
        if limit is None:
            limit = Settings.MAX_POSTS_TO_CHECK
        
        # First try to get posts with activity from /home
        # This is more efficient as it only returns posts that have comments
        posts_with_activity = self.get_my_posts_with_activity()
        if posts_with_activity:
            logger.info(f"Using {len(posts_with_activity)} posts from /home (posts with activity)")
            return posts_with_activity
        
        # Fallback: search through feed/posts for all your posts
        try:
            # Ensure we have agent name
            if not self.agent_name:
                self.get_agent_profile()
            
            posts = []
            cursor = None
            pages_checked = 0
            max_pages = 10
            
            while len(posts) < limit and pages_checked < max_pages:
                params = {'sort': 'new', 'limit': 25}
                if cursor:
                    params['cursor'] = cursor
                
                response = requests.get(
                    f"{self.base_url}/posts",
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                all_posts = data.get('posts', [])
                logger.debug(f"Posts page {pages_checked + 1}: returned {len(all_posts)} total posts")
                
                # Filter for your posts
                my_posts = [
                    p for p in all_posts
                    if p.get('author', {}).get('name') == self.agent_name
                ]
                
                if my_posts:
                    logger.debug(f"Found {len(my_posts)} of your posts in this page")
                
                posts.extend(my_posts)
                pages_checked += 1
                
                cursor = data.get('next_cursor')
                if not cursor:
                    break
            
            result = posts[:limit]
            logger.info(f"Retrieved {len(result)} posts from /posts (checked {pages_checked} pages)")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Error fetching posts: {e}")
            return []
    
    def get_comments_for_post(self, post_id: str) -> List[Dict]:
        """
        Retrieve all comments for a specific post.
        
        Args:
            post_id: ID of the post
        
        Returns:
            List of comment dictionaries
        """
        try:
            response = requests.get(
                f"{self.base_url}/posts/{post_id}/comments",
                headers=self.headers,
                params={
                    'sort': 'new',
                    'limit': Settings.MAX_COMMENTS_PER_POST
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            comments = data.get('comments', [])
            
            logger.debug(f"Retrieved {len(comments)} comments for post {post_id}")
            return comments
            
        except requests.RequestException as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []
    
    def post_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Post a comment or reply to a post.
        
        Args:
            post_id: ID of the post
            content: Comment content
            parent_id: ID of parent comment (for replies)
        
        Returns:
            Response data if successful, None otherwise
        """
        try:
            payload = {"content": content}
            if parent_id:
                payload["parent_id"] = parent_id
            
            response = requests.post(
                f"{self.base_url}/posts/{post_id}/comments",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Log rate limit info if present
            if 'retry_after_seconds' in data:
                logger.info(f"API cooldown: {data['retry_after_seconds']}s")
            if 'daily_remaining' in data:
                logger.info(f"Daily comments remaining: {data['daily_remaining']}")
            
            logger.info(f"Successfully posted comment to post {post_id}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Error posting comment: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
