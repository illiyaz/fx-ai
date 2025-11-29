"""
News source interfaces for fetching articles from various providers.
"""
from __future__ import annotations
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional
import structlog

log = structlog.get_logger()


@dataclass
class NewsItem:
    """Represents a single news article or post."""
    id: str  # Unique identifier (hash of url + timestamp)
    ts: datetime  # Publication timestamp
    source: str  # reuters, bloomberg, twitter, etc.
    headline: str
    content: str
    url: str
    author: str = ""
    language: str = "en"
    raw_json: str = ""  # Original JSON for debugging
    
    @classmethod
    def create(cls, headline: str, content: str, url: str, source: str,
               ts: Optional[datetime] = None, **kwargs) -> NewsItem:
        """Create a NewsItem with auto-generated ID."""
        if ts is None:
            ts = datetime.now(timezone.utc)
        
        # Generate unique ID from url + timestamp
        id_str = f"{url}_{ts.isoformat()}"
        item_id = hashlib.sha256(id_str.encode()).hexdigest()[:16]
        
        return cls(
            id=item_id,
            ts=ts,
            source=source,
            headline=headline,
            content=content,
            url=url,
            **kwargs
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        d = asdict(self)
        # Convert datetime to string for ClickHouse
        d['ts'] = self.ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return d


class NewsSource(ABC):
    """Abstract base class for news sources."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    async def fetch_latest(self, lookback_hours: int = 1) -> List[NewsItem]:
        """
        Fetch latest news items.
        
        Args:
            lookback_hours: How far back to fetch news
        
        Returns:
            List of NewsItem objects
        """
        pass
    
    def is_relevant(self, item: NewsItem) -> bool:
        """
        Check if news item is relevant to FX trading.
        
        Override this method for custom filtering logic.
        """
        # Basic relevance check: contains FX-related keywords
        keywords = [
            "forex", "exchange rate", "currency", "central bank",
            "fed", "federal reserve", "rbi", "ecb", "boj",
            "interest rate", "monetary policy", "inflation",
            "usd", "inr", "eur", "gbp", "jpy",
            "dollar", "rupee", "euro", "pound", "yen"
        ]
        
        text = (item.headline + " " + item.content).lower()
        return any(keyword in text for keyword in keywords)


class RSSSource(NewsSource):
    """Fetch news from RSS feeds."""
    
    def __init__(self, source_name: str, feed_url: str):
        super().__init__(source_name)
        self.feed_url = feed_url
    
    async def fetch_latest(self, lookback_hours: int = 1) -> List[NewsItem]:
        """Fetch latest items from RSS feed."""
        try:
            import feedparser
            from datetime import timedelta
            
            # Parse feed
            feed = feedparser.parse(self.feed_url)
            
            items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for entry in feed.entries:
                try:
                    # Parse publication date
                    if hasattr(entry, 'published_parsed'):
                        pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed'):
                        pub_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_time = datetime.now(timezone.utc)
                    
                    # Skip old items
                    if pub_time < cutoff_time:
                        continue
                    
                    # Extract content
                    headline = entry.get('title', '')
                    content = entry.get('summary', '') or entry.get('description', '')
                    url = entry.get('link', '')
                    author = entry.get('author', '')
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=headline,
                        content=content,
                        url=url,
                        source=self.source_name,
                        ts=pub_time,
                        author=author,
                        raw_json=json.dumps(dict(entry))
                    )
                    
                    # Filter for relevance
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("rss_entry_parse_error", error=str(e), source=self.source_name)
                    continue
            
            log.info("rss_fetch_complete", source=self.source_name, count=len(items))
            return items
        
        except Exception as e:
            log.error("rss_fetch_failed", source=self.source_name, error=str(e))
            return []


class NewsAPISource(NewsSource):
    """Fetch news from NewsAPI.org."""
    
    def __init__(self, api_key: str, query: str = "forex OR currency OR \"central bank\""):
        super().__init__("newsapi")
        self.api_key = api_key
        self.query = query
        self.base_url = "https://newsapi.org/v2/everything"
    
    async def fetch_latest(self, lookback_hours: int = 1) -> List[NewsItem]:
        """Fetch latest news from NewsAPI."""
        try:
            import httpx
            from datetime import timedelta
            
            # Calculate time range
            from_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            # Build request
            params = {
                "q": self.query,
                "from": from_time.isoformat(),
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": self.api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            items = []
            for article in data.get("articles", []):
                try:
                    # Parse timestamp
                    pub_time_str = article.get("publishedAt", "")
                    pub_time = datetime.fromisoformat(pub_time_str.replace('Z', '+00:00'))
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=article.get("title", ""),
                        content=article.get("description", "") + "\n\n" + article.get("content", ""),
                        url=article.get("url", ""),
                        source=f"newsapi_{article.get('source', {}).get('name', 'unknown')}",
                        ts=pub_time,
                        author=article.get("author", ""),
                        raw_json=json.dumps(article)
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("newsapi_article_parse_error", error=str(e))
                    continue
            
            log.info("newsapi_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("newsapi_fetch_failed", error=str(e))
            return []


class AlphaVantageNewsSource(NewsSource):
    """Fetch news from Alpha Vantage News API."""
    
    def __init__(self, api_key: str, topics: str = "forex,economy"):
        super().__init__("alphavantage")
        self.api_key = api_key
        self.topics = topics
        self.base_url = "https://www.alphavantage.co/query"
    
    async def fetch_latest(self, lookback_hours: int = 1) -> List[NewsItem]:
        """Fetch latest news from Alpha Vantage."""
        try:
            import httpx
            from datetime import timedelta
            
            params = {
                "function": "NEWS_SENTIMENT",
                "topics": self.topics,
                "apikey": self.api_key,
                "sort": "LATEST",
                "limit": 50
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for article in data.get("feed", []):
                try:
                    # Parse timestamp
                    time_str = article.get("time_published", "")
                    # Format: YYYYMMDDTHHMMSS
                    pub_time = datetime.strptime(time_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                    
                    if pub_time < cutoff_time:
                        continue
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=article.get("title", ""),
                        content=article.get("summary", ""),
                        url=article.get("url", ""),
                        source=f"alphavantage_{article.get('source', 'unknown')}",
                        ts=pub_time,
                        author=article.get("authors", [""])[0] if article.get("authors") else "",
                        raw_json=json.dumps(article)
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("alphavantage_article_parse_error", error=str(e))
                    continue
            
            log.info("alphavantage_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("alphavantage_fetch_failed", error=str(e))
            return []


# Predefined RSS feeds for major financial news sources
DEFAULT_RSS_FEEDS = {
    "reuters_business": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
    "bloomberg_markets": "https://www.bloomberg.com/feed/podcast/markets-daily.xml",
    "forexlive": "https://www.forexlive.com/feed/news",
    "fxstreet": "https://www.fxstreet.com/rss/news",
    "investing_forex": "https://www.investing.com/rss/news_285.rss",
    "marketwatch_economy": "https://www.marketwatch.com/rss/economy",
}


def create_default_sources(newsapi_key: str = "", alphavantage_key: str = "") -> List[NewsSource]:
    """
    Create default news sources.
    
    Args:
        newsapi_key: NewsAPI.org API key (optional)
        alphavantage_key: Alpha Vantage API key (optional)
    
    Returns:
        List of configured news sources
    """
    sources = []
    
    # Add RSS feeds
    for name, url in DEFAULT_RSS_FEEDS.items():
        sources.append(RSSSource(name, url))
    
    # Add API sources if keys provided
    if newsapi_key:
        sources.append(NewsAPISource(newsapi_key))
    
    if alphavantage_key:
        sources.append(AlphaVantageNewsSource(alphavantage_key))
    
    return sources
