import os
import sys

# [CRITICAL] Add Project Root to Path to fix ModuleNotFoundError
# Current file: infinite_buying_bot/main_portfolio.py
# Root: open-trading-api/
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import logging
import argparse
import time
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from infinite_buying_bot.config.logging_config import setup_logging
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.core.portfolio_manager import PortfolioManager
from infinite_buying_bot.telegram_bot.bot import Notifier
from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.telegram_bot.handlers.callbacks import setup_handlers
import infinite_buying_bot.telegram_bot.formatters.portfolio_messages as pm

# Setup Logging
setup_logging()
logger = logging.getLogger(__name__)

# [DEBUG] Print Loaded Module Paths
print(f"DEBUG: BotController loaded from: {BotController.__module__}")
print(f"DEBUG: Portfolio Messages loaded from: {pm.__file__}")


def load_config():
    # Load from Project Root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(root_dir, 'kis_devlp.yaml')
    
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def main():
    logger.info("🚀 Starting Bot (CLEAN REAL VERSION)")
    
    # Files Cleanup
    try:
        # DB Delete
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard', 'trading.db')
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("Deleted DB File")
            
        # Pid Delete
        pid_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.bot.pid')
        if os.path.exists(pid_path):
            os.remove(pid_path)
    except:
        pass

    try:
        config = load_config()
        notifier = Notifier(config) # Assuming this works or needs minimal config
        
        # Initialize Core - Fail Fast
        trader = Trader(config, notifier)
        
        # Check Balance - NO FALLBACK
        cash, qty, avg = trader.get_balance()
        logger.info(f"Initial Check: Cash=${cash}, Qty={qty}")
        
        if cash <= 0:
            logger.warning("⚠️ Cash is 0 or API Error. Bot starting but might need check.")
            
        # Init Managers (0 Init Capital)
        portfolio_manager = PortfolioManager(initial_capital=0.0) 
        if cash > 0:
            portfolio_manager.update_cash(cash)

        # Bot Controller
        bot_controller = BotController()
        bot_controller.set_trader(trader)
        bot_controller.set_notifier(notifier)
        bot_controller.portfolio_manager = portfolio_manager
        
        # Telegram Setup
        token = config.get('telegram_token')
        if not token: # Fallback to manual setup or error
             logger.error("No Telegram Token in Config")
             return

        app = Application.builder().token(token).build()
        setup_handlers(app, bot_controller)
        
        # Notify Start with UNIQUE IDENTIFIER
        notifier.send("📢 **[LOCAL-PC-VERIFIED] SYSTEM ONLINE**\nMode: REAL TRADING\nStatus: Clean Boot")
        
        logger.info("Polling...")
        app.run_polling()
        
    except Exception as e:
        logger.critical(f"Main Loop Crash: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
