#!/bin/bash
# Generate features for all currency pairs with all historical data

set -e

echo "=========================================="
echo "Generating Features for All Currency Pairs"
echo "=========================================="

PAIRS=("USDINR" "EURUSD" "GBPUSD" "USDJPY" "AUDUSD" "USDCAD" "USDCHF" "NZDUSD")

for PAIR in "${PAIRS[@]}"; do
    echo ""
    echo "📊 Generating features for $PAIR..."
    echo "----------------------------------------"
    
    # Get bar count
    BAR_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q \
        "SELECT count() FROM fxai.bars_1m WHERE pair='$PAIR'" 2>/dev/null || echo "0")
    
    echo "  Bars available: $BAR_COUNT"
    
    if [ "$BAR_COUNT" -eq "0" ]; then
        echo "  ⚠️  No bars found for $PAIR, skipping..."
        continue
    fi
    
    # Generate features (will process all available bars)
    echo "  Generating features..."
    .venv/bin/python -m apps.features.featurize --pair $PAIR
    
    # Check feature count
    FEAT_COUNT=$(docker exec fxai-clickhouse clickhouse-client -q \
        "SELECT count() FROM fxai.features_1m WHERE pair='$PAIR'" 2>/dev/null || echo "0")
    
    echo "  ✅ Features generated: $FEAT_COUNT"
done

echo ""
echo "=========================================="
echo "✅ Feature Generation Complete!"
echo "=========================================="
echo ""
echo "Summary:"
docker exec fxai-clickhouse clickhouse-client -q \
    "SELECT pair, count() as features, formatReadableSize(count() * 1000) as size 
     FROM fxai.features_1m 
     GROUP BY pair 
     ORDER BY pair"

echo ""
echo "Next steps:"
echo "  1. Train models: make train-lgbm PAIR=EURUSD HORIZON=4h"
echo "  2. Test predictions in dashboard"
echo ""
