#!/bin/bash
# Quick test to enable hybrid predictions

echo "=========================================="
echo "  Quick Hybrid Prediction Test"
echo "=========================================="
echo ""

# Step 1: Insert sample news
echo "Step 1: Inserting sample news..."
docker exec fxai-clickhouse clickhouse-client -q "
INSERT INTO fxai.news_items (id, ts, source, headline, content, url, author, language, raw_json) VALUES
('test001', now() - INTERVAL 5 MINUTE, 'reuters', 'Federal Reserve signals potential rate cuts in 2025', 'The Federal Reserve indicated it may begin cutting interest rates in early 2025 if inflation continues to moderate.', 'https://example.com/1', '', 'en', ''),
('test002', now() - INTERVAL 10 MINUTE, 'rbi', 'RBI maintains repo rate at 6.5%', 'The Reserve Bank of India kept its key lending rate unchanged at 6.5% as inflation remains within the target range.', 'https://example.com/2', '', 'en', ''),
('test003', now() - INTERVAL 15 MINUTE, 'bloomberg', 'US Dollar strengthens on strong jobs data', 'The US dollar rallied against major currencies after better-than-expected employment figures.', 'https://example.com/3', '', 'en', ''),
('test004', now() - INTERVAL 20 MINUTE, 'forexlive', 'India forex reserves hit record high', 'India foreign exchange reserves reached an all-time high providing a strong buffer.', 'https://example.com/4', '', 'en', ''),
('test005', now() - INTERVAL 25 MINUTE, 'economic_times', 'Global trade tensions ease', 'Positive developments in US-China trade negotiations have reduced market uncertainty.', 'https://example.com/5', '', 'en', '')
"

echo "✓ Inserted 5 sample news items"
echo ""

# Step 2: Insert sample sentiment scores
echo "Step 2: Inserting sample sentiment scores..."
docker exec fxai-clickhouse clickhouse-client -q "
INSERT INTO fxai.sentiment_scores (news_id, ts, model_version, sentiment_overall, sentiment_usd, sentiment_inr, confidence, impact_score, urgency, currencies, explanation, processing_time_ms, tokens_used) VALUES
('test001', now() - INTERVAL 5 MINUTE, 'llama3', -0.6, -0.6, 0.6, 0.8, 0.7, 'high', ['USD', 'INR'], 'Rate cuts typically weaken USD', 2000, 150),
('test002', now() - INTERVAL 10 MINUTE, 'llama3', 0.0, 0.0, 0.0, 0.7, 0.5, 'medium', ['USD', 'INR'], 'Stable policy stance', 1800, 120),
('test003', now() - INTERVAL 15 MINUTE, 'llama3', 0.7, 0.7, -0.7, 0.9, 0.8, 'high', ['USD', 'INR'], 'Strong jobs data supports USD', 1900, 140),
('test004', now() - INTERVAL 20 MINUTE, 'llama3', 0.5, -0.5, 0.5, 0.75, 0.6, 'medium', ['USD', 'INR'], 'High reserves strengthen INR', 1850, 130),
('test005', now() - INTERVAL 25 MINUTE, 'llama3', 0.4, 0.2, 0.2, 0.7, 0.5, 'medium', ['USD', 'INR'], 'Reduced tensions support risk assets', 1750, 125)
"

echo "✓ Inserted 5 sentiment scores"
echo ""

# Step 3: Check data
echo "Step 3: Verifying data..."
NEWS_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.news_items WHERE ts >= now() - INTERVAL 1 HOUR")
SENTIMENT_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.sentiment_scores WHERE ts >= now() - INTERVAL 1 HOUR")

echo "  Recent news: $NEWS_COUNT"
echo "  Recent sentiment: $SENTIMENT_COUNT"
echo ""

# Step 4: Test hybrid prediction
echo "Step 4: Testing hybrid prediction..."
echo ""
curl -s -H "X-API-Key: changeme-dev-key" \
  "http://localhost:9090/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" | jq '{
    pair,
    prob_up,
    recommendation,
    direction,
    hybrid: {
      enabled: .hybrid.enabled,
      prob_up_ml: .hybrid.prob_up_ml,
      prob_up_hybrid: .hybrid.prob_up_hybrid,
      news_sentiment: .hybrid.news_sentiment
    }
  }'

echo ""
echo "=========================================="
echo "✅ Test complete!"
echo "=========================================="
echo ""
echo "If hybrid.enabled = true, the system is working!"
echo "If hybrid.enabled = false, restart the API server:"
echo "  1. Stop API (Ctrl+C)"
echo "  2. Run: make api"
echo "  3. Run this script again"
