"""Trading control command handlers"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from ..formatters.keyboards import get_confirmation_keyboard

logger = logging.getLogger(__name__)

async def stop_entry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopentry command - stop new entries"""
    try:
        bot_controller = context.bot_data.get('controller')
        
        if not bot_controller:
            await update.message.reply_text("❌ Bot controller not initialized")
            return
        
        bot_controller.stop_entry()
        
        message = (
            "🚫 <b>Entry Stopped</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Bot will not enter new positions.\n"
            "Existing positions will be maintained.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in stop_entry_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def force_exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /forceexit command - force exit all positions"""
    try:
        # Ask for confirmation
        message = (
            "⚠️ <b>Force Exit Confirmation</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "This will sell ALL positions immediately.\n"
            "Are you sure?\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = get_confirmation_keyboard('force_exit')
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in force_exit_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def emergency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /emergency command - emergency stop"""
    try:
        # Ask for confirmation
        message = (
            "🚨 <b>EMERGENCY STOP</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "This will:\n"
            "• Stop the bot immediately\n"
            "• Sell ALL positions\n"
            "• Require manual restart\n\n"
            "⚠️ Are you absolutely sure?\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = get_confirmation_keyboard('emergency')
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in emergency_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
