#!/usr/bin/env python
"""
Test script for Ollama local LLM integration.

Tests Ollama installation and sentiment analysis capabilities.
"""
import sys
import asyncio
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, '.')

from apps.llm.ollama_client import (
    OllamaClient, 
    check_ollama_available, 
    list_ollama_models,
    RECOMMENDED_MODELS
)


async def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print("\n" + "="*60)
    print("TEST 1: Ollama Connection")
    print("="*60)
    
    if check_ollama_available():
        print("✓ Ollama is running and accessible")
        return True
    else:
        print("✗ Ollama is not running")
        print("\nTo start Ollama:")
        print("  1. Open Ollama.app from Applications")
        print("  2. Or run: ollama serve")
        print("  3. Visit: https://ollama.ai/download")
        return False


async def test_list_models():
    """Test listing available models."""
    print("\n" + "="*60)
    print("TEST 2: List Available Models")
    print("="*60)
    
    models = list_ollama_models()
    
    if models:
        print(f"✓ Found {len(models)} installed model(s):")
        for model in models:
            print(f"  - {model}")
        return True
    else:
        print("✗ No models found")
        print("\nTo install a model:")
        print("  ollama pull llama3:8b")
        print("  ollama pull mistral:7b")
        print("  ollama pull phi3:mini")
        return False


async def test_sentiment_analysis():
    """Test sentiment analysis with Ollama."""
    print("\n" + "="*60)
    print("TEST 3: Sentiment Analysis")
    print("="*60)
    
    # Check if any model is available
    models = list_ollama_models()
    if not models:
        print("✗ No models available for testing")
        return False
    
    # Use first available model
    model_name = models[0].split(':')[0]  # Extract base name
    print(f"Using model: {models[0]}")
    
    try:
        client = OllamaClient(model=model_name)
        
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
        print("Please wait... (this may take 2-5 seconds)")
        
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
        print(f"  Topics: {', '.join(result.topics) if result.topics else 'None'}")
        print(f"  Explanation: {result.explanation[:100]}...")
        print(f"  Processing Time: {result.processing_time_ms}ms")
        print(f"  Tokens Used: {result.tokens_used}")
        print(f"  API Cost: ${result.api_cost_usd:.4f} (FREE!)")
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_performance():
    """Test performance with multiple analyses."""
    print("\n" + "="*60)
    print("TEST 4: Performance Test (3 analyses)")
    print("="*60)
    
    models = list_ollama_models()
    if not models:
        print("✗ No models available")
        return False
    
    model_name = models[0].split(':')[0]
    client = OllamaClient(model=model_name)
    
    test_cases = [
        ("Fed raises rates", "Federal Reserve increases rates by 25bps"),
        ("RBI holds rates", "Reserve Bank of India maintains repo rate at 6.50%"),
        ("ECB cuts rates", "European Central Bank reduces rates by 25bps"),
    ]
    
    total_time = 0
    
    for i, (headline, content) in enumerate(test_cases, 1):
        print(f"\nAnalysis {i}/3: {headline}")
        
        result = await client.analyze_sentiment(
            headline=headline,
            content=content,
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        print(f"  Time: {result.processing_time_ms}ms")
        print(f"  Sentiment: {result.sentiment_overall:+.2f}")
        total_time += result.processing_time_ms
    
    avg_time = total_time / len(test_cases)
    print(f"\n✓ Average processing time: {avg_time:.0f}ms ({avg_time/1000:.1f}s)")
    
    if avg_time < 3000:
        print("  Performance: Excellent ⚡")
    elif avg_time < 5000:
        print("  Performance: Good ✓")
    elif avg_time < 10000:
        print("  Performance: Acceptable ⚠️")
    else:
        print("  Performance: Slow ❌")
        print("  Tip: Try a smaller model (phi3:mini)")
    
    return True


async def show_recommendations():
    """Show model recommendations."""
    print("\n" + "="*60)
    print("RECOMMENDED MODELS")
    print("="*60)
    
    for key, info in RECOMMENDED_MODELS.items():
        print(f"\n{info['name']}")
        print(f"  Size: {info['size']}")
        print(f"  Speed: {info['speed']}")
        print(f"  Quality: {info['quality']}")
        print(f"  Description: {info['description']}")
        print(f"  Install: ollama pull {info['name']}")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("OLLAMA TEST SUITE FOR FX-AI ADVISOR")
    print("="*60)
    
    results = {}
    
    # Test 1: Connection
    results["Connection"] = await test_ollama_connection()
    
    if not results["Connection"]:
        print("\n⚠️  Ollama is not running. Please start Ollama and try again.")
        return False
    
    # Test 2: List models
    results["List Models"] = await test_list_models()
    
    if not results["List Models"]:
        print("\n⚠️  No models installed. Please install a model:")
        await show_recommendations()
        return False
    
    # Test 3: Sentiment analysis
    results["Sentiment Analysis"] = await test_sentiment_analysis()
    
    # Test 4: Performance
    results["Performance"] = await test_performance()
    
    # Show recommendations
    await show_recommendations()
    
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
        print("\n🎉 All tests passed! Ollama is ready for FX-AI Advisor.")
        print("\nNext steps:")
        print("  1. Update .env: LLM_PROVIDER=ollama")
        print("  2. Update .env: OLLAMA_MODEL=llama3")
        print("  3. Run: make news-ingester")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
