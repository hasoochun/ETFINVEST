"""
Update existing database to add new columns
Run this once to migrate existing data
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "trading.db"

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(trades)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'trade_count' not in columns:
        print("Adding trade_count column...")
        cursor.execute("ALTER TABLE trades ADD COLUMN trade_count INTEGER")
    
    if 'mdd_pct' not in columns:
        print("Adding mdd_pct column...")
        cursor.execute("ALTER TABLE trades ADD COLUMN mdd_pct REAL")
    
    conn.commit()
    conn.close()
    print("✅ Migration complete!")

if __name__ == "__main__":
    migrate_db()
