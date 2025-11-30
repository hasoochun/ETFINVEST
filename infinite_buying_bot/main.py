import sys
import os
import time
import logging
import yaml
import asyncio
from threading import Thread
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.utils.notifier import Notifier
from infinite_buying_bot.utils.scheduler import MarketScheduler
from infinite_buying_bot.core.strategy import InfiniteBuyingStrategy
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.telegram_bot.bot import TradingTelegramBot
from infinite_buying_bot.dashboard.database import log_trade, set_initial_capital

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

# Global trading control flags
trade_counter = 0
entry_value = 0
max_drawdown = 0

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
    global trade_counter, entry_value, max_drawdown
    
    logger.info("Initializing Infinite Buying Bot...")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    notifier = Notifier(config)
    scheduler = MarketScheduler()
    strategy = InfiniteBuyingStrategy(config)
    
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
    
    # Start Telegram bot in separate thread
    telegram_thread = Thread(target=start_telegram_bot, args=(bot_controller, config), daemon=True)
    telegram_thread.start()
    logger.info("Telegram bot thread started")
    
    notifier.send("Bot Started. Waiting for user to start trading via Telegram...")
    
    while True:
        try:
            # 0. Check if trading is enabled
            if not bot_controller.is_running:
                logger.info("Trading not started. Waiting for user command...")
                time.sleep(5)
                continue
            
            # 1. Check Market Status
            if not scheduler.is_market_open():
                logger.info("Market is closed. Sleeping...")
                time.sleep(60)
                continue

            # 2. Get Data
            current_price = trader.get_price()
            buying_power, quantity, avg_price = trader.get_balance()
            
            if current_price is None:
                logger.warning("Failed to fetch price. Retrying...")
                time.sleep(10)
                continue

            logger.info(f"Price: ${current_price}, Holdings: {quantity} @ ${avg_price:.2f}, Cash: ${buying_power:.2f}")
            logger.info(f"Selected ETF: {bot_controller.trading_symbol}")
            
            # Log holdings to database for dashboard
            try:
                all_holdings = trader.get_all_holdings()
                from infinite_buying_bot.dashboard.database import log_holdings
                log_holdings(all_holdings)
            except Exception as e:
                logger.error(f"Failed to log holdings: {e}")
            
            # Track MDD
            if quantity > 0:
                current_position_value = quantity * current_price
                cash = buying_power
                total_now = cash + current_position_value
                if entry_value > 0:
                    drawdown = ((total_now - entry_value) / entry_value) * 100
                    max_drawdown = min(max_drawdown, drawdown)

            # 3. Sell Logic (Profit Taking)
            if strategy.should_sell(current_price, avg_price, quantity):
                # Calculate P&L
                pnl = (current_price - avg_price) * quantity
                pnl_pct = ((current_price - avg_price) / avg_price) * 100
                
                # Execute sell
                trader.sell_all(quantity)
                
                # Log to dashboard with selected ETF
                log_trade(
                    "sell",
                    bot_controller.trading_symbol,  # Use selected ETF
                    quantity,
                    current_price,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    trade_count=trade_counter,
                    mdd_pct=max_drawdown,
                    reason="Profit target" if pnl_pct >= 10 else "Stop loss"
                )
                logger.info(f"Sell logged to dashboard: {bot_controller.trading_symbol} {quantity} @ ${current_price:.2f}, P&L: {pnl_pct:.2f}%")
                
                # Reset counters
                trade_counter = 0
                max_drawdown = 0
                entry_value = 0
                
                time.sleep(60)
                continue

            # 4. Buy Logic (Near Close)
            is_near_close = scheduler.is_near_close(minutes=5)
            should_buy, split_count = strategy.should_buy(current_price, avg_price, quantity, is_near_close)
            
            if should_buy and split_count > 0 and bot_controller.entry_allowed:
                buy_amount = buying_power / split_count
                buy_qty = int(buy_amount / current_price)
                
                if buy_qty > 0:
                    trader.buy(buy_amount)
                    
                    # Log to dashboard with selected ETF
                    log_trade(
                        "buy",
                        bot_controller.trading_symbol,  # Use selected ETF
                        buy_qty,
                        current_price,
                        reason="Strategy signal"
                    )
                    logger.info(f"Buy logged to dashboard: {bot_controller.trading_symbol} {buy_qty} @ ${current_price:.2f}")
                    
                    # Update counters
                    trade_counter += 1
                    if entry_value == 0:
                        entry_value = buying_power + (quantity * avg_price)
                    
                    time.sleep(300)
            
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
