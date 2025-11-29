"""
LLM client for sentiment analysis and news interpretation.

Supports multiple LLM providers with fallback logic:
- OpenAI GPT-4 Turbo (primary)
- Anthropic Claude 3 (backup)
- Local models (future)
"""
from __future__ import annotations
import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import structlog

log = structlog.get_logger()

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, local
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))


@dataclass
class SentimentResult:
    """Result from LLM sentiment analysis."""
    sentiment_overall: float  # -1 to +1
    sentiment_usd: float
    sentiment_inr: float
    sentiment_eur: float = 0.0
    sentiment_gbp: float = 0.0
    sentiment_jpy: float = 0.0
    
    confidence: float = 0.5  # 0 to 1
    impact_score: float = 5.0  # 0 to 10
    urgency: str = "medium"  # low, medium, high, critical
    
    currencies: List[str] = None
    countries: List[str] = None
    institutions: List[str] = None
    topics: List[str] = None
    
    explanation: str = ""
    key_phrases: List[str] = None
    
    # Metadata
    processing_time_ms: int = 0
    tokens_used: int = 0
    api_cost_usd: float = 0.0
    model_version: str = ""
    
    def __post_init__(self):
        if self.currencies is None:
            self.currencies = []
        if self.countries is None:
            self.countries = []
        if self.institutions is None:
            self.institutions = []
        if self.topics is None:
            self.topics = []
        if self.key_phrases is None:
            self.key_phrases = []


class LLMClient:
    """Base LLM client interface."""
    
    def __init__(self, model: str = LLM_MODEL, temperature: float = LLM_TEMPERATURE):
        self.model = model
        self.temperature = temperature
        self.max_tokens = LLM_MAX_TOKENS
    
    async def analyze_sentiment(self, headline: str, content: str, source: str, 
                                timestamp: datetime) -> SentimentResult:
        """Analyze sentiment of a news article."""
        raise NotImplementedError
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost in USD."""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI GPT-4 client for sentiment analysis."""
    
    # Pricing (per 1M tokens, as of Nov 2025)
    PRICING = {
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }
    
    def __init__(self, api_key: str = OPENAI_API_KEY, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client
    
    async def analyze_sentiment(self, headline: str, content: str, source: str,
                                timestamp: datetime) -> SentimentResult:
        """Analyze sentiment using GPT-4."""
        start_time = time.time()
        
        prompt = self._build_sentiment_prompt(headline, content, source, timestamp)
        
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result_json = json.loads(response.choices[0].message.content)
            
            # Extract token usage
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            tokens_total = tokens_input + tokens_output
            
            # Calculate cost
            cost = self.estimate_cost(tokens_input, tokens_output)
            
            # Build result
            result = SentimentResult(
                sentiment_overall=float(result_json.get("sentiment_overall", 0.0)),
                sentiment_usd=float(result_json.get("sentiment_usd", 0.0)),
                sentiment_inr=float(result_json.get("sentiment_inr", 0.0)),
                sentiment_eur=float(result_json.get("sentiment_eur", 0.0)),
                sentiment_gbp=float(result_json.get("sentiment_gbp", 0.0)),
                sentiment_jpy=float(result_json.get("sentiment_jpy", 0.0)),
                confidence=float(result_json.get("confidence", 0.5)),
                impact_score=float(result_json.get("impact_score", 5.0)),
                urgency=result_json.get("urgency", "medium"),
                currencies=result_json.get("currencies", []),
                countries=result_json.get("countries", []),
                institutions=result_json.get("institutions", []),
                topics=result_json.get("topics", []),
                explanation=result_json.get("explanation", ""),
                key_phrases=result_json.get("key_phrases", []),
                processing_time_ms=int((time.time() - start_time) * 1000),
                tokens_used=tokens_total,
                api_cost_usd=cost,
                model_version=self.model
            )
            
            log.info("sentiment_analysis_success", 
                    model=self.model, 
                    tokens=tokens_total, 
                    cost=cost,
                    latency_ms=result.processing_time_ms)
            
            return result
            
        except Exception as e:
            log.error("sentiment_analysis_failed", error=str(e), model=self.model)
            # Return neutral sentiment on error
            return SentimentResult(
                sentiment_overall=0.0,
                sentiment_usd=0.0,
                sentiment_inr=0.0,
                confidence=0.0,
                explanation=f"Error: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_version=self.model
            )
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost in USD."""
        pricing = self.PRICING.get(self.model, self.PRICING["gpt-4-turbo"])
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        return round(cost, 6)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for sentiment analysis."""
        return """You are a financial analyst specializing in foreign exchange markets.
Your task is to analyze news articles and provide precise sentiment analysis for currency trading decisions.

Focus on:
1. How the news affects currency values (USD, INR, EUR, GBP, JPY)
2. Market impact and urgency
3. Key entities and topics
4. Clear, actionable insights

Be objective, precise, and consistent in your analysis."""
    
    def _build_sentiment_prompt(self, headline: str, content: str, source: str, 
                                timestamp: datetime) -> str:
        """Build the sentiment analysis prompt."""
        # Truncate content to avoid token limits
        max_content_length = 2000
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "... [truncated]"
        
        return f"""Analyze the following news article and provide sentiment analysis for FX trading.

**News Article:**
- Headline: {headline}
- Source: {source}
- Published: {timestamp.isoformat()}
- Content: {truncated_content}

**Required Analysis:**
Provide your analysis in JSON format with the following fields:

1. **sentiment_overall**: Overall market sentiment (-1 to +1, where -1 is very bearish, +1 is very bullish)
2. **sentiment_usd**: USD-specific sentiment (-1 to +1)
3. **sentiment_inr**: INR-specific sentiment (-1 to +1)
4. **sentiment_eur**: EUR-specific sentiment (-1 to +1)
5. **sentiment_gbp**: GBP-specific sentiment (-1 to +1)
6. **sentiment_jpy**: JPY-specific sentiment (-1 to +1)
7. **impact_score**: Predicted market impact (0-10, where 10 is highly market-moving)
8. **urgency**: Time sensitivity (low, medium, high, critical)
9. **confidence**: Your confidence in this analysis (0-1)
10. **currencies**: List of mentioned currencies (e.g., ["USD", "INR"])
11. **countries**: List of mentioned countries (e.g., ["US", "India"])
12. **institutions**: List of mentioned institutions (e.g., ["Federal Reserve", "RBI"])
13. **topics**: List of key topics (e.g., ["interest_rates", "inflation", "trade"])
14. **explanation**: Brief explanation (2-3 sentences) of your analysis
15. **key_phrases**: Important phrases from the article (list of strings)

**Response Format:**
{{
  "sentiment_overall": <float>,
  "sentiment_usd": <float>,
  "sentiment_inr": <float>,
  "sentiment_eur": <float>,
  "sentiment_gbp": <float>,
  "sentiment_jpy": <float>,
  "impact_score": <float>,
  "urgency": "<string>",
  "confidence": <float>,
  "currencies": [<strings>],
  "countries": [<strings>],
  "institutions": [<strings>],
  "topics": [<strings>],
  "explanation": "<string>",
  "key_phrases": [<strings>]
}}

Respond ONLY with valid JSON. No additional text."""


class AnthropicClient(LLMClient):
    """Anthropic Claude client for sentiment analysis."""
    
    # Pricing (per 1M tokens, as of Nov 2025)
    PRICING = {
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    }
    
    def __init__(self, api_key: str = ANTHROPIC_API_KEY, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        """Lazy load Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client
    
    async def analyze_sentiment(self, headline: str, content: str, source: str,
                                timestamp: datetime) -> SentimentResult:
        """Analyze sentiment using Claude."""
        # Implementation similar to OpenAI but using Anthropic API
        # For brevity, using OpenAI-style prompt with Claude
        start_time = time.time()
        
        try:
            client = self._get_client()
            prompt = self._build_sentiment_prompt(headline, content, source, timestamp)
            
            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response
            result_text = response.content[0].text
            result_json = json.loads(result_text)
            
            # Extract token usage
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens
            tokens_total = tokens_input + tokens_output
            
            # Calculate cost
            cost = self.estimate_cost(tokens_input, tokens_output)
            
            # Build result (same as OpenAI)
            result = SentimentResult(
                sentiment_overall=float(result_json.get("sentiment_overall", 0.0)),
                sentiment_usd=float(result_json.get("sentiment_usd", 0.0)),
                sentiment_inr=float(result_json.get("sentiment_inr", 0.0)),
                confidence=float(result_json.get("confidence", 0.5)),
                impact_score=float(result_json.get("impact_score", 5.0)),
                urgency=result_json.get("urgency", "medium"),
                currencies=result_json.get("currencies", []),
                topics=result_json.get("topics", []),
                explanation=result_json.get("explanation", ""),
                processing_time_ms=int((time.time() - start_time) * 1000),
                tokens_used=tokens_total,
                api_cost_usd=cost,
                model_version=self.model
            )
            
            return result
            
        except Exception as e:
            log.error("sentiment_analysis_failed", error=str(e), model=self.model)
            return SentimentResult(
                sentiment_overall=0.0,
                sentiment_usd=0.0,
                sentiment_inr=0.0,
                confidence=0.0,
                explanation=f"Error: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_version=self.model
            )
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost in USD."""
        pricing = self.PRICING.get(self.model, self.PRICING["claude-3-sonnet"])
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        return round(cost, 6)
    
    def _build_sentiment_prompt(self, headline: str, content: str, source: str,
                                timestamp: datetime) -> str:
        """Build sentiment analysis prompt for Claude."""
        # Reuse OpenAI prompt structure
        openai_client = OpenAIClient()
        return openai_client._build_sentiment_prompt(headline, content, source, timestamp)


def get_llm_client(provider: str = LLM_PROVIDER, model: str = LLM_MODEL) -> LLMClient:
    """Factory function to get appropriate LLM client."""
    if provider == "openai":
        return OpenAIClient(model=model)
    elif provider == "anthropic":
        return AnthropicClient(model=model)
    elif provider == "ollama":
        from apps.llm.ollama_client import OllamaClient
        return OllamaClient(model=model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
