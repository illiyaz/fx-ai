"""
Bayesian fusion engine for combining ML and LLM predictions.

This module implements the hybrid approach that combines:
- Technical ML predictions (LightGBM)
- News sentiment analysis (LLM)

The fusion uses Bayesian updating to adjust probabilities based on
news sentiment, with adaptive weighting based on confidence levels.
"""
from __future__ import annotations
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import structlog

log = structlog.get_logger()


@dataclass
class MLPrediction:
    """ML model prediction."""
    prob_up: float  # 0 to 1
    expected_delta_bps: float
    confidence: float = 0.5
    model_id: str = "unknown"


@dataclass
class NewsSentiment:
    """News sentiment from LLM."""
    sentiment_score: float  # -1 to +1
    confidence: float  # 0 to 1
    impact_score: float  # 0 to 10
    urgency: str  # low, medium, high, critical
    summary: str = ""


@dataclass
class HybridPrediction:
    """Fused ML + LLM prediction."""
    # ML component
    prob_up_ml: float
    expected_delta_ml: float
    ml_model_id: str
    
    # LLM component
    sentiment_score: float
    sentiment_confidence: float
    news_impact: float
    news_summary: str
    
    # Fused result
    prob_up_hybrid: float
    expected_delta_hybrid: float
    fusion_weight_ml: float
    fusion_weight_llm: float
    
    # Explanation
    explanation: str


class BayesianFusionEngine:
    """
    Bayesian fusion engine for combining ML and LLM predictions.
    
    The fusion strategy adapts based on:
    1. LLM confidence level
    2. News impact score
    3. News urgency
    4. Market conditions
    """
    
    def __init__(self,
                 max_llm_weight: float = 0.4,
                 min_confidence_threshold: float = 0.3,
                 high_impact_threshold: float = 7.0):
        """
        Initialize fusion engine.
        
        Args:
            max_llm_weight: Maximum weight given to LLM (0-1)
            min_confidence_threshold: Minimum LLM confidence to use
            high_impact_threshold: Impact score threshold for high-impact news
        """
        self.max_llm_weight = max_llm_weight
        self.min_confidence_threshold = min_confidence_threshold
        self.high_impact_threshold = high_impact_threshold
    
    def fuse(self, ml_pred: MLPrediction, news_sent: Optional[NewsSentiment]) -> HybridPrediction:
        """
        Fuse ML and LLM predictions using Bayesian updating.
        
        Args:
            ml_pred: ML model prediction
            news_sent: News sentiment from LLM (None if no recent news)
        
        Returns:
            HybridPrediction with fused probability and explanation
        """
        # If no news or low confidence, use ML only
        if news_sent is None or news_sent.confidence < self.min_confidence_threshold:
            return self._ml_only_prediction(ml_pred, news_sent)
        
        # Calculate fusion weights based on news characteristics
        weight_llm = self._calculate_llm_weight(news_sent)
        weight_ml = 1.0 - weight_llm
        
        # Bayesian probability update
        prob_hybrid = self._bayesian_update(
            ml_pred.prob_up,
            news_sent.sentiment_score,
            weight_llm
        )
        
        # Adjust expected delta based on news
        delta_hybrid = self._adjust_expected_delta(
            ml_pred.expected_delta_bps,
            news_sent.sentiment_score,
            news_sent.impact_score,
            weight_llm
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            ml_pred, news_sent, prob_hybrid, delta_hybrid, weight_ml, weight_llm
        )
        
        log.info("fusion_complete",
                prob_ml=ml_pred.prob_up,
                prob_hybrid=prob_hybrid,
                weight_ml=weight_ml,
                weight_llm=weight_llm,
                sentiment=news_sent.sentiment_score)
        
        return HybridPrediction(
            prob_up_ml=ml_pred.prob_up,
            expected_delta_ml=ml_pred.expected_delta_bps,
            ml_model_id=ml_pred.model_id,
            sentiment_score=news_sent.sentiment_score,
            sentiment_confidence=news_sent.confidence,
            news_impact=news_sent.impact_score,
            news_summary=news_sent.summary,
            prob_up_hybrid=prob_hybrid,
            expected_delta_hybrid=delta_hybrid,
            fusion_weight_ml=weight_ml,
            fusion_weight_llm=weight_llm,
            explanation=explanation
        )
    
    def _ml_only_prediction(self, ml_pred: MLPrediction, 
                           news_sent: Optional[NewsSentiment]) -> HybridPrediction:
        """Return ML-only prediction when news is unavailable or unreliable."""
        reason = "no recent news" if news_sent is None else "low news confidence"
        
        return HybridPrediction(
            prob_up_ml=ml_pred.prob_up,
            expected_delta_ml=ml_pred.expected_delta_bps,
            ml_model_id=ml_pred.model_id,
            sentiment_score=0.0,
            sentiment_confidence=0.0,
            news_impact=0.0,
            news_summary=f"Using ML-only prediction ({reason})",
            prob_up_hybrid=ml_pred.prob_up,
            expected_delta_hybrid=ml_pred.expected_delta_bps,
            fusion_weight_ml=1.0,
            fusion_weight_llm=0.0,
            explanation=f"Technical analysis only ({reason})"
        )
    
    def _calculate_llm_weight(self, news_sent: NewsSentiment) -> float:
        """
        Calculate weight to give LLM based on news characteristics.
        
        Higher weight when:
        - High confidence
        - High impact score
        - Critical urgency
        
        Returns:
            Weight between 0 and max_llm_weight
        """
        # Base weight from confidence
        base_weight = news_sent.confidence * self.max_llm_weight
        
        # Boost for high-impact news
        if news_sent.impact_score >= self.high_impact_threshold:
            impact_boost = min(0.1, (news_sent.impact_score - self.high_impact_threshold) * 0.02)
            base_weight += impact_boost
        
        # Boost for critical urgency
        urgency_boost = {
            "low": 0.0,
            "medium": 0.0,
            "high": 0.05,
            "critical": 0.1
        }.get(news_sent.urgency, 0.0)
        base_weight += urgency_boost
        
        # Cap at max_llm_weight
        return min(base_weight, self.max_llm_weight)
    
    def _bayesian_update(self, prior_prob: float, sentiment: float, 
                        llm_weight: float) -> float:
        """
        Update probability using Bayesian-inspired approach.
        
        Args:
            prior_prob: ML model's probability (0-1)
            sentiment: News sentiment (-1 to +1)
            llm_weight: Weight to give LLM signal (0-1)
        
        Returns:
            Updated probability (0-1)
        """
        # Convert sentiment to probability shift
        # Positive sentiment increases prob_up, negative decreases it
        sentiment_adjustment = sentiment * llm_weight
        
        # Apply adjustment asymmetrically based on direction
        if sentiment_adjustment > 0:
            # Positive sentiment: shift up, but with diminishing returns near 1.0
            posterior = prior_prob + sentiment_adjustment * (1.0 - prior_prob)
        else:
            # Negative sentiment: shift down, but with diminishing returns near 0.0
            posterior = prior_prob + sentiment_adjustment * prior_prob
        
        # Ensure bounds
        return float(np.clip(posterior, 0.0, 1.0))
    
    def _adjust_expected_delta(self, base_delta: float, sentiment: float,
                               impact_score: float, llm_weight: float) -> float:
        """
        Adjust expected price change based on news.
        
        High-impact news can amplify or dampen expected moves.
        
        Args:
            base_delta: ML model's expected delta (bps)
            sentiment: News sentiment (-1 to +1)
            impact_score: News impact (0-10)
            llm_weight: Weight given to LLM
        
        Returns:
            Adjusted expected delta (bps)
        """
        # Calculate multiplier based on sentiment and impact
        # High-impact bullish news amplifies positive moves
        # High-impact bearish news amplifies negative moves
        
        # Normalize impact to 0-1
        impact_normalized = min(impact_score / 10.0, 1.0)
        
        # Multiplier ranges from 0.7 to 1.5 based on sentiment and impact
        max_amplification = 0.5  # Up to 50% amplification
        multiplier = 1.0 + (sentiment * impact_normalized * llm_weight * max_amplification)
        
        adjusted_delta = base_delta * multiplier
        
        return float(adjusted_delta)
    
    def _generate_explanation(self, ml_pred: MLPrediction, news_sent: NewsSentiment,
                             prob_hybrid: float, delta_hybrid: float,
                             weight_ml: float, weight_llm: float) -> str:
        """Generate human-readable explanation of fusion."""
        parts = []
        
        # ML component
        ml_direction = "bullish" if ml_pred.prob_up > 0.5 else "bearish"
        parts.append(f"Technical analysis: {ml_direction} (prob={ml_pred.prob_up:.2f})")
        
        # News component
        if weight_llm > 0.05:  # Only mention if significant
            news_direction = "bullish" if news_sent.sentiment_score > 0 else "bearish"
            parts.append(f"News sentiment: {news_direction} (score={news_sent.sentiment_score:+.2f}, impact={news_sent.impact_score:.1f}/10)")
            
            if news_sent.summary:
                parts.append(f"Context: {news_sent.summary}")
        
        # Fusion result
        final_direction = "bullish" if prob_hybrid > 0.5 else "bearish"
        parts.append(f"Combined: {final_direction} (prob={prob_hybrid:.2f}, expected={delta_hybrid:+.2f} bps)")
        
        # Weights
        parts.append(f"Weights: ML={weight_ml:.0%}, News={weight_llm:.0%}")
        
        return " | ".join(parts)


def sentiment_to_probability(sentiment: float) -> float:
    """
    Convert sentiment score (-1 to +1) to probability (0 to 1).
    
    Uses sigmoid-like transformation centered at 0.5.
    """
    # Map -1 to 0.1, 0 to 0.5, +1 to 0.9
    # This prevents extreme probabilities from sentiment alone
    return 0.5 + (sentiment * 0.4)
