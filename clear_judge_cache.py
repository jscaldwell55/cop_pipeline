#!/usr/bin/env python3
"""
Clear Judge Cache

Clears Redis cache for jailbreak scores. Use this when:
- Judge logic has been updated
- Evaluation prompts have changed
- You want to force re-evaluation

Usage:
    python clear_judge_cache.py
    python clear_judge_cache.py --confirm
"""

import asyncio
import redis.asyncio as redis
import argparse
from config.settings import get_settings

settings = get_settings()


async def clear_cache(dry_run: bool = True):
    """Clear all jailbreak score cache entries."""
    print("=" * 80)
    print("JUDGE CACHE CLEARING TOOL")
    print("=" * 80)
    print()
    
    # Connect to Redis
    try:
        client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        print(f"✓ Connected to Redis: {settings.redis_url}")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")
        return
    
    try:
        # Find all jailbreak_score keys
        pattern = "jailbreak_score:*"
        print(f"\nSearching for keys matching: {pattern}")
        
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        
        print(f"Found {len(keys)} cached scores")
        
        if len(keys) == 0:
            print("\n✓ No cached scores to clear")
            await client.close()
            return
        
        # Show sample keys
        print("\nSample keys:")
        for key in keys[:5]:
            print(f"  - {key}")
        if len(keys) > 5:
            print(f"  ... and {len(keys) - 5} more")
        
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No keys will be deleted")
            print("Run with --confirm to actually clear the cache")
        else:
            print(f"\n⚠️  About to delete {len(keys)} keys")
            print("Are you sure? This cannot be undone.")
            
            confirmation = input("Type 'yes' to confirm: ")
            if confirmation.lower() != 'yes':
                print("\n✗ Cancelled")
                await client.close()
                return
            
            print("\nDeleting keys...")
            deleted = 0
            for key in keys:
                await client.delete(key)
                deleted += 1
                if deleted % 100 == 0:
                    print(f"  Deleted {deleted}/{len(keys)}...")
            
            print(f"\n✓ Successfully deleted {deleted} cached scores")
        
        await client.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        await client.close()


def main():
    parser = argparse.ArgumentParser(description="Clear judge LLM cache")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete cache (default is dry run)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(clear_cache(dry_run=not args.confirm))
    
    print("\n" + "=" * 80)
    if args.confirm:
        print("Cache cleared! Rerun calibration test for fresh evaluation:")
        print("  python test_judge_calibration.py --detailed")
    else:
        print("To actually clear cache, run:")
        print("  python clear_judge_cache.py --confirm")
    print("=" * 80)


if __name__ == "__main__":
    main()