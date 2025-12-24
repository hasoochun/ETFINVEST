import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

class TradingTelegramBot:
    def __init__(self, token, allowed_chat_ids, bot_controller):
        self.token = token
        self.allowed_chat_ids = allowed_chat_ids
        self.controller = bot_controller
        self.app = None
        
    async def start(self):
        """Start the bot polling"""
        try:
            self.app = ApplicationBuilder().token(self.token).build()
            
            # Handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("stop", self.cmd_stop))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("balance", self.cmd_balance))
            
            # Start polling
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("Telegram Bot polling started")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram Bot: {e}")

    async def send_startup_message(self, chat_id):
        if self.app:
            await self.app.bot.send_message(chat_id=chat_id, text="[Trading Bot Started]\nReady to accept commands.")

    async def _check_auth(self, update: Update):
        if update.effective_chat.id not in self.allowed_chat_ids:
            await update.message.reply_text("[!] Unauthorized access.")
            return False
        return True

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        self.controller.start_bot()
        await update.message.reply_text("[!] **Trading Started**")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        self.controller.stop_bot()
        await update.message.reply_text("[!] **Trading Stopped** (Paused)")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        status = self.controller.get_status()
        msg = f"[STATUS: {status['status']}]\n"
        msg += f"Symbol: {status['trading_symbol']}\n"
        msg += f"Mode: {status['mode']}\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        bal = self.controller.get_balance()
        msg = f"[Balance]\n"
        msg += f"Cash: ${bal['cash']:,.2f}\n"
        msg += f"Stock: ${bal['stock_val']:,.2f}\n"
        msg += f"Total: ${bal['total']:,.2f}"
        await update.message.reply_text(msg, parse_mode='Markdown')

