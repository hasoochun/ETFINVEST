"""Main entry point for Real Trading Bot with Full UI"""

import sys
import os

# Fix Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from real_trading_bot.config.config_loader import ConfigLoader
from real_trading_bot.api.auth import KisAuth
from real_trading_bot.core.trader import RealTrader
from real_trading_bot.bot.telegram_ui import RealTradingUI

def main():
    print("=" * 50)
    print("🚀 REAL TRADING BOT (Full UI) STARTING...")
    print("=" * 50)
    
    # 1. Config
    config = ConfigLoader.load()
    print("✅ Config Loaded")
    
    # 2. Auth
    print("🔑 Authenticating with KIS (REAL)...")
    auth = KisAuth(config)
    auth_data = auth.auth()
    print("✅ Authenticated (REAL ACCOUNT)")
    
    # 3. Trader
    trader = RealTrader(auth_data)
    print("✅ Trader Initialized")
    
    # 4. Full UI Bot
    print("🤖 Starting Telegram Bot with Full UI...")
    bot = RealTradingUI(config, trader)
    bot.run()  # Sync call

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user.")
