#!/usr/bin/env python3
"""
Moltbook Daily Workflow - Main Entry Point

This is the main script that orchestrates all 6 workflow tasks.

Usage:
    python moltbook/main.py
    python moltbook/main.py --dry-run
    python moltbook/main.py --provider anthropic
"""

import sys
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Settings
from utils import StateManager, RateLimiter
from src import MoltbookClient, WorkflowTasks, DataArchiver


def setup_logging():
    """Configure logging for the workflow."""
    Settings.create_directories()
    
    # Create log file with timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    log_file = Settings.LOGS_DIR / f"workflow_{timestamp}.log"
    
    logging.basicConfig(
        level=getattr(logging, Settings.LOG_LEVEL),
        format=Settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='w')
        ]
    )
    
    # Log the file location
    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")


def run_workflow(
    llm_provider: str = "openai",
    dry_run: bool = False,
    enable_archival: bool = True
) -> bool:
    """
    Run the complete Moltbook workflow.
    
    Args:
        llm_provider: LLM provider to use ('openai' or 'anthropic')
        dry_run: If True, don't actually post replies
        enable_archival: If True, archive all interactions
    
    Returns:
        True if workflow completed successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now(timezone.utc)
    
    logger.info("=" * 80)
    logger.info("MOLTBOOK DAILY WORKFLOW")
    logger.info("=" * 80)
    logger.info(f"Start time: {start_time.isoformat()}")
    logger.info(f"LLM Provider: {llm_provider}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info(f"Archival Enabled: {enable_archival}")
    logger.info("=" * 80)
    
    try:
        # Validate settings
        Settings.validate()
        
        # Initialize components
        client = MoltbookClient()
        state_manager = StateManager(Settings.PROCESSED_COMMENTS_FILE)
        rate_limiter = RateLimiter(
            cooldown_seconds=Settings.COMMENT_COOLDOWN_SECONDS,
            daily_limit=Settings.DAILY_COMMENT_LIMIT
        )
        workflow = WorkflowTasks(client, state_manager, rate_limiter)
        archiver = DataArchiver() if enable_archival else None
        
        # Task 1: Check for new comments
        new_comments = workflow.task1_check_new_comments()
        
        if not new_comments:
            logger.info("No new comments found. Workflow complete.")
            if archiver:
                summary = archiver.get_daily_summary()
                logger.info(f"Daily summary: {summary}")
            return True
        
        # Archive received comments
        if archiver:
            for comment in new_comments:
                archiver.archive_interaction(
                    interaction_type="comment_received",
                    comment_data=comment
                )
        
        # Task 2: Build context
        enriched_comments = workflow.task2_build_context(new_comments)
        
        if not enriched_comments:
            logger.warning("Failed to build context for comments")
            return False
        
        # Task 3: Generate responses
        comments_with_responses = workflow.task3_generate_responses(
            enriched_comments,
            provider=llm_provider
        )
        
        if not comments_with_responses:
            logger.warning("Failed to generate any responses")
            return False
        
        # Task 4: Send replies
        results = workflow.task4_send_replies(comments_with_responses, dry_run=dry_run)
        
        # Archive sent replies
        if archiver and not dry_run:
            for comment in comments_with_responses:
                archiver.archive_interaction(
                    interaction_type="reply_sent",
                    comment_data=comment,
                    reply_data=comment,
                    success=True
                )
        
        # Task 6: Generate daily summary
        if archiver:
            logger.info("\n" + "=" * 80)
            logger.info("TASK 6: Daily Archive Summary")
            logger.info("=" * 80)
            summary = archiver.get_daily_summary()
            logger.info(f"Date: {summary['date']}")
            logger.info(f"Total interactions: {summary['total_interactions']}")
            logger.info(f"Comments received: {summary['comments_received']}")
            logger.info(f"Replies sent: {summary['replies_sent']}")
            logger.info(f"Unique posts: {summary['unique_posts']}")
            logger.info(f"Unique commenters: {summary['unique_commenters']}")
            logger.info(f"Submolts: {', '.join(summary['submolts'])}")
        
        # Final summary
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("WORKFLOW COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"New comments found: {len(new_comments)}")
        logger.info(f"Responses generated: {len(comments_with_responses)}")
        logger.info(f"Replies sent: {results['success']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {e}", exc_info=True)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Moltbook Daily Workflow - Automated Comment Response System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the full workflow
  python moltbook/main.py
  
  # Dry run (don't actually post replies)
  python moltbook/main.py --dry-run
  
  # Use Anthropic instead of OpenAI
  python moltbook/main.py --provider anthropic
  
  # Disable archival
  python moltbook/main.py --no-archive
  
  # Verbose logging
  python moltbook/main.py -v

Environment Variables Required:
  MOLTBOOK_API_KEY     - Your Moltbook API key
  OPENAI_API_KEY       - OpenAI API key (if using OpenAI)
  ANTHROPIC_API_KEY    - Anthropic API key (if using Anthropic)
        """
    )
    
    parser.add_argument(
        '--provider',
        choices=['openai', 'anthropic'],
        default='openai',
        help='LLM provider to use for response generation (default: openai)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually posting replies (for testing)'
    )
    
    parser.add_argument(
        '--no-archive',
        action='store_true',
        help='Disable daily data archival'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        Settings.LOG_LEVEL = "DEBUG"
    
    # Setup logging
    setup_logging()
    
    # Run the workflow
    success = run_workflow(
        llm_provider=args.provider,
        dry_run=args.dry_run,
        enable_archival=not args.no_archive
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
