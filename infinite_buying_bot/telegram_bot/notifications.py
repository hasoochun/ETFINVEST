"""Telegram notification system"""

import asyncio
import logging
from telegram import Bot
from typing import Dict
from infinite_buying_bot.telegram_bot.formatters.messages import (
    format_trade_notification,
    format_profit_target_notification,
    format_error_notification
)

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Handles sending notifications via Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        logger.info(f"Telegram notifier initialized for chat_id: {chat_id}")
    
    async def send_message(self, message: str, parse_mode: str = 'HTML'):
        """
        Send a message to Telegram
        
        Args:
            message: Message text to send
            parse_mode: Parse mode ('HTML' or 'Markdown')
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("Telegram message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def send_trade_notification(self, trade_type: str, data: Dict):
        """
        Send trade execution notification
        
        Args:
            trade_type: 'BUY' or 'SELL'
            data: Trade data dictionary
        """
        message = format_trade_notification(trade_type, data)
        await self.send_message(message)
    
    async def send_profit_target_notification(self, data: Dict):
        """
        Send profit target reached notification
        
        Args:
            data: Profit data dictionary
        """
        message = format_profit_target_notification(data)
        await self.send_message(message)
    
    async def send_error_notification(self, error: str):
        """
        Send error notification
        
        Args:
            error: Error message
        """
        message = format_error_notification(error)
        await self.send_message(message)
    
    async def send_bot_started(self):
        """Send bot started notification"""
        message = (
            "🚀 <b>Bot Started</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Trading bot is now running.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send_message(message)
    
    async def send_bot_stopped(self):
        """Send bot stopped notification"""
        message = (
            "⏸️ <b>Bot Stopped</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Trading bot has been stopped.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send_message(message)
    
    async def send_market_open(self):
        """Send market open notification"""
        message = (
            "🟢 <b>Market Opened</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Market is now open for trading.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send_message(message)
    
    async def send_market_closed(self):
        """Send market closed notification"""
        message = (
            "🔴 <b>Market Closed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Market has closed.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send_message(message)
    
    def send(self, message: str):
        """
        Synchronous wrapper for sending messages (compatible with Trader)
        
        Args:
            message: Message to send
        """
        try:
            # Try to get existing event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    asyncio.create_task(self.send_message(message))
                else:
                    # If loop exists but not running, use it
                    loop.run_until_complete(self.send_message(message))
            except RuntimeError:
                # No event loop, create new one
                asyncio.run(self.send_message(message))
        except Exception as e:
            logger.error(f"Failed to send sync message: {e}")
    
    def send_sync(self, message: str):
        """Alias for send() for backward compatibility"""
        self.send(message)
