"""Status command handlers for Telegram bot"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from ..formatters.messages import format_status, format_balance, format_position
from ..formatters.keyboards import get_status_keyboard

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_msg = (
        "🤖 <b>Welcome to Trading Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "I'm your trading assistant!\n\n"
        "Available commands:\n"
        "/status - Bot status\n"
        "/balance - Account balance\n"
        "/position - Current position\n"
        "/help - Show all commands\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(welcome_msg, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_msg = (
        "📚 <b>Available Commands</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Status Commands:</b>\n"
        "/status - Bot status\n"
        "/balance - Account balance\n"
        "/position - Current position\n"
        "/pnl - Profit &amp; Loss\n\n"
        "<b>Control Commands:</b>\n"
        "/stopentry - Stop new entries\n"
        "/forceexit - Force exit all\n"
        "/emergency - Emergency stop\n\n"
        "<b>Info Commands:</b>\n"
        "/help - This message\n"
        "/ping - Check bot response\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(help_msg, parse_mode='HTML')

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command"""
    await update.message.reply_text("🏓 Pong! Bot is alive.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        # Get bot controller from context
        bot_controller = context.bot_data.get('controller')
        
        if not bot_controller:
            await update.message.reply_text("❌ Bot controller not initialized")
            return
        
        # Get current status
        status_data = bot_controller.get_status()
        
        # Format message
        message = format_status(status_data)
        keyboard = get_status_keyboard()
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    try:
        bot_controller = context.bot_data.get('controller')
        
        if not bot_controller:
            await update.message.reply_text("❌ Bot controller not initialized")
            return
        
        balance_data = bot_controller.get_balance()
        message = format_balance(balance_data)
        
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in balance_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def position_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /position command"""
    try:
        bot_controller = context.bot_data.get('controller')
        
        if not bot_controller:
            await update.message.reply_text("❌ Bot controller not initialized")
            return
        
        position_data = bot_controller.get_position()
        message = format_position(position_data)
        
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in position_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pnl command"""
    try:
        bot_controller = context.bot_data.get('controller')
        
        if not bot_controller:
            await update.message.reply_text("❌ Bot controller not initialized")
            return
        
        pnl_data = bot_controller.get_pnl()
        
        pnl = pnl_data.get('pnl', 0)
        pnl_pct = pnl_data.get('pnl_pct', 0)
        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        pnl_sign = "+" if pnl >= 0 else ""
        
        message = (
            f"💹 <b>Profit &amp; Loss</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Total P&amp;L:   <code>{pnl_icon} {pnl_sign}${pnl:,.2f}</code>\n"
            f"Return:      <code>{pnl_sign}{pnl_pct:.2f}%</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Today:       <code>{pnl_sign}${pnl_data.get('today_pnl', 0):.2f}</code>\n"
            f"This Week:   <code>{pnl_sign}${pnl_data.get('week_pnl', 0):.2f}</code>\n"
            f"This Month:  <code>{pnl_sign}${pnl_data.get('month_pnl', 0):.2f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in pnl_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
