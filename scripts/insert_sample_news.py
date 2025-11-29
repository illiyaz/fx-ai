#!/usr/bin/env python
"""
Insert sample news items to test hybrid predictions.
"""
import sys
sys.path.insert(0, '.')

import asyncio
from datetime import datetime, timezone, timedelta
from apps.news.sources import NewsItem
from apps.common.clickhouse_client import insert_rows
from apps.llm.client import get_llm_client

# Sample news items
SAMPLE_NEWS = [
    {
        "headline": "Federal Reserve signals potential rate cuts in 2025",
        "content": "The Federal Reserve indicated it may begin cutting interest rates in early 2025 if inflation continues to moderate. This dovish stance could weaken the US dollar against major currencies.",
        "source": "reuters",
        "url": "https://example.com/fed-rate-cuts"
    },
    {
        "headline": "RBI maintains repo rate at 6.5% amid stable inflation",
        "content": "The Reserve Bank of India kept its key lending rate unchanged at 6.5% as inflation remains within the target range. The central bank emphasized a balanced approach to monetary policy.",
        "source": "rbi",
        "url": "https://example.com/rbi-rate-decision"
    },
    {
        "headline": "US Dollar strengthens on strong jobs data",
        "content": "The US dollar rallied against major currencies after better-than-expected employment figures showed the labor market remains robust. This reduces pressure on the Fed to cut rates aggressively.",
        "source": "bloomberg",
        "url": "https://example.com/usd-jobs-data"
    },
    {
        "headline": "India's forex reserves hit record high",
        "content": "India's foreign exchange reserves reached an all-time high of $650 billion, providing a strong buffer against external shocks. This strengthens the rupee's position in global markets.",
        "source": "economic_times",
        "url": "https://example.com/india-forex-reserves"
    },
    {
        "headline": "Global trade tensions ease as US-China talks progress",
        "content": "Positive developments in US-China trade negotiations have reduced market uncertainty. Risk appetite is improving, which typically supports emerging market currencies like the Indian rupee.",
        "source": "forexlive",
        "url": "https://example.com/us-china-trade"
    }
]


async def insert_and_analyze():
    """Insert sample news and analyze sentiment."""
    print("=" * 60)
    print("Inserting Sample News for Testing")
    print("=" * 60)
    print()
    
    # Create news items
    news_items = []
    now = datetime.now(timezone.utc)
    
    for i, sample in enumerate(SAMPLE_NEWS):
        # Stagger timestamps by 5 minutes (but keep within last hour)
        ts = now - timedelta(minutes=i * 2)
        
        item = NewsItem.create(
            headline=sample["headline"],
            content=sample["content"],
            url=sample["url"],
            source=sample["source"],
            ts=ts
        )
        news_items.append(item)
        print(f"✓ Created: {item.headline[:60]}...")
    
    # Insert into database
    print()
    print("Inserting into database...")
    rows = [
        (
            item.id,
            item.ts.strftime('%Y-%m-%d %H:%M:%S'),
            item.source,
            item.headline,
            item.content,
            item.url,
            item.author,
            item.language,
            ""
        )
        for item in news_items
    ]
    
    insert_rows(
        "fxai.news_items",
        rows,
        ["id", "ts", "source", "headline", "content", "url", "author", "language", "raw_json"]
    )
    print(f"✓ Inserted {len(rows)} news items")
    
    # Analyze sentiment
    print()
    print("Analyzing sentiment with Ollama...")
    llm_client = get_llm_client()
    
    sentiment_rows = []
    for item in news_items:
        try:
            result = await llm_client.analyze_sentiment(
                headline=item.headline,
                content=item.content,
                source=item.source,
                timestamp=item.ts
            )
            
            sentiment_rows.append((
                item.id,
                item.ts.strftime('%Y-%m-%d %H:%M:%S'),
                result.sentiment,
                result.score,
                result.confidence,
                result.reasoning,
                llm_client.model,
                result.tokens_used,
                result.latency_ms
            ))
            
            print(f"✓ {item.source}: {result.sentiment} (score: {result.score:.2f}, confidence: {result.confidence:.2f})")
            
        except Exception as e:
            print(f"✗ Error analyzing {item.source}: {e}")
    
    # Insert sentiment scores
    if sentiment_rows:
        print()
        print("Inserting sentiment scores...")
        insert_rows(
            "fxai.sentiment_scores",
            sentiment_rows,
            ["news_id", "ts", "sentiment", "score", "confidence", "reasoning", "model", "tokens_used", "latency_ms"]
        )
        print(f"✓ Inserted {len(sentiment_rows)} sentiment scores")
    
    print()
    print("=" * 60)
    print("✅ Sample news inserted and analyzed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Test hybrid forecast: make curl-hybrid")
    print("  2. View news: make tail-news")
    print("  3. View sentiment: make tail-sentiment")
    print("  4. Monitor hybrid: make tail-hybrid")


if __name__ == "__main__":
    asyncio.run(insert_and_analyze())
