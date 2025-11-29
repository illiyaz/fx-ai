#!/bin/bash
# Quick system status check

echo "=========================================="
echo "  FX-AI System Status"
echo "=========================================="
echo ""

# Check Docker
echo "1. Docker:"
if docker ps > /dev/null 2>&1; then
    echo "   ✓ Docker running"
else
    echo "   ✗ Docker not running - Run: open -a Docker"
fi

# Check ClickHouse
echo ""
echo "2. ClickHouse:"
if docker ps | grep -q fxai-clickhouse; then
    echo "   ✓ ClickHouse running"
    BARS=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_1m" 2>/dev/null || echo "0")
    echo "   - Price bars: $BARS"
else
    echo "   ✗ ClickHouse not running - Run: make up"
fi

# Check Ollama
echo ""
echo "3. Ollama:"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ✓ Ollama running"
    if ollama list | grep -q llama3; then
        echo "   ✓ Llama3 model available"
    else
        echo "   ✗ Llama3 not found - Run: make setup-ollama"
    fi
else
    echo "   ✗ Ollama not running - Run: ollama serve"
fi

# Check Python packages
echo ""
echo "4. Python Dependencies:"
# Check venv if it exists, otherwise system python
if [ -f .venv/bin/python ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi
$PYTHON -c "import feedparser" 2>/dev/null && echo "   ✓ feedparser" || echo "   ✗ feedparser - Run: .venv/bin/pip install feedparser"
$PYTHON -c "import bs4" 2>/dev/null && echo "   ✓ beautifulsoup4" || echo "   ✗ beautifulsoup4 - Run: .venv/bin/pip install beautifulsoup4"
$PYTHON -c "import lightgbm" 2>/dev/null && echo "   ✓ lightgbm" || echo "   ✗ lightgbm - Run: make deps"

# Check if data exists
echo ""
echo "5. Data Status:"
if docker ps | grep -q fxai-clickhouse; then
    BARS=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_1m" 2>/dev/null || echo "0")
    FEATURES=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.features_1m" 2>/dev/null || echo "0")
    MODELS=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.models" 2>/dev/null || echo "0")
    NEWS=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.news_items WHERE ts >= now() - INTERVAL 1 HOUR" 2>/dev/null || echo "0")
    
    if [ "$BARS" -gt 100 ]; then
        echo "   ✓ Price data: $BARS bars"
    else
        echo "   ⚠ Price data: $BARS bars - Run: make ingest-usdinr"
    fi
    
    if [ "$FEATURES" -gt 100 ]; then
        echo "   ✓ Features: $FEATURES rows"
    else
        echo "   ⚠ Features: $FEATURES rows - Run: make featurize"
    fi
    
    if [ "$MODELS" -gt 0 ]; then
        echo "   ✓ ML models: $MODELS trained"
    else
        echo "   ⚠ ML models: $MODELS - Run: make train-lgbm PAIR=USDINR HORIZON=4h"
    fi
    
    if [ "$NEWS" -gt 0 ]; then
        echo "   ✓ Recent news: $NEWS items"
    else
        echo "   ⚠ Recent news: $NEWS items - Run: make news-ingester"
    fi
else
    echo "   ⚠ ClickHouse not running - cannot check data"
fi

echo ""
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo ""

# Determine what needs to be done
NEEDS_INFRA=false
NEEDS_DATA=false
NEEDS_OLLAMA=false

if ! docker ps | grep -q fxai-clickhouse; then
    NEEDS_INFRA=true
fi

if docker ps | grep -q fxai-clickhouse; then
    BARS=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_1m" 2>/dev/null || echo "0")
    MODELS=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.models" 2>/dev/null || echo "0")
    if [ "$BARS" -lt 100 ] || [ "$MODELS" -eq 0 ]; then
        NEEDS_DATA=true
    fi
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    NEEDS_OLLAMA=true
fi

if [ "$NEEDS_INFRA" = true ]; then
    echo "1. Start infrastructure:"
    echo "   make up"
    echo "   make init-db"
    echo "   make init-news-schema"
    echo ""
fi

if [ "$NEEDS_DATA" = true ]; then
    echo "2. Ingest data and train model:"
    echo "   make ingest-usdinr     # 30 minutes"
    echo "   make featurize         # 10 minutes"
    echo "   make train-lgbm PAIR=USDINR HORIZON=4h  # 15 minutes"
    echo ""
fi

if [ "$NEEDS_OLLAMA" = true ]; then
    echo "3. Setup Ollama:"
    echo "   make setup-ollama      # 5 minutes"
    echo ""
fi

if [ "$NEEDS_INFRA" = false ] && [ "$NEEDS_DATA" = false ] && [ "$NEEDS_OLLAMA" = false ]; then
    echo "✓ System is ready!"
    echo ""
    echo "To start services:"
    echo "  Terminal 1: make news-ingester"
    echo "  Terminal 2: make api"
    echo ""
    echo "To test:"
    echo "  make curl-hybrid"
else
    echo "After completing the above steps, run:"
    echo "  make e2e-quick"
fi

echo ""
