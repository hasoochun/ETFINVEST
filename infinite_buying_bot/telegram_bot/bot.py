"""Main Telegram Bot class"""

import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from .handlers import status, trading, callbacks
from .security import SecurityManager

logger = logging.getLogger(__name__)

class TradingTelegramBot:
    """Main Telegram bot for trading control and monitoring"""
    
    def __init__(self, token: str, allowed_chat_ids: list, bot_controller):
        """
        Initialize Telegram bot
        
        Args:
            token: Telegram bot token
            allowed_chat_ids: List of authorized chat IDs
            bot_controller: Bot controller instance
        """
        self.token = token
        self.security = SecurityManager(allowed_chat_ids)
        self.bot_controller = bot_controller
        self.application = None
        logger.info("Trading Telegram Bot initialized")
    
    def setup_handlers(self):
        """Register all command and callback handlers"""
        app = self.application
        
        # Store bot controller in bot_data for handlers to access
        app.bot_data['controller'] = self.bot_controller
        
        # Basic commands
        app.add_handler(CommandHandler("start", status.start_command))
        app.add_handler(CommandHandler("help", status.help_command))
        app.add_handler(CommandHandler("ping", status.ping_command))
        
        # Status commands
        app.add_handler(CommandHandler("status", status.status_command))
        app.add_handler(CommandHandler("balance", status.balance_command))
        app.add_handler(CommandHandler("position", status.position_command))
        app.add_handler(CommandHandler("pnl", status.pnl_command))
        
        # Trading control commands
        app.add_handler(CommandHandler("stopentry", trading.stop_entry_command))
        app.add_handler(CommandHandler("forceexit", trading.force_exit_command))
        app.add_handler(CommandHandler("emergency", trading.emergency_command))
        
        # Callback query handler for inline buttons
        app.add_handler(CallbackQueryHandler(callbacks.button_callback))
        
        logger.info("All handlers registered")
    
    async def start(self):
        """Start the Telegram bot"""
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot started successfully")
    
    async def stop(self):
        """Stop the Telegram bot"""
        if self.application:
            logger.info("Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped")

    async def send_startup_message(self, chat_id):
        """Send startup status message with GUI"""
        from .formatters import messages, keyboards
        
        # Get status from controller
        status_data = self.bot_controller.get_status()
        text = messages.format_status(status_data)
        keyboard = keyboards.get_status_keyboard()
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            logger.info(f"Startup GUI sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send startup GUI: {e}")
