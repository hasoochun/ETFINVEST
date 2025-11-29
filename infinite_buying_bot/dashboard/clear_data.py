"""
Clear all sample data from database
Run this before starting real trading
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "trading.db"

def clear_all_data():
    """Delete all data from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delete all trades
    cursor.execute("DELETE FROM trades")
    print("✅ Deleted all trades")
    
    # Delete all daily stats
    cursor.execute("DELETE FROM daily_stats")
    print("✅ Deleted all daily stats")
    
    # Keep config (initial capital)
    
    conn.commit()
    conn.close()
    print("\n✅ Database cleared! Ready for real trading.")

if __name__ == "__main__":
    confirm = input("⚠️  This will delete ALL data. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_all_data()
    else:
        print("❌ Cancelled")
