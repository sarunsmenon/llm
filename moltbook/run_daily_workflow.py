#!/usr/bin/env python3
"""
Moltbook Daily Workflow - Master Task Runner

This script runs all 6 tasks in sequence:
1. Check for new comments on your posts
2. Understand what posts are being replied to
3. Generate contextual responses using LLM
4. Send replies to comments
5. Orchestrate the workflow with error handling
6. Archive all daily interactions for analytics

Usage:
    python moltbook/run_daily_workflow.py
    python moltbook/run_daily_workflow.py --dry-run
    python moltbook/run_daily_workflow.py --provider anthropic
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('moltbook/logs/daily_workflow.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def check_environment():
    """Check that all required environment variables are set"""
    required_vars = ['MOLTBOOK_API_KEY']
    optional_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    
    missing_required = [var for var in required_vars if not os.getenv(var)]
    
    if missing_required:
        logger.error(f"Missing required environment variables: {', '.join(missing_required)}")
        logger.error("Please set them in your .env file or export them:")
        logger.error("  export MOLTBOOK_API_KEY='your_key_here'")
        return False
    
    # Check for at least one LLM provider
    has_llm = any(os.getenv(var) for var in optional_vars)
    if not has_llm:
        logger.warning("No LLM API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        logger.warning("Response generation will fail without an LLM provider.")
    
    return True


def create_directories():
    """Create necessary directories for logs and data"""
    directories = [
        'moltbook/logs',
        'moltbook/data/archives',
        'moltbook/data/state'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")


def run_master_workflow(
    llm_provider: str = "openai",
    dry_run: bool = False,
    enable_archival: bool = True
) -> dict:
    """
    Master Task: Run all 6 workflow tasks in sequence
    
    Args:
        llm_provider: LLM provider to use ('openai' or 'anthropic')
        dry_run: If True, don't actually post replies
        enable_archival: If True, archive all interactions
    
    Returns:
        Dictionary with workflow results and statistics
    """
    start_time = datetime.utcnow()
    
    logger.info("=" * 80)
    logger.info("MOLTBOOK DAILY WORKFLOW - MASTER TASK")
    logger.info("=" * 80)
    logger.info(f"Start time: {start_time.isoformat()}")
    logger.info(f"LLM Provider: {llm_provider}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info(f"Archival Enabled: {enable_archival}")
    logger.info("=" * 80)
    
    results = {
        'start_time': start_time.isoformat(),
        'llm_provider': llm_provider,
        'dry_run': dry_run,
        'tasks': {},
        'summary': {},
        'success': False
    }
    
    try:
        # Import workflow functions (these would be in separate modules)
        # For now, we'll create placeholder implementations
        
        # TASK 1: Check for new comments
        logger.info("\n" + "=" * 80)
        logger.info("TASK 1: Checking for new comments on your posts")
        logger.info("=" * 80)
        
        task1_result = run_task_1()
        results['tasks']['task_1_check_comments'] = task1_result
        
        new_comments = task1_result.get('new_comments', [])
        logger.info(f"✓ Task 1 Complete: Found {len(new_comments)} new comments")
        
        if not new_comments:
            logger.info("No new comments to process. Workflow complete.")
            results['success'] = True
            results['summary'] = {
                'new_comments_found': 0,
                'replies_sent': 0,
                'message': 'No new comments to process'
            }
            return results
        
        # TASK 2: Understand reply context
        logger.info("\n" + "=" * 80)
        logger.info("TASK 2: Understanding what posts are being replied to")
        logger.info("=" * 80)
        
        task2_result = run_task_2(new_comments)
        results['tasks']['task_2_build_context'] = task2_result
        
        enriched_comments = task2_result.get('enriched_comments', [])
        logger.info(f"✓ Task 2 Complete: Built context for {len(enriched_comments)} comments")
        
        # TASK 3: Generate responses
        logger.info("\n" + "=" * 80)
        logger.info("TASK 3: Generating contextual responses")
        logger.info("=" * 80)
        
        task3_result = run_task_3(enriched_comments, llm_provider)
        results['tasks']['task_3_generate_responses'] = task3_result
        
        comments_with_responses = task3_result.get('comments_with_responses', [])
        logger.info(f"✓ Task 3 Complete: Generated {len(comments_with_responses)} responses")
        
        # TASK 4: Send replies
        logger.info("\n" + "=" * 80)
        logger.info("TASK 4: Sending replies to comments")
        logger.info("=" * 80)
        
        task4_result = run_task_4(comments_with_responses, dry_run)
        results['tasks']['task_4_send_replies'] = task4_result
        
        replies_sent = task4_result.get('success_count', 0)
        logger.info(f"✓ Task 4 Complete: Sent {replies_sent} replies")
        
        # TASK 6: Archive daily interactions
        if enable_archival:
            logger.info("\n" + "=" * 80)
            logger.info("TASK 6: Archiving daily interactions")
            logger.info("=" * 80)
            
            task6_result = run_task_6(comments_with_responses)
            results['tasks']['task_6_archive_data'] = task6_result
            
            logger.info(f"✓ Task 6 Complete: Archived {task6_result.get('records_archived', 0)} records")
        
        # Generate summary
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration
        results['success'] = True
        results['summary'] = {
            'new_comments_found': len(new_comments),
            'contexts_built': len(enriched_comments),
            'responses_generated': len(comments_with_responses),
            'replies_sent': replies_sent,
            'duration_seconds': duration
        }
        
        # Print final summary
        logger.info("\n" + "=" * 80)
        logger.info("WORKFLOW SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"New comments found: {len(new_comments)}")
        logger.info(f"Responses generated: {len(comments_with_responses)}")
        logger.info(f"Replies sent: {replies_sent}")
        logger.info(f"Status: {'SUCCESS' if results['success'] else 'FAILED'}")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {e}", exc_info=True)
        results['success'] = False
        results['error'] = str(e)
        return results


def run_task_1() -> dict:
    """Task 1: Check for new comments"""
    # Placeholder implementation
    # In production, this would call the actual implementation
    logger.info("Fetching your posts from Moltbook...")
    logger.info("Checking for new comments...")
    
    # Simulate finding comments
    return {
        'success': True,
        'new_comments': [],  # Would contain actual comment data
        'posts_checked': 0
    }


def run_task_2(new_comments: list) -> dict:
    """Task 2: Build context for comments"""
    logger.info(f"Building context for {len(new_comments)} comments...")
    
    return {
        'success': True,
        'enriched_comments': new_comments,  # Would contain enriched data
        'threads_analyzed': len(new_comments)
    }


def run_task_3(enriched_comments: list, provider: str) -> dict:
    """Task 3: Generate responses using LLM"""
    logger.info(f"Generating responses using {provider}...")
    
    return {
        'success': True,
        'comments_with_responses': enriched_comments,  # Would contain generated responses
        'provider': provider
    }


def run_task_4(comments_with_responses: list, dry_run: bool) -> dict:
    """Task 4: Send replies to Moltbook"""
    if dry_run:
        logger.info("DRY RUN MODE - Not actually posting replies")
        for i, comment in enumerate(comments_with_responses, 1):
            logger.info(f"Would send reply {i}/{len(comments_with_responses)}")
        return {
            'success': True,
            'success_count': len(comments_with_responses),
            'failed_count': 0,
            'dry_run': True
        }
    
    logger.info(f"Posting {len(comments_with_responses)} replies...")
    
    return {
        'success': True,
        'success_count': 0,  # Would contain actual count
        'failed_count': 0
    }


def run_task_6(interactions: list) -> dict:
    """Task 6: Archive daily interactions"""
    logger.info("Archiving interactions to JSONL format...")
    
    # Create archive file
    today = datetime.utcnow().date()
    archive_dir = Path('moltbook/data/archives') / str(today.year) / f"{today.month:02d}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    archive_file = archive_dir / f"moltbook_interactions_{today.isoformat()}.jsonl"
    
    logger.info(f"Archive file: {archive_file}")
    
    return {
        'success': True,
        'records_archived': len(interactions),
        'archive_file': str(archive_file)
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Moltbook Daily Workflow - Master Task Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the full workflow
  python moltbook/run_daily_workflow.py
  
  # Dry run (don't actually post replies)
  python moltbook/run_daily_workflow.py --dry-run
  
  # Use Anthropic instead of OpenAI
  python moltbook/run_daily_workflow.py --provider anthropic
  
  # Disable archival
  python moltbook/run_daily_workflow.py --no-archive
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
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create necessary directories
    create_directories()
    
    # Run the master workflow
    results = run_master_workflow(
        llm_provider=args.provider,
        dry_run=args.dry_run,
        enable_archival=not args.no_archive
    )
    
    # Save results to file
    results_file = Path('moltbook/logs') / f"workflow_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved to: {results_file}")
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()
