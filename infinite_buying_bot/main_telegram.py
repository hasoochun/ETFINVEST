"""Main entry point for Telegram bot mode (real trader integration)"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
import yaml

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables (.env)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'telegram_bot.log'))
    ]
)
logger = logging.getLogger(__name__)

# Import internal modules after path adjustment
from telegram_bot.bot import TradingTelegramBot
from telegram_bot.notifications import TelegramNotifier
from api.bot_controller import BotController
from infinite_buying_bot.core.trader import Trader

async def main():
    """Initialize components and run the Telegram bot together with the BotController."""
    # Telegram credentials
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        logger.error('TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env')
        print('\n❌ Error: Telegram credentials missing. Add them to .env')
        return

    # Load KIS configuration (kis_devlp.yaml) – used by Trader
    # Try loading from project root
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kis_devlp.yaml')
    if not os.path.exists(config_path):
        # Fallback to config dir if not found in root
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'kis_devlp.yaml')
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            kis_config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f'Failed to load KIS config from {config_path}: {e}')
        return

    # Initialize BotController and notifier
    bot_controller = BotController()
    notifier = TelegramNotifier(bot_token, chat_id)
    bot_controller.set_notifier(notifier)

    # Initialize real Trader and attach to controller
    try:
        trader = Trader(kis_config, notifier)
        bot_controller.set_trader(trader)
    except Exception as e:
        logger.error(f'Failed to initialize Trader: {e}')
        notifier.send(f'Bot initialization error: {e}')
        return

    # Initialize Telegram bot with controller reference
    telegram_bot = TradingTelegramBot(
        token=bot_token,
        allowed_chat_ids=[chat_id],
        bot_controller=bot_controller
    )

    try:
        # Start both async components
        await telegram_bot.start()
        await bot_controller.start()
        
        # Force initial balance check to trigger debug logging
        try:
            logger.info("Forcing initial balance check for debugging...")
            trader.get_balance()
        except Exception as e:
            logger.error(f"Initial balance check failed: {e}")

        # Send startup GUI
        await telegram_bot.send_startup_message(chat_id)
        
        logger.info('✅ Bot is running. Press Ctrl+C to stop.')
        print('\n✅ Telegram Bot is running!')
        print('📱 Send /start to your bot to begin')
        print('Press Ctrl+C to stop\n')
        # Keep the process alive
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info('Shutting down...')
        print('\n⏸️ Shutting down...')
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        print(f'\n❌ Error: {e}')
    finally:
        await telegram_bot.stop()
        await bot_controller.stop()
        logger.info('Bot stopped')

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Goodbye!')
