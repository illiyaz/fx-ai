#!/bin/bash
# Train models for all currency pairs

set -e

echo "=========================================="
echo "Training Models for All Currency Pairs"
echo "=========================================="

PAIRS=("EURUSD" "GBPUSD" "USDJPY" "AUDUSD" "USDCAD" "USDCHF" "NZDUSD")
HORIZON="4h"

TOTAL=${#PAIRS[@]}
CURRENT=0

for PAIR in "${PAIRS[@]}"; do
    CURRENT=$((CURRENT + 1))
    
    echo ""
    echo "[$CURRENT/$TOTAL] 🎯 Training $PAIR..."
    echo "----------------------------------------"
    
    # Check if features exist
    FEAT_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q \
        "SELECT count() FROM fxai.features_1m WHERE pair='$PAIR'" 2>/dev/null || echo "0")
    
    if [ "$FEAT_COUNT" -eq "0" ]; then
        echo "  ⚠️  No features found for $PAIR, skipping..."
        continue
    fi
    
    echo "  Features available: $FEAT_COUNT"
    echo "  Horizon: $HORIZON"
    echo ""
    
    # Train the model
    if .venv/bin/python -m apps.train.train_lgbm --pair $PAIR --horizon $HORIZON --lookback-hours 24; then
        echo "  ✅ Model trained successfully for $PAIR"
    else
        echo "  ❌ Training failed for $PAIR"
    fi
    
    echo "----------------------------------------"
done

echo ""
echo "=========================================="
echo "✅ Training Complete!"
echo "=========================================="
echo ""

# Show trained models
echo "Trained Models:"
docker exec fxai-clickhouse clickhouse-client -q \
    "SELECT pair, horizon, ts, 
     JSONExtractFloat(metrics, 'auc') as auc,
     JSONExtractFloat(metrics, 'brier') as brier,
     JSONExtractInt(metrics, 'n_valid') as n_valid
     FROM fxai.models 
     WHERE pair IN ('EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD')
     ORDER BY ts DESC"

echo ""
echo "Next steps:"
echo "  1. Open dashboard: http://localhost:3002"
echo "  2. Select any currency pair from dropdown"
echo "  3. View predictions and charts"
echo "  4. Test hybrid predictions with news"
echo ""
