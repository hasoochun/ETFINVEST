"""
Database module for storing trading data
Stores: trades, daily snapshots, current position
"""
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "trading.db"

def init_db():
    """Initialize database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Trades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total_value REAL NOT NULL,
            pnl REAL,
            pnl_pct REAL,
            trade_count INTEGER,
            mdd_pct REAL,
            reason TEXT
        )
    """)
    
    # Daily stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            total_value REAL NOT NULL,
            daily_return_pct REAL,
            cumulative_return_pct REAL,
            position_quantity INTEGER,
            position_avg_price REAL
        )
    """)
    
    # Config table (for initial capital, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def set_initial_capital(amount: float):
    """Set initial capital (only once)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('initial_capital', ?)", (str(amount),))
    conn.commit()
    conn.close()

def get_initial_capital() -> float:
    """Get initial capital"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'initial_capital'")
    result = cursor.fetchone()
    conn.close()
    return float(result[0]) if result else 100000000.0  # Default 1억

def log_trade(trade_type: str, symbol: str, quantity: int, price: float, 
              pnl: float = None, pnl_pct: float = None, trade_count: int = None,
              mdd_pct: float = None, reason: str = None):
    """Log a trade to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    total_value = quantity * price
    
    cursor.execute("""
        INSERT INTO trades (timestamp, type, symbol, quantity, price, total_value, pnl, pnl_pct, trade_count, mdd_pct, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, trade_type, symbol, quantity, price, total_value, pnl, pnl_pct, trade_count, mdd_pct, reason))
    
    conn.commit()
    conn.close()

def log_daily_stats(total_value: float, daily_return_pct: float, cumulative_return_pct: float,
                   position_quantity: int = 0, position_avg_price: float = 0):
    """Log daily statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    date = datetime.now().date().isoformat()
    
    cursor.execute("""
        INSERT OR REPLACE INTO daily_stats 
        (date, total_value, daily_return_pct, cumulative_return_pct, position_quantity, position_avg_price)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date, total_value, daily_return_pct, cumulative_return_pct, position_quantity, position_avg_price))
    
    conn.commit()
    conn.close()

def get_all_trades() -> pd.DataFrame:
    """Get all trades as DataFrame"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def get_recent_trades(limit: int = 10) -> pd.DataFrame:
    """Get recent trades"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM trades ORDER BY timestamp DESC LIMIT {limit}", conn)
    conn.close()
    return df

def get_daily_stats() -> pd.DataFrame:
    """Get all daily stats"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM daily_stats ORDER BY date ASC", conn)
    conn.close()
    return df

def get_current_stats():
    """Get current trading statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get latest daily stat
    cursor.execute("SELECT * FROM daily_stats ORDER BY date DESC LIMIT 1")
    latest = cursor.fetchone()
    
    # Get total trades
    cursor.execute("SELECT COUNT(*) FROM trades")
    total_trades = cursor.fetchone()[0]
    
    # Get winning trades (pnl > 0)
    cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
    winning_trades = cursor.fetchone()[0]
    
    # Get target achieved trades (pnl_pct >= 10)
    cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl_pct >= 10")
    target_achieved = cursor.fetchone()[0]
    
    conn.close()
    
    if latest:
        return {
            'total_value': latest[1],
            'daily_return_pct': latest[2] or 0,
            'cumulative_return_pct': latest[3] or 0,
            'position_quantity': latest[4] or 0,
            'position_avg_price': latest[5] or 0,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'target_achieved': target_achieved,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0
        }
    else:
        return {
            'total_value': get_initial_capital(),
            'daily_return_pct': 0,
            'cumulative_return_pct': 0,
            'position_quantity': 0,
            'position_avg_price': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'target_achieved': 0,
            'win_rate': 0
        }

# Initialize DB on import
init_db()
