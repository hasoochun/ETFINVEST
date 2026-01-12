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
    
    last_snapshot_time = datetime.now() - timedelta(minutes=5)  # Force initial log
    
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

            # 2. Check Market Status
            if not scheduler.is_market_open() and not is_st_scheduled_now:
                logger.info("Market is closed. Sleeping...")
                # [FIX] Update Logic status
                bot_controller.status_manager.update_logic("Sleeping", "Market is Closed", "MARKET CLOSED")
                time.sleep(60)
                continue

            # 2. Get Data
            current_price = trader.get_price(bot_controller.trading_symbol)
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
                from infinite_buying_bot.dashboard.database import log_holdings, log_holdings_history
                log_holdings(all_holdings)
                
                # Phase E: Log 5-minute snapshot
                now = datetime.now()
                if (now - last_snapshot_time).total_seconds() >= 300:  # 300 seconds = 5 minutes
                    strategy_mode = getattr(bot_controller, 'strategy_mode', 'neutral')
                    log_holdings_history(all_holdings, strategy_mode)
                    last_snapshot_time = now
                    logger.info("[Snapshot] Saved 5-minute holdings history")
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

            # 4. Buy Logic - Gradual or S-T Exchange Mode
            is_near_close = scheduler.is_near_close(minutes=5)
            
            # Get trading mode from config
            trading_mode = getattr(bot_controller, 'trading_mode', 'gradual')
            gradual_interval = getattr(bot_controller, 'gradual_interval', 5)  # Phase E: Default to 5 minutes
            
            # Check interval for gradual mode
            force_buy = False
            if trading_mode == 'gradual':
                now = datetime.now()
                last_buy = bot_controller.last_dip_buy_time
                if last_buy is None or (now - last_buy) >= timedelta(minutes=gradual_interval):
                    force_buy = True
                    logger.info(f"[GRADUAL] Mode active: {gradual_interval} minutes elapsed, buying all ETFs simultaneously")
            elif trading_mode == 'st-exchange':
                # S-T Exchange: Check if it's the scheduled time for SHV->TQQQ exchange
                daily_time = getattr(bot_controller, 'daily_time', '22:00')
                now = datetime.now()
                # Check if current time matches daily_time (within 1 minute)
                target_hour, target_minute = map(int, daily_time.split(':'))
                if now.hour == target_hour and now.minute == target_minute:
                    if not hasattr(bot_controller, 'last_st_exchange_date') or bot_controller.last_st_exchange_date != now.date():
                        force_buy = True
                        bot_controller.last_st_exchange_date = now.date()
                        logger.info(f"[S-T EXCHANGE] Scheduled time reached: {daily_time}, executing SHV->TQQQ exchange")

            
            should_buy, split_count = strategy.should_buy(current_price, avg_price, quantity, is_near_close, force_buy)
            
            if should_buy and split_count > 0 and bot_controller.entry_allowed:
                # === PORTFOLIO REBALANCING LOGIC ===
                # Get target allocations from config
                target_portfolio = bot_controller.get_target_portfolio()
                if not target_portfolio:
                    target_portfolio = {"TQQQ": 0.3, "MAGS": 0.2, "SHV": 0.3, "JEPI": 0.2}
                
                # Get current holdings
                all_holdings = trader.get_all_holdings()
                holdings_dict = {h['symbol']: h for h in all_holdings}
                
                # Calculate total portfolio value
                total_value = buying_power
                for h in all_holdings:
                    total_value += h['qty'] * h.get('current_price', h['avg_price'])
                
                # === GRADUAL MODE: Buy ALL ETFs with deficit simultaneously ===
                if trading_mode == 'gradual':
                    etfs_to_buy = []
                    for symbol, target_pct in target_portfolio.items():
                        if target_pct <= 0:
                            continue
                        
                        current_qty = holdings_dict.get(symbol, {}).get('qty', 0)
                        current_price_sym = trader.get_price(symbol)
                        if current_price_sym <= 0:
                            continue
                        
                        current_value = current_qty * current_price_sym
                        current_pct = (current_value / total_value) * 100 if total_value > 0 else 0
                        target_pct_100 = target_pct * 100 if target_pct <= 1 else target_pct
                        
                        deficit = target_pct_100 - current_pct
                        
                        if deficit > 1:  # At least 1% deficit
                            etfs_to_buy.append({
                                'symbol': symbol,
                                'price': current_price_sym,
                                'deficit': deficit
                            })
                    
                    # Buy 1 share of each ETF with deficit
                    if etfs_to_buy:
                        logger.info(f"[GRADUAL] Buying 1 share of each: {[e['symbol'] for e in etfs_to_buy]}")
                        for etf in etfs_to_buy:
                            try:
                                buy_amount = etf['price'] * 1.01  # Price + 1 cent for limit order
                                trader.buy(buy_amount, etf['symbol'])
                                log_trade("buy", etf['symbol'], 1, etf['price'], reason=f"Gradual: {etf['deficit']:.1f}% deficit")
                                logger.info(f"[GRADUAL] Bought 1 share of {etf['symbol']} @ ${etf['price']:.2f}")
                            except Exception as e:
                                logger.error(f"[GRADUAL] Failed to buy {etf['symbol']}: {e}")
                        
                        bot_controller.last_dip_buy_time = datetime.now()
                        trade_counter += len(etfs_to_buy)
                        time.sleep(60)
                    else:
                        logger.info("[GRADUAL] All ETFs at or above target allocation")
                
                # === S-T EXCHANGE MODE: Sell SHV, Buy TQQQ ===
                elif trading_mode == 'st-exchange':
                    # This is the core TQQQ infinite buying strategy
                    # Sell SHV proportionally and buy TQQQ with the proceeds
                    shv_holding = holdings_dict.get('SHV', {})
                    shv_qty = shv_holding.get('qty', 0)
                    shv_price = trader.get_price('SHV') or 110
                    
                    tqqq_price = trader.get_price('TQQQ') or 55
                    
                    # Determine how much SHV to sell based on strategy mode
                    strategy_mode = getattr(bot_controller, 'strategy_mode', 'neutral')
                    if strategy_mode == 'aggressive':
                        sell_pct = 0.10  # Sell 10% of SHV
                    elif strategy_mode == 'defensive':
                        sell_pct = 0.02  # Sell 2% of SHV
                    else:  # neutral
                        sell_pct = 0.05  # Sell 5% of SHV
                    
                    shv_to_sell = max(1, int(shv_qty * sell_pct))
                    sell_amount = shv_to_sell * shv_price
                    
                    if shv_to_sell > 0 and shv_qty >= shv_to_sell:
                        logger.info(f"[S-T EXCHANGE] Selling {shv_to_sell} SHV @ ${shv_price:.2f}")
                        trader.sell_all(shv_to_sell)  # TODO: implement sell with specific qty
                        
                        # Buy TQQQ with proceeds
                        tqqq_to_buy = int(sell_amount / tqqq_price)
                        if tqqq_to_buy > 0:
                            logger.info(f"[S-T EXCHANGE] Buying {tqqq_to_buy} TQQQ @ ${tqqq_price:.2f}")
                            trader.buy(sell_amount, 'TQQQ')
                            log_trade("buy", "TQQQ", tqqq_to_buy, tqqq_price, reason=f"S-T Exchange ({strategy_mode})")
                        
                        trade_counter += 1
                        time.sleep(60)
                    else:
                        logger.info("[S-T EXCHANGE] Not enough SHV to exchange")
                
                # Update entry value for drawdown calculation
                if entry_value == 0:
                    entry_value = buying_power + (quantity * avg_price)
            
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
