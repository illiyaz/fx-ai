#!/usr/bin/env python
"""
Test script for hybrid ML+LLM API endpoint.

Tests the enhanced /v1/forecast endpoint with news sentiment fusion.
"""
import sys
import json
import httpx
import asyncio
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:9090"
API_KEY = "changeme-dev-key"  # Update if you changed it in .env


async def test_health():
    """Test health endpoint."""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API is healthy")
            print(f"  Status: {data['status']}")
            print(f"  Environment: {data['env']}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False


async def test_ml_only_forecast():
    """Test ML-only forecast (hybrid disabled)."""
    print("\n" + "="*60)
    print("TEST 2: ML-Only Forecast")
    print("="*60)
    
    params = {
        "pair": "USDINR",
        "h": "4h",
        "use_hybrid": False  # Explicitly disable hybrid
    }
    
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/v1/forecast",
            params=params,
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ ML-only forecast received")
            print(f"  Pair: {data['pair']}")
            print(f"  Horizon: {data['horizon']}")
            print(f"  Probability Up: {data['prob_up']:.3f}")
            print(f"  Expected Delta: {data['expected_delta_bps']:+.2f} bps")
            print(f"  Recommendation: {data['recommendation']}")
            print(f"  Model: {data['model_id']}")
            print(f"  Direction: {data['direction']}")
            print(f"  Hybrid Enabled: {data['hybrid']['enabled']}")
            return True
        else:
            print(f"✗ Forecast failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return False


async def test_hybrid_forecast():
    """Test hybrid ML+LLM forecast."""
    print("\n" + "="*60)
    print("TEST 3: Hybrid ML+LLM Forecast")
    print("="*60)
    
    params = {
        "pair": "USDINR",
        "h": "4h",
        "use_hybrid": True  # Explicitly enable hybrid
    }
    
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/v1/forecast",
            params=params,
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Hybrid forecast received")
            print(f"  Pair: {data['pair']}")
            print(f"  Horizon: {data['horizon']}")
            print(f"  Probability Up: {data['prob_up']:.3f}")
            print(f"  Expected Delta: {data['expected_delta_bps']:+.2f} bps")
            print(f"  Recommendation: {data['recommendation']}")
            print(f"  Direction: {data['direction']}")
            
            # Hybrid-specific info
            hybrid = data.get('hybrid', {})
            if hybrid.get('enabled'):
                print(f"\n  🔄 HYBRID FUSION APPLIED:")
                print(f"    ML Probability: {hybrid['prob_up_ml']:.3f}")
                print(f"    Hybrid Probability: {hybrid['prob_up_hybrid']:.3f}")
                print(f"    Adjustment: {hybrid['prob_up_hybrid'] - hybrid['prob_up_ml']:+.3f}")
                print(f"    ML Delta: {hybrid['expected_delta_ml']:+.2f} bps")
                print(f"    Hybrid Delta: {hybrid['expected_delta_hybrid']:+.2f} bps")
                print(f"    Fusion Weights: ML={hybrid['fusion_weights']['ml']:.0%}, News={hybrid['fusion_weights']['llm']:.0%}")
                
                if hybrid.get('news_sentiment') is not None:
                    print(f"\n  📰 NEWS SENTIMENT:")
                    print(f"    Sentiment Score: {hybrid['news_sentiment']:+.2f}")
                    print(f"    Confidence: {hybrid['news_confidence']:.2f}")
                    print(f"    Impact: {hybrid['news_impact']:.1f}/10")
                    print(f"    Summary: {hybrid['news_summary']}")
            else:
                print(f"\n  ℹ️  Hybrid mode enabled but no news sentiment available")
            
            print(f"\n  📝 Explanation:")
            for part in data['explanation']:
                print(f"    - {part}")
            
            print(f"\n  💡 Action Hint:")
            print(f"    {data['action_hint']}")
            
            return True
        else:
            print(f"✗ Forecast failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return False


async def test_comparison():
    """Compare ML-only vs Hybrid forecasts side-by-side."""
    print("\n" + "="*60)
    print("TEST 4: ML vs Hybrid Comparison")
    print("="*60)
    
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        # Get ML-only forecast
        ml_response = await client.get(
            f"{API_BASE_URL}/v1/forecast",
            params={"pair": "USDINR", "h": "4h", "use_hybrid": False},
            headers=headers,
            timeout=10.0
        )
        
        # Get hybrid forecast
        hybrid_response = await client.get(
            f"{API_BASE_URL}/v1/forecast",
            params={"pair": "USDINR", "h": "4h", "use_hybrid": True},
            headers=headers,
            timeout=10.0
        )
        
        if ml_response.status_code == 200 and hybrid_response.status_code == 200:
            ml_data = ml_response.json()
            hybrid_data = hybrid_response.json()
            
            print(f"\n{'Metric':<25} {'ML-Only':<15} {'Hybrid':<15} {'Difference':<15}")
            print("-" * 70)
            
            ml_prob = ml_data['prob_up']
            hybrid_prob = hybrid_data['prob_up']
            print(f"{'Probability Up':<25} {ml_prob:<15.3f} {hybrid_prob:<15.3f} {hybrid_prob - ml_prob:+.3f}")
            
            ml_delta = ml_data['expected_delta_bps']
            hybrid_delta = hybrid_data['expected_delta_bps']
            print(f"{'Expected Delta (bps)':<25} {ml_delta:<15.2f} {hybrid_delta:<15.2f} {hybrid_delta - ml_delta:+.2f}")
            
            ml_rec = ml_data['recommendation']
            hybrid_rec = hybrid_data['recommendation']
            rec_change = "✓ Same" if ml_rec == hybrid_rec else "⚠️  Changed"
            print(f"{'Recommendation':<25} {ml_rec:<15} {hybrid_rec:<15} {rec_change}")
            
            ml_dir = ml_data['direction']
            hybrid_dir = hybrid_data['direction']
            dir_change = "✓ Same" if ml_dir == hybrid_dir else "⚠️  Changed"
            print(f"{'Direction':<25} {ml_dir:<15} {hybrid_dir:<15} {dir_change}")
            
            # Show news impact if available
            if hybrid_data.get('hybrid', {}).get('enabled'):
                hybrid_info = hybrid_data['hybrid']
                print(f"\n📊 News Impact:")
                print(f"  Fusion Weight (News): {hybrid_info['fusion_weights']['llm']:.0%}")
                if hybrid_info.get('news_sentiment') is not None:
                    print(f"  News Sentiment: {hybrid_info['news_sentiment']:+.2f}")
                    print(f"  News Impact: {hybrid_info['news_impact']:.1f}/10")
            
            return True
        else:
            print(f"✗ Comparison failed")
            return False


async def test_different_pairs():
    """Test hybrid forecast for multiple currency pairs."""
    print("\n" + "="*60)
    print("TEST 5: Multiple Currency Pairs")
    print("="*60)
    
    pairs = ["USDINR", "EURUSD", "GBPUSD"]
    headers = {"X-API-Key": API_KEY}
    
    results = []
    
    async with httpx.AsyncClient() as client:
        for pair in pairs:
            try:
                response = await client.get(
                    f"{API_BASE_URL}/v1/forecast",
                    params={"pair": pair, "h": "4h", "use_hybrid": True},
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    hybrid_enabled = data.get('hybrid', {}).get('enabled', False)
                    has_news = data.get('hybrid', {}).get('news_sentiment') is not None
                    
                    print(f"\n  {pair}:")
                    print(f"    Prob Up: {data['prob_up']:.3f}")
                    print(f"    Delta: {data['expected_delta_bps']:+.2f} bps")
                    print(f"    Recommendation: {data['recommendation']}")
                    print(f"    Hybrid: {'✓ Active' if has_news else '○ No news'}")
                    
                    results.append(True)
                else:
                    print(f"\n  {pair}: ✗ Failed ({response.status_code})")
                    results.append(False)
            except Exception as e:
                print(f"\n  {pair}: ✗ Error - {e}")
                results.append(False)
    
    return all(results)


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("HYBRID ML+LLM API TEST SUITE")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {}
    
    # Test 1: Health check
    results["Health Check"] = await test_health()
    
    # Test 2: ML-only forecast
    results["ML-Only Forecast"] = await test_ml_only_forecast()
    
    # Test 3: Hybrid forecast
    results["Hybrid Forecast"] = await test_hybrid_forecast()
    
    # Test 4: Comparison
    results["ML vs Hybrid Comparison"] = await test_comparison()
    
    # Test 5: Multiple pairs
    results["Multiple Pairs"] = await test_different_pairs()
    
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
        print("\n🎉 All tests passed! Hybrid API is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n💡 Tips:")
    print("  - Make sure the API server is running: make api")
    print("  - Ensure ClickHouse is running: make up")
    print("  - Check news data exists: make tail-news")
    print("  - View sentiment scores: make tail-sentiment")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
