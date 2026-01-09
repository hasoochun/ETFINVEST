"""
Database module for storing trading data
Stores: trades, daily snapshots, current position
"""
import sqlite3
import pandas as pd
import time
import functools
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "trading.db"


def retry_on_locked(max_retries=3, delay=0.5):
    """Decorator to retry database operations on lock errors.
    
    SQLite는 동시 쓰기가 불가능하여 'database is locked' 오류 발생 가능.
    이 데코레이터는 자동으로 재시도하여 일시적인 락 문제를 해결함.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower():
                        last_error = e
                        logger.warning(f"[DB] Lock detected, retry {attempt+1}/{max_retries}...")
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise
            logger.error(f"[DB] Max retries reached, operation failed: {last_error}")
            raise last_error
        return wrapper
    return decorator


def get_connection():
    """Get database connection with WAL mode for better concurrency."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db():
    """Initialize database with required tables"""
    conn = get_connection()
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
    
    # Portfolio snapshots table (for dashboard charts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_value REAL NOT NULL,
            tqqq_value REAL,
            shv_value REAL,
            schd_value REAL,
            cash_value REAL,
            tqqq_pct REAL,
            shv_pct REAL,
            schd_pct REAL,
            cash_pct REAL,
            drift_tqqq REAL,
            drift_shv REAL,
            drift_schd REAL
        )
    """)
    
    # Rebalancing history table (for audit trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rebalancing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            from_symbol TEXT,
            to_symbol TEXT,
            amount REAL NOT NULL,
            reason TEXT
        )
    """)
    
    # Portfolio history table (for performance tracking & benchmark comparison)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL UNIQUE,
            total_value REAL NOT NULL,
            cash_balance REAL DEFAULT 0,
            invested_value REAL DEFAULT 0,
            daily_return_pct REAL DEFAULT 0,
            cumulative_return_pct REAL DEFAULT 0,
            benchmark_value REAL,
            benchmark_return_pct REAL DEFAULT 0,
            mdd_pct REAL DEFAULT 0,
            peak_value REAL,
            holdings_json TEXT
        )
    """)
    
    # [NEW] Holdings history table for 5-minute interval snapshots (for reports & analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            quantity INTEGER,
            avg_price REAL,
            current_price REAL,
            value REAL,
            profit_pct REAL,
            strategy_mode TEXT
        )
    """)
    
    # [NEW] Add strategy columns to portfolio_history (ignore if already exist)
    for column in ['strategy_mode TEXT', 'trading_mode TEXT', 'graphrag_confidence REAL']:
        try:
            col_name = column.split()[0]
            cursor.execute(f"ALTER TABLE portfolio_history ADD COLUMN {column}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    
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
    return float(result[0]) if result else 0.0  # [FIX] Default 0 (Was 100M)

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

def create_holdings_table():
    """Create holdings table if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            quantity INTEGER,
            avg_price REAL,
            current_price REAL,
            value REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_holdings(holdings: list):
    """Log current holdings to database"""
    create_holdings_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM holdings')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for h in holdings:
        cursor.execute('''
            INSERT INTO holdings (timestamp, symbol, quantity, avg_price, current_price, value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            h['symbol'],
            h['qty'],
            h['avg_price'],
            h['current_price'],
            h['value']
        ))
    
    conn.commit()
    conn.close()

def log_holdings_history(holdings: list, strategy_mode: str = None):
    """
    [NEW] Log holdings snapshot to history table for 5-minute interval tracking.
    Unlike log_holdings(), this APPENDS data for historical analysis.
    
    Args:
        holdings: List of holdings with symbol, qty, avg_price, current_price, value
        strategy_mode: Current strategy mode (aggressive/neutral/defensive)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for h in holdings:
        # Calculate profit percentage
        avg_price = h.get('avg_price', 0)
        current_price = h.get('current_price', 0)
        profit_pct = 0
        if avg_price > 0:
            profit_pct = ((current_price - avg_price) / avg_price) * 100
        
        cursor.execute('''
            INSERT INTO holdings_history 
            (timestamp, symbol, quantity, avg_price, current_price, value, profit_pct, strategy_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            h['symbol'],
            h.get('qty', 0),
            avg_price,
            current_price,
            h.get('value', 0),
            profit_pct,
            strategy_mode
        ))
    
    conn.commit()
    conn.close()
    logger.info(f"[DB] Holdings history saved: {len(holdings)} ETFs at {timestamp}")

def get_current_holdings():
    """Get current holdings from database"""
    create_holdings_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM holdings')
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

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

# =============================================================================
# PORTFOLIO HISTORY FUNCTIONS (for Performance Report)
# =============================================================================

import json
import logging

logger = logging.getLogger(__name__)

def log_portfolio_history(
    total_value: float,
    cash_balance: float = 0,
    invested_value: float = 0,
    daily_return_pct: float = 0,
    cumulative_return_pct: float = 0,
    benchmark_value: float = None,
    benchmark_return_pct: float = 0,
    holdings: list = None,
    strategy_mode: str = None,
    trading_mode: str = None,
    graphrag_confidence: float = 0.0
):
    """
    Log daily portfolio snapshot for performance tracking.
    Uses UPSERT to update if same date exists.
    
    Args:
        total_value: Total portfolio value in USD
        cash_balance: Cash balance in USD
        invested_value: Invested amount in USD
        daily_return_pct: Daily return percentage
        cumulative_return_pct: Cumulative return since inception
        benchmark_value: S&P 500 index value (for comparison)
        benchmark_return_pct: Benchmark cumulative return
        holdings: List of holdings with qty, symbol, value
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    date = datetime.now().date().isoformat()
    
    # Calculate MDD
    cursor.execute("SELECT MAX(peak_value) FROM portfolio_history")
    result = cursor.fetchone()
    peak_value = result[0] if result and result[0] else total_value
    peak_value = max(peak_value, total_value)
    
    mdd_pct = 0.0
    if peak_value > 0:
        mdd_pct = ((total_value - peak_value) / peak_value) * 100
    
    # Serialize holdings to JSON
    holdings_json = json.dumps(holdings, ensure_ascii=False) if holdings else None
    
    try:
        cursor.execute("""
            INSERT INTO portfolio_history 
            (timestamp, date, total_value, cash_balance, invested_value,
             daily_return_pct, cumulative_return_pct, benchmark_value, 
             benchmark_return_pct, mdd_pct, peak_value, holdings_json,
             strategy_mode, trading_mode, graphrag_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                holdings_json = excluded.holdings_json,
                strategy_mode = excluded.strategy_mode,
                trading_mode = excluded.trading_mode,
                graphrag_confidence = excluded.graphrag_confidence
        """, (timestamp, date, total_value, cash_balance, invested_value,
              daily_return_pct, cumulative_return_pct, benchmark_value,
              benchmark_return_pct, mdd_pct, peak_value, holdings_json,
              strategy_mode, trading_mode, graphrag_confidence))
        
        conn.commit()
        logger.info(f"[DB] Portfolio history saved: date={date}, total=${total_value:.2f}, return={cumulative_return_pct:.2f}%, mdd={mdd_pct:.2f}%")
    except Exception as e:
        logger.error(f"[DB] Failed to log portfolio history: {e}")
    finally:
        conn.close()


def get_portfolio_history(days: int = 30) -> pd.DataFrame:
    """
    Get portfolio history for the last N days.
    
    Args:
        days: Number of days to retrieve
        
    Returns:
        DataFrame with portfolio history
    """
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT date, total_value, cash_balance, invested_value,
               daily_return_pct, cumulative_return_pct, 
               benchmark_value, benchmark_return_pct, mdd_pct, holdings_json
        FROM portfolio_history 
        WHERE date >= date('now', '-{days} days')
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    logger.info(f"[DB] Retrieved {len(df)} portfolio history records (last {days} days)")
    return df


def get_latest_portfolio_snapshot():
    """
    Get the most recent portfolio snapshot.
    
    Returns:
        Dict with latest portfolio data or None
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, total_value, cash_balance, invested_value,
               daily_return_pct, cumulative_return_pct, 
               benchmark_value, benchmark_return_pct, mdd_pct, holdings_json
        FROM portfolio_history 
        ORDER BY date DESC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'date': row[0],
            'total_value': row[1],
            'cash_balance': row[2],
            'invested_value': row[3],
            'daily_return_pct': row[4],
            'cumulative_return_pct': row[5],
            'benchmark_value': row[6],
            'benchmark_return_pct': row[7],
            'mdd_pct': row[8],
            'holdings': json.loads(row[9]) if row[9] else []
        }
    return None


def get_performance_metrics():
    """
    Calculate key performance metrics for investment analysis.
    
    Returns:
        Dict with performance metrics including:
        - total_return: Cumulative return percentage
        - mdd: Maximum Drawdown
        - sharpe_ratio: Risk-adjusted return (simplified)
        - win_rate: Percentage of positive days
        - avg_daily_return: Average daily return
        - volatility: Standard deviation of daily returns
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT date, daily_return_pct, cumulative_return_pct, mdd_pct
        FROM portfolio_history 
        ORDER BY date ASC
    """, conn)
    conn.close()
    
    if df.empty:
        return {
            'total_return': 0,
            'mdd': 0,
            'sharpe_ratio': 0,
            'win_rate': 0,
            'avg_daily_return': 0,
            'volatility': 0,
            'total_days': 0
        }
    
    daily_returns = df['daily_return_pct'].dropna()
    
    # Basic metrics
    total_return = df['cumulative_return_pct'].iloc[-1] if len(df) > 0 else 0
    mdd = df['mdd_pct'].min() if len(df) > 0 else 0
    
    # Win rate (positive return days)
    positive_days = (daily_returns > 0).sum()
    total_days = len(daily_returns)
    win_rate = (positive_days / total_days * 100) if total_days > 0 else 0
    
    # Average daily return and volatility
    avg_daily = daily_returns.mean() if len(daily_returns) > 0 else 0
    volatility = daily_returns.std() if len(daily_returns) > 1 else 0
    
    # Simplified Sharpe Ratio (annualized, assuming 252 trading days)
    # Sharpe = (avg_return - risk_free_rate) / volatility
    # Using 0% risk-free rate for simplicity
    sharpe_ratio = 0
    if volatility > 0:
        sharpe_ratio = (avg_daily * 252**0.5) / (volatility * 252**0.5)
    
    return {
        'total_return': round(total_return, 2),
        'mdd': round(mdd, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'win_rate': round(win_rate, 1),
        'avg_daily_return': round(avg_daily, 3),
        'volatility': round(volatility, 3),
        'total_days': total_days
    }
