from telegram.ext import CommandHandler, CallbackQueryHandler
from infinite_buying_bot.telegram_bot.formatters.portfolio_messages import format_status, format_balance

def setup_handlers(app, bot_controller):
    """Register command handlers"""
    app.add_handler(CommandHandler("start", lambda u, c: start(u, c, bot_controller)))
    app.add_handler(CommandHandler("status", lambda u, c: status(u, c, bot_controller)))
    app.add_handler(CommandHandler("balance", lambda u, c: balance(u, c, bot_controller)))
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_callback(u, c, bot_controller)))

async def start(update, context, controller):
    await update.message.reply_text("🤖 **[LOCAL-PC-VERIFIED]** Bot Started\nUse /status or /balance")
    controller.start_bot()

async def status(update, context, controller):
    status_data = controller.get_status()
    await update.message.reply_text(format_status(status_data), parse_mode='Markdown')

async def balance(update, context, controller):
    bal = controller.get_balance()
    await update.message.reply_text(format_balance(bal), parse_mode='Markdown')

async def handle_callback(update, context, controller):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_trading':
        controller.start_bot()
        await query.edit_message_text("✅ Trading Started")
    elif query.data == 'stop_trading':
        controller.stop_bot()
        await query.edit_message_text("adb Bot Stopped")
    elif query.data == 'balance':
        bal = controller.get_balance()
        await query.edit_message_text(format_balance(bal), parse_mode='Markdown')
