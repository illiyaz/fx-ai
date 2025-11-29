"""
News aggregator for fetching and summarizing recent news sentiment.

Provides cached access to recent news sentiment scores for use in
hybrid ML+LLM predictions.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog

from apps.common.clickhouse_client import query_df
from apps.llm.fusion import NewsSentiment

log = structlog.get_logger()

# Cache TTL from environment
CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", "300"))


class NewsAggregator:
    """
    Aggregates recent news sentiment for a currency pair.
    
    Provides cached access to avoid repeated database queries.
    """
    
    def __init__(self, cache_ttl_seconds: int = CACHE_TTL_SECONDS):
        self.cache_ttl = cache_ttl_seconds
        self._cache = {}  # {pair: (sentiment, timestamp)}
    
    def get_recent_sentiment(self, pair: str, lookback_hours: int = 1) -> Optional[NewsSentiment]:
        """
        Get aggregated news sentiment for a currency pair.
        
        Args:
            pair: Currency pair (e.g., "USDINR")
            lookback_hours: How far back to aggregate sentiment
        
        Returns:
            NewsSentiment object or None if no recent news
        """
        # Check cache
        if pair in self._cache:
            cached_sentiment, cached_time = self._cache[pair]
            age_seconds = (datetime.now(timezone.utc) - cached_time).total_seconds()
            if age_seconds < self.cache_ttl:
                log.debug("sentiment_cache_hit", pair=pair, age_seconds=age_seconds)
                return cached_sentiment
        
        # Fetch from database
        sentiment = self._fetch_sentiment_from_db(pair, lookback_hours)
        
        # Update cache
        if sentiment:
            self._cache[pair] = (sentiment, datetime.now(timezone.utc))
        
        return sentiment
    
    def _fetch_sentiment_from_db(self, pair: str, lookback_hours: int) -> Optional[NewsSentiment]:
        """Fetch and aggregate sentiment from database."""
        try:
            # Extract currencies from pair
            base_currency = pair[:3]  # e.g., "USD"
            quote_currency = pair[3:6]  # e.g., "INR"
            
            # Query recent sentiment scores
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            sql = f"""
                SELECT 
                    sentiment_overall,
                    sentiment_usd,
                    sentiment_inr,
                    sentiment_eur,
                    sentiment_gbp,
                    sentiment_jpy,
                    confidence,
                    impact_score,
                    urgency,
                    explanation,
                    ts
                FROM fxai.sentiment_scores
                WHERE ts >= '{cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}'
                  AND (
                    has(currencies, '{base_currency}') 
                    OR has(currencies, '{quote_currency}')
                  )
                ORDER BY ts DESC
                LIMIT 20
            """
            
            df = query_df(sql)
            
            if df.empty:
                log.debug("no_recent_sentiment", pair=pair, lookback_hours=lookback_hours)
                return None
            
            # Aggregate sentiment scores (weighted by confidence and recency)
            total_weight = 0.0
            weighted_sentiment = 0.0
            weighted_impact = 0.0
            max_urgency = "low"
            explanations = []
            
            urgency_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            
            for idx, row in df.iterrows():
                # Calculate weight: more recent and more confident = higher weight
                # Make timestamp timezone-aware if it isn't already
                ts = row['ts']
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                recency_weight = max(0.1, 1.0 - (age_hours / lookback_hours))
                confidence = float(row['confidence'])
                weight = recency_weight * confidence
                
                # Aggregate sentiment (pair-specific)
                # For USDINR: positive USD sentiment = positive overall
                sentiment_base = float(row.get(f'sentiment_{base_currency.lower()}', row['sentiment_overall']))
                sentiment_quote = float(row.get(f'sentiment_{quote_currency.lower()}', 0.0))
                
                # Net sentiment: base strengthening vs quote
                net_sentiment = sentiment_base - sentiment_quote
                
                weighted_sentiment += net_sentiment * weight
                weighted_impact += float(row['impact_score']) * weight
                total_weight += weight
                
                # Track highest urgency
                row_urgency = row.get('urgency', 'low')
                if urgency_levels.get(row_urgency, 0) > urgency_levels.get(max_urgency, 0):
                    max_urgency = row_urgency
                
                # Collect explanations from high-impact news
                if float(row['impact_score']) >= 7.0 and len(explanations) < 3:
                    explanations.append(row.get('explanation', ''))
            
            if total_weight == 0:
                return None
            
            # Calculate final aggregated values
            avg_sentiment = weighted_sentiment / total_weight
            avg_impact = weighted_impact / total_weight
            avg_confidence = total_weight / len(df)  # Normalized confidence
            
            # Create summary
            summary = self._create_summary(pair, avg_sentiment, avg_impact, explanations)
            
            log.info("sentiment_aggregated",
                    pair=pair,
                    sentiment=avg_sentiment,
                    impact=avg_impact,
                    confidence=avg_confidence,
                    news_count=len(df))
            
            return NewsSentiment(
                sentiment_score=avg_sentiment,
                confidence=avg_confidence,
                impact_score=avg_impact,
                urgency=max_urgency,
                summary=summary
            )
        
        except Exception as e:
            log.error("sentiment_fetch_error", pair=pair, error=str(e))
            return None
    
    def _create_summary(self, pair: str, sentiment: float, impact: float, 
                       explanations: list) -> str:
        """Create human-readable summary of news sentiment."""
        base = pair[:3]
        quote = pair[3:6]
        
        # Sentiment direction
        if sentiment > 0.3:
            direction = f"{base} bullish vs {quote}"
        elif sentiment < -0.3:
            direction = f"{base} bearish vs {quote}"
        else:
            direction = "mixed signals"
        
        # Impact level
        if impact >= 8.0:
            impact_desc = "high-impact"
        elif impact >= 6.0:
            impact_desc = "moderate-impact"
        else:
            impact_desc = "low-impact"
        
        # Build summary
        parts = [f"Recent news: {direction} ({impact_desc})"]
        
        # Add top explanations
        if explanations:
            parts.append(f"Key: {explanations[0][:100]}...")
        
        return " | ".join(parts)
    
    def clear_cache(self, pair: Optional[str] = None):
        """Clear sentiment cache."""
        if pair:
            self._cache.pop(pair, None)
        else:
            self._cache.clear()


# Global instance for reuse
_global_aggregator = None


def get_news_aggregator() -> NewsAggregator:
    """Get global NewsAggregator instance."""
    global _global_aggregator
    if _global_aggregator is None:
        _global_aggregator = NewsAggregator()
    return _global_aggregator
