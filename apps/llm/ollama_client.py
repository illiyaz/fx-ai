"""
Ollama client for local LLM inference.

Supports running models locally on MacBook Pro (M1/M2/M3) without API costs.
Compatible models: llama3, mistral, phi3, gemma, etc.
"""
from __future__ import annotations
import os
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import structlog

from apps.llm.client import LLMClient, SentimentResult

log = structlog.get_logger()

# Environment variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))


class OllamaClient(LLMClient):
    """
    Ollama client for local LLM inference.
    
    Supports models like:
    - llama3 (8B, 70B) - Meta's Llama 3
    - mistral (7B) - Mistral AI
    - phi3 (3.8B) - Microsoft Phi-3
    - gemma (2B, 7B) - Google Gemma
    - qwen2 (7B) - Alibaba Qwen
    """
    
    # No pricing for local models (free!)
    PRICING = {
        "llama3": {"input": 0.0, "output": 0.0},
        "mistral": {"input": 0.0, "output": 0.0},
        "phi3": {"input": 0.0, "output": 0.0},
        "gemma": {"input": 0.0, "output": 0.0},
        "qwen2": {"input": 0.0, "output": 0.0},
    }
    
    def __init__(self, 
                 base_url: str = OLLAMA_BASE_URL,
                 model: str = OLLAMA_MODEL,
                 timeout: int = OLLAMA_TIMEOUT,
                 **kwargs):
        super().__init__(model=model, **kwargs)
        self.base_url = base_url
        self.timeout = timeout
        self.api_endpoint = f"{base_url}/api/generate"
    
    async def analyze_sentiment(self, headline: str, content: str, source: str,
                                timestamp: datetime) -> SentimentResult:
        """Analyze sentiment using local Ollama model."""
        start_time = time.time()
        
        prompt = self._build_sentiment_prompt(headline, content, source, timestamp)
        
        try:
            import httpx
            
            # Prepare request
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",  # Request JSON output
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            }
            
            # Call Ollama API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_endpoint,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
            
            # Parse response
            response_text = data.get("response", "{}")
            
            # Try to extract JSON from response
            result_json = self._extract_json(response_text)
            
            # Calculate tokens (approximate for local models)
            prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
            response_tokens = len(response_text.split()) * 1.3
            total_tokens = int(prompt_tokens + response_tokens)
            
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
                tokens_used=total_tokens,
                api_cost_usd=0.0,  # Free!
                model_version=f"ollama_{self.model}"
            )
            
            log.info("ollama_sentiment_success",
                    model=self.model,
                    tokens=total_tokens,
                    latency_ms=result.processing_time_ms)
            
            return result
        
        except json.JSONDecodeError as e:
            log.error("ollama_json_parse_error", error=str(e), response=response_text[:200])
            # Return neutral sentiment on parse error
            return self._neutral_sentiment(start_time)
        
        except Exception as e:
            log.error("ollama_sentiment_failed", error=str(e), model=self.model)
            return self._neutral_sentiment(start_time)
    
    def _extract_json(self, text: str) -> dict:
        """Extract JSON from response text."""
        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Return empty dict if no JSON found
        log.warning("no_json_found_in_response", text=text[:200])
        return {}
    
    def _neutral_sentiment(self, start_time: float) -> SentimentResult:
        """Return neutral sentiment on error."""
        return SentimentResult(
            sentiment_overall=0.0,
            sentiment_usd=0.0,
            sentiment_inr=0.0,
            confidence=0.0,
            explanation="Error: Could not analyze sentiment",
            processing_time_ms=int((time.time() - start_time) * 1000),
            model_version=f"ollama_{self.model}"
        )
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost (always $0 for local models)."""
        return 0.0
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for sentiment analysis."""
        return """You are a financial analyst specializing in foreign exchange markets.
Analyze news articles and provide precise sentiment analysis for currency trading decisions.

IMPORTANT: Respond ONLY with valid JSON. Do not include any other text or markdown.

Focus on:
1. Currency value impacts (USD, INR, EUR, GBP, JPY)
2. Market impact and urgency
3. Key entities and topics
4. Clear, actionable insights"""
    
    def _build_sentiment_prompt(self, headline: str, content: str, source: str,
                                timestamp: datetime) -> str:
        """Build sentiment analysis prompt for Ollama."""
        # Truncate content for faster processing
        max_content_length = 1500
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "... [truncated]"
        
        system_prompt = self._get_system_prompt()
        
        prompt = f"""{system_prompt}

Analyze this news article:

Headline: {headline}
Source: {source}
Published: {timestamp.isoformat()}
Content: {truncated_content}

Provide sentiment analysis in JSON format with these fields:
- sentiment_overall: float (-1 to +1, where -1=very bearish, +1=very bullish)
- sentiment_usd: float (-1 to +1, USD-specific sentiment)
- sentiment_inr: float (-1 to +1, INR-specific sentiment)
- sentiment_eur: float (-1 to +1, EUR-specific sentiment)
- sentiment_gbp: float (-1 to +1, GBP-specific sentiment)
- sentiment_jpy: float (-1 to +1, JPY-specific sentiment)
- impact_score: float (0-10, market impact magnitude)
- urgency: string (low, medium, high, critical)
- confidence: float (0-1, your confidence in this analysis)
- currencies: array of strings (mentioned currencies)
- countries: array of strings (mentioned countries)
- institutions: array of strings (central banks, governments)
- topics: array of strings (interest_rates, inflation, trade, etc.)
- explanation: string (2-3 sentences explaining your analysis)
- key_phrases: array of strings (important phrases from article)

Respond with ONLY the JSON object, no other text:"""
        
        return prompt


def check_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        import httpx
        import asyncio
        
        async def _check():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{OLLAMA_BASE_URL}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        
        return asyncio.run(_check())
    except Exception:
        return False


def list_ollama_models() -> List[str]:
    """List available Ollama models."""
    try:
        import httpx
        import asyncio
        
        async def _list():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{OLLAMA_BASE_URL}/api/tags",
                    timeout=5.0
                )
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        
        return asyncio.run(_list())
    except Exception as e:
        log.error("ollama_list_models_failed", error=str(e))
        return []


# Recommended models for FX sentiment analysis
RECOMMENDED_MODELS = {
    "llama3": {
        "name": "llama3:8b",
        "size": "4.7GB",
        "speed": "Fast",
        "quality": "Excellent",
        "description": "Meta's Llama 3 8B - Best balance of speed and quality"
    },
    "mistral": {
        "name": "mistral:7b",
        "size": "4.1GB",
        "speed": "Very Fast",
        "quality": "Good",
        "description": "Mistral 7B - Fast and efficient"
    },
    "phi3": {
        "name": "phi3:mini",
        "size": "2.3GB",
        "speed": "Very Fast",
        "quality": "Good",
        "description": "Microsoft Phi-3 Mini - Smallest, fastest"
    },
    "gemma": {
        "name": "gemma:7b",
        "size": "5.0GB",
        "speed": "Fast",
        "quality": "Good",
        "description": "Google Gemma 7B - Good for structured output"
    },
    "qwen2": {
        "name": "qwen2:7b",
        "size": "4.4GB",
        "speed": "Fast",
        "quality": "Excellent",
        "description": "Alibaba Qwen2 7B - Strong reasoning"
    }
}
