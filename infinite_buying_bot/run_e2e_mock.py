import sys
import os
import time
import logging
import asyncio
from threading import Thread
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.utils.notifier import Notifier
from infinite_buying_bot.core.strategy import InfiniteBuyingStrategy
from infinite_buying_bot.core.portfolio_manager import PortfolioManager
from infinite_buying_bot.core.rebalancing_engine import RebalancingEngine
from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.telegram_bot.bot import TradingTelegramBot
from infinite_buying_bot.dashboard.database import log_trade, set_initial_capital, log_holdings
from infinite_buying_bot.test.mocks import MockTrader, MockScheduler

# Load .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [E2E TEST] - %(message)s'
)
logger = logging.getLogger(__name__)

# Global vars
trade_counter = 0
entry_value = 0
max_drawdown = 0

def start_telegram_bot(bot_controller):
    """Run Telegram bot in separate thread"""
    async def run_bot():
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in .env")
            return
            
        allowed_chat_ids = [int(telegram_chat_id)] if telegram_chat_id else []
        telegram_bot = TradingTelegramBot(telegram_token, allowed_chat_ids, bot_controller)
        
        try:
            await telegram_bot.start()
            if telegram_chat_id:
                await telegram_bot.send_startup_message(int(telegram_chat_id))
            logger.info("Telegram bot started")
            
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

def main():
    global trade_counter, entry_value, max_drawdown
    
    logger.info("Starting E2E Integration Test with Mock Data...")
    
    # Initialize Mocks
    trader = MockTrader()
    scheduler = MockScheduler()
    
    # Config placeholder
    config = {'strategy': {'division_count': 40, 'profit_target': 10}}
    strategy = InfiniteBuyingStrategy(config)
    notifier = Notifier(config) # This might try to send real notifications if configured
    
    # Initialize DB
    set_initial_capital(100000000)
    
    # Initialize Portfolio Components
    portfolio_manager = PortfolioManager(initial_capital=100000000.0)
    rebalancing_engine = RebalancingEngine(portfolio_manager)
    
    # Initialize Controller
    bot_controller = BotController()
    bot_controller.set_trader(trader)
    bot_controller.set_notifier(notifier)
    
    # Add portfolio components to bot controller for Telegram UI
    bot_controller.portfolio_manager = portfolio_manager
    bot_controller.rebalancing_engine = rebalancing_engine
    
    # Start Telegram
    telegram_thread = Thread(target=start_telegram_bot, args=(bot_controller,), daemon=True)
    telegram_thread.start()
    
    logger.info("System Ready. Waiting for 'Start Bot' command via Telegram...")
    logger.info("Use the Telegram Bot to Start/Stop trading and change ETFs.")
    
    while True:
        try:
            # Sync MockTrader symbol with Controller
            if trader.symbol != bot_controller.trading_symbol:
                logger.info(f"Switching ETF: {trader.symbol} -> {bot_controller.trading_symbol}")
                trader.symbol = bot_controller.trading_symbol
            
            if not bot_controller.is_running:
                time.sleep(1)
                continue
                
            # Trading Loop
            current_price = trader.get_price()
            buying_power, quantity, avg_price = trader.get_balance()
            
            logger.info(f"[{trader.symbol}] Price: ${current_price}, Holdings: {quantity}, Cash: ${buying_power:,.0f}")
            
            # Log holdings for dashboard
            log_holdings(trader.get_all_holdings())
            
            # Track MDD
            if quantity > 0:
                current_val = quantity * current_price
                total = buying_power + current_val
                if entry_value > 0:
                    dd = ((total - entry_value) / entry_value) * 100
                    max_drawdown = min(max_drawdown, dd)
            
            # Sell Logic
            if strategy.should_sell(current_price, avg_price, quantity):
                pnl = (current_price - avg_price) * quantity
                pnl_pct = (pnl / (avg_price * quantity)) * 100
                
                trader.sell_all(quantity)
                
                log_trade("sell", trader.symbol, quantity, current_price, 
                         pnl=pnl, pnl_pct=pnl_pct, trade_count=trade_counter, mdd_pct=max_drawdown, reason="Mock Profit")
                
                trade_counter = 0
                max_drawdown = 0
                entry_value = 0
                logger.info(f"*** SOLD {trader.symbol} - PnL: {pnl_pct:.2f}% ***")
                time.sleep(2)
                continue
                
            # Buy Logic (Mock: Buy randomly if no holdings or price drops)
            # Force a buy if we have no holdings to start the cycle
            should_buy = quantity == 0 or (current_price < avg_price * 0.95)
            
            if should_buy and bot_controller.entry_allowed:
                buy_amount = 1000000 # 1M KRW equivalent approx $1000
                if trader.buy(buy_amount):
                    log_trade("buy", trader.symbol, int(buy_amount/current_price), current_price, reason="Mock Buy")
                    
                    trade_counter += 1
                    if entry_value == 0:
                        entry_value = buying_power + (quantity * avg_price)
                    logger.info(f"*** BOUGHT {trader.symbol} ***")
            
            time.sleep(2) # Fast loop for testing
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
