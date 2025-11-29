"""
Advanced news sources for FX-AI Advisor.

Includes:
- Twitter/X API integration
- Central bank websites (Fed, RBI, ECB, BOJ)
- Financial data providers
- Web scraping for official announcements
"""
from __future__ import annotations
import re
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import structlog

from apps.news.sources import NewsSource, NewsItem

log = structlog.get_logger()


class TwitterSource(NewsSource):
    """
    Fetch tweets from financial accounts using Twitter API v2.
    
    Requires Twitter API credentials (Bearer Token).
    """
    
    def __init__(self, bearer_token: str, accounts: List[str]):
        """
        Initialize Twitter source.
        
        Args:
            bearer_token: Twitter API Bearer Token
            accounts: List of Twitter usernames to monitor (e.g., ["federalreserve", "RBI"])
        """
        super().__init__("twitter")
        self.bearer_token = bearer_token
        self.accounts = accounts
        self.base_url = "https://api.twitter.com/2"
    
    async def fetch_latest(self, lookback_hours: int = 1) -> List[NewsItem]:
        """Fetch latest tweets from monitored accounts."""
        try:
            import httpx
            
            items = []
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            
            # Calculate time range
            start_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
            
            for account in self.accounts:
                try:
                    # Get user ID first
                    user_response = await self._get_user_id(account, headers)
                    if not user_response:
                        continue
                    
                    user_id = user_response["id"]
                    
                    # Get user's tweets
                    params = {
                        "max_results": 10,
                        "start_time": start_time,
                        "tweet.fields": "created_at,public_metrics,entities",
                        "expansions": "referenced_tweets.id"
                    }
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{self.base_url}/users/{user_id}/tweets",
                            headers=headers,
                            params=params,
                            timeout=10.0
                        )
                        response.raise_for_status()
                        data = response.json()
                    
                    # Parse tweets
                    for tweet in data.get("data", []):
                        item = self._parse_tweet(tweet, account)
                        if item and self.is_relevant(item):
                            items.append(item)
                
                except Exception as e:
                    log.warning("twitter_account_fetch_error", account=account, error=str(e))
                    continue
            
            log.info("twitter_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("twitter_fetch_failed", error=str(e))
            return []
    
    async def _get_user_id(self, username: str, headers: dict) -> Optional[dict]:
        """Get Twitter user ID from username."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/by/username/{username}",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json().get("data")
        except Exception as e:
            log.error("twitter_user_lookup_failed", username=username, error=str(e))
            return None
    
    def _parse_tweet(self, tweet: dict, account: str) -> Optional[NewsItem]:
        """Parse tweet data into NewsItem."""
        try:
            tweet_id = tweet["id"]
            text = tweet["text"]
            created_at = datetime.fromisoformat(tweet["created_at"].replace('Z', '+00:00'))
            
            # Create news item
            item = NewsItem.create(
                headline=f"@{account}: {text[:100]}...",
                content=text,
                url=f"https://twitter.com/{account}/status/{tweet_id}",
                source=f"twitter_{account}",
                ts=created_at,
                author=f"@{account}",
                raw_json=json.dumps(tweet)
            )
            
            return item
        except Exception as e:
            log.warning("tweet_parse_error", error=str(e))
            return None


class FederalReserveSource(NewsSource):
    """
    Fetch press releases and speeches from Federal Reserve website.
    
    Scrapes: https://www.federalreserve.gov/newsevents/pressreleases.htm
    """
    
    def __init__(self):
        super().__init__("federal_reserve")
        self.base_url = "https://www.federalreserve.gov"
        self.press_releases_url = f"{self.base_url}/newsevents/pressreleases.htm"
    
    async def fetch_latest(self, lookback_hours: int = 24) -> List[NewsItem]:
        """Fetch latest Fed press releases."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.press_releases_url, timeout=10.0)
                response.raise_for_status()
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            # Find press release items
            for row in soup.find_all('div', class_='row'):
                try:
                    # Extract date
                    date_elem = row.find('time')
                    if not date_elem:
                        continue
                    
                    date_str = date_elem.get('datetime', '')
                    pub_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    if pub_time < cutoff_time:
                        continue
                    
                    # Extract title and link
                    link_elem = row.find('a')
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    url = self.base_url + link_elem.get('href', '')
                    
                    # Fetch full content
                    content = await self._fetch_article_content(url)
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=title,
                        content=content or title,
                        url=url,
                        source="federal_reserve",
                        ts=pub_time,
                        author="Federal Reserve"
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("fed_item_parse_error", error=str(e))
                    continue
            
            log.info("fed_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("fed_fetch_failed", error=str(e))
            return []
    
    async def _fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch full article content."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find main content
            content_div = soup.find('div', class_='col-xs-12')
            if content_div:
                # Extract text, remove scripts and styles
                for script in content_div(["script", "style"]):
                    script.decompose()
                text = content_div.get_text(separator=' ', strip=True)
                return text[:5000]  # Limit length
            
            return None
        except Exception:
            return None


class RBISource(NewsSource):
    """
    Fetch press releases from Reserve Bank of India.
    
    Scrapes: https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx
    """
    
    def __init__(self):
        super().__init__("rbi")
        self.base_url = "https://www.rbi.org.in"
        self.press_releases_url = f"{self.base_url}/Scripts/BS_PressReleaseDisplay.aspx"
    
    async def fetch_latest(self, lookback_hours: int = 24) -> List[NewsItem]:
        """Fetch latest RBI press releases."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.press_releases_url, timeout=10.0)
                response.raise_for_status()
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            # Find press release table
            table = soup.find('table')
            if not table:
                return items
            
            for row in table.find_all('tr')[1:]:  # Skip header
                try:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    
                    # Extract date
                    date_str = cols[0].get_text(strip=True)
                    # Parse date (format: "Nov 28, 2025")
                    pub_time = datetime.strptime(date_str, "%b %d, %Y").replace(tzinfo=timezone.utc)
                    
                    if pub_time < cutoff_time:
                        continue
                    
                    # Extract title and link
                    link_elem = cols[1].find('a')
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    url = self.base_url + link_elem.get('href', '')
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=title,
                        content=title,  # RBI doesn't provide full content easily
                        url=url,
                        source="rbi",
                        ts=pub_time,
                        author="Reserve Bank of India"
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("rbi_item_parse_error", error=str(e))
                    continue
            
            log.info("rbi_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("rbi_fetch_failed", error=str(e))
            return []


class ECBSource(NewsSource):
    """
    Fetch press releases from European Central Bank.
    
    Uses ECB's RSS feed.
    """
    
    def __init__(self):
        super().__init__("ecb")
        self.feed_url = "https://www.ecb.europa.eu/rss/press.html"
    
    async def fetch_latest(self, lookback_hours: int = 24) -> List[NewsItem]:
        """Fetch latest ECB press releases."""
        try:
            import feedparser
            
            feed = feedparser.parse(self.feed_url)
            items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for entry in feed.entries:
                try:
                    # Parse publication date
                    if hasattr(entry, 'published_parsed'):
                        pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_time = datetime.now(timezone.utc)
                    
                    if pub_time < cutoff_time:
                        continue
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=entry.get('title', ''),
                        content=entry.get('summary', ''),
                        url=entry.get('link', ''),
                        source="ecb",
                        ts=pub_time,
                        author="European Central Bank",
                        raw_json=json.dumps(dict(entry))
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("ecb_item_parse_error", error=str(e))
                    continue
            
            log.info("ecb_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("ecb_fetch_failed", error=str(e))
            return []


class BOJSource(NewsSource):
    """
    Fetch press releases from Bank of Japan.
    
    Scrapes: https://www.boj.or.jp/en/announcements/index.htm
    """
    
    def __init__(self):
        super().__init__("boj")
        self.base_url = "https://www.boj.or.jp"
        self.announcements_url = f"{self.base_url}/en/announcements/index.htm"
    
    async def fetch_latest(self, lookback_hours: int = 24) -> List[NewsItem]:
        """Fetch latest BOJ announcements."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.announcements_url, timeout=10.0)
                response.raise_for_status()
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            # Find announcement items
            for item_div in soup.find_all('div', class_='release'):
                try:
                    # Extract date
                    date_elem = item_div.find('time')
                    if not date_elem:
                        continue
                    
                    date_str = date_elem.get('datetime', '')
                    pub_time = datetime.fromisoformat(date_str)
                    
                    if pub_time < cutoff_time:
                        continue
                    
                    # Extract title and link
                    link_elem = item_div.find('a')
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    url = self.base_url + link_elem.get('href', '')
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=title,
                        content=title,
                        url=url,
                        source="boj",
                        ts=pub_time,
                        author="Bank of Japan"
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("boj_item_parse_error", error=str(e))
                    continue
            
            log.info("boj_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("boj_fetch_failed", error=str(e))
            return []


class TradingEconomicsSource(NewsSource):
    """
    Fetch economic calendar events from Trading Economics API.
    
    Requires Trading Economics API key.
    """
    
    def __init__(self, api_key: str, countries: List[str] = None):
        """
        Initialize Trading Economics source.
        
        Args:
            api_key: Trading Economics API key
            countries: List of country codes (e.g., ["US", "IN", "EU"])
        """
        super().__init__("trading_economics")
        self.api_key = api_key
        self.countries = countries or ["US", "IN", "EU", "GB", "JP"]
        self.base_url = "https://api.tradingeconomics.com"
    
    async def fetch_latest(self, lookback_hours: int = 24) -> List[NewsItem]:
        """Fetch upcoming economic events."""
        try:
            import httpx
            
            items = []
            
            # Fetch calendar events
            params = {
                "c": self.api_key,
                "country": ",".join(self.countries),
                "format": "json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/calendar",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                events = response.json()
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for event in events:
                try:
                    # Parse event time
                    date_str = event.get("Date", "")
                    pub_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    if pub_time < cutoff_time:
                        continue
                    
                    # Build headline
                    country = event.get("Country", "")
                    event_name = event.get("Event", "")
                    actual = event.get("Actual", "")
                    forecast = event.get("Forecast", "")
                    previous = event.get("Previous", "")
                    
                    headline = f"{country}: {event_name}"
                    content = f"{event_name} - Actual: {actual}, Forecast: {forecast}, Previous: {previous}"
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=headline,
                        content=content,
                        url=f"https://tradingeconomics.com/{country}/calendar",
                        source="trading_economics",
                        ts=pub_time,
                        author="Trading Economics",
                        raw_json=json.dumps(event)
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("trading_economics_event_parse_error", error=str(e))
                    continue
            
            log.info("trading_economics_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("trading_economics_fetch_failed", error=str(e))
            return []


class FinnhubNewsSource(NewsSource):
    """
    Fetch forex news from Finnhub API.
    
    Requires Finnhub API key (free tier available).
    """
    
    def __init__(self, api_key: str):
        super().__init__("finnhub")
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
    
    async def fetch_latest(self, lookback_hours: int = 24) -> List[NewsItem]:
        """Fetch latest forex news from Finnhub."""
        try:
            import httpx
            
            # Calculate time range (Unix timestamp)
            from_time = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())
            to_time = int(datetime.now(timezone.utc).timestamp())
            
            params = {
                "category": "forex",
                "token": self.api_key,
                "from": from_time,
                "to": to_time
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/news",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                news_items = response.json()
            
            items = []
            for article in news_items:
                try:
                    # Parse timestamp
                    pub_time = datetime.fromtimestamp(article.get("datetime", 0), tz=timezone.utc)
                    
                    # Create news item
                    item = NewsItem.create(
                        headline=article.get("headline", ""),
                        content=article.get("summary", ""),
                        url=article.get("url", ""),
                        source=f"finnhub_{article.get('source', 'unknown')}",
                        ts=pub_time,
                        author=article.get("source", ""),
                        raw_json=json.dumps(article)
                    )
                    
                    if self.is_relevant(item):
                        items.append(item)
                
                except Exception as e:
                    log.warning("finnhub_article_parse_error", error=str(e))
                    continue
            
            log.info("finnhub_fetch_complete", count=len(items))
            return items
        
        except Exception as e:
            log.error("finnhub_fetch_failed", error=str(e))
            return []


# Predefined central bank Twitter accounts
CENTRAL_BANK_TWITTER_ACCOUNTS = [
    "federalreserve",  # US Federal Reserve
    "RBI",             # Reserve Bank of India
    "ecb",             # European Central Bank
    "bankofengland",   # Bank of England
    "bankofcanada",    # Bank of Canada
    "RBA_Media",       # Reserve Bank of Australia
]

# Financial news Twitter accounts
FINANCIAL_NEWS_TWITTER_ACCOUNTS = [
    "Reuters",
    "Bloomberg",
    "WSJ",
    "FT",
    "CNBC",
    "ForexLive",
    "FXStreetNews",
]


def create_advanced_sources(
    twitter_bearer_token: str = "",
    trading_economics_key: str = "",
    finnhub_key: str = "",
    include_central_banks: bool = True,
    include_twitter: bool = True
) -> List[NewsSource]:
    """
    Create advanced news sources.
    
    Args:
        twitter_bearer_token: Twitter API Bearer Token
        trading_economics_key: Trading Economics API key
        finnhub_key: Finnhub API key
        include_central_banks: Include central bank website scrapers
        include_twitter: Include Twitter sources
    
    Returns:
        List of configured advanced news sources
    """
    sources = []
    
    # Central bank websites
    if include_central_banks:
        sources.append(FederalReserveSource())
        sources.append(RBISource())
        sources.append(ECBSource())
        sources.append(BOJSource())
    
    # Twitter
    if include_twitter and twitter_bearer_token:
        # Central bank accounts
        sources.append(TwitterSource(
            twitter_bearer_token,
            CENTRAL_BANK_TWITTER_ACCOUNTS
        ))
        # Financial news accounts
        sources.append(TwitterSource(
            twitter_bearer_token,
            FINANCIAL_NEWS_TWITTER_ACCOUNTS
        ))
    
    # API sources
    if trading_economics_key:
        sources.append(TradingEconomicsSource(trading_economics_key))
    
    if finnhub_key:
        sources.append(FinnhubNewsSource(finnhub_key))
    
    return sources
