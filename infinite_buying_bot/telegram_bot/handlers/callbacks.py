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
            try:
                balance_data = bot_controller.get_balance()
                if getattr(bot_controller, 'trader', None):
                    balance_data['price_sources'] = getattr(bot_controller.trader, 'price_source', {})
                message = format_balance(balance_data)
            except Exception as e:
                logger.error(f"Error getting balance: {e}")
                message = (
                    "💰 <b>잔고 조회 오류</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "잔고 정보를 가져오는 중 오류가 발생했습니다.\n"
                    f"오류: {str(e)}\n\n"
                    "잠시 후 다시 시도해주세요.\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'show_position':
            position_data = bot_controller.get_position()
            
            # Check if position exists
            if position_data is None:
                message = (
                    "📊 <b>포지션</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "현재 보유 중인 포지션이 없습니다.\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
            else:
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
                # Get portfolio summary for allocation display
                portfolio_summary = None
                if getattr(bot_controller, 'portfolio_manager', None):
                    portfolio_summary = bot_controller.portfolio_manager.get_portfolio_summary()
                message = format_rebalancing_plan(actions, portfolio_summary)
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
            # Send detailed strategy explanation
            strategy_explanation = (
                "🚀 <b>자동 매매 전략 상세 안내</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>⏰ 가격 체크 방식:</b>\n"
                "• <b>실시간 현재가 기준</b> (캔들 차트 X)\n"
                "• 5분마다 현재 시장가 조회\n"
                "• KIS API → 실패 시 Yahoo Finance\n\n"
                "<b>📊 포트폴리오 구성:</b>\n"
                "• TQQQ 30% (나스닥 3배 레버리지)\n"
                "• SHV 50% (안전자산 + 매수자금)\n"
                "• SCHD 20% (배당 성장)\n\n"
                "<b>🎯 매매 규칙 (우선순위 순):</b>\n\n"
                "<b>1. 수익 실현 (최우선)</b>\n"
                "   조건: TQQQ 현재가 ≥ 평균가 × 1.10\n"
                "   실행: TQQQ 전량 매도 → SCHD 재투자\n"
                "   예시: 평균가 $50 → $55 도달 시 전량 매도\n\n"
                "<b>2. 물타기 (40/80 분할)</b>\n"
                "   <u>평균가 미만 (공격적)</u>\n"
                "   • SHV 총액의 1/40 금액으로 매수\n"
                "   • 예: SHV $100,000 → $2,500 매수\n\n"
                "   <u>평균가 이상 (보수적)</u>\n"
                "   • SHV 총액의 1/80 금액으로 매수\n"
                "   • 예: SHV $100,000 → $1,250 매수\n\n"
                "<b>3. 리밸런싱</b>\n"
                "   조건: 비중이 목표에서 ±10% 벗어남\n"
                "   실행: 목표 비중으로 자동 조정\n\n"
                "<b>🕐 작동 시간:</b>\n"
                "• 미국 장중: 월~금 23:30~06:00 (KST)\n"
                "• 체크 주기: 5분마다\n"
                "• 장 마감 시: 대기 상태\n\n"
                "<b>✅ 이제 자동 매매를 시작합니다!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=strategy_explanation,
                parse_mode='HTML'
            )
            
            # Start trading
            await bot_controller.start()
            message = (
                "✅ <b>매매 시작</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "자동매매가 활성화되었습니다.\n"
                "5분마다 실시간 가격을 체크합니다.\n"
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
            
            # Update bot controller
            bot_controller.trading_symbol = etf_symbol
            
            # Reinitialize portfolio manager with new ETF
            if bot_controller.portfolio_manager:
                from infinite_buying_bot.core.portfolio_manager import PortfolioManager
                from infinite_buying_bot.core.rebalancing_engine import RebalancingEngine
                
                bot_controller.portfolio_manager = PortfolioManager(
                    initial_capital=bot_controller.portfolio_manager.initial_capital,
                    aggressive_etf=etf_symbol
                )
                
                # Reinitialize rebalancing engine
                bot_controller.rebalancing_engine = RebalancingEngine(
                    bot_controller.portfolio_manager,
                    accelerated=bot_controller.is_accelerated
                )
            
            etf_names = {
                'TQQQ': '나스닥 3배 레버리지',
                'MAGS': 'M7 전용 ETF',
                'QQQ': '나스닥 100',
                'SPY': 'S&P 500',
                'VOO': 'S&P 500 저비용'
            }
            
            message = (
                f"✅ <b>ETF 변경 완료</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"선택된 ETF: <b>{etf_symbol}</b>\n"
                f"({etf_names.get(etf_symbol, 'Unknown')})\n\n"
                f"<b>📊 포트폴리오 구성:</b>\n"
                f"• {etf_symbol} 30% (단기 매매)\n"
                f"• SHV 50% (안전 자산)\n"
                f"• SCHD 20% (장기 보유)\n\n"
                f"<b>🎯 매매 전략:</b>\n"
                f"• {etf_symbol} +10% 도달 → 전량 매도 → SCHD 재투자\n"
                f"• {etf_symbol} 하락 시 → SHV로 물타기 (40/80 분할)\n"
                f"• 비중 ±10% 벗어나면 자동 리밸런싱\n\n"
                f"다음 리밸런싱부터 적용됩니다.\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(message, parse_mode='HTML')
            await _send_status_gui(context, query.message.chat_id, bot_controller)
        
        elif query.data == 'show_dip_mode':
            # Show dip buy mode selection
            current_mode = bot_controller.dip_buy_mode
            if current_mode == 'daily':
                mode_text = "📅 일일 모드 (장종료 5분전)"
                description = "하루 1회, 장 마감 5분 전에 매수합니다."
            else:
                mode_text = "🏃 가속 모드 (10분마다)"
                description = "10분마다 매수 조건을 확인합니다."
            
            message = (
                f"⚙️ <b>매수 모드 설정</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"현재 모드: {mode_text}\n"
                f"\n"
                f"{description}\n"
                f"\n"
                f"<b>모드 설명:</b>\n"
                f"📅 일일 모드:\n"
                f"  • 시간: 15:55-16:00 ET\n"
                f"  • 주기: 하루 1회\n"
                f"  • 용도: 실전 운용\n"
                f"\n"
                f"🏃 가속 모드:\n"
                f"  • 시간: 10분마다\n"
                f"  • 주기: 10분 간격\n"
                f"  • 용도: 빠른 테스트\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            
            from ..formatters.keyboards import get_dip_mode_keyboard
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode='HTML',
                reply_markup=get_dip_mode_keyboard()
            )
        
        elif query.data.startswith('set_dip_mode_'):
            # Change dip buy mode
            mode = query.data.replace('set_dip_mode_', '')
            bot_controller.set_dip_buy_mode(mode)
            
            if mode == 'daily':
                mode_text = "📅 일일 모드"
            else:
                mode_text = "🏃 가속 모드"
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ 매수 모드 변경: {mode_text}",
                parse_mode='HTML'
            )
            
            # Show updated status
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

