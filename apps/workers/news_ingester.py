"""
News ingestion worker daemon.

Continuously fetches news from configured sources and stores in ClickHouse.
Optionally triggers LLM sentiment analysis for high-priority news.
"""
from __future__ import annotations
import os
import time
import signal
import asyncio
import argparse
from typing import List
import structlog

from apps.news.sources import NewsItem, NewsSource, create_default_sources
from apps.news.advanced_sources import create_advanced_sources
from apps.common.clickhouse_client import insert_rows
from apps.llm.client import get_llm_client, SentimentResult

log = structlog.get_logger()

RUNNING = True


def _handle_signal(signum, frame):
    global RUNNING
    RUNNING = False
    log.info("shutdown_signal_received", signal=signum)


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _handle_signal)


class NewsIngester:
    """News ingestion worker."""
    
    def __init__(self,
                 sources: List[NewsSource],
                 poll_interval_seconds: int = 60,
                 lookback_hours: int = 1,
                 enable_sentiment: bool = True,
                 sentiment_batch_size: int = 5):
        """
        Initialize news ingester.
        
        Args:
            sources: List of news sources to poll
            poll_interval_seconds: Seconds between polling cycles
            lookback_hours: How far back to fetch news
            enable_sentiment: Whether to run LLM sentiment analysis
            sentiment_batch_size: Max items to analyze per cycle
        """
        self.sources = sources
        self.poll_interval = poll_interval_seconds
        self.lookback_hours = lookback_hours
        self.enable_sentiment = enable_sentiment
        self.sentiment_batch_size = sentiment_batch_size
        
        # Initialize LLM client if sentiment enabled
        self.llm_client = None
        if self.enable_sentiment:
            try:
                self.llm_client = get_llm_client()
                log.info("llm_client_initialized", model=self.llm_client.model)
            except Exception as e:
                log.warning("llm_client_init_failed", error=str(e))
                self.enable_sentiment = False
        
        # Track seen news IDs to avoid duplicates
        self.seen_ids = set()
        self.max_seen_ids = 10000  # Prevent unbounded growth
    
    async def run_once(self) -> dict:
        """
        Run one ingestion cycle.
        
        Returns:
            Stats dict with counts
        """
        stats = {
            "news_fetched": 0,
            "news_inserted": 0,
            "news_duplicate": 0,
            "sentiment_analyzed": 0,
            "errors": 0
        }
        
        # Fetch from all sources
        all_items = []
        for source in self.sources:
            try:
                items = await source.fetch_latest(self.lookback_hours)
                all_items.extend(items)
                stats["news_fetched"] += len(items)
            except Exception as e:
                log.error("source_fetch_error", source=source.source_name, error=str(e))
                stats["errors"] += 1
        
        if not all_items:
            log.info("no_news_fetched")
            return stats
        
        # Deduplicate
        unique_items = []
        for item in all_items:
            if item.id not in self.seen_ids:
                unique_items.append(item)
                self.seen_ids.add(item.id)
            else:
                stats["news_duplicate"] += 1
        
        # Trim seen_ids if too large
        if len(self.seen_ids) > self.max_seen_ids:
            # Keep most recent half
            self.seen_ids = set(list(self.seen_ids)[-self.max_seen_ids // 2:])
        
        if not unique_items:
            log.info("all_news_duplicate", count=len(all_items))
            return stats
        
        # Insert news items into database
        try:
            rows = [self._news_item_to_row(item) for item in unique_items]
            insert_rows(
                "fxai.news_items",
                rows,
                ["id", "ts", "source", "headline", "content", "url", "author", "language", "raw_json"]
            )
            stats["news_inserted"] = len(rows)
            log.info("news_inserted", count=len(rows))
        except Exception as e:
            log.error("news_insert_failed", error=str(e))
            stats["errors"] += 1
        
        # Run sentiment analysis on subset
        if self.enable_sentiment and self.llm_client:
            await self._analyze_sentiment(unique_items[:self.sentiment_batch_size], stats)
        
        return stats
    
    async def _analyze_sentiment(self, items: List[NewsItem], stats: dict):
        """Analyze sentiment for news items."""
        for item in items:
            try:
                result = await self.llm_client.analyze_sentiment(
                    headline=item.headline,
                    content=item.content,
                    source=item.source,
                    timestamp=item.ts
                )
                
                # Insert sentiment score
                row = self._sentiment_result_to_row(item.id, result)
                insert_rows(
                    "fxai.sentiment_scores",
                    [row],
                    [
                        "news_id", "ts", "model_version",
                        "sentiment_overall", "sentiment_usd", "sentiment_inr",
                        "sentiment_eur", "sentiment_gbp", "sentiment_jpy",
                        "confidence", "impact_score", "urgency",
                        "currencies", "countries", "institutions", "topics",
                        "explanation", "key_phrases",
                        "processing_time_ms", "tokens_used", "api_cost_usd"
                    ]
                )
                
                stats["sentiment_analyzed"] += 1
                log.info("sentiment_analyzed",
                        news_id=item.id,
                        sentiment=result.sentiment_overall,
                        impact=result.impact_score,
                        cost=result.api_cost_usd)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            
            except Exception as e:
                log.error("sentiment_analysis_error", news_id=item.id, error=str(e))
                stats["errors"] += 1
    
    def _news_item_to_row(self, item: NewsItem) -> tuple:
        """Convert NewsItem to database row."""
        return (
            item.id,
            item.ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            item.source,
            item.headline,
            item.content[:10000],  # Truncate very long content
            item.url,
            item.author,
            item.language,
            item.raw_json[:5000] if item.raw_json else ""  # Truncate raw JSON
        )
    
    def _sentiment_result_to_row(self, news_id: str, result: SentimentResult) -> tuple:
        """Convert SentimentResult to database row."""
        from datetime import datetime, timezone
        
        return (
            news_id,
            datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            result.model_version,
            result.sentiment_overall,
            result.sentiment_usd,
            result.sentiment_inr,
            result.sentiment_eur,
            result.sentiment_gbp,
            result.sentiment_jpy,
            result.confidence,
            result.impact_score,
            result.urgency,
            result.currencies,
            result.countries,
            result.institutions,
            result.topics,
            result.explanation,
            result.key_phrases,
            result.processing_time_ms,
            result.tokens_used,
            result.api_cost_usd
        )
    
    async def run_continuous(self):
        """Run continuous ingestion loop."""
        log.info("news_ingester_starting",
                sources=len(self.sources),
                poll_interval=self.poll_interval,
                sentiment_enabled=self.enable_sentiment)
        
        # Initial delay to avoid startup race conditions
        await asyncio.sleep(2)
        
        while RUNNING:
            try:
                stats = await self.run_once()
                log.info("ingestion_cycle_complete", **stats)
            except Exception as e:
                log.error("ingestion_cycle_error", error=str(e))
            
            # Sleep until next cycle
            for _ in range(self.poll_interval):
                if not RUNNING:
                    break
                await asyncio.sleep(1)
        
        log.info("news_ingester_shutdown")


def parse_args():
    """Parse command-line arguments."""
    ap = argparse.ArgumentParser(description="News ingestion worker")
    
    ap.add_argument("--poll-interval", type=int,
                   default=int(os.getenv("NEWS_POLL_INTERVAL_SEC", "60")),
                   help="Seconds between polling cycles")
    
    ap.add_argument("--lookback-hours", type=int,
                   default=int(os.getenv("NEWS_LOOKBACK_HOURS", "1")),
                   help="Hours of news history to fetch")
    
    ap.add_argument("--enable-sentiment", action="store_true",
                   default=os.getenv("NEWS_ENABLE_SENTIMENT", "true").lower() == "true",
                   help="Enable LLM sentiment analysis")
    
    ap.add_argument("--sentiment-batch-size", type=int,
                   default=int(os.getenv("NEWS_SENTIMENT_BATCH_SIZE", "5")),
                   help="Max news items to analyze per cycle")
    
    ap.add_argument("--newsapi-key", type=str,
                   default=os.getenv("NEWSAPI_KEY", ""),
                   help="NewsAPI.org API key")
    
    ap.add_argument("--alphavantage-key", type=str,
                   default=os.getenv("ALPHAVANTAGE_KEY", ""),
                   help="Alpha Vantage API key")
    
    # Advanced sources
    ap.add_argument("--twitter-bearer-token", type=str,
                   default=os.getenv("TWITTER_BEARER_TOKEN", ""),
                   help="Twitter API Bearer Token")
    
    ap.add_argument("--trading-economics-key", type=str,
                   default=os.getenv("TRADING_ECONOMICS_KEY", ""),
                   help="Trading Economics API key")
    
    ap.add_argument("--finnhub-key", type=str,
                   default=os.getenv("FINNHUB_KEY", ""),
                   help="Finnhub API key")
    
    ap.add_argument("--enable-central-banks", action="store_true",
                   default=os.getenv("ENABLE_CENTRAL_BANKS", "true").lower() == "true",
                   help="Enable central bank website scrapers")
    
    ap.add_argument("--enable-twitter", action="store_true",
                   default=os.getenv("ENABLE_TWITTER", "false").lower() == "true",
                   help="Enable Twitter sources")
    
    ap.add_argument("--enable-advanced-apis", action="store_true",
                   default=os.getenv("ENABLE_ADVANCED_APIS", "false").lower() == "true",
                   help="Enable advanced API sources (Trading Economics, Finnhub)")
    
    return ap.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Create basic news sources
    sources = create_default_sources(
        newsapi_key=args.newsapi_key,
        alphavantage_key=args.alphavantage_key
    )
    
    # Add advanced sources if enabled
    advanced_sources = create_advanced_sources(
        twitter_bearer_token=args.twitter_bearer_token,
        trading_economics_key=args.trading_economics_key,
        finnhub_key=args.finnhub_key,
        include_central_banks=args.enable_central_banks,
        include_twitter=args.enable_twitter
    )
    
    sources.extend(advanced_sources)
    
    if not sources:
        log.error("no_sources_configured")
        return
    
    log.info("sources_configured", 
            total=len(sources),
            basic=len(sources) - len(advanced_sources),
            advanced=len(advanced_sources))
    
    # Create and run ingester
    ingester = NewsIngester(
        sources=sources,
        poll_interval_seconds=args.poll_interval,
        lookback_hours=args.lookback_hours,
        enable_sentiment=args.enable_sentiment,
        sentiment_batch_size=args.sentiment_batch_size
    )
    
    await ingester.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())
