"""Callback query handlers for inline buttons"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from ..formatters.messages import format_status, format_balance, format_position
from ..formatters.keyboards import get_status_keyboard, get_etf_selection_keyboard
try:
    from ..formatters.portfolio_messages import format_portfolio, format_rebalancing_plan
except ImportError:
    # Fallback if portfolio_messages not available
    def format_portfolio(data):
        return "📊 Portfolio view coming soon..."
    def format_rebalancing_plan(data):
        return "⚖️ Rebalancing view coming soon..."

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    bot_controller = context.bot_data.get('controller')
    
    if not bot_controller:
        await query.edit_message_text("❌ Bot controller not initialized")
        return
    
    try:
        # Handle different callback data
        if query.data == 'refresh_status':
            status_data = bot_controller.get_status()
            message = format_status(status_data)
            keyboard = get_status_keyboard()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        elif query.data == 'show_balance':
            balance_data = bot_controller.get_balance()
            if getattr(bot_controller, 'trader', None):
                balance_data['price_sources'] = getattr(bot_controller.trader, 'price_source', {})
            message = format_balance(balance_data)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'show_position':
            position_data = bot_controller.get_position()
            # Inject source info
            if getattr(bot_controller, 'trader', None):
                symbol = position_data.get('symbol')
                if symbol:
                    position_data['price_source'] = getattr(bot_controller.trader, 'price_source', {}).get(symbol, 'KIS')
            
            message = format_position(position_data)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await _send_status_gui(context, query.message.chat_id, bot_controller)

        elif query.data == 'show_portfolio':
            logger.info(f"DEBUG: Checking portfolio_manager in bot_controller. Dir: {dir(bot_controller)}")
            if bot_controller.portfolio_manager and bot_controller.trader:
                # Fetch fresh prices for all symbols
                print("DEBUG: Fetching fresh prices for portfolio display...")
                prices = bot_controller.trader.get_all_prices()
                print(f"DEBUG: Fetched prices: {prices}")
                
                # Update portfolio manager with fresh prices
                for symbol in ['TQQQ', 'SHV', 'SCHD']:
                    if symbol in prices:
                        current_pos = bot_controller.portfolio_manager.positions.get(symbol, {})
                        current_pos['current_price'] = prices[symbol]
                
                summary = bot_controller.portfolio_manager.get_portfolio_summary()
                summary['price_sources'] = getattr(bot_controller.trader, 'price_source', {})
                message = format_portfolio(summary)
            else:
                logger.error("DEBUG: portfolio_manager is None or missing")
                message = (
                    "💼 <b>포트폴리오</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "포트폴리오 기능이 활성화되지 않았습니다.\n"
                    "<code>main_portfolio.py</code>를 실행해주세요.\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'show_chart':
            message = "📊 Chart feature coming soon..."
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'show_rebalance':
            # Get rebalancing actions from bot controller
            if getattr(bot_controller, 'rebalancing_engine', None):
                actions = bot_controller.rebalancing_engine.get_rebalancing_actions()
                message = format_rebalancing_plan(actions)
            else:
                message = (
                    "⚖️ <b>리밸런싱</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "리밸런싱 기능이 활성화되지 않았습니다.\n"
                    "<code>main_portfolio.py</code>를 실행해주세요.\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'confirm_force_exit':
            bot_controller.force_exit_all()
            message = (
                "💸 <b>Force Exit Executed</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "All positions have been sold.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(message, parse_mode='HTML')
        
        elif query.data == 'confirm_emergency':
            bot_controller.emergency_stop()
            message = (
                "🚨 <b>EMERGENCY STOP ACTIVATED</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Bot stopped.\n"
                "All positions sold.\n"
                "Manual restart required.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(message, parse_mode='HTML')
        
        elif query.data == 'start_bot':
            await bot_controller.start()
            message = (
                "✅ <b>매매 시작</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "자동매매가 활성화되었습니다.\n"
                "시장 개장 시 전략에 따라 거래를 시작합니다.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(message, parse_mode='HTML')
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'stop_bot':
            await bot_controller.stop()
            message = (
                "⏸️ <b>매매 중지</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "자동매매가 일시중지되었습니다.\n"
                "현재 포지션은 유지됩니다.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(message, parse_mode='HTML')
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'show_etf_selection':
            current_etf = bot_controller.trading_symbol if hasattr(bot_controller, 'trading_symbol') else 'SOXL'
            message = (
                f"🎯 <b>ETF 선택</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"현재 선택: <b>{current_etf}</b>\n\n"
                f"거래할 ETF를 선택하세요:\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            keyboard = get_etf_selection_keyboard()
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=keyboard)
        
        elif query.data.startswith('select_etf_'):
            etf_symbol = query.data.split('_')[-1]
            bot_controller.trading_symbol = etf_symbol
            
            etf_names = {
                'TQQQ': '나스닥 3x 레버리지',
                'SHV': '단기 국채 ETF',
                'SCHD': '고배당 성장 ETF'
            }
            
            message = (
                f"✅ <b>ETF 변경 완료</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"선택된 ETF: <b>{etf_symbol}</b>\n"
                f"({etf_names.get(etf_symbol, 'Unknown')})\n\n"
                f"다음 거래부터 적용됩니다.\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(message, parse_mode='HTML')
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'back_to_status':
            status_data = bot_controller.get_status()
            message = format_status(status_data)
            keyboard = get_status_keyboard()
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=keyboard)
        
        elif query.data == 'cancel':
            await query.edit_message_text("❌ Action cancelled.")
        
        else:
            await query.edit_message_text(f"Unknown action: {query.data}")
    
    except Exception as e:
        error_msg = str(e)
        if "Message is not modified" in error_msg:
            return
            
        import traceback
        logger.error(f"Error in button_callback: {e}\n{traceback.format_exc()}")
        try:
            await query.edit_message_text(f"❌ Error: {error_msg}")
        except Exception:
            pass

async def _send_status_gui(context: ContextTypes.DEFAULT_TYPE, chat_id: int, bot_controller):
    """Helper to send status GUI at the bottom"""
    status_data = bot_controller.get_status()
    message = format_status(status_data)
    keyboard = get_status_keyboard()
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Failed to resend status GUI: {e}")

