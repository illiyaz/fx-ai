#!/usr/bin/env python
"""
Test script for news ingestion system.

Tests:
1. RSS feed parsing
2. News relevance filtering
3. Database insertion
4. LLM sentiment analysis (if API key provided)
"""
import asyncio
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, '.')

from apps.news.sources import RSSSource, NewsAPISource, NewsItem
from apps.llm.client import get_llm_client
from apps.common.clickhouse_client import query_df


async def test_rss_source():
    """Test RSS feed fetching."""
    print("\n" + "="*60)
    print("TEST 1: RSS Feed Fetching")
    print("="*60)
    
    # Test with ForexLive RSS feed
    source = RSSSource("forexlive", "https://www.forexlive.com/feed/news")
    
    print(f"Fetching from: {source.feed_url}")
    items = await source.fetch_latest(lookback_hours=24)
    
    print(f"✓ Fetched {len(items)} relevant items")
    
    if items:
        print("\nSample item:")
        item = items[0]
        print(f"  Headline: {item.headline[:80]}...")
        print(f"  Source: {item.source}")
        print(f"  Published: {item.ts}")
        print(f"  URL: {item.url[:60]}...")
    
    return items


async def test_relevance_filter():
    """Test news relevance filtering."""
    print("\n" + "="*60)
    print("TEST 2: Relevance Filtering")
    print("="*60)
    
    source = RSSSource("test", "http://example.com")
    
    # Test cases
    test_cases = [
        ("Fed raises interest rates", "The Federal Reserve raised rates by 25bps", True),
        ("USD/INR hits new high", "The dollar strengthened against the rupee", True),
        ("Celebrity gossip news", "Famous actor spotted at restaurant", False),
        ("Sports update", "Team wins championship game", False),
        ("ECB monetary policy", "European Central Bank signals rate cuts", True),
    ]
    
    passed = 0
    for headline, content, expected in test_cases:
        item = NewsItem.create(
            headline=headline,
            content=content,
            url="http://test.com",
            source="test"
        )
        result = source.is_relevant(item)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{headline[:40]}...' -> {result} (expected {expected})")
        if result == expected:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


async def test_llm_sentiment():
    """Test LLM sentiment analysis."""
    print("\n" + "="*60)
    print("TEST 3: LLM Sentiment Analysis")
    print("="*60)
    
    try:
        client = get_llm_client()
        print(f"Using model: {client.model}")
        
        # Test article
        headline = "Fed Raises Rates by 25bps, Signals More Hikes Ahead"
        content = """
        The Federal Reserve raised interest rates by 25 basis points today, 
        bringing the target rate to 5.50%. Chair Powell indicated that further 
        rate increases may be necessary to combat persistent inflation. The 
        decision was widely expected by markets. The dollar strengthened 
        following the announcement.
        """
        
        print(f"\nAnalyzing: '{headline}'")
        
        result = await client.analyze_sentiment(
            headline=headline,
            content=content,
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        print(f"\n✓ Analysis complete:")
        print(f"  Sentiment Overall: {result.sentiment_overall:+.2f}")
        print(f"  Sentiment USD: {result.sentiment_usd:+.2f}")
        print(f"  Sentiment INR: {result.sentiment_inr:+.2f}")
        print(f"  Impact Score: {result.impact_score:.1f}/10")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Urgency: {result.urgency}")
        print(f"  Topics: {', '.join(result.topics)}")
        print(f"  Explanation: {result.explanation}")
        print(f"  Processing Time: {result.processing_time_ms}ms")
        print(f"  Tokens Used: {result.tokens_used}")
        print(f"  API Cost: ${result.api_cost_usd:.4f}")
        
        return True
    
    except ImportError:
        print("✗ OpenAI package not installed")
        print("  Run: pip install openai")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        print("  Make sure OPENAI_API_KEY is set in .env")
        return False


async def test_database_query():
    """Test database connectivity."""
    print("\n" + "="*60)
    print("TEST 4: Database Connectivity")
    print("="*60)
    
    try:
        # Check if news tables exist
        df = query_df("SHOW TABLES FROM fxai LIKE '%news%'")
        tables = df.iloc[:, 0].tolist() if not df.empty else []
        
        print(f"✓ Found {len(tables)} news-related tables:")
        for table in tables:
            print(f"  - {table}")
        
        if "news_items" in tables:
            # Count existing news
            count_df = query_df("SELECT count() FROM fxai.news_items")
            count = int(count_df.iloc[0, 0]) if not count_df.empty else 0
            print(f"\n✓ Existing news items: {count}")
        
        return len(tables) > 0
    
    except Exception as e:
        print(f"✗ Database error: {e}")
        print("  Make sure ClickHouse is running and schema is initialized")
        print("  Run: make init-news-schema")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("NEWS INGESTION SYSTEM TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: RSS fetching
    try:
        items = await test_rss_source()
        results["RSS Fetching"] = len(items) > 0
    except Exception as e:
        print(f"✗ Error: {e}")
        results["RSS Fetching"] = False
    
    # Test 2: Relevance filtering
    try:
        results["Relevance Filter"] = await test_relevance_filter()
    except Exception as e:
        print(f"✗ Error: {e}")
        results["Relevance Filter"] = False
    
    # Test 3: LLM sentiment (optional)
    try:
        results["LLM Sentiment"] = await test_llm_sentiment()
    except Exception as e:
        print(f"✗ Error: {e}")
        results["LLM Sentiment"] = False
    
    # Test 4: Database
    try:
        results["Database"] = await test_database_query()
    except Exception as e:
        print(f"✗ Error: {e}")
        results["Database"] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! News ingestion system is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
