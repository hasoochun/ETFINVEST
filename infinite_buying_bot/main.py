import sys
import os
import time
import logging
import yaml
import asyncio
from datetime import datetime, timedelta
import pytz
from threading import Thread
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.utils.notifier import Notifier
from infinite_buying_bot.utils.scheduler import MarketScheduler
# InfiniteBuyingStrategy moved to bot_controller
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.telegram_bot.bot import TradingTelegramBot
from infinite_buying_bot.dashboard.database import set_initial_capital

# Logging Setup
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'kis_devlp.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Override Notification Settings from Env
    if os.getenv("DISCORD_WEBHOOK_URL"):
        if 'notification' not in config: config['notification'] = {}
        config['notification']['discord_webhook_url'] = os.getenv("DISCORD_WEBHOOK_URL")
        
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        if 'notification' not in config: config['notification'] = {}
        config['notification']['telegram_token'] = os.getenv("TELEGRAM_BOT_TOKEN")
        
    if os.getenv("TELEGRAM_CHAT_ID"):
        if 'notification' not in config: config['notification'] = {}
        config['notification']['telegram_chat_id'] = os.getenv("TELEGRAM_CHAT_ID")
        
    return config

# Note: Trading counters moved to bot_controller.py

def start_telegram_bot(bot_controller, config):
    """Run Telegram bot in separate thread"""
    async def run_bot():
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not telegram_token or not telegram_chat_id:
            logger.warning("Telegram credentials not found. Bot will run without Telegram.")
            return
        
        allowed_chat_ids = [int(telegram_chat_id)]
        telegram_bot = TradingTelegramBot(telegram_token, allowed_chat_ids, bot_controller)
        
        try:
            await telegram_bot.start()
            # Send startup message
            await telegram_bot.send_startup_message(int(telegram_chat_id))
            logger.info("Telegram bot started and startup message sent")
            
            # Keep bot running
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
    
    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

def main():
    """
    Unified entrypoint for the trading bot.
    Delegates all trading logic to bot_controller.run_monitoring_cycle().
    """
    
    logger.info("Initializing Infinite Buying Bot...")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    notifier = Notifier(config)
    scheduler = MarketScheduler()
    # Note: Strategy logic now fully handled by bot_controller
    
    try:
        trader = Trader(config, notifier)
    except Exception as e:
        logger.error(f"Failed to initialize Trader: {e}")
        notifier.send(f"Bot Initialization Failed: {e}")
        return
    
    # Initialize dashboard database
    set_initial_capital(100000000)  # 1억
    logger.info("Dashboard database initialized")
    
    # Initialize bot controller
    bot_controller = BotController()
    bot_controller.set_trader(trader)
    bot_controller.set_notifier(notifier)
    
    # [FIX] Add PortfolioManager Initialization (Critical for Gradual Mode)
    from infinite_buying_bot.core.portfolio_manager import PortfolioManager
    portfolio_manager = PortfolioManager(initial_capital=0.0)
    cash, _, _ = trader.get_balance()
    if cash > 0:
        portfolio_manager.update_cash(cash)
    bot_controller.portfolio_manager = portfolio_manager
    logger.info(f"[FIX] PortfolioManager connected with cash: ${cash:.2f}")
    
    # Start Telegram bot in separate thread
    telegram_thread = Thread(target=start_telegram_bot, args=(bot_controller, config), daemon=True)
    telegram_thread.start()
    logger.info("Telegram bot thread started")
    
    notifier.send("Bot Started. Waiting for user to start trading via Telegram...")
    
    # [FIX] Explicitly set status to RUNNING
    bot_controller.status_manager.set_status("running")
    bot_controller.status_manager.update_logic("Started", "Bot is running and waiting for command")
    
    while True:
        try:
            # [FIX] Update Heartbeat
            bot_controller.status_manager.update_heartbeat()

            # 0. Sync Config (Control Mechanism)
            bot_controller.sync_with_config()

            # 1. Check if trading is enabled
            if not bot_controller.is_running:
                logger.info("Trading not started. Waiting for user command...")
                bot_controller.status_manager.update_logic("Paused", "Trading disabled in config")
                time.sleep(5)
                continue
            
            # 1.5 Check S-T Exchange Schedule (Allow Pre-market Execution)
            is_st_scheduled_now = False
            trading_mode = getattr(bot_controller, 'trading_mode', 'gradual')
            
            if trading_mode == 'st-exchange':
                daily_time = getattr(bot_controller, 'daily_time', '22:00')
                # [FIX] Use KST for time comparison (Server is UTC)
                tz_kst = pytz.timezone('Asia/Seoul')
                now_kst = datetime.now(tz_kst)
                
                try:
                    target_hour, target_minute = map(int, daily_time.split(':'))
                    if now_kst.hour == target_hour and now_kst.minute == target_minute:
                        # Check if already executed today
                        if not hasattr(bot_controller, 'last_st_exchange_date') or bot_controller.last_st_exchange_date != now_kst.date(): 
                            is_st_scheduled_now = True
                            logger.info(f"[S-T EXCHANGE] Pre-market execution allowed for scheduled time: {daily_time} KST")
                except ValueError:
                    logger.error(f"Invalid daily_time format: {daily_time}")

            # 2. Check Market Status (S-T Exchange bypasses market check)
            if not scheduler.is_market_open() and not is_st_scheduled_now:
                logger.info("Market is closed. Sleeping...")
                bot_controller.status_manager.update_logic("Sleeping", "Market is Closed", "MARKET CLOSED")
                time.sleep(60)
                continue

            # ============================================================
            # [UNIFIED] Delegate ALL trading logic to BotController
            # ============================================================
            # bot_controller.run_monitoring_cycle() handles:
            # - Market data fetching
            # - Holdings logging to DB
            # - Profit taking (10% auto-sell)
            # - Gradual mode execution
            # - S-T Exchange execution
            # - Scheduled single execution
            # - Status updates
            bot_controller.run_monitoring_cycle()
            
            # Sleep between cycles
            time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            notifier.send(f"Bot Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
