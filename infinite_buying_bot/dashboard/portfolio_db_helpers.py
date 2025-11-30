"""
Database helper functions for portfolio snapshots and rebalancing history
"""
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# Import DB_PATH from main database module
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import DB_PATH

# Database helper functions for portfolio snapshots and rebalancing history

def log_portfolio_snapshot(portfolio_summary: dict):
    """Log current portfolio state for dashboard charts
    
    Args:
        portfolio_summary: Dict from PortfolioManager.get_portfolio_summary()
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    total_value = portfolio_summary['total_value']
    
    # Get position values
    positions = portfolio_summary['positions']
    tqqq_value = positions.get('TQQQ', {}).get('quantity', 0) * positions.get('TQQQ', {}).get('current_price', 0)
    shv_value = positions.get('SHV', {}).get('quantity', 0) * positions.get('SHV', {}).get('current_price', 0)
    schd_value = positions.get('SCHD', {}).get('quantity', 0) * positions.get('SCHD', {}).get('current_price', 0)
    cash_value = portfolio_summary['cash']
    
    # Get allocation percentages
    current_alloc = portfolio_summary['current_allocation']
    tqqq_pct = current_alloc.get('TQQQ', 0)
    shv_pct = current_alloc.get('SHV', 0)
    schd_pct = current_alloc.get('SCHD', 0)
    cash_pct = current_alloc.get('CASH', 0)
    
    # Get drift
    drift = portfolio_summary['allocation_drift']
    drift_tqqq = drift.get('TQQQ', 0)
    drift_shv = drift.get('SHV', 0)
    drift_schd = drift.get('SCHD', 0)
    
    cursor.execute("""
        INSERT INTO portfolio_snapshots 
        (timestamp, total_value, tqqq_value, shv_value, schd_value, cash_value,
         tqqq_pct, shv_pct, schd_pct, cash_pct, drift_tqqq, drift_shv, drift_schd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, total_value, tqqq_value, shv_value, schd_value, cash_value,
          tqqq_pct, shv_pct, schd_pct, cash_pct, drift_tqqq, drift_shv, drift_schd))
    
    conn.commit()
    conn.close()


def log_rebalancing_action(action: dict):
    """Log a rebalancing action for audit trail
    
    Args:
        action: Dict from RebalancingEngine with action details
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    action_type = action['action']
    from_symbol = action.get('sell_symbol') or action.get('from_symbol')
    to_symbol = action.get('buy_symbol') or action.get('to_symbol')
    amount = action.get('amount') or action.get('sell_amount') or action.get('profit_amount', 0)
    reason = action.get('reason', '')
    
    cursor.execute("""
        INSERT INTO rebalancing_history 
        (timestamp, action_type, from_symbol, to_symbol, amount, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, action_type, from_symbol, to_symbol, amount, reason))
    
    conn.commit()
    conn.close()


def get_portfolio_snapshots(days: int = 30) -> pd.DataFrame:
    """Get portfolio snapshots for the last N days
    
    Args:
        days: Number of days to retrieve
        
    Returns:
        DataFrame with portfolio history
    """
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT * FROM portfolio_snapshots 
        WHERE timestamp >= datetime('now', '-{days} days')
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_rebalancing_history(limit: int = 50) -> pd.DataFrame:
    """Get recent rebalancing actions
    
    Args:
        limit: Number of records to retrieve
        
    Returns:
        DataFrame with rebalancing history
    """
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT * FROM rebalancing_history 
        ORDER BY timestamp DESC 
        LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_allocation_drift_history(days: int = 7) -> pd.DataFrame:
    """Get allocation drift over time for charts
    
    Args:
        days: Number of days to retrieve
        
    Returns:
        DataFrame with drift history
    """
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT timestamp, drift_tqqq, drift_shv, drift_schd
        FROM portfolio_snapshots 
        WHERE timestamp >= datetime('now', '-{days} days')
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

