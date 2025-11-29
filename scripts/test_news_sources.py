#!/usr/bin/env python
"""
Test news sources to diagnose issues.
"""
import sys
sys.path.insert(0, '.')

import asyncio
import feedparser
from apps.news.sources import RSS_SOURCES

async def test_rss_sources():
    """Test all RSS sources."""
    print("=" * 60)
    print("Testing RSS News Sources")
    print("=" * 60)
    print()
    
    for source_name, url in RSS_SOURCES.items():
        print(f"Testing: {source_name}")
        print(f"URL: {url}")
        
        try:
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"  ⚠️  Feed has parsing issues: {feed.bozo_exception}")
            
            if hasattr(feed, 'status'):
                print(f"  Status: {feed.status}")
            
            if hasattr(feed, 'entries'):
                print(f"  ✓ Entries found: {len(feed.entries)}")
                
                if len(feed.entries) > 0:
                    entry = feed.entries[0]
                    print(f"  Latest: {entry.get('title', 'No title')[:80]}")
                    print(f"  Date: {entry.get('published', 'No date')}")
                else:
                    print(f"  ⚠️  No entries in feed")
            else:
                print(f"  ✗ No entries attribute")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_rss_sources())
