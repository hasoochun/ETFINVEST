"""
Complete Telegram Bot with Full 8-Button UI (REAL TRADING ONLY)
디버깅 강화 버전 - Paper/Mock 모드 없음, 모든 오류 즉시 로깅
버튼 기능 정확히 구현: 포트폴리오=목표비중비교, 포지션=현재보유현황
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

# 포트폴리오 목표 비중 설정
TARGET_ALLOCATION = {
    'TQQQ': 0.10,   # 10% - 3배 레버리지 공격적
    'MAGS': 0.20,   # 20% - Magnificent 7
    'SHV': 0.50,    # 50% - 안전자산 + 물타기 자금
    'JEPI': 0.20,   # 20% - 커버드콜 인컴
}

# 매수 순서 (안전자산 먼저)
BUY_ORDER = ['SHV', 'JEPI', 'MAGS', 'TQQQ']


class RealTradingUI:
    """Full UI restoration - NO PAPER TRADING, 정확한 버튼 기능 구현"""
    
    def __init__(self, config: Dict, trader):
        # 필수 설정 검증
        if 'telegram_token' not in config:
            raise ValueError("[UI ERROR] Missing telegram_token")
        if 'telegram_chat_id' not in config:
            raise ValueError("[UI ERROR] Missing telegram_chat_id")
        
        self.token = config['telegram_token']
        self.chat_id = config['telegram_chat_id']
        self.trader = trader
        
        # 상태 변수
        self.selected_symbol = "TQQQ"
        self.is_running = False
        self.dip_buy_mode = "daily"  # 'daily', 'accelerated', 'accel_test'
        self.app = None
        self.last_update = datetime.now()
        self.pending_monitor_task = None  # 백그라운드 모니터링 태스크
        
        logger.info(f"[UI] Initialized - Chat ID: {self.chat_id}")
        
    def get_main_keyboard(self) -> InlineKeyboardMarkup:
        """8버튼 메인 키보드 (Legacy UI 일치)"""
        keyboard = [
            [
                InlineKeyboardButton("▶️ 매매 시작", callback_data='start_bot'),
                InlineKeyboardButton("⏸️ 매매 중지", callback_data='stop_bot')
            ],
            [
                InlineKeyboardButton("📊 포트폴리오", callback_data='show_portfolio'),
                InlineKeyboardButton("⚖️ 리밸런싱", callback_data='show_rebalance')
            ],
            [
                InlineKeyboardButton("🎯 ETF 선택", callback_data='show_etf_selection'),
                InlineKeyboardButton("⚙️ 매수 모드", callback_data='show_dip_mode')
            ],
            [
                InlineKeyboardButton("💰 잔고", callback_data='show_balance'),
                InlineKeyboardButton("📈 포지션", callback_data='show_position')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_mode_keyboard(self) -> InlineKeyboardMarkup:
        """매수 모드 선택 메뉴"""
        keyboard = [
            [InlineKeyboardButton("📅 Daily (15:55 ET)", callback_data='mode_daily')],
            [InlineKeyboardButton("🚀 Accelerated (10분)", callback_data='mode_accelerated')],
            [InlineKeyboardButton("⚡ Accel Test (5분)", callback_data='mode_accel_test')],
            [InlineKeyboardButton("◀️ 뒤로", callback_data='back_to_status')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_etf_keyboard(self) -> InlineKeyboardMarkup:
        """ETF 선택 서브메뉴"""
        keyboard = [
            [InlineKeyboardButton("📈 TQQQ (나스닥 3x)", callback_data='select_etf_TQQQ')],
            [InlineKeyboardButton("🌟 SOXL (반도체 3x)", callback_data='select_etf_SOXL')],
            [InlineKeyboardButton("💎 QQQ (나스닥 100)", callback_data='select_etf_QQQ')],
            [InlineKeyboardButton("🏛️ SPY (S&P 500)", callback_data='select_etf_SPY')],
            [InlineKeyboardButton("◀️ 뒤로", callback_data='back_to_status')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_init_keyboard(self) -> InlineKeyboardMarkup:
        """초기화 확인 키보드"""
        keyboard = [
            [
                InlineKeyboardButton("✅ 초기화 시작", callback_data='confirm_init'),
                InlineKeyboardButton("❌ 취소", callback_data='back_to_status')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"[CMD] /start from user {update.effective_user.id}")
        status_msg = self._get_status_message()
        await update.message.reply_text(
            status_msg,
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard()
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks - 메시지 전환 오류 처리 포함"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        logger.info(f"[CALLBACK] Button: {data}")
        
        try:
            # Main Actions
            if data == 'start_bot':
                await self._handle_start_trading(query)
            elif data == 'stop_bot':
                await self._handle_stop_trading(query)
            elif data == 'show_portfolio':
                await self._handle_portfolio(query)
            elif data == 'show_rebalance':
                await self._handle_rebalance(query)
            elif data == 'show_etf_selection':
                await self._handle_etf_menu(query)
            elif data == 'show_dip_mode':
                await self._handle_dip_mode(query)
            elif data == 'show_balance':
                await self._handle_balance(query)
            elif data == 'show_position':
                await self._handle_position(query)
            elif data == 'back_to_status':
                await self._handle_back_to_status(query)
            # ETF Selection
            elif data.startswith('select_etf_'):
                symbol = data.replace('select_etf_', '')
                await self._handle_etf_select(query, symbol)
            # Mode Selection
            elif data.startswith('mode_'):
                mode = data.replace('mode_', '')
                await self._handle_mode_select(query, mode)
            # Initialization
            elif data == 'confirm_init':
                await self._execute_initialization(query)
            else:
                logger.warning(f"[CALLBACK] Unknown: {data}")
                
        except Exception as e:
            logger.error(f"[CALLBACK ERROR] {data}: {str(e)}", exc_info=True)
            await self._safe_send(query, f"❌ <b>오류 발생</b>\n<code>{str(e)[:200]}</code>")
    
    async def _safe_send(self, query, text: str, keyboard=None):
        """메시지 전환 오류 방지 - 새 메시지로 전송"""
        if keyboard is None:
            keyboard = self.get_main_keyboard()
        
        try:
            # 먼저 수정 시도
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                # 같은 내용이면 새 메시지로 전송
                logger.debug("[SAFE_SEND] Same content, sending new message")
                await query.message.reply_text(
                    text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                raise
    
    def _get_status_message(self) -> str:
        """상태 메시지 생성"""
        status = "🟢 RUNNING" if self.is_running else "🟡 STOPPED"
        mode_icons = {'daily': '📅', 'accelerated': '🚀', 'accel_test': '⚡'}
        mode_icon = mode_icons.get(self.dip_buy_mode, '📅')
        
        elapsed = (datetime.now() - self.last_update).total_seconds()
        
        return (
            f"🤖 <b>봇 상태</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"상태: {status}\n"
            f"종목: 🎯 {self.selected_symbol}\n"
            f"모드: {mode_icon} {self.dip_buy_mode.upper()}\n"
            f"시장: 🔴 <b>REAL TRADING</b>\n"
            f"업데이트: {int(elapsed)}초 전\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    
    def _needs_initialization(self) -> tuple[bool, Dict]:
        """초기화 필요 여부 확인"""
        logger.info("[INIT CHECK] Checking positions...")
        
        try:
            positions = self.trader.get_all_positions()
            logger.info(f"[INIT CHECK] Positions: {list(positions.keys())}")
            
            for symbol in BUY_ORDER:
                if symbol not in positions or positions[symbol]['quantity'] == 0:
                    logger.info(f"[INIT CHECK] Missing: {symbol}")
                    return True, positions
            
            return False, positions
            
        except Exception as e:
            logger.error(f"[INIT CHECK ERROR] {str(e)}")
            raise
    
    async def _handle_start_trading(self, query):
        """매매 시작 - 초기화 체크 포함"""
        logger.info("[START] Requested")
        
        try:
            needs_init, positions = self._needs_initialization()
            
            if needs_init:
                await self._show_initialization_prompt(query)
                return
            
            self.is_running = True
            self.last_update = datetime.now()
            
            msg = (
                "▶️ <b>매매 시작</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"모드: {self.dip_buy_mode.upper()}\n"
                f"보유: {len(positions)}종목\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await self._safe_send(query, msg)
            
        except Exception as e:
            logger.error(f"[START ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _show_initialization_prompt(self, query):
        """초기화 프롬프트"""
        logger.info("[INIT PROMPT] Showing")
        
        try:
            cash, _, _ = self.trader.get_balance()
            logger.info(f"[INIT PROMPT] Cash: ${cash:,.2f}")
            
            lines = []
            for symbol in BUY_ORDER:
                ratio = TARGET_ALLOCATION[symbol]
                amount = cash * ratio
                lines.append(f"• {symbol} {int(ratio*100)}%: <code>${amount:,.0f}</code>")
            
            msg = (
                "📊 <b>포트폴리오 초기화 필요</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"현재 현금: <code>${cash:,.2f}</code>\n\n"
                "💡 <b>목표 포트폴리오</b>\n"
                + "\n".join(lines) + "\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ 순차 매수: SHV → JEPI → MAGS → TQQQ"
            )
            
            await self._safe_send(query, msg, self.get_init_keyboard())
            
        except Exception as e:
            logger.error(f"[INIT PROMPT ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _execute_initialization(self, query):
        """비중별 순차 매수 실행"""
        logger.info("[INIT EXEC] Starting")
        
        try:
            cash, _, _ = self.trader.get_balance()
            logger.info(f"[INIT EXEC] Cash: ${cash:,.2f}")
            
            results = []
            
            for symbol in BUY_ORDER:
                ratio = TARGET_ALLOCATION[symbol]
                amount = cash * ratio
                
                price = self.trader.get_price(symbol)
                # 즉시 체결을 위해 현재가 +1% 로 주문
                order_price = round(price * 1.01, 2)
                logger.info(f"[INIT EXEC] {symbol} price: ${price:.2f} → order: ${order_price:.2f}")
                
                qty = int(amount / price)
                
                if qty <= 0:
                    logger.warning(f"[INIT EXEC] {symbol} qty=0, skipping")
                    results.append((symbol, 0, False, "수량 부족"))
                    continue
                
                logger.info(f"[INIT EXEC] Buying {symbol}: {qty}주 @ ${order_price:.2f}")
                
                try:
                    success = self.trader.buy(symbol, qty, order_price)
                    results.append((symbol, qty, success, "성공"))
                    
                    # 체결 알림 전송
                    if success:
                        await self._send_notification(
                            f"✅ <b>{symbol}</b> 주문 완료\n"
                            f"수량: {qty}주 @ ${order_price:.2f}\n"
                            f"금액: ${qty * order_price:,.2f}"
                        )
                except Exception as e:
                    logger.error(f"[INIT EXEC ERROR] {symbol}: {str(e)}")
                    results.append((symbol, qty, False, str(e)[:30]))
                    await self._send_notification(f"❌ <b>{symbol}</b> 주문 실패: {str(e)[:30]}")
                
                await asyncio.sleep(1)  # Rate limit
            
            msg = "✅ <b>초기화 완료</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            for symbol, qty, success, reason in results:
                icon = "✅" if success else "❌"
                msg += f"{icon} {symbol}: {qty}주"
                if not success:
                    msg += f" ({reason})"
                msg += "\n"
            msg += "━━━━━━━━━━━━━━━━━━━━"
            
            self.is_running = True
            await self._safe_send(query, msg)
            
            # 백그라운드 미체결 모니터링 시작
            self.pending_monitor_task = asyncio.create_task(self._start_pending_monitor())
            logger.info("[INIT] Pending monitor task started")
            
        except Exception as e:
            logger.error(f"[INIT EXEC ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _handle_stop_trading(self, query):
        """매매 중지"""
        self.is_running = False
        self.last_update = datetime.now()
        logger.info("[STOP] Trading stopped")
        
        # 백그라운드 모니터링 중지
        if self.pending_monitor_task:
            self.pending_monitor_task.cancel()
            logger.info("[STOP] Pending monitor task cancelled")
        
        msg = (
            "⏸️ <b>매매 중지</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "봇이 중지되었습니다.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self._safe_send(query, msg)
    
    async def _handle_portfolio(self, query):
        """📊 포트폴리오 - 목표 비중 vs 현재 비중 비교"""
        logger.info("[PORTFOLIO] Fetching")
        
        try:
            positions = self.trader.get_all_positions()
            cash, _, _ = self.trader.get_balance()
            
            total_stock = sum(p.get('eval_amount', p['quantity'] * p['current_price']) for p in positions.values())
            total = cash + total_stock
            
            msg = (
                "📊 <b>포트폴리오 전략</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"총 자산: <code>${total:,.2f}</code>\n\n"
                "<b>목표 비중 vs 현재 비중</b>\n"
            )
            
            for symbol, target_pct in TARGET_ALLOCATION.items():
                pos = positions.get(symbol, {'quantity': 0, 'current_price': 0, 'eval_amount': 0})
                current_val = pos.get('eval_amount', pos['quantity'] * pos['current_price'])
                current_pct = (current_val / total * 100) if total > 0 else 0
                target = target_pct * 100
                diff = current_pct - target
                
                if abs(diff) < 3:
                    icon = "🟢"
                elif abs(diff) < 7:
                    icon = "🟡"
                else:
                    icon = "🔴"
                
                msg += f"{icon} {symbol}: {current_pct:.1f}% / {target:.0f}% ({diff:+.1f}%)\n"
            
            msg += (
                "\n━━━━━━━━━━━━━━━━━━━━\n"
                "🎯 목표: TQQQ 10% | MAGS 20% | SHV 50% | JEPI 20%"
            )
            
            self.last_update = datetime.now()
            await self._safe_send(query, msg)
            
        except Exception as e:
            logger.error(f"[PORTFOLIO ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _handle_rebalance(self, query):
        """⚖️ 리밸런싱 - 조정 필요 여부 및 금액"""
        logger.info("[REBALANCE] Checking")
        
        try:
            positions = self.trader.get_all_positions()
            cash, _, _ = self.trader.get_balance()
            
            total_stock = sum(p.get('eval_amount', p['quantity'] * p['current_price']) for p in positions.values())
            total = cash + total_stock
            
            needs_rebalance = False
            adjustments = []
            
            for symbol, target_pct in TARGET_ALLOCATION.items():
                pos = positions.get(symbol, {'quantity': 0, 'current_price': 0, 'eval_amount': 0})
                current_val = pos.get('eval_amount', pos['quantity'] * pos['current_price'])
                target_val = total * target_pct
                diff_val = target_val - current_val
                diff_pct = (current_val / total * 100 - target_pct * 100) if total > 0 else 0
                
                if abs(diff_pct) > 5:
                    needs_rebalance = True
                
                action = "매수" if diff_val > 0 else "매도"
                adjustments.append((symbol, diff_pct, diff_val, action))
            
            status = "🔴 리밸런싱 필요" if needs_rebalance else "🟢 균형 상태"
            
            msg = (
                f"⚖️ <b>리밸런싱 분석</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"상태: {status}\n"
                f"총 자산: <code>${total:,.2f}</code>\n\n"
                f"<b>조정 필요 내역</b>\n"
            )
            
            for symbol, diff_pct, diff_val, action in adjustments:
                icon = "📈" if diff_val > 0 else "📉"
                msg += f"{icon} {symbol}: {action} ${abs(diff_val):,.0f} ({diff_pct:+.1f}%)\n"
            
            msg += "━━━━━━━━━━━━━━━━━━━━"
            
            self.last_update = datetime.now()
            await self._safe_send(query, msg)
            
        except Exception as e:
            logger.error(f"[REBALANCE ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _handle_etf_menu(self, query):
        """🎯 ETF 선택 메뉴"""
        msg = (
            "🎯 <b>ETF 선택</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"현재 선택: <code>{self.selected_symbol}</code>\n\n"
            "변경할 ETF를 선택하세요:\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self._safe_send(query, msg, self.get_etf_keyboard())
    
    async def _handle_etf_select(self, query, symbol):
        """ETF 선택 처리"""
        self.selected_symbol = symbol
        logger.info(f"[ETF] Selected: {symbol}")
        self.last_update = datetime.now()
        
        msg = f"✅ ETF 변경: <code>{symbol}</code>"
        await self._safe_send(query, msg)
    
    async def _handle_dip_mode(self, query):
        """⚙️ 매수 모드 선택"""
        mode_desc = {
            'daily': "📅 Daily: 15:55 ET, 하루 1회",
            'accelerated': "🚀 Accelerated: 10분마다",
            'accel_test': "⚡ Accel Test: 5분마다"
        }
        
        msg = (
            "⚙️ <b>매수 모드 선택</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"현재: <b>{self.dip_buy_mode.upper()}</b>\n\n"
            f"{mode_desc.get(self.dip_buy_mode, '')}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await self._safe_send(query, msg, self.get_mode_keyboard())
    
    async def _handle_mode_select(self, query, mode: str):
        """모드 선택 처리"""
        self.dip_buy_mode = mode
        logger.info(f"[MODE] Selected: {mode}")
        self.last_update = datetime.now()
        
        names = {'daily': 'Daily', 'accelerated': 'Accelerated', 'accel_test': 'Accel Test'}
        msg = f"✅ 모드 변경: <b>{names.get(mode, mode)}</b>"
        await self._safe_send(query, msg)
    
    async def _handle_balance(self, query):
        """💰 잔고 - 현금 및 총 자산"""
        logger.info("[BALANCE] Fetching")
        
        try:
            cash, qty, avg = self.trader.get_balance()
            positions = self.trader.get_all_positions()
            
            total_stock = sum(p.get('eval_amount', p['quantity'] * p['current_price']) for p in positions.values())
            total = cash + total_stock
            
            msg = (
                "💰 <b>계좌 잔고</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"현금:   <code>${cash:,.2f}</code>\n"
                f"주식:   <code>${total_stock:,.2f}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"총 자산: <code>${total:,.2f}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
            self.last_update = datetime.now()
            await self._safe_send(query, msg)
            
        except Exception as e:
            logger.error(f"[BALANCE ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _handle_position(self, query):
        """📈 포지션 - 현재 보유 종목 수량 및 손익 + 미체결 주문"""
        logger.info("[POSITION] Fetching")
        
        try:
            positions = self.trader.get_all_positions()
            
            msg = "📈 <b>보유 포지션</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            
            if not positions:
                msg += "보유 중인 주식이 없습니다.\n"
            else:
                total_pnl = 0
                for symbol, pos in positions.items():
                    qty = pos['quantity']
                    avg = pos.get('avg_price', 0)
                    current = pos.get('current_price', 0)
                    pnl = pos.get('profit_loss', (current - avg) * qty)
                    pnl_pct = (pnl / (qty * avg) * 100) if avg > 0 and qty > 0 else 0
                    total_pnl += pnl
                    
                    emoji = "🟢" if pnl >= 0 else "🔴"
                    
                    msg += (
                        f"<b>{symbol}</b>\n"
                        f"  수량: {qty}주\n"
                        f"  평단: ${avg:.2f} → 현재: ${current:.2f}\n"
                        f"  {emoji} 손익: ${pnl:,.2f} ({pnl_pct:+.1f}%)\n\n"
                    )
                
                total_emoji = "🟢" if total_pnl >= 0 else "🔴"
                msg += f"{total_emoji} 총 손익: <code>${total_pnl:,.2f}</code>\n"
            
            # 미체결 주문 조회
            msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
            msg += "⏳ <b>미체결 주문 (예수금 묶임)</b>\n"
            
            try:
                pending = self.trader.get_pending_orders()
                
                if not pending:
                    msg += "미체결 주문이 없습니다. ✅\n"
                else:
                    total_pending = 0
                    for order in pending:
                        side_icon = "🔵" if order['side'] == 'buy' else "🟠"
                        side_text = "매수" if order['side'] == 'buy' else "매도"
                        order_amt = order['qty'] * order['price']
                        total_pending += order_amt
                        
                        msg += (
                            f"{side_icon} {order['symbol']}: "
                            f"{order['qty']}주 @ ${order['price']:.2f} "
                            f"({side_text})\n"
                            f"   주문금액: <code>${order_amt:,.2f}</code>\n"
                        )
                    
                    msg += f"\n⚠️ <b>총 묶인 금액: <code>${total_pending:,.2f}</code></b>\n"
                    msg += "💡 한투 앱에서 미체결 취소 가능"
                    
            except Exception as e:
                logger.warning(f"[PENDING] Failed to fetch: {e}")
                msg += f"미체결 조회 실패: {str(e)[:30]}\n"
            
            msg += "\n━━━━━━━━━━━━━━━━━━━━"
            
            self.last_update = datetime.now()
            await self._safe_send(query, msg)
            
        except Exception as e:
            logger.error(f"[POSITION ERROR] {str(e)}", exc_info=True)
            raise
    
    async def _handle_back_to_status(self, query):
        """메인 상태로 복귀"""
        self.last_update = datetime.now()
        msg = self._get_status_message()
        await self._safe_send(query, msg)
    
    def run(self):
        """봇 시작"""
        print("=" * 50)
        print("🚀 REAL TRADING BOT (Full UI) STARTING...")
        print("=" * 50)
        
        # 파일 로깅 설정
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('bot_debug.log', encoding='utf-8')
            ]
        )
        
        # Application 빌드
        self.app = (
            Application.builder()
            .token(self.token)
            .post_init(self._post_init)
            .build()
        )
        
        # 핸들러 등록
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        logger.info("[BOT] Handlers registered. Starting polling...")
        self.app.run_polling()
    
    async def _post_init(self, application):
        """초기 상태 메시지 전송"""
        logger.info("[BOT] Sending initial status...")
        await application.bot.send_message(
            chat_id=self.chat_id,
            text=self._get_status_message(),
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard()
        )
        logger.info("[BOT] Initial message sent")
    
    async def _send_notification(self, text: str):
        """
        실시간 메시지 전송 (새로고침 필요 없이 사용자에게 알림)
        """
        if self.app:
            try:
                await self.app.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode='HTML'
                )
                logger.info(f"[NOTIFY] Sent: {text[:50]}...")
            except Exception as e:
                logger.error(f"[NOTIFY ERROR] {str(e)}")
    
    async def _start_pending_monitor(self):
        """
        백그라운드 미체결 모니터링 (30초마다 체크)
        """
        logger.info("[MONITOR] Starting pending order monitor...")
        
        while self.is_running:
            await asyncio.sleep(30)  # 30초 대기
            
            if not self.is_running:
                break
            
            try:
                await self._check_and_reorder()
            except Exception as e:
                logger.error(f"[MONITOR ERROR] {str(e)}")
        
        logger.info("[MONITOR] Pending order monitor stopped")
    
    async def _check_and_reorder(self):
        """
        미체결 주문 확인 → 취소 → 시장가 재주문
        """
        logger.info("[REORDER] Checking pending orders...")
        
        try:
            pending = self.trader.get_pending_orders()
            
            if not pending:
                logger.info("[REORDER] No pending orders")
                return
            
            for order in pending:
                symbol = order['symbol']
                qty = order['qty']
                order_no = order['order_no']
                old_price = order['price']
                
                # 거래소 코드 매핑 (취소용)
                ORDER_EXCHANGE = {
                    'TQQQ': 'NASD', 'SOXL': 'NASD', 'QQQ': 'NASD', 'SHV': 'NASD',
                    'MAGS': 'AMEX', 'JEPI': 'AMEX', 'SPY': 'AMEX',
                }
                exchange = ORDER_EXCHANGE.get(symbol, 'NASD')
                
                # 1. 취소
                logger.info(f"[REORDER] Cancelling {symbol} #{order_no} (excd={exchange})")
                try:
                    self.trader.cancel_order(symbol, order_no, qty, exchange)
                except Exception as e:
                    logger.error(f"[REORDER] Cancel failed: {e}")
                    await self._send_notification(f"❌ {symbol} 취소 실패: {str(e)[:30]}")
                    continue
                
                await asyncio.sleep(1)  # 취소 후 대기
                
                # 2. 현재가 +2%로 재주문 (즉시 체결 보장)
                try:
                    new_price = self.trader.get_price(symbol)
                    order_price = round(new_price * 1.02, 2)  # +2%
                    
                    logger.info(f"[REORDER] Reordering {symbol}: {qty}주 @ ${order_price:.2f}")
                    success = self.trader.buy(symbol, qty, order_price)
                    
                    if success:
                        await self._send_notification(
                            f"🔄 <b>재주문 완료</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"종목: {symbol}\n"
                            f"수량: {qty}주\n"
                            f"가격: ${old_price:.2f} → ${order_price:.2f}\n"
                            f"사유: 30초 미체결 → 자동 재주문"
                        )
                except Exception as e:
                    logger.error(f"[REORDER] Reorder failed: {e}")
                    await self._send_notification(f"❌ {symbol} 재주문 실패: {str(e)[:30]}")
                
                await asyncio.sleep(1)  # Rate limit
                
        except Exception as e:
            logger.error(f"[REORDER ERROR] {str(e)}")
