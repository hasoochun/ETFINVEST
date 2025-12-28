#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Historical Portfolio Data
Uses trade history from KIS API and market data to backfill portfolio_history
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
import pandas as pd

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DB Path
DB_PATH = Path(__file__).parent / "trading.db"


def get_historical_prices(symbols: list, days: int = 30) -> dict:
    """
    Get historical prices for given symbols using yfinance
    
    Returns:
        dict: {symbol: {date: close_price, ...}, ...}
    """
    logger.info(f"Fetching historical prices for {symbols}...")
    prices = {}
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{days}d")
            if not hist.empty:
                prices[symbol] = {}
                for date, row in hist.iterrows():
                    date_str = date.strftime('%Y-%m-%d')
                    prices[symbol][date_str] = float(row['Close'])
                logger.info(f"  {symbol}: {len(prices[symbol])} days of data")
        except Exception as e:
            logger.warning(f"  Failed to get {symbol}: {e}")
    
    return prices


def generate_historical_portfolio(days: int = 14):
    """
    Generate historical portfolio data by:
    1. Getting current holdings from trades table
    2. Getting historical prices for each holding
    3. Calculating daily portfolio values
    4. Saving to portfolio_history table
    """
    logger.info("=" * 60)
    logger.info("📊 Generating Historical Portfolio Data")
    logger.info("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get current holdings from trades table or holdings table
    logger.info("\n1️⃣ Getting current holdings...")
    
    # Try holdings table first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='holdings'")
    if cursor.fetchone():
        cursor.execute("SELECT symbol, quantity, avg_price FROM holdings")
        rows = cursor.fetchall()
        holdings = {row[0]: {'qty': row[1], 'avg_price': row[2]} for row in rows if row[1] > 0}
    else:
        holdings = {}
    
    # If no holdings, try to get from trades
    if not holdings:
        cursor.execute("SELECT DISTINCT symbol FROM trades")
        symbols_rows = cursor.fetchall()
        for (symbol,) in symbols_rows:
            # Get net position from trades
            cursor.execute("""
                SELECT SUM(CASE WHEN type='BUY' THEN quantity ELSE -quantity END),
                       AVG(CASE WHEN type='BUY' THEN price ELSE NULL END)
                FROM trades WHERE symbol = ?
            """, (symbol,))
            row = cursor.fetchone()
            if row and row[0] and row[0] > 0:
                holdings[symbol] = {'qty': int(row[0]), 'avg_price': float(row[1] or 0)}
    
    if not holdings:
        # Use known holdings from current state
        logger.info("  No trade history, using default holdings from API...")
        # We'll get this from the bridge
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'us-stockanalysis'))
            from portfolio_bridge import get_bridge
            bridge = get_bridge()
            if bridge.initialized:
                summary = bridge.get_portfolio_summary()
                for h in summary.get('holdings', []):
                    qty = h.get('qty', 0)
                    if qty > 0:
                        holdings[h['symbol']] = {
                            'qty': qty,
                            'avg_price': h.get('avg_price', 0)
                        }
                cash = summary.get('cash', 0)
            else:
                logger.error("  Bridge not initialized!")
                return False
        except Exception as e:
            logger.error(f"  Failed to get holdings: {e}")
            return False
    else:
        cash = 1000  # Assume some cash
    
    logger.info(f"  Found {len(holdings)} holdings: {list(holdings.keys())}")
    
    # 2. Get historical prices
    logger.info("\n2️⃣ Fetching historical prices...")
    symbols = list(holdings.keys()) + ['^GSPC']  # Add S&P 500
    prices = get_historical_prices(symbols, days + 5)
    
    if not prices:
        logger.error("  No price data available!")
        return False
    
    # Get trading dates from S&P 500
    if '^GSPC' in prices:
        trading_dates = sorted(prices['^GSPC'].keys())[-days:]
    else:
        # Generate dates
        trading_dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') 
                        for i in range(days-1, -1, -1)]
    
    logger.info(f"  Trading dates: {trading_dates[0]} to {trading_dates[-1]}")
    
    # 3. Calculate daily portfolio values
    logger.info("\n3️⃣ Calculating daily portfolio values...")
    
    daily_values = []
    initial_value = None
    initial_benchmark = None
    peak_value = 0
    
    for i, date in enumerate(trading_dates):
        total_value = cash
        holdings_json_data = []
        
        for symbol, info in holdings.items():
            qty = info['qty']
            avg_price = info['avg_price']
            
            # Get price for this date
            if symbol in prices and date in prices[symbol]:
                current_price = prices[symbol][date]
            elif symbol in prices:
                # Use closest available date
                available = sorted(prices[symbol].keys())
                closest = [d for d in available if d <= date]
                current_price = prices[symbol][closest[-1]] if closest else list(prices[symbol].values())[-1]
            else:
                current_price = avg_price
            
            market_value = qty * current_price
            total_value += market_value
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            
            holdings_json_data.append({
                'symbol': symbol,
                'qty': qty,
                'avg_price': avg_price,
                'current_price': round(current_price, 2),
                'market_value': round(market_value, 2),
                'pnl_pct': round(pnl_pct, 2)
            })
        
        # Get benchmark value
        benchmark_value = prices.get('^GSPC', {}).get(date, None)
        
        # Calculate returns
        if initial_value is None:
            initial_value = total_value
            initial_benchmark = benchmark_value
        
        daily_return = 0
        if i > 0 and daily_values:
            prev_value = daily_values[-1]['total_value']
            if prev_value > 0:
                daily_return = ((total_value - prev_value) / prev_value) * 100
        
        cumulative_return = ((total_value - initial_value) / initial_value * 100) if initial_value > 0 else 0
        benchmark_return = 0
        if initial_benchmark and benchmark_value:
            benchmark_return = ((benchmark_value - initial_benchmark) / initial_benchmark * 100)
        
        # Calculate MDD
        peak_value = max(peak_value, total_value)
        mdd = ((total_value - peak_value) / peak_value * 100) if peak_value > 0 else 0
        
        daily_values.append({
            'date': date,
            'total_value': round(total_value, 2),
            'cash_balance': round(cash, 2),
            'invested_value': round(total_value - cash, 2),
            'daily_return_pct': round(daily_return, 2),
            'cumulative_return_pct': round(cumulative_return, 2),
            'benchmark_value': benchmark_value,
            'benchmark_return_pct': round(benchmark_return, 2),
            'mdd_pct': round(mdd, 2),
            'peak_value': round(peak_value, 2),
            'holdings_json': holdings_json_data
        })
        
        logger.info(f"  {date}: ${total_value:.2f} ({cumulative_return:+.2f}%) MDD: {mdd:.2f}%")
    
    # 4. Save to database
    logger.info(f"\n4️⃣ Saving {len(daily_values)} records to database...")
    
    import json
    
    for dv in daily_values:
        timestamp = datetime.now().isoformat()
        holdings_json_str = json.dumps(dv['holdings_json'], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO portfolio_history 
            (timestamp, date, total_value, cash_balance, invested_value,
             daily_return_pct, cumulative_return_pct, benchmark_value, 
             benchmark_return_pct, mdd_pct, peak_value, holdings_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                timestamp = excluded.timestamp,
                total_value = excluded.total_value,
                cash_balance = excluded.cash_balance,
                invested_value = excluded.invested_value,
                daily_return_pct = excluded.daily_return_pct,
                cumulative_return_pct = excluded.cumulative_return_pct,
                benchmark_value = excluded.benchmark_value,
                benchmark_return_pct = excluded.benchmark_return_pct,
                mdd_pct = excluded.mdd_pct,
                peak_value = excluded.peak_value,
                holdings_json = excluded.holdings_json
        """, (timestamp, dv['date'], dv['total_value'], dv['cash_balance'],
              dv['invested_value'], dv['daily_return_pct'], dv['cumulative_return_pct'],
              dv['benchmark_value'], dv['benchmark_return_pct'], dv['mdd_pct'],
              dv['peak_value'], holdings_json_str))
    
    conn.commit()
    conn.close()
    
    # 5. Verify
    logger.info("\n5️⃣ Verification...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM portfolio_history")
    count, min_date, max_date = cursor.fetchone()
    conn.close()
    
    logger.info(f"  Records: {count}")
    logger.info(f"  Date range: {min_date} to {max_date}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Historical portfolio data generated successfully!")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=14, help='Number of days to generate (default: 14)')
    args = parser.parse_args()
    
    success = generate_historical_portfolio(args.days)
    sys.exit(0 if success else 1)
