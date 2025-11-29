#!/bin/bash
# End-to-End Test Runner
# Automates the complete testing process

# Don't exit on error - we want to collect all test results
set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

run_test() {
    local test_name=$1
    local test_command=$2
    
    log_info "Running: $test_name"
    if eval "$test_command" > /dev/null 2>&1; then
        log_success "$test_name"
        return 0
    else
        log_error "$test_name"
        return 1
    fi
}

# Banner
echo ""
echo "=========================================="
echo "  FX-AI Advisor - E2E Test Runner"
echo "=========================================="
echo ""

# Phase 1: Prerequisites
echo "Phase 1: Checking Prerequisites"
echo "----------------------------------------"

run_test "Docker installed" "which docker"
run_test "Python installed" "which python3"
run_test "Ollama installed" "which ollama"
run_test "Llama3 model available" "ollama list | grep -q llama3"

if [ $FAILED -gt 0 ]; then
    log_error "Prerequisites not met. Please install missing components."
    exit 1
fi

echo ""

# Phase 2: Infrastructure
echo "Phase 2: Infrastructure Setup"
echo "----------------------------------------"

log_info "Starting Docker containers..."
make up > /dev/null 2>&1
sleep 10

run_test "ClickHouse running" "docker ps | grep -q fxai-clickhouse"
run_test "Kafka running" "docker ps | grep -q fxai-redpanda"

log_info "Initializing database schema..."
make init-db > /dev/null 2>&1
make init-news-schema > /dev/null 2>&1

run_test "Database initialized" "docker exec fxai-clickhouse clickhouse-client -q 'SHOW TABLES FROM fxai' | grep -q bars"

echo ""

# Phase 3: Data Check
echo "Phase 3: Data Availability"
echo "----------------------------------------"

BAR_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_1m" 2>/dev/null || echo "0")
if [ "$BAR_COUNT" -gt 100 ]; then
    log_success "Price data available ($BAR_COUNT bars)"
    ((PASSED++))
else
    log_warning "Limited price data ($BAR_COUNT bars). Run: make ingest-usdinr"
fi

FEATURE_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.features_1m" 2>/dev/null || echo "0")
if [ "$FEATURE_COUNT" -gt 100 ]; then
    log_success "Features available ($FEATURE_COUNT rows)"
    ((PASSED++))
else
    log_warning "Limited features ($FEATURE_COUNT rows). Run: make featurize"
fi

MODEL_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.models" 2>/dev/null || echo "0")
if [ "$MODEL_COUNT" -gt 0 ]; then
    log_success "ML model trained ($MODEL_COUNT models)"
    ((PASSED++))
else
    log_warning "No ML model. Run: make train-lgbm PAIR=USDINR HORIZON=4h"
fi

echo ""

# Phase 4: Ollama
echo "Phase 4: Ollama LLM"
echo "----------------------------------------"

run_test "Ollama service running" "curl -s http://localhost:11434/api/tags > /dev/null"

log_info "Testing Ollama sentiment analysis..."
if python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from datetime import datetime, timezone
from apps.llm.ollama_client import OllamaClient

async def test():
    try:
        client = OllamaClient(model='llama3')
        result = await client.analyze_sentiment(
            'Test headline',
            'Test content',
            'test',
            datetime.now(timezone.utc)
        )
        return result.processing_time_ms < 10000
    except:
        return False

success = asyncio.run(test())
sys.exit(0 if success else 1)
" 2>/dev/null; then
    log_success "Ollama sentiment analysis working"
    ((PASSED++))
else
    log_error "Ollama sentiment analysis failed"
    ((FAILED++))
fi

echo ""

# Phase 5: News Ingestion
echo "Phase 5: News Ingestion"
echo "----------------------------------------"

NEWS_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.news_items WHERE ts >= now() - INTERVAL 1 HOUR" 2>/dev/null || echo "0")
if [ "$NEWS_COUNT" -gt 0 ]; then
    log_success "Recent news available ($NEWS_COUNT items)"
    ((PASSED++))
else
    log_warning "No recent news. Start: make news-ingester"
fi

SENTIMENT_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.sentiment_scores WHERE ts >= now() - INTERVAL 1 HOUR" 2>/dev/null || echo "0")
if [ "$SENTIMENT_COUNT" -gt 0 ]; then
    log_success "Recent sentiment scores ($SENTIMENT_COUNT scores)"
    ((PASSED++))
else
    log_warning "No recent sentiment. Ensure news ingester is running with sentiment enabled"
fi

echo ""

# Phase 6: API
echo "Phase 6: API Server"
echo "----------------------------------------"

# Check if API is already running
if curl -s http://localhost:9090/health > /dev/null 2>&1; then
    log_success "API server running"
    ((PASSED++))
    API_WAS_RUNNING=true
else
    log_info "Starting API server..."
    make api > /tmp/api.log 2>&1 &
    API_PID=$!
    sleep 5
    
    if curl -s http://localhost:9090/health > /dev/null 2>&1; then
        log_success "API server started"
        ((PASSED++))
        API_WAS_RUNNING=false
    else
        log_error "API server failed to start"
        ((FAILED++))
        API_WAS_RUNNING=false
    fi
fi

# Test API endpoints
if curl -s http://localhost:9090/health | grep -q "ok"; then
    log_success "Health endpoint working"
    ((PASSED++))
else
    log_error "Health endpoint failed"
    ((FAILED++))
fi

log_info "Testing ML-only forecast..."
ML_RESPONSE=$(curl -s -H "X-API-Key: changeme-dev-key" \
    "http://localhost:9090/v1/forecast?pair=USDINR&h=4h&use_hybrid=false" 2>/dev/null)

if echo "$ML_RESPONSE" | grep -q "prob_up"; then
    log_success "ML-only forecast working"
    ((PASSED++))
else
    log_error "ML-only forecast failed"
    ((FAILED++))
fi

log_info "Testing hybrid forecast..."
HYBRID_RESPONSE=$(curl -s -H "X-API-Key: changeme-dev-key" \
    "http://localhost:9090/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" 2>/dev/null)

if echo "$HYBRID_RESPONSE" | grep -q "prob_up"; then
    log_success "Hybrid forecast working"
    ((PASSED++))
    
    # Check if hybrid was actually used
    if echo "$HYBRID_RESPONSE" | grep -q '"enabled":true'; then
        log_success "Hybrid fusion enabled"
        ((PASSED++))
    else
        log_warning "Hybrid fusion not enabled (no recent news?)"
    fi
else
    log_error "Hybrid forecast failed"
    ((FAILED++))
fi

echo ""

# Phase 7: Performance
echo "Phase 7: Performance Check"
echo "----------------------------------------"

log_info "Measuring API response time..."
START_TIME=$(date +%s%N)
curl -s -H "X-API-Key: changeme-dev-key" \
    "http://localhost:9090/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" > /dev/null 2>&1
END_TIME=$(date +%s%N)
RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))

if [ $RESPONSE_TIME -lt 1000 ]; then
    log_success "API response time: ${RESPONSE_TIME}ms (excellent)"
    ((PASSED++))
elif [ $RESPONSE_TIME -lt 2000 ]; then
    log_success "API response time: ${RESPONSE_TIME}ms (good)"
    ((PASSED++))
else
    log_warning "API response time: ${RESPONSE_TIME}ms (slow)"
fi

echo ""

# Cleanup
if [ "$API_WAS_RUNNING" = false ] && [ ! -z "$API_PID" ]; then
    log_info "Stopping API server..."
    kill $API_PID 2>/dev/null || true
fi

# Summary
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

TOTAL=$((PASSED + FAILED))
SUCCESS_RATE=$((PASSED * 100 / TOTAL))

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! System is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start news ingester: make news-ingester"
    echo "  2. Start API server: make api"
    echo "  3. Test hybrid forecast: make curl-hybrid"
    exit 0
elif [ $SUCCESS_RATE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  Most tests passed ($SUCCESS_RATE%). Review warnings above.${NC}"
    exit 0
else
    echo -e "${RED}❌ Multiple tests failed ($SUCCESS_RATE% passed). Check errors above.${NC}"
    exit 1
fi
