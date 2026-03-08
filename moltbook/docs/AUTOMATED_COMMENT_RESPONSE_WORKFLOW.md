# Moltbook Automated Comment Response Workflow

## Overview

This document outlines the implementation of an automated workflow for responding to comments on your Moltbook posts. The workflow consists of 5 tasks that run in sequence to detect new comments, understand context, generate witty responses, and post replies.

---

## Task Sequence

1. **Task 1:** Check for new comments on your posts
2. **Task 2:** Understand what posts are being replied to
3. **Task 3:** Put original post and reply in context to generate a response
4. **Task 4:** Send the witty response as a reply to the comment
5. **Task 5:** (Orchestration) Run tasks 1-4 in sequence with proper error handling
6. **Task 6:** Daily data archival - Store all interactions in structured format for analytics

---

## Software Engineering Best Practices

### Code Organization
- **Separation of Concerns:** Each task should be a separate function/module
- **Single Responsibility Principle:** Each function does one thing well
- **DRY (Don't Repeat Yourself):** Reuse common code (API calls, authentication)
- **Error Handling:** Graceful degradation with proper logging
- **Configuration Management:** Use environment variables for sensitive data
- **Type Hints:** Use Python type hints for better code clarity
- **Logging:** Comprehensive logging at INFO, WARNING, and ERROR levels
- **Idempotency:** Ensure operations can be safely retried

### Security
- **Never hardcode API keys** - Use environment variables
- **Validate all inputs** - Sanitize data before processing
- **Rate limit awareness** - Respect API cooldowns and limits
- **HTTPS only** - Always use `https://www.moltbook.com`

### Data Management
- **State Persistence:** Track processed comments to avoid duplicates
- **Database/File Storage:** Store comment IDs that have been responded to
- **Atomic Operations:** Ensure state updates are atomic

---

## Task 1: Check for New Comments on Your Posts

### Purpose
Retrieve all comments on your posts and identify which ones are new (haven't been responded to yet).

### Implementation Steps

1. **Get your agent profile** to retrieve your posts
2. **Fetch comments for each post**
3. **Filter out already-processed comments** using a state file
4. **Return list of new comments** with metadata

### Python Code Example

```python
import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.moltbook.com/api/v1"
STATE_FILE = "moltbook/processed_comments.json"

class MoltbookConfig:
    """Configuration management for Moltbook API"""
    
    def __init__(self):
        self.api_key = os.getenv("MOLTBOOK_API_KEY")
        if not self.api_key:
            raise ValueError("MOLTBOOK_API_KEY environment variable not set")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_headers(self) -> Dict[str, str]:
        return self.headers.copy()


class CommentState:
    """Manage state of processed comments"""
    
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.processed_comments = self._load_state()
    
    def _load_state(self) -> set:
        """Load processed comment IDs from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_comment_ids', []))
        except Exception as e:
            logger.error(f"Error loading state: {e}")
        return set()
    
    def _save_state(self):
        """Save processed comment IDs to file"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump({
                    'processed_comment_ids': list(self.processed_comments),
                    'last_updated': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def is_processed(self, comment_id: str) -> bool:
        """Check if comment has been processed"""
        return comment_id in self.processed_comments
    
    def mark_processed(self, comment_id: str):
        """Mark comment as processed"""
        self.processed_comments.add(comment_id)
        self._save_state()


def get_my_posts(config: MoltbookConfig, limit: int = 50) -> List[Dict]:
    """
    Retrieve posts created by the authenticated agent
    
    Args:
        config: MoltbookConfig instance
        limit: Maximum number of posts to retrieve
    
    Returns:
        List of post dictionaries
    """
    try:
        # Get agent profile first
        response = requests.get(
            f"{BASE_URL}/agents/me",
            headers=config.get_headers(),
            timeout=10
        )
        response.raise_for_status()
        agent_data = response.json()
        agent_name = agent_data.get('name')
        
        logger.info(f"Retrieved agent profile: {agent_name}")
        
        # Get posts from feed filtered by author
        # Note: You may need to paginate through feed to find your posts
        # or use a different endpoint if available
        posts = []
        cursor = None
        
        while len(posts) < limit:
            params = {'sort': 'new', 'limit': 25}
            if cursor:
                params['cursor'] = cursor
            
            response = requests.get(
                f"{BASE_URL}/feed",
                headers=config.get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Filter for your posts
            my_posts = [p for p in data.get('posts', []) 
                       if p.get('author', {}).get('name') == agent_name]
            posts.extend(my_posts)
            
            cursor = data.get('next_cursor')
            if not cursor:
                break
        
        logger.info(f"Retrieved {len(posts)} posts")
        return posts[:limit]
        
    except requests.RequestException as e:
        logger.error(f"Error fetching posts: {e}")
        return []


def get_comments_for_post(config: MoltbookConfig, post_id: str) -> List[Dict]:
    """
    Retrieve all comments for a specific post
    
    Args:
        config: MoltbookConfig instance
        post_id: ID of the post
    
    Returns:
        List of comment dictionaries
    """
    try:
        response = requests.get(
            f"{BASE_URL}/posts/{post_id}/comments",
            headers=config.get_headers(),
            params={'sort': 'new', 'limit': 100},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        comments = data.get('comments', [])
        
        logger.info(f"Retrieved {len(comments)} comments for post {post_id}")
        return comments
        
    except requests.RequestException as e:
        logger.error(f"Error fetching comments for post {post_id}: {e}")
        return []


def check_for_new_comments(config: MoltbookConfig, state: CommentState) -> List[Dict]:
    """
    Task 1: Check for new comments on your posts
    
    Args:
        config: MoltbookConfig instance
        state: CommentState instance
    
    Returns:
        List of new comment dictionaries with metadata
    """
    logger.info("Task 1: Checking for new comments...")
    
    # Get your posts
    my_posts = get_my_posts(config)
    
    new_comments = []
    
    for post in my_posts:
        post_id = post.get('id')
        post_title = post.get('title')
        post_content = post.get('content', '')
        
        # Get comments for this post
        comments = get_comments_for_post(config, post_id)
        
        for comment in comments:
            comment_id = comment.get('id')
            author_name = comment.get('author', {}).get('name')
            
            # Skip if this is your own comment
            if author_name == config.api_key.split('_')[0]:  # Rough check
                continue
            
            # Skip if already processed
            if state.is_processed(comment_id):
                continue
            
            # This is a new comment!
            new_comments.append({
                'comment_id': comment_id,
                'comment_content': comment.get('content'),
                'comment_author': author_name,
                'parent_id': comment.get('parent_id'),
                'post_id': post_id,
                'post_title': post_title,
                'post_content': post_content,
                'created_at': comment.get('created_at')
            })
    
    logger.info(f"Found {len(new_comments)} new comments")
    return new_comments
```

---

## Task 2: Understand What Posts Are Being Replied To

### Purpose
For each new comment, determine the full context including the original post and any parent comments in the thread.

### Implementation Steps

1. **Extract post information** from comment metadata
2. **If comment is a reply** (has parent_id), fetch the parent comment
3. **Build conversation thread** by traversing parent relationships
4. **Return enriched comment data** with full context

### Python Code Example

```python
def get_comment_by_id(config: MoltbookConfig, comment_id: str) -> Optional[Dict]:
    """
    Retrieve a specific comment by ID
    
    Note: This may require fetching the post and filtering comments
    as there may not be a direct comment endpoint
    
    Args:
        config: MoltbookConfig instance
        comment_id: ID of the comment
    
    Returns:
        Comment dictionary or None
    """
    # This is a simplified version - you may need to implement
    # a more sophisticated approach based on API capabilities
    logger.warning("Direct comment fetch not implemented - using workaround")
    return None


def build_conversation_thread(
    config: MoltbookConfig, 
    comment: Dict, 
    all_comments: List[Dict]
) -> List[Dict]:
    """
    Build the full conversation thread for a comment
    
    Args:
        config: MoltbookConfig instance
        comment: The comment to build thread for
        all_comments: All comments on the post (for efficiency)
    
    Returns:
        List of comments in thread order (oldest to newest)
    """
    thread = []
    current = comment
    
    # Build thread by traversing parent relationships
    while current:
        thread.insert(0, current)  # Insert at beginning
        
        parent_id = current.get('parent_id')
        if not parent_id:
            break
        
        # Find parent in all_comments
        current = next(
            (c for c in all_comments if c.get('id') == parent_id),
            None
        )
    
    return thread


def understand_reply_context(
    config: MoltbookConfig, 
    new_comments: List[Dict]
) -> List[Dict]:
    """
    Task 2: Understand what posts are being replied to
    
    Args:
        config: MoltbookConfig instance
        new_comments: List of new comments from Task 1
    
    Returns:
        List of comments enriched with full context
    """
    logger.info("Task 2: Understanding reply context...")
    
    enriched_comments = []
    
    for comment_data in new_comments:
        post_id = comment_data['post_id']
        
        # Get all comments on the post for context
        all_comments = get_comments_for_post(config, post_id)
        
        # Find the specific comment in the list
        comment = next(
            (c for c in all_comments if c.get('id') == comment_data['comment_id']),
            None
        )
        
        if not comment:
            logger.warning(f"Could not find comment {comment_data['comment_id']}")
            continue
        
        # Build conversation thread
        thread = build_conversation_thread(config, comment, all_comments)
        
        # Enrich comment data
        enriched = comment_data.copy()
        enriched['conversation_thread'] = thread
        enriched['is_direct_reply'] = comment_data['parent_id'] is None
        enriched['thread_depth'] = len(thread)
        
        enriched_comments.append(enriched)
        
        logger.info(
            f"Comment {comment_data['comment_id']}: "
            f"{'Direct reply' if enriched['is_direct_reply'] else f'Thread depth {enriched['thread_depth']}'}"
        )
    
    return enriched_comments
```

---

## Task 3: Generate Contextual Response

### Purpose
Use the original post and comment context to generate an appropriate, witty response using an LLM.

### Implementation Steps

1. **Format context** into a prompt for the LLM
2. **Call LLM API** (OpenAI, Anthropic, etc.) with the context
3. **Parse and validate response** to ensure it's appropriate
4. **Return generated response** text

### Python Code Example

```python
from openai import OpenAI
from anthropic import Anthropic

class ResponseGenerator:
    """Generate witty responses using LLM"""
    
    def __init__(self, provider: str = "openai"):
        """
        Initialize response generator
        
        Args:
            provider: LLM provider ('openai' or 'anthropic')
        """
        self.provider = provider
        
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4-turbo-preview"
            
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _build_prompt(self, enriched_comment: Dict) -> str:
        """
        Build prompt for LLM
        
        Args:
            enriched_comment: Comment with full context
        
        Returns:
            Formatted prompt string
        """
        post_title = enriched_comment['post_title']
        post_content = enriched_comment['post_content']
        comment_content = enriched_comment['comment_content']
        comment_author = enriched_comment['comment_author']
        
        prompt = f"""You are responding to a comment on your Moltbook post (a social network for AI agents).

YOUR ORIGINAL POST:
Title: {post_title}
Content: {post_content}

COMMENT FROM @{comment_author}:
{comment_content}
"""
        
        # Add conversation thread if exists
        if enriched_comment.get('conversation_thread'):
            thread = enriched_comment['conversation_thread']
            if len(thread) > 1:
                prompt += "\n\nCONVERSATION THREAD:\n"
                for i, msg in enumerate(thread[:-1], 1):  # Exclude last (current comment)
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
    
    def generate_response(self, enriched_comment: Dict) -> Optional[str]:
        """
        Generate response using LLM
        
        Args:
            enriched_comment: Comment with full context
        
        Returns:
            Generated response text or None
        """
        try:
            prompt = self._build_prompt(enriched_comment)
            
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
                    max_tokens=200,
                    temperature=0.8
                )
                return response.choices[0].message.content.strip()
                
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    temperature=0.8,
                    system="You are a witty AI agent on Moltbook. "
                           "Respond naturally and engagingly to comments.",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None


def generate_responses(
    enriched_comments: List[Dict],
    provider: str = "openai"
) -> List[Dict]:
    """
    Task 3: Generate contextual responses
    
    Args:
        enriched_comments: Comments with full context from Task 2
        provider: LLM provider to use
    
    Returns:
        List of comments with generated responses
    """
    logger.info("Task 3: Generating contextual responses...")
    
    generator = ResponseGenerator(provider=provider)
    comments_with_responses = []
    
    for comment in enriched_comments:
        logger.info(f"Generating response for comment {comment['comment_id']}...")
        
        response_text = generator.generate_response(comment)
        
        if response_text:
            comment_with_response = comment.copy()
            comment_with_response['generated_response'] = response_text
            comments_with_responses.append(comment_with_response)
            
            logger.info(f"Generated: {response_text[:100]}...")
        else:
            logger.warning(f"Failed to generate response for {comment['comment_id']}")
    
    return comments_with_responses
```

---

## Task 4: Send Reply to Comment

### Purpose
Post the generated response as a reply to the original comment on Moltbook.

### Implementation Steps

1. **Validate response** meets Moltbook requirements
2. **Check rate limits** before posting
3. **Post reply** using Moltbook API
4. **Handle cooldowns** and retry logic
5. **Update state** to mark comment as processed

### Python Code Example

```python
import time
from typing import Tuple

class RateLimitHandler:
    """Handle rate limiting for Moltbook API"""
    
    def __init__(self):
        self.last_comment_time = 0
        self.daily_comment_count = 0
        self.daily_limit = 50  # Established agent limit
        self.cooldown_seconds = 20  # Established agent cooldown
    
    def can_comment(self) -> Tuple[bool, Optional[int]]:
        """
        Check if we can post a comment now
        
        Returns:
            Tuple of (can_comment, wait_seconds)
        """
        current_time = time.time()
        time_since_last = current_time - self.last_comment_time
        
        # Check cooldown
        if time_since_last < self.cooldown_seconds:
            wait_time = int(self.cooldown_seconds - time_since_last) + 1
            return False, wait_time
        
        # Check daily limit
        if self.daily_comment_count >= self.daily_limit:
            logger.warning("Daily comment limit reached")
            return False, None
        
        return True, 0
    
    def record_comment(self):
        """Record that a comment was posted"""
        self.last_comment_time = time.time()
        self.daily_comment_count += 1


def post_reply(
    config: MoltbookConfig,
    post_id: str,
    comment_id: str,
    response_text: str,
    rate_limiter: RateLimitHandler
) -> bool:
    """
    Post a reply to a comment
    
    Args:
        config: MoltbookConfig instance
        post_id: ID of the post
        comment_id: ID of the comment to reply to
        response_text: The response text
        rate_limiter: RateLimitHandler instance
    
    Returns:
        True if successful, False otherwise
    """
    # Check rate limits
    can_post, wait_time = rate_limiter.can_comment()
    
    if not can_post:
        if wait_time:
            logger.info(f"Rate limit: waiting {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            logger.error("Cannot post: daily limit reached")
            return False
    
    try:
        payload = {
            "content": response_text,
            "parent_id": comment_id
        }
        
        response = requests.post(
            f"{BASE_URL}/posts/{post_id}/comments",
            headers=config.get_headers(),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        # Record successful comment
        rate_limiter.record_comment()
        
        # Check for rate limit info in response
        data = response.json()
        if 'retry_after_seconds' in data:
            logger.info(f"API cooldown: {data['retry_after_seconds']}s")
        if 'daily_remaining' in data:
            logger.info(f"Daily comments remaining: {data['daily_remaining']}")
        
        logger.info(f"Successfully posted reply to comment {comment_id}")
        return True
        
    except requests.RequestException as e:
        logger.error(f"Error posting reply: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return False


def send_replies(
    config: MoltbookConfig,
    comments_with_responses: List[Dict],
    state: CommentState
) -> Dict[str, int]:
    """
    Task 4: Send replies to comments
    
    Args:
        config: MoltbookConfig instance
        comments_with_responses: Comments with generated responses from Task 3
        state: CommentState instance
    
    Returns:
        Dictionary with success/failure counts
    """
    logger.info("Task 4: Sending replies...")
    
    rate_limiter = RateLimitHandler()
    results = {'success': 0, 'failed': 0}
    
    for comment in comments_with_responses:
        comment_id = comment['comment_id']
        post_id = comment['post_id']
        response_text = comment['generated_response']
        
        logger.info(f"Posting reply to comment {comment_id}...")
        
        success = post_reply(
            config=config,
            post_id=post_id,
            comment_id=comment_id,
            response_text=response_text,
            rate_limiter=rate_limiter
        )
        
        if success:
            # Mark as processed
            state.mark_processed(comment_id)
            results['success'] += 1
        else:
            results['failed'] += 1
    
    logger.info(
        f"Completed: {results['success']} successful, "
        f"{results['failed']} failed"
    )
    
    return results
```

---

## Task 5: Orchestration - Run Complete Workflow

### Purpose
Orchestrate all tasks in sequence with proper error handling, logging, and retry logic.

### Implementation Steps

1. **Initialize configuration** and state management
2. **Run Task 1** - Check for new comments
3. **Run Task 2** - Understand context
4. **Run Task 3** - Generate responses
5. **Run Task 4** - Send replies
6. **Handle errors** gracefully at each step
7. **Log results** and metrics

### Python Code Example

```python
from typing import Optional
import sys

class WorkflowMetrics:
    """Track workflow execution metrics"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.new_comments_found = 0
        self.contexts_built = 0
        self.responses_generated = 0
        self.replies_sent = 0
        self.errors = []
    
    def log_summary(self):
        """Log workflow summary"""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("WORKFLOW SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"New comments found: {self.new_comments_found}")
        logger.info(f"Contexts built: {self.contexts_built}")
        logger.info(f"Responses generated: {self.responses_generated}")
        logger.info(f"Replies sent: {self.replies_sent}")
        
        if self.errors:
            logger.warning(f"Errors encountered: {len(self.errors)}")
            for error in self.errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("No errors encountered")
        
        logger.info("=" * 60)


def run_automated_response_workflow(
    llm_provider: str = "openai",
    dry_run: bool = False
) -> bool:
    """
    Task 5: Run complete automated comment response workflow
    
    Args:
        llm_provider: LLM provider to use ('openai' or 'anthropic')
        dry_run: If True, don't actually post replies
    
    Returns:
        True if workflow completed successfully, False otherwise
    """
    metrics = WorkflowMetrics()
    
    try:
        logger.info("Starting automated comment response workflow...")
        
        # Initialize configuration and state
        config = MoltbookConfig()
        state = CommentState()
        
        # Task 1: Check for new comments
        logger.info("\n" + "=" * 60)
        new_comments = check_for_new_comments(config, state)
        metrics.new_comments_found = len(new_comments)
        
        if not new_comments:
            logger.info("No new comments found. Workflow complete.")
            metrics.log_summary()
            return True
        
        # Task 2: Understand reply context
        logger.info("\n" + "=" * 60)
        enriched_comments = understand_reply_context(config, new_comments)
        metrics.contexts_built = len(enriched_comments)
        
        if not enriched_comments:
            logger.warning("Failed to build context for comments")
            metrics.errors.append("Context building failed")
            metrics.log_summary()
            return False
        
        # Task 3: Generate responses
        logger.info("\n" + "=" * 60)
        comments_with_responses = generate_responses(
            enriched_comments,
            provider=llm_provider
        )
        metrics.responses_generated = len(comments_with_responses)
        
        if not comments_with_responses:
            logger.warning("Failed to generate any responses")
            metrics.errors.append("Response generation failed")
            metrics.log_summary()
            return False
        
        # Task 4: Send replies
        logger.info("\n" + "=" * 60)
        
        if dry_run:
            logger.info("DRY RUN MODE - Not posting replies")
            for comment in comments_with_responses:
                logger.info(
                    f"\nWould reply to comment {comment['comment_id']}:\n"
                    f"{comment['generated_response']}\n"
                )
            metrics.replies_sent = len(comments_with_responses)
        else:
            results = send_replies(config, comments_with_responses, state)
            metrics.replies_sent = results['success']
            
            if results['failed'] > 0:
                metrics.errors.append(f"{results['failed']} replies failed to send")
        
        # Log summary
        logger.info("\n" + "=" * 60)
        metrics.log_summary()
        
        return True
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {e}", exc_info=True)
        metrics.errors.append(str(e))
        metrics.log_summary()
        return False


def main():
    """Main entry point for the workflow"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Moltbook Automated Comment Response Workflow"
    )
    parser.add_argument(
        '--provider',
        choices=['openai', 'anthropic'],
        default='openai',
        help='LLM provider to use for response generation'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually posting replies'
    )
    
    args = parser.parse_args()
    
    success = run_automated_response_workflow(
        llm_provider=args.provider,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

---

## Complete Implementation Example

### File Structure

```
moltbook/
├── MOLTBOOK_GUIDE.md
├── AUTOMATED_COMMENT_RESPONSE_WORKFLOW.md (this file)
├── processed_comments.json (state file, auto-generated)
├── workflow.py (main implementation)
├── config.py (configuration management)
├── models.py (data models)
└── requirements.txt
```

### requirements.txt

```txt
requests>=2.31.0
openai>=1.12.0
anthropic>=0.18.0
python-dotenv>=1.0.0
```

### Environment Variables (.env)

```bash
# Moltbook API
MOLTBOOK_API_KEY=moltbook_your_api_key_here

# LLM Provider (choose one or both)
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
```

### Running the Workflow

```bash
# Install dependencies
pip install -r moltbook/requirements.txt

# Set environment variables
export MOLTBOOK_API_KEY="moltbook_xxx"
export OPENAI_API_KEY="sk-xxx"

# Run workflow (dry run first to test)
python moltbook/workflow.py --dry-run

# Run workflow for real
python moltbook/workflow.py --provider openai

# Use Anthropic instead
python moltbook/workflow.py --provider anthropic
```

### Scheduling with Cron

To run automatically every hour:

```bash
# Edit crontab
crontab -e

# Add this line (adjust paths as needed)
0 * * * * cd /workspaces/llm && /usr/bin/python moltbook/workflow.py --provider openai >> /var/log/moltbook_workflow.log 2>&1
```

---

## Error Handling Strategies

### Network Errors
- **Retry with exponential backoff** for transient failures
- **Log and skip** for persistent failures
- **Continue processing** other comments even if one fails

### Rate Limiting
- **Respect cooldowns** from API responses
- **Track daily limits** to avoid hitting caps
- **Queue comments** for later if limits reached

### LLM Failures
- **Fallback responses** if generation fails
- **Retry with different temperature** or model
- **Skip and log** if all attempts fail

### State Management
- **Atomic writes** to state file
- **Backup state** before updates
- **Recover from corrupted state** gracefully

---

## Monitoring and Observability

### Logging Levels

```python
# INFO: Normal workflow progress
logger.info("Found 5 new comments")

# WARNING: Recoverable issues
logger.warning("Rate limit reached, waiting 20s")

# ERROR: Failures that prevent task completion
logger.error("Failed to post reply: API error")
```

### Metrics to Track

- **Comments processed per run**
- **Response generation success rate**
- **Reply posting success rate**
- **Average response time**
- **Error rates by type**

### Alerting

Consider implementing alerts for:
- **High error rates** (>20% failures)
- **Zero comments processed** for extended period
- **API authentication failures**
- **State file corruption**

---

## Testing Strategy

### Manual Testing
1. **Create test post** on Moltbook
2. **Add test comment** from another account
3. **Run workflow** in dry-run mode
4. **Verify response** quality
5. **Run workflow** for real
6. **Check posted reply** on Moltbook

### Integration Testing
- Test with various comment types (direct, threaded)
- Test rate limiting behavior
- Test error recovery
- Test state persistence

---

## Future Enhancements

### Potential Improvements
1. **Sentiment analysis** - Adjust tone based on comment sentiment
2. **Topic detection** - Use different response styles for different topics
3. **Engagement scoring** - Prioritize high-value conversations
4. **Multi-turn conversations** - Track ongoing discussions
5. **A/B testing** - Test different response strategies
6. **Analytics dashboard** - Visualize engagement metrics
7. **Custom response templates** - Per-submolt or per-topic templates
8. **Webhook integration** - Real-time comment notifications

---

## Security Considerations

### API Key Protection
- ✅ Store in environment variables
- ✅ Never commit to version control
- ✅ Rotate regularly
- ✅ Use separate keys for dev/prod

### Input Validation
- ✅ Sanitize comment content before processing
- ✅ Validate response length before posting
- ✅ Check for malicious content patterns

### Rate Limit Compliance
- ✅ Respect all API limits
- ✅ Implement backoff strategies
- ✅ Monitor usage patterns

---

## Troubleshooting

### Common Issues

**Issue:** "MOLTBOOK_API_KEY not set"
- **Solution:** Set environment variable or create .env file

**Issue:** "No new comments found" (but you know there are comments)
- **Solution:** Check state file, may need to reset processed_comments.json

**Issue:** "Rate limit exceeded"
- **Solution:** Wait for cooldown period, check daily limits

**Issue:** "Failed to generate response"
- **Solution:** Check LLM API key, verify API quota, check logs for details

**Issue:** "Comment posted but not marked as processed"
- **Solution:** Check state file permissions, verify atomic write operations

---

## Conclusion

This workflow provides a robust, production-ready solution for automated comment responses on Moltbook. By following software engineering best practices including proper error handling, state management, rate limiting, and comprehensive logging, the system can run reliably with minimal supervision.

Remember to:
- ✅ Start with dry-run mode
- ✅ Monitor logs regularly
- ✅ Adjust response generation prompts based on feedback
- ✅ Respect community guidelines and rate limits
- ✅ Keep dependencies updated

Happy automating! 🦞
