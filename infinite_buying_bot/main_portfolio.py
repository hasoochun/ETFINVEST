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
import asyncio # Fixed missing import
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from infinite_buying_bot.config.logging_config import setup_logging
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.core.portfolio_manager import PortfolioManager
from infinite_buying_bot.telegram_bot.notifications import TelegramNotifier as Notifier # Fixed Import
from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.telegram_bot.handlers.callbacks import setup_handlers
import infinite_buying_bot.telegram_bot.formatters.portfolio_messages as pm
from infinite_buying_bot.utils.bot_status_manager import BotStatusManager
from datetime import datetime, timedelta

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

# --- Async Background Service ---
async def status_service(controller, manager):
    logger.info("✅ Status Service Started")
    last_monitor = 0
    last_config = 0
    
    while True:
        try:
            now = time.time()
            
            # 1. Heartbeat (Every 1s)
            manager.update_heartbeat()
            
            # 2. Config Sync (Every 5s)
            if now - last_config >= 5:
                controller.sync_with_config()
                manager.set_config_info(
                    controller.strategy_mode, 
                    controller.trading_mode, 
                    controller.accel_interval_minutes
                )
                manager.set_status('running' if controller.is_running else 'paused')
                last_config = now
                
            # 3. Monitor Cycle (Every 10s for Demo)
            if now - last_monitor >= 10:
                next_run = datetime.now() + timedelta(seconds=10)
                manager.set_schedule(next_run, "Next Monitoring Cycle")
                controller.run_monitoring_cycle()
                last_monitor = now
                
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Status Loop Error: {e}")
            await asyncio.sleep(5)

async def post_init(application: Application):
    """Start background tasks on bot startup"""
    # Get references from application.bot_data (we need to store them there first)
    controller = application.bot_data['controller']
    manager = application.bot_data['manager']
    
    # Start the service
    asyncio.create_task(status_service(controller, manager))


def main():
    logger.info("🚀 Starting Bot (CLEAN REAL VERSION)")
    
    # Files Cleanup (PID only - DO NOT DELETE trading.db!)
    try:
        # [REMOVED] DB Delete - Keep trading.db for portfolio history tracking!
        # db_path = os.path.join(..., 'trading.db')
        # os.remove(db_path)  # <- This was deleting all history data!
            
        # Pid Delete (safe to remove)
        pid_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.bot.pid')
        if os.path.exists(pid_path):
            os.remove(pid_path)
    except:
        pass

    try:
        config = load_config()
        # Fix: Pass individual args instead of config dict
        token = config.get('telegram_token')
        chat_id = config.get('telegram_chat_id')
        notifier = Notifier(token, chat_id) 
        
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

        # [NEW] Status Manager Setup
        status_manager = BotStatusManager(root_dir)
        bot_controller.set_status_manager(status_manager)

        # Use post_init to start background tasks
        app = Application.builder().token(token).post_init(post_init).build()
        
        # Store refs for post_init
        app.bot_data['controller'] = bot_controller
        app.bot_data['manager'] = status_manager
        
        setup_handlers(app, bot_controller)
        
        logger.info("✅ Status System Initialized (No JobQueue)")
        
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
