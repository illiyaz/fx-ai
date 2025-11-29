#!/usr/bin/env python
"""
Backfill historical FX data for multiple currency pairs.

This script generates synthetic historical data for popular currency pairs
to enable longer time range views in the dashboard.
"""
import sys
sys.path.insert(0, '.')

import argparse
from datetime import datetime, timedelta, timezone
import random
from apps.common.clickhouse_client import insert_rows

# Popular currency pairs with realistic price ranges
CURRENCY_PAIRS = {
    'USDINR': {'base': 84.0, 'volatility': 0.5},
    'EURUSD': {'base': 1.08, 'volatility': 0.01},
    'GBPUSD': {'base': 1.27, 'volatility': 0.01},
    'USDJPY': {'base': 150.0, 'volatility': 1.0},
    'AUDUSD': {'base': 0.65, 'volatility': 0.005},
    'USDCAD': {'base': 1.36, 'volatility': 0.01},
    'USDCHF': {'base': 0.88, 'volatility': 0.005},
    'NZDUSD': {'base': 0.59, 'volatility': 0.005},
}


def generate_realistic_bar(pair: str, timestamp: datetime, prev_close: float = None):
    """Generate a realistic OHLC bar with trend and noise."""
    config = CURRENCY_PAIRS[pair]
    base_price = config['base']
    volatility = config['volatility']
    
    if prev_close is None:
        prev_close = base_price
    
    # Add trend (slight upward bias)
    trend = random.uniform(-0.0001, 0.0002) * prev_close
    
    # Add random walk
    change = random.gauss(0, volatility)
    close = prev_close + trend + change
    
    # Generate OHLC
    high_offset = abs(random.gauss(0, volatility * 0.5))
    low_offset = abs(random.gauss(0, volatility * 0.5))
    
    open_price = prev_close
    high = max(open_price, close) + high_offset
    low = min(open_price, close) - low_offset
    
    # Spread (typical FX spread in pips)
    spread_avg = random.uniform(0.0001, 0.0003) * close
    
    return {
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'spread_avg': spread_avg
    }


def backfill_pair(pair: str, days: int = 30):
    """Backfill historical data for a currency pair."""
    print(f"\n{'='*60}")
    print(f"Backfilling {pair} - Last {days} days")
    print(f"{'='*60}")
    
    # Generate bars (1-minute intervals)
    bars_per_day = 24 * 60  # 1440 bars per day
    total_bars = days * bars_per_day
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    print(f"Start: {start_time}")
    print(f"End: {end_time}")
    print(f"Total bars: {total_bars:,}")
    
    rows = []
    current_time = start_time
    prev_close = CURRENCY_PAIRS[pair]['base']
    
    print("Generating bars...")
    for i in range(total_bars):
        bar = generate_realistic_bar(pair, current_time, prev_close)
        
        rows.append((
            current_time,
            pair,
            bar['open'],
            bar['high'],
            bar['low'],
            bar['close'],
            bar['spread_avg'],
            'backfill'
        ))
        
        prev_close = bar['close']
        current_time += timedelta(minutes=1)
        
        # Progress indicator
        if (i + 1) % 10000 == 0:
            print(f"  Generated {i+1:,}/{total_bars:,} bars ({(i+1)/total_bars*100:.1f}%)")
    
    print(f"\n✓ Generated {len(rows):,} bars")
    
    # Insert in batches
    batch_size = 10000
    print(f"Inserting into ClickHouse (batch size: {batch_size:,})...")
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        insert_rows(
            "fxai.bars_1m",
            batch,
            ["ts", "pair", "open", "high", "low", "close", "spread_avg", "src"]
        )
        print(f"  Inserted batch {i//batch_size + 1}/{(len(rows)-1)//batch_size + 1}")
    
    print(f"✓ Inserted {len(rows):,} bars for {pair}")
    
    # Show price range
    first_close = rows[0][5]
    last_close = rows[-1][5]
    change_pct = ((last_close - first_close) / first_close) * 100
    
    print(f"\nPrice Summary:")
    print(f"  Start: {first_close:.4f}")
    print(f"  End: {last_close:.4f}")
    print(f"  Change: {change_pct:+.2f}%")


def main():
    parser = argparse.ArgumentParser(description='Backfill historical FX data')
    parser.add_argument('--pairs', nargs='+', default=list(CURRENCY_PAIRS.keys()),
                        choices=list(CURRENCY_PAIRS.keys()),
                        help='Currency pairs to backfill')
    parser.add_argument('--days', type=int, default=30,
                        help='Number of days to backfill (default: 30)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("FX Historical Data Backfill")
    print("="*60)
    print(f"Pairs: {', '.join(args.pairs)}")
    print(f"Days: {args.days}")
    print(f"Bars per pair: {args.days * 24 * 60:,}")
    print("="*60)
    
    for pair in args.pairs:
        try:
            backfill_pair(pair, args.days)
        except Exception as e:
            print(f"✗ Error backfilling {pair}: {e}")
            continue
    
    print("\n" + "="*60)
    print("✅ Backfill Complete!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Restart dashboard to see new data")
    print("  2. Use time range filters (4H, 1D, 1W, 1M)")
    print("  3. Train models for new pairs:")
    for pair in args.pairs:
        if pair != 'USDINR':
            print(f"     make train-lgbm PAIR={pair} HORIZON=4h")


if __name__ == "__main__":
    main()
