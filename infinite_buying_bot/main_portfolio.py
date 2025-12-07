import sys
import os
import time
import logging
import yaml
import asyncio
from threading import Thread
import argparse
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.utils.notifier import Notifier
from infinite_buying_bot.utils.scheduler import MarketScheduler
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.core.portfolio_manager import PortfolioManager
from infinite_buying_bot.core.rebalancing_engine import RebalancingEngine
from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.telegram_bot.bot import TradingTelegramBot
from infinite_buying_bot.dashboard.database import (
    log_trade, set_initial_capital, log_holdings
)
from infinite_buying_bot.dashboard.portfolio_db_helpers import (
    log_portfolio_snapshot, log_rebalancing_action
)

# Logging Setup
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot_portfolio.log')),
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
            await telegram_bot.send_startup_message(int(telegram_chat_id))
            logger.info("Telegram bot started and startup message sent")
            
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

def main():
    logger.info("Initializing Portfolio-Based Infinite Buying Bot...")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    # Initialize components
    notifier = Notifier(config)
    scheduler = MarketScheduler()
    
    try:
        trader = Trader(config, notifier)
    except Exception as e:
        logger.error(f"Failed to initialize Trader: {e}")
        notifier.send(f"Bot Initialization Failed: {e}")
        return
    
    # Initialize portfolio components
    initial_capital = 100000000.0  # 1억
    portfolio_manager = PortfolioManager(initial_capital)
    
    # Parse arguments first to determine mode
    parser = argparse.ArgumentParser(description='Infinite Buying Bot')
    parser.add_argument('--simulation', action='store_true', help='Run in simulation mode (1 min = 1 day)')
    parser.add_argument('--accelerated', action='store_true', help='Run in accelerated mode (10 min = 1 day, 3% profit)')
    args = parser.parse_args()
    
    # Initialize rebalancing engine
    rebalancing_engine = RebalancingEngine(portfolio_manager)
    
    # Initialize dashboard database
    set_initial_capital(initial_capital)
    logger.info("Dashboard database initialized")
    
    # Initialize bot controller
    bot_controller = BotController()
    bot_controller.set_trader(trader)
    bot_controller.set_notifier(notifier)
    
    bot_controller.portfolio_manager = portfolio_manager
    bot_controller.rebalancing_engine = rebalancing_engine
    
    # Set mode flags
    if args.simulation:
        bot_controller.is_simulation = True
        bot_controller.is_running = True # Auto-start in simulation
        bot_controller.start_time = datetime.now()
        logger.info("🧪 SIMULATION MODE ACTIVATED: 1 minute = 1 day")
        logger.info("🚀 Auto-starting bot for simulation...")
    elif args.accelerated:
        bot_controller.is_accelerated = True
        bot_controller.is_running = True # Auto-start in accelerated mode
        bot_controller.start_time = datetime.now()
        logger.info("⚡ ACCELERATED MODE ACTIVATED: 10 minutes = 1 day, 3% profit target")
        logger.info("🚀 Auto-starting bot for accelerated testing...")
    
    logger.info(f"DEBUG: BotController attributes: {dir(bot_controller)}")
    
    # Start Telegram bot in separate thread
    telegram_thread = Thread(target=start_telegram_bot, args=(bot_controller, config), daemon=True)
    telegram_thread.start()
    logger.info("Telegram bot thread started")
    
    notifier.send("Portfolio Bot Started. Waiting for user to start trading via Telegram...")
    
    # Main trading loop
    loop_count = 0
    
    while True:
        try:
            # 0. Check if trading is enabled
            if not bot_controller.is_running:
                logger.info("Trading not started. Waiting for user command...")
                time.sleep(5)
                continue
            
            # 1. Check Market Status
            if not bot_controller.is_simulation:
                if not scheduler.is_market_open():
                    logger.info("Market is closed. Sleeping...")
                    bot_controller.update_heartbeat() # Update heartbeat even when sleeping
                    time.sleep(60)
                    continue
            else:
                logger.info("🧪 Simulation Mode: Market always OPEN")

            # Update heartbeat at start of loop
            bot_controller.update_heartbeat()

            # 2. Get all prices and positions
            prices = trader.get_all_prices()
            holdings = trader.get_all_holdings()
            buying_power, _, _ = trader.get_balance()
            
            if not prices:
                logger.warning("Failed to fetch prices. Retrying...")
                time.sleep(10)
                continue
            
            logger.info(f"Prices: TQQQ=${prices.get('TQQQ', 0):.2f}, SHV=${prices.get('SHV', 0):.2f}, SCHD=${prices.get('SCHD', 0):.2f}")
            logger.info(f"Cash: ${buying_power:,.2f}")
            
            # 3. Update portfolio manager
            positions = {}
            for holding in holdings:
                symbol = holding['symbol']
                positions[symbol] = {
                    'quantity': holding['qty'],
                    'avg_price': holding['avg_price'],
                    'current_price': holding['current_price']
                }
            
            # Fill in missing positions
            for symbol in ['TQQQ', 'SHV', 'SCHD']:
                if symbol not in positions:
                    positions[symbol] = {
                        'quantity': 0,
                        'avg_price': 0.0,
                        'current_price': prices.get(symbol, 0.0)
                    }
                else:
                    # Update current price
                    positions[symbol]['current_price'] = prices.get(symbol, positions[symbol]['current_price'])
            
            portfolio_manager.update_positions(positions)
            portfolio_manager.update_cash(buying_power)
            
            # 4. Log holdings to database for dashboard
            try:
                log_holdings(holdings)
            except Exception as e:
                logger.error(f"Failed to log holdings: {e}")
            
            # 5. Log portfolio snapshot every 10 loops (reduce DB writes)
            loop_count += 1
            if loop_count % 10 == 0:
                try:
                    portfolio_summary = portfolio_manager.get_portfolio_summary()
                    log_portfolio_snapshot(portfolio_summary)
                    logger.info(f"Portfolio snapshot logged. Total value: ${portfolio_summary['total_value']:,.2f}")
                except Exception as e:
                    logger.error(f"Failed to log portfolio snapshot: {e}")
            
            # 6. Check for rebalancing actions
            if bot_controller.entry_allowed:
                actions = rebalancing_engine.get_rebalancing_actions()
                
                if actions:
                    logger.info(f"🔄 Rebalancing actions detected: {len(actions)}")
                    
                    for action in actions:
                        try:
                            logger.info(f"Executing action: {action['action']} - {action.get('reason', '')}")
                            
                            # Execute the action
                            success = rebalancing_engine.execute_action(action, trader)
                            
                            if success:
                                # Log to database
                                log_rebalancing_action(action)
                                
                                # Log individual trades
                                if action['action'] == 'profit_taking':
                                    log_trade(
                                        "sell",
                                        action['sell_symbol'],
                                        action['sell_quantity'],
                                        prices[action['sell_symbol']],
                                        pnl=action['profit_amount'],
                                        pnl_pct=action['profit_pct'],
                                        reason=action['reason']
                                    )
                                    log_trade(
                                        "buy",
                                        action['buy_symbol'],
                                        0,  # Will be filled by actual execution
                                        prices[action['buy_symbol']],
                                        reason=f"Reinvest from {action['sell_symbol']}"
                                    )
                                
                                elif action['action'] == 'dip_buying':
                                    log_trade(
                                        "buy",
                                        action['buy_symbol'],
                                        0,  # Will be filled by actual execution
                                        prices[action['buy_symbol']],
                                        reason=action['reason']
                                    )
                                
                                logger.info(f"✅ Action executed successfully: {action['action']}")
                            else:
                                logger.error(f"❌ Failed to execute action: {action['action']}")
                        
                        except Exception as e:
                            logger.error(f"Error executing action {action['action']}: {e}")
                            notifier.send(f"⚠️ Rebalancing error: {e}")
                    
                    # Sleep after rebalancing
                    time.sleep(60)
                else:
                    logger.debug("No rebalancing actions needed")
            
            # 7. Sleep before next iteration
            if bot_controller.is_simulation:
                logger.info("🧪 Simulation: Sleeping for 60s (representing 1 day)...")
                time.sleep(60)
            elif bot_controller.is_accelerated:
                logger.info("⚡ Accelerated: Sleeping for 600s (representing 1 day)...")
                time.sleep(600)
            else:
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
