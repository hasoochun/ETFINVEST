"""
Bot Controller (Production Only / Clean Version)
"""
import logging
from datetime import datetime, timezone, timedelta

# KST (Korea Standard Time) = UTC+9
KST = timezone(timedelta(hours=9))




# KST (Korea Standard Time) = UTC+9
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 시간을 KST로 반환 (서버 위치와 무관하게 항상 한국시간)"""
    return datetime.now(KST).replace(tzinfo=None)  # naive datetime for comparison

logger = logging.getLogger(__name__)

import os
from infinite_buying_bot.utils.bot_status_manager import BotStatusManager

class BotController:
    def __init__(self):
        self.is_running = False
        self.notifier = None
        self.trader = None
        self.start_time = None
        self.portfolio_manager = None 
        # Hardcoded REAL settings
        self.trading_symbol = "TQQQ"
        self.is_simulation = False
        self.is_accelerated = False
        
        # Strategy settings (synced from runtime_config.json)
        self.strategy_mode = "neutral"  # aggressive, neutral, defensive
        self.dip_buy_mode = "accelerated"  # CHANGED: 'accelerated' for test (was 'daily')
        self.last_dip_buy_time = None
        self.entry_allowed = True
        self.accel_interval_minutes = 5  # NEW: 5-minute interval for accelerated test
        
        # Initialize Status Manager
        root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.status_manager = BotStatusManager(root_path)
        
        # NEW: Trading Mode Settings (for S-T Exchange / Gradual)
        self.trading_mode = "gradual"  # gradual, st-exchange, scheduled-single
        self.daily_time = "16:00"  # Target time for st-exchange mode (HH:MM)
        self.gradual_interval = 5  # Minutes between gradual buys
        
        # [NEW] Portfolio snapshot timer (every 30 minutes)
        self.last_snapshot_time = None
        self.snapshot_interval_minutes = 30  # Save portfolio history every 30 mins
        
        # [NEW] Time-based auto schedule mode
        self.auto_schedule_enabled = False  # Enable time-based mode switching
        self.schedule_zones = [
            # Default schedule (user can customize via UI)
            {"start": "22:30", "end": "01:00", "mode": "gradual", "name": "개장 초반"},
            {"start": "01:00", "end": "04:00", "mode": "st-exchange", "name": "본장"},
            {"start": "04:00", "end": "06:00", "mode": "scheduled-single", "name": "마감"}
        ]
        
        # Load from config file on init
        self._sync_from_config()

        # [NEW] Holdings history timer
        self.last_holdings_log_time = None

        
    def set_status_manager(self, manager):
        self.status_manager = manager

    def run_monitoring_cycle(self):
        """
        Main logic loop called by JobQueue/Asyncio.
        Analyzes portfolio and updates status/logic for user transparency.
        Delegates execution to PortfolioManager/Engine while maintaining clear UI feedback.
        """
        if not self.is_running:
            if self.status_manager:
                self.status_manager.update_logic("Paused", "Bot stopped by user command.")
                self.status_manager.update_heartbeat()  # Keep heartbeat alive even when paused
            return

        try:
            # [NEW] 이전 거래 체결 확인 (옵션 C)
            self._verify_last_trade()
            
            # [NEW] Sync config every cycle to pick up UI changes
            self._sync_from_config()

            # [FIX] Update heartbeat
            if self.status_manager:
                self.status_manager.update_heartbeat()
            
            
            # 1. Update Market Data
            current_price = self.trader.get_price(self.trading_symbol)
            cash, qty, avg = self.trader.get_balance()
            
            # [FIX] Check for API Failure
            if cash is None:
                logger.error("[CYCLE] API Failure detected (Balance is None)")
                if self.status_manager:
                    self.status_manager.update_logic("API Error", "Connection failed (500)", "ERROR")
                return # Skip cycle
            

            # [NEW] Log Holdings to DB for Report Page
            try:
                from infinite_buying_bot.dashboard.database import log_holdings, log_holdings_history
                all_holdings = self.trader.get_all_holdings()
                # Enriched with 'value' for DB
                for h in all_holdings:
                    h['value'] = h['qty'] * h.get('current_price', 0)
                log_holdings(all_holdings)
                
                # [NEW] Log holdings history for 5-minute interval tracking
                now_kst = get_kst_now()
                if self.last_holdings_log_time is None or (now_kst - self.last_holdings_log_time).total_seconds() >= 300:
                    log_holdings_history(all_holdings, strategy_mode=self.strategy_mode)
                    self.last_holdings_log_time = now_kst
                    logger.info("[Snapshot] Saved 5-minute holdings history (KST)")
                
                # [NEW] Save portfolio history snapshot every 30 minutes
                self._maybe_save_portfolio_snapshot(all_holdings, cash)
            except Exception as e:
                logger.error(f"DB Log Error: {e}")
            
            # Update Status Manager with latest market data
            if self.status_manager:
                self.status_manager.update_market_data(current_price, cash, qty, avg)
            
            # ============================================================
            # LAYER 0: Always-on Profit Monitoring (runs EVERY cycle)
            # ============================================================
            profit_action_executed = self._check_and_execute_profit_taking(all_holdings)
            if profit_action_executed:
                logger.info("[LAYER 0] Profit taking executed, skipping mode logic this cycle")
                return  # Exit early - let next cycle continue mode logic
            
            # ============================================================
            # AUTO SCHEDULE: Time-based mode switching
            # ============================================================
            if self.auto_schedule_enabled:
                new_mode = self._get_mode_for_current_time()
                if new_mode and new_mode != self.trading_mode:
                    logger.info(f"[AUTO SCHEDULE] Mode change: {self.trading_mode} → {new_mode}")
                    self.trading_mode = new_mode
            
            # 2. Check Trading Mode & Update Display Logic
            from datetime import timedelta
            
            if self.trading_mode == 'gradual':
                # Gradual Mode: Check 1-minute interval
                now = get_kst_now()  # KST 시간 사용
                interval_mins = getattr(self, 'gradual_interval', 1) 
                interval_sec = interval_mins * 60
                
                last_buy = getattr(self, 'last_dip_buy_time', None)
                
                if last_buy:
                    elapsed_sec = (now - last_buy).total_seconds()
                    remaining_sec = max(0, interval_sec - elapsed_sec)
                else:
                    elapsed_sec = 9999
                    remaining_sec = 0
                
                if remaining_sec <= 0:
                    if self.status_manager:
                        self.status_manager.update_logic("Executing", f"Gradual: Interval reached. Starting split buy...", "BUSY")
                    
                    # [Architectural Separation] 
                    # Delegate execution to PortfolioManager or Strategy Engine
                    # self.portfolio_manager.execute_gradual_step() 
                    
                    # For now, we perform the minimal action to satisfy the "Simultaneous Gradual" definition 
                    # while causing minimal side-effects in this controller.
                    self._execute_gradual_buy(cash) 
                else:
                    if self.status_manager:
                        self.status_manager.update_logic("Gradual Waiting", f"Next Split Buy: in {remaining_sec:.0f}s (Interval: {interval_mins}m)")
                    
            elif self.trading_mode == 'st-exchange':
                # S-T Exchange Mode: Check target time with market day awareness
                now = get_kst_now()  # KST 시간 사용 (사용자 입력과 일치)
                target_str = getattr(self, 'daily_time', '16:00')
                
                # 다음 거래 가능 시간 계산 (휴장일 고려)
                next_trade_dt = self._get_next_trading_datetime(target_str)
                
                # 목표 시간 도달 여부 체크
                target_hour, target_minute = map(int, target_str.split(':'))
                is_target_time = (now.hour == target_hour and now.minute == target_minute)
                is_trading_day = now.weekday() < 5  # 월~금만 거래
                
                if is_target_time and is_trading_day:
                    last_exchange = getattr(self, 'last_st_exchange_date', None)
                    if last_exchange != now.date():
                        if self.status_manager:
                            self.status_manager.update_logic("Exchanging", "TIME MATCH! Swapping SHV -> TQQQ now.", "BUSY")
                        self._execute_st_exchange()
                        self.last_st_exchange_date = now.date()
                        logger.info(f"[S-T EXCHANGE] Executed at {now.strftime('%Y-%m-%d %H:%M')}")
                else:
                    if self.status_manager:
                        # 대기시간 계산 (휴장일 포함)
                        wait_delta = next_trade_dt - now
                        wait_str = str(wait_delta).split('.')[0]
                        
                        # 요일 표시 추가
                        day_names_ko = ['월', '화', '수', '목', '금', '토', '일']
                        next_day_name = day_names_ko[next_trade_dt.weekday()]
                        
                        # 기본 대기 시간 문자열
                        if wait_delta.days > 0:
                            time_part = f"Target: {next_day_name} {target_str} (Wait: {wait_delta.days}일 {wait_str.split(', ')[-1] if ', ' in wait_str else wait_str})"
                        else:
                            time_part = f"Target: {target_str} (Wait: {wait_str})"
                        
                        # [NEW] 다음 매수 ETF 미리보기 추가
                        next_etf, deficit, shv_qty = self._calculate_next_etf_preview()
                        if next_etf and deficit > 0:
                            preview_part = f"📌 다음: {next_etf} (-${deficit:.0f})"
                            display_str = f"{time_part} | {preview_part}"
                            logger.info(f"[PREVIEW] Next ETF: {next_etf}, Deficit: ${deficit:.2f}")
                        elif shv_qty <= 0:
                            display_str = f"{time_part} | ⚠️ SHV 없음"
                        else:
                            display_str = f"{time_part} | ✅ 비중충족"
                        
                        self.status_manager.update_logic("Exchange Waiting", display_str)
            
            elif self.trading_mode == 'scheduled-single':
                # Scheduled Single Mode: Buy specific ETF at scheduled time
                now = get_kst_now()  # KST 시간 사용
                target_str = getattr(self, 'scheduled_time', '22:00')
                symbol = getattr(self, 'scheduled_symbol', 'TQQQ')
                qty = getattr(self, 'scheduled_qty', 1)
                
                # 다음 거래 가능 시간 계산 (휴장일 고려)
                next_trade_dt = self._get_next_trading_datetime(target_str)
                
                # 목표 시간 도달 여부 체크
                target_hour, target_minute = map(int, target_str.split(':'))
                is_target_time = (now.hour == target_hour and now.minute == target_minute)
                is_trading_day = now.weekday() < 5  # 월~금만 거래
                
                if is_target_time and is_trading_day:
                    last_scheduled = getattr(self, 'last_scheduled_buy_date', None)
                    if last_scheduled != now.date():
                        if self.status_manager:
                            self.status_manager.update_logic("Buying", f"Scheduled: Buying {qty} {symbol}...", "BUSY")
                        
                        # Execute the scheduled buy
                        try:
                            if self.trader:
                                current_price = self.trader.get_price(symbol)
                                buy_price = current_price * 1.01  # 1% buffer
                                success = self.trader.buy(buy_price, symbol)
                                logger.info(f"[SCHEDULED] Bought {qty} {symbol} @ ${current_price:.2f}")
                                
                                if success:
                                    # [NEW] 예약매수 체결 예상 알림
                                    if self.notifier:
                                        self.notifier.send(f"✅ [{symbol} 예약매수 전송] {qty}주 @ ${current_price:.2f} 체결 예상")
                                    
                                    # [NEW] 최종 요약 알림
                                    self._send_trade_summary(
                                        mode='예약매매',
                                        bought_symbol=symbol,
                                        bought_qty=qty,
                                        bought_price=current_price
                                    )
                                    
                                    if self.status_manager:
                                        self.status_manager.update_logic("Trade Success", f"Bought {qty} {symbol}", "ORDER FILLED")
                                else:
                                    if self.notifier:
                                        self.notifier.send(f"❌ [{symbol} 예약매수 실패]")
                                    if self.status_manager:
                                        self.status_manager.update_logic("Error", f"Buy failed for {symbol}")
                        except Exception as e:
                            logger.error(f"[SCHEDULED] Buy failed: {e}")
                            if self.notifier:
                                self.notifier.send(f"❌ [예약매매 오류] {e}")
                            if self.status_manager:
                                self.status_manager.update_logic("Error", f"Buy failed: {e}")
                        
                        self.last_scheduled_buy_date = now.date()
                else:
                    if self.status_manager:
                        # 대기시간 계산 (휴장일 포함)
                        wait_delta = next_trade_dt - now
                        wait_str = str(wait_delta).split('.')[0]
                        
                        day_names_ko = ['월', '화', '수', '목', '금', '토', '일']
                        next_day_name = day_names_ko[next_trade_dt.weekday()]
                        
                        if wait_delta.days > 0:
                            display_str = f"Next: {next_day_name} {target_str} → Buy {qty} {symbol}"
                        else:
                            display_str = f"Target: {target_str} → Buy {qty} {symbol} (Wait: {wait_str})"
                        
                        self.status_manager.update_logic("Scheduled Waiting", display_str)
            
            else:
                # Default / Lump-sum Mode
                drift_status = "Checked"
                if self.status_manager:
                    self.status_manager.update_logic("Monitoring", f"Mode: {self.trading_mode} (Standard Rebalancing)")

        except Exception as e:
            logger.error(f"Cycle Error: {e}")
            if self.status_manager:
                self.status_manager.update_logic("Error", f"Cycle failed: {e}")

    def _execute_gradual_buy(self, total_value):
        """
        Executes gradual buy logic by asking PortfolioManager for the order.
        [Delegation Pattern Implementation]
        """
        if not self.portfolio_manager:
            logger.error("Portfolio Manager not connected")
            return

        # 1. Provide latest state to Manager (Crucial)
        all_holdings = self.trader.get_all_holdings()
        positions_map = {h['symbol']: {'quantity': h['qty'], 'current_price': h.get('current_price', 0), 'avg_price': h['avg_price']} for h in all_holdings}
        self.portfolio_manager.update_positions(positions_map)
        self.portfolio_manager.update_cash(total_value)
        
        # 2. Get Order Proposal (with target filter)
        targets = getattr(self, 'gradual_targets', ['all'])
        orders = self.portfolio_manager.calculate_split_buy_order(targets=targets)
        
        logger.info(f"[GRADUAL] Targets filter: {targets}, Orders: {len(orders)}")
        
        # 3. Execute Orders
        executed = False
        executed_orders = []
        for order in orders:
            if order['type'] == 'buy':
                # Add 1% buffer for limit order
                buy_price = order['price'] * 1.01 
                success = self.trader.buy(buy_price, order['symbol'])
                logger.info(f"[GRADUAL] Delegated Buy: 1 {order['symbol']} ({order.get('reason','')})")
                
                if success:
                    executed = True
                    executed_orders.append(order)
                    
                    # [NEW] 매수 체결 예상 알림
                    if self.notifier:
                        self.notifier.send(f"✅ [{order['symbol']} 매수 전송] 1주 @ ${order['price']:.2f} 체결 예상")
                
        if executed:
            self.last_dip_buy_time = get_kst_now()
            
            # [NEW] 최종 요약 알림 (등시점진 모드)
            if self.notifier and executed_orders:
                bought_symbols = [o['symbol'] for o in executed_orders]
                total_amount = sum(o['price'] for o in executed_orders)
                
                # 여러 종목 매수 시 요약
                if len(executed_orders) == 1:
                    self._send_trade_summary(
                        mode='등시점진',
                        bought_symbol=executed_orders[0]['symbol'],
                        bought_qty=1,
                        bought_price=executed_orders[0]['price']
                    )
                else:
                    # 다중 매수 시 커스텀 메시지
                    now = get_kst_now()
                    summary_msg = (
                        f"✅ [거래 완료] {now.strftime('%Y-%m-%d %H:%M')} KST\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                    )
                    for o in executed_orders:
                        summary_msg += f"📥 매수: {o['symbol']} 1주 @ ${o['price']:.2f}\n"
                    summary_msg += f"💰 총 금액: ${total_amount:.2f}\n"
                    summary_msg += f"🏷️ 모드: 등시점진\n"
                    summary_msg += f"━━━━━━━━━━━━━━━━━━"
                    self.notifier.send(summary_msg)
                    
                    # 체결 확인용 저장 (첫 번째 종목만)
                    self._last_trade = {
                        'timestamp': now,
                        'mode': '등시점진',
                        'bought_symbol': executed_orders[0]['symbol'],
                        'bought_qty': 1,
                        'verified': False
                    }
            
            if self.status_manager:
                bought_list = [f"1 {o['symbol']}" for o in orders if o['type'] == 'buy']
                msg = f"Bought {', '.join(bought_list)}"
                self.status_manager.update_logic("Trade Success", msg, "ORDER FILLED")
        else:
             if self.status_manager:
                 self.status_manager.update_logic("Monitoring", "Gradual Mode: All targets met. No buys needed.")

    def _get_next_trading_datetime(self, target_time_str: str):
        """
        다음 거래 가능 시간 계산 (미국 휴장일 고려)
        
        Args:
            target_time_str: "HH:MM" 형식 (한국시간)
        
        Returns:
            datetime: 다음 거래 가능 시점 (한국시간, naive datetime)
        """
        from datetime import timedelta
        
        now = get_kst_now()  # KST 시간 사용
        target_hour, target_minute = map(int, target_time_str.split(':'))
        
        # 오늘 목표 시간
        target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        # 이미 지났으면 내일로 (같은 시간이면 오늘 실행)
        if target_dt < now:  # Fixed: was <= which caused same-minute to skip to next day
            target_dt += timedelta(days=1)
        
        # 토요일(5) 또는 일요일(6)이면 월요일로 이동
        # 한국시간 기준으로 체크 (미국 시장은 한국시간 월~금 밤에 열림)
        while target_dt.weekday() >= 5:  # 5=토, 6=일
            target_dt += timedelta(days=1)
            logger.info(f"[SCHEDULE] 휴장일 감지, 다음 거래일로 이동: {target_dt.strftime('%Y-%m-%d %H:%M')} KST")
        
        logger.debug(f"[SCHEDULE] 다음 거래 시간: {target_dt.strftime('%Y-%m-%d %H:%M %A')}")
        return target_dt

    def _calculate_next_etf_preview(self) -> tuple:
        """
        Calculate which ETF will be bought next in S-T exchange mode.
        Used to show preview in BRAIN LOGIC before actual execution.
        
        Returns:
            tuple: (selected_etf: str | None, deficit: float, shv_qty: int)
        """
        if not self.trader:
            logger.debug("[PREVIEW] Trader not connected, cannot calculate preview")
            return (None, 0.0, 0)
        
        try:
            # 1. Get current holdings
            all_holdings = self.trader.get_all_holdings()
            if all_holdings is None:
                logger.warning("[PREVIEW] Holdings fetch failed")
                return (None, 0.0, 0)
            
            holdings_dict = {}
            for h in all_holdings:
                symbol = h.get('symbol', '')
                if symbol not in holdings_dict:
                    holdings_dict[symbol] = h
            
            # 1.5 Ensure all target ETFs have complete data (prevents flickering)
            target_etfs = ['TQQQ', 'MAGS', 'SHV', 'JEPI', 'SCHD']
            for etf in target_etfs:
                if etf not in holdings_dict:
                    # ETF not in holdings - fetch price and add with qty=0
                    price = self.trader.get_price(etf) or 0
                    holdings_dict[etf] = {
                        'symbol': etf,
                        'qty': 0,
                        'current_price': price,
                        'avg_price': 0
                    }
                    logger.debug(f"[PREVIEW] Added missing ETF {etf} with price ${price:.2f}")
                elif 'current_price' not in holdings_dict[etf] or holdings_dict[etf].get('current_price', 0) <= 0:
                    # ETF exists but missing price - fetch it
                    price = self.trader.get_price(etf) or 0
                    holdings_dict[etf]['current_price'] = price
                    logger.debug(f"[PREVIEW] Updated {etf} price to ${price:.2f}")
            
            # 2. Check SHV holdings AND Cash
            shv_holding = holdings_dict.get('SHV', {})
            shv_qty = shv_holding.get('qty', 0)
            
            # Fetch cash
            cash, _, _ = self.trader.get_balance()
            
            # Calculate Total Liquidity (SHV + Cash)
            shv_value = shv_qty * shv_holding.get('current_price', 0)
            total_liquidity = shv_value + cash
            
            if total_liquidity <= 10: # Minimum $10 to do anything
                logger.debug("[PREVIEW] No liquidity (SHV/Cash) available")
                # Return dummy queue to show empty
                return (None, 0.0, 0)
            
            # 3. Calculate total portfolio value
            total_value = sum(
                h.get('qty', 0) * h.get('current_price', 0) 
                for h in holdings_dict.values()
            )
            
            if total_value <= 0:
                logger.debug("[PREVIEW] Total portfolio value is 0")
                return (None, 0.0, shv_qty)
            
            # 4. Load target allocation from runtime_config.json (synced with UI sliders)
            saved_targets = self.get_target_portfolio()  # Read from config file
            if saved_targets:
                # Config already stores as decimals (0.18 = 18%), use directly
                target_allocation = saved_targets
                logger.debug(f"[PREVIEW] Using saved target allocation: {saved_targets}")
            else:
                # Fallback to defaults if config not available
                target_allocation = {
                    'TQQQ': 0.10, 'SHV': 0.50, 'MAGS': 0.20, 'JEPI': 0.20, 'SCHD': 0.0
                }
                logger.debug("[PREVIEW] Using default target allocation (no config found)")
            
            # 5. Find priority ETF (most below target)
            buy_priority = ['TQQQ', 'MAGS', 'JEPI', 'SCHD']
            selected_etf = None
            max_deficit = 0.0
            
            for etf in buy_priority:
                holding = holdings_dict.get(etf, {})
                current_value = holding.get('qty', 0) * holding.get('current_price', self.trader.get_price(etf) or 0)
                target_value = total_value * target_allocation.get(etf, 0)
                deficit = target_value - current_value
                
                if deficit > max_deficit:
                    max_deficit = deficit
                    selected_etf = etf
            
            logger.debug(f"[PREVIEW] Next ETF: {selected_etf}, Deficit: ${max_deficit:.2f}, SHV: {shv_qty}, Cash: ${cash:.2f}")
            # Use 99999 as shv_qty signal if we have cash but no SHV, so UI says "Liquidity OK" instead of "SHV missing"
            display_qty = shv_qty if shv_qty > 0 else (99999 if cash > 50 else 0)
            return (selected_etf, max_deficit, display_qty)
            
        except Exception as e:
            logger.warning(f"[PREVIEW] Failed to calculate preview: {e}")
            return (None, 0.0, 0)

    def _execute_st_exchange(self):
        """
        Executes S-T exchange logic: Sell SHV → Buy priority ETF
        
        Priority Order (based on deficit from target):
        1. TQQQ (if below target)
        2. MAGS (if below target)
        3. JEPI (if below target)
        4. SCHD (if below target)
        
        If all ETFs are at/above target, skip buying.
        
        Strategy Mode determines sell percentage:
        - aggressive: 10% of SHV
        - neutral: 5% of SHV  
        - defensive: 2% of SHV
        """
        if not self.trader:
            logger.error("[S-T EXCHANGE] Trader not connected")
            return
        
        try:
            # 1. Get current holdings
            all_holdings = self.trader.get_all_holdings()
            if all_holdings is None:
                logger.error("[S-T EXCHANGE] Failed to fetch holdings (API Error)")
                if self.status_manager:
                     self.status_manager.update_logic("Error", "API 500: Failed to fetch holdings", "ERROR")
                if self.notifier:
                     self.notifier.send("⚠️ [매매 실패] 잔고 조회 오류 (API 500)\n증권사 서버 응답 없음 (재시도 실패)")
                return
            
            holdings_dict = {}
            for h in all_holdings:
                symbol = h.get('symbol', '')
                if symbol not in holdings_dict:
                    holdings_dict[symbol] = h
            
            shv_holding = holdings_dict.get('SHV', {})
            shv_qty = shv_holding.get('qty', 0)
            
            # [FIX] Get Cash as well
            cash, _, _ = self.trader.get_balance()
            shv_price = self.trader.get_price('SHV') or 110
            shv_value = shv_qty * shv_price
            
            total_liquidity = shv_value + cash
            
            if total_liquidity < 50:
                logger.info(f"[S-T EXCHANGE] Insufficient liquidity (SHV ${shv_value:.0f} + Cash ${cash:.0f})")
                if self.status_manager:
                    self.status_manager.update_logic("Exchange Skipped", "Low Liquidity")
                return
            
            # 2. Get current prices
            shv_price = self.trader.get_price('SHV') or 110
            
            # 3. Calculate total portfolio value for allocation check
            total_value = sum(
                h.get('qty', 0) * h.get('current_price', 0) 
                for h in holdings_dict.values()
            )
            
            # 4. Load target allocation
            target_allocation = getattr(self, 'target_allocation', {
                'TQQQ': 0.10, 'SHV': 0.50, 'MAGS': 0.20, 'JEPI': 0.20, 'SCHD': 0.0
            })
            
            # 5. Find priority ETF (most below target)
            buy_priority = ['TQQQ', 'MAGS', 'JEPI', 'SCHD']
            selected_etf = None
            max_deficit = 0
            
            for etf in buy_priority:
                holding = holdings_dict.get(etf, {})
                current_value = holding.get('qty', 0) * holding.get('current_price', self.trader.get_price(etf) or 0)
                target_value = total_value * target_allocation.get(etf, 0)
                deficit = target_value - current_value
                
                if deficit > max_deficit:
                    max_deficit = deficit
                    selected_etf = etf
                    
            if not selected_etf:
                logger.info("[S-T EXCHANGE] All ETFs at or above target allocation, skipping")
                if self.status_manager:
                    self.status_manager.update_logic("Exchange Skipped", "All ETFs at target allocation")
                return
            
            # 6. Get selected ETF price
            etf_price = self.trader.get_price(selected_etf) or 50
            
            # 7. Determine sell percentage based on strategy mode
            strategy_mode = getattr(self, 'strategy_mode', 'neutral')
            if strategy_mode == 'aggressive':
                sell_pct = 0.10  # 10%
            elif strategy_mode == 'defensive':
                sell_pct = 0.02  # 2%
            else:  # neutral
                sell_pct = 0.05  # 5%
            
            # 8. Calculate quantities
            # Use Cash FIRST, then Sell SHV if needed
            
            # Desired buy amount: Strategy % of Total Liquidity??
            # Or just Strategy % of SHV?
            # User wants to deploy CASH.
            # Let's say we want to deploy 5% of Total Liquidity?
            # Or if we have Cash, use ALL Cash up to the deficit?
            
            # Policy: Use Strategy % of Total Liquidity as the "Budget"
            budget = total_liquidity * sell_pct
            
            # If we have excess cash, we can be more aggressive? 
            # Let's stick to the budget to be gradual.
            
            # Determine funding source
            use_cash = min(budget, cash)
            sell_shv_val = max(0, budget - use_cash)
            
            shv_to_sell = 0
            if sell_shv_val > 0:
                shv_to_sell = int(sell_shv_val / shv_price)
            
            # Buy amount is budget (approx)
            buy_budget = use_cash + (shv_to_sell * shv_price)
            etf_to_buy = int(buy_budget / etf_price)
            
            logger.info(f"[S-T EXCHANGE] Priority: {selected_etf} (deficit: ${max_deficit:.2f})")
            logger.info(f"[S-T EXCHANGE] Budget: ${buy_budget:.2f} (Cash: ${use_cash:.2f}, SHV: {shv_to_sell} shares)")
            
            if etf_to_buy <= 0:
                logger.info("[S-T EXCHANGE] Quantities too small to execute")
                return
            
            # 9. Execute Sell SHV (if needed)
            proceeds = 0
            if shv_to_sell > 0:
                # [NEW] 매도 주문 알림
                if self.notifier:
                    self.notifier.send(f"📤 [SHV 매도 주문] {shv_to_sell}주 @ ${shv_price:.2f}")
                
                sell_success = self.trader.sell(shv_to_sell, 'SHV', reason=f"S-T Exchange → {selected_etf}", fallback_price=shv_price)
                if sell_success:
                    logger.info(f"[S-T EXCHANGE] Sold {shv_to_sell} SHV")
                    proceeds = shv_to_sell * shv_price # approx
                    
                    # [NEW] 매도 체결 예상 알림
                    if self.notifier:
                        self.notifier.send(f"✅ [SHV 매도 전송] {shv_to_sell}주 체결 예상")
                else:
                    logger.error("[S-T EXCHANGE] SHV sell failed")
                    if self.notifier:
                        self.notifier.send(f"❌ [SHV 매도 실패]")
                    return # Stop if sell failed (don't use cash if main mechanism failed?)
                    # Actually if sell failed but we have cash, should we proceed? 
                    # Safer to stop/retry next time.
            
            # 10. Execute Buy selected ETF
            # Amount = Cash Used + Proceeds
            total_buy_funds = use_cash + proceeds
            
            if total_buy_funds > 10:
                buy_amount = total_buy_funds * 1.01  # 1% buffer
                buy_success = self.trader.buy(buy_amount, selected_etf, reason=f"S-T Exchange ({strategy_mode})")
                
                if buy_success:
                    logger.info(f"[S-T EXCHANGE] Bought ~{etf_to_buy} {selected_etf}")
                    
                    # [NEW] 매수 체결 예상 알림
                    if self.notifier:
                        self.notifier.send(f"✅ [{selected_etf} 매수 전송] {etf_to_buy}주 체결 예상")
                    
                    # [NEW] 최종 요약 알림
                    self._send_trade_summary(
                        mode='S-T 교환',
                        sold_symbol='SHV' if shv_to_sell > 0 else None,
                        sold_qty=shv_to_sell,
                        sold_price=shv_price,
                        bought_symbol=selected_etf,
                        bought_qty=etf_to_buy,
                        bought_price=etf_price,
                        cash_used=use_cash
                    )
                    
                    if self.status_manager:
                        source_msg = f"Cash+SHV" if shv_to_sell > 0 else "Cash"
                        self.status_manager.update_logic(
                            "Exchange Complete", 
                            f"{source_msg} → {selected_etf}",
                            "ORDER FILLED"
                        )
                else:
                    logger.error(f"[S-T EXCHANGE] {selected_etf} buy failed")
                    if self.notifier:
                        self.notifier.send(f"❌ [{selected_etf} 매수 실패]")
                    if self.status_manager:
                        self.status_manager.update_logic("Partial Fail", f"Funds ready but buy failed")
            else:
                logger.info("Funds too small to buy")
                    
        except Exception as e:
            logger.error(f"[S-T EXCHANGE] Error: {e}")
            if self.status_manager:
                self.status_manager.update_logic("Error", f"Exchange failed: {e}")
        
    def set_trader(self, trader):
        self.trader = trader
        
    def _sync_from_config(self):
        """runtime_config.json에서 설정 동기화"""
        import os
        import json
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'runtime_config.json'
        )
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Sync trading mode settings
                if 'trading_mode' in config:
                    self.trading_mode = config['trading_mode']
                if 'daily_time' in config:
                    self.daily_time = config['daily_time']
                if 'gradual_interval' in config:
                    self.gradual_interval = config['gradual_interval']
                if 'strategy_mode' in config:
                    self.strategy_mode = config['strategy_mode']
                if 'command' in config:
                    if config['command'] == 'start':
                        self.is_running = True
                    elif config['command'] == 'stop':
                        self.is_running = False
                
                # [NEW] Sync gradual targets (ETF filter)
                if 'gradual_targets' in config:
                    self.gradual_targets = config['gradual_targets']
                else:
                    self.gradual_targets = ['all']  # Default: all ETFs
                
                # [NEW] Sync scheduled-single settings
                if 'scheduled_symbol' in config:
                    self.scheduled_symbol = config['scheduled_symbol']
                if 'scheduled_time' in config:
                    self.scheduled_time = config['scheduled_time']
                if 'scheduled_qty' in config:
                    self.scheduled_qty = config['scheduled_qty']
                
                logger.info(f"[CONFIG SYNC] trading_mode={self.trading_mode}, daily_time={self.daily_time}")
                if self.trading_mode == 'scheduled-single':
                    logger.info(f"[CONFIG SYNC] Scheduled: {getattr(self, 'scheduled_symbol', 'TQQQ')} @ {getattr(self, 'scheduled_time', '22:00')}")
                
                # [NEW] Sync auto schedule settings
                if 'auto_schedule_enabled' in config:
                    self.auto_schedule_enabled = config['auto_schedule_enabled']
                if 'schedule_zones' in config:
                    self.schedule_zones = config['schedule_zones']
                
                if self.auto_schedule_enabled:
                    logger.info(f"[CONFIG SYNC] Auto Schedule: ENABLED ({len(self.schedule_zones)} zones)")
        except Exception as e:
            logger.error(f"[CONFIG SYNC] Failed to sync: {e}")
        
    def set_notifier(self, notifier):
        self.notifier = notifier
    
    def _maybe_save_portfolio_snapshot(self, holdings: list, cash: float):
        """
        Save portfolio snapshot every 30 minutes for performance report.
        Calculates daily/cumulative returns and MDD.
        """
        now = get_kst_now()
        
        # Check if 30 minutes have passed since last snapshot
        if self.last_snapshot_time:
            elapsed = (now - self.last_snapshot_time).total_seconds() / 60
            if elapsed < self.snapshot_interval_minutes:
                return  # Not time yet
        
        try:
            from infinite_buying_bot.dashboard.database import (
                log_portfolio_history,
                get_latest_portfolio_snapshot,
                get_initial_capital,
                set_initial_capital
            )
            import yfinance as yf
            
            # Deduplicate holdings by symbol (NASD + AMEX may return duplicates)
            holdings_by_symbol = {}
            for h in holdings:
                symbol = h.get('symbol', '')
                if symbol not in holdings_by_symbol:
                    holdings_by_symbol[symbol] = h
                # else: skip duplicate
            
            # Calculate total portfolio value
            total_value = cash
            invested_value = 0
            holdings_data = []
            
            for symbol, h in holdings_by_symbol.items():
                qty = h.get('qty', 0)
                current_price = h.get('current_price', 0)
                avg_price = h.get('avg_price', 0)
                market_value = qty * current_price
                
                total_value += market_value
                invested_value += market_value
                
                pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                
                holdings_data.append({
                    'symbol': symbol,
                    'qty': qty,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'market_value': market_value,
                    'pnl_pct': round(pnl_pct, 2)
                })
            
            # Calculate daily return
            daily_return_pct = 0
            prev_snapshot = get_latest_portfolio_snapshot()
            if prev_snapshot:
                prev_value = prev_snapshot.get('total_value', total_value)
                if prev_value > 0:
                    daily_return_pct = ((total_value - prev_value) / prev_value) * 100
            
            # Calculate cumulative return
            initial_capital = get_initial_capital() or total_value
            cumulative_return_pct = ((total_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
            
            # Get S&P 500 benchmark
            benchmark_value = None
            benchmark_return_pct = 0
            try:
                sp500 = yf.Ticker('^GSPC')
                hist = sp500.history(period='1d')
                if not hist.empty:
                    benchmark_value = float(hist['Close'].iloc[-1])
            except Exception as e:
                logger.warning(f"[SNAPSHOT] Could not fetch S&P 500: {e}")
            
            # Save to database
            log_portfolio_history(
                total_value=total_value,
                cash_balance=cash,
                invested_value=invested_value,
                daily_return_pct=daily_return_pct,
                cumulative_return_pct=cumulative_return_pct,
                benchmark_value=benchmark_value,
                benchmark_return_pct=benchmark_return_pct,
                holdings=holdings_data
            )
            
            self.last_snapshot_time = now
            logger.info(f"[SNAPSHOT] Saved: ${total_value:.2f}, Return: {cumulative_return_pct:+.2f}%")
            
        except Exception as e:
            logger.error(f"[SNAPSHOT] Failed to save: {e}")
    
    def _check_and_execute_profit_taking(self, holdings: list) -> bool:
        """
        LAYER 0: Always-on profit monitoring for ALL ETFs.
        Executes profit taking if any ETF has profit >= 10%.
        
        Returns:
            True if profit taking was executed, False otherwise
        """
        if not self.trader:
            return False
        
        PROFIT_TARGET_PCT = 10.0  # 10% profit target
        executed = False
        
        # Deduplicate holdings by symbol
        holdings_by_symbol = {}
        for h in holdings:
            symbol = h.get('symbol', '')
            if symbol not in holdings_by_symbol:
                holdings_by_symbol[symbol] = h
        
        for symbol, h in holdings_by_symbol.items():
            qty = h.get('qty', 0)
            avg_price = h.get('avg_price', 0)
            current_price = h.get('current_price', 0)
            
            if qty <= 0 or avg_price <= 0:
                continue
            
            profit_pct = ((current_price - avg_price) / avg_price) * 100
            
            if profit_pct >= PROFIT_TARGET_PCT:
                logger.info(f"[LAYER 0] 🎯 {symbol} profit target reached: +{profit_pct:.1f}%")
                
                # [CORRECT LOGIC] Calculate excess quantity based on target allocation
                # Load target allocation from portfolio_manager or config
                target_allocation = getattr(self, 'target_allocation', {
                    'TQQQ': 0.10, 'SHV': 0.50, 'MAGS': 0.20, 'JEPI': 0.20, 'SCHD': 0.0
                })
                
                # Calculate total portfolio value
                total_value = sum(
                    h.get('qty', 0) * h.get('current_price', 0) 
                    for h in holdings_by_symbol.values()
                )
                
                # Calculate current and target value for this symbol
                current_value = qty * current_price
                target_pct = target_allocation.get(symbol, 0)
                target_value = total_value * target_pct
                
                # Only sell if current value exceeds target
                excess_value = current_value - target_value
                if excess_value <= 0:
                    logger.info(f"[LAYER 0] {symbol}: No excess (current: ${current_value:.2f} <= target: ${target_value:.2f})")
                    continue
                
                # Calculate excess quantity to sell
                excess_qty = int(excess_value / current_price)
                if excess_qty < 1:
                    logger.info(f"[LAYER 0] {symbol}: Excess < 1 share, skipping")
                    continue
                    
                logger.info(f"[LAYER 0] {symbol}: Selling excess {excess_qty} shares (${excess_value:.2f})")
                
                # Execute sell
                success = self.trader.sell(excess_qty, symbol, reason=f"Profit taking +{profit_pct:.1f}% (excess)")
                if success:
                    sell_proceeds = excess_qty * current_price
                    logger.info(f"[LAYER 0] ✅ Sold {excess_qty} {symbol} @ ${current_price:.2f} = ${sell_proceeds:.2f}")
                    
                    # [NEW] Buy SHV with proceeds (complete the cycle)
                    shv_price = self.trader.get_price('SHV') or 110
                    shv_buy_success = self.trader.buy(sell_proceeds, 'SHV', reason=f"Profit taking → SHV")
                    
                    if shv_buy_success:
                        shv_qty_bought = int(sell_proceeds / shv_price)
                        logger.info(f"[LAYER 0] ✅ Bought ~{shv_qty_bought} SHV with proceeds")
                        
                        # Log to database
                        try:
                            from infinite_buying_bot.dashboard.database import log_trade
                            log_trade("sell", symbol, excess_qty, current_price, reason=f"Profit taking +{profit_pct:.1f}%")
                            log_trade("buy", "SHV", shv_qty_bought, shv_price, reason=f"Profit taking → SHV")
                        except Exception as e:
                            logger.warning(f"[LAYER 0] DB log failed: {e}")
                        
                        if self.status_manager:
                            self.status_manager.update_logic(
                                "Profit Taking", 
                                f"{symbol} → SHV (+{profit_pct:.1f}%)", 
                                "BUSY"
                            )
                    else:
                        logger.warning(f"[LAYER 0] SHV buy failed, proceeds remain as cash")
                        if self.status_manager:
                            self.status_manager.update_logic("Profit Taking", f"Sold {excess_qty} {symbol} (+{profit_pct:.1f}%)", "BUSY")
                    
                    executed = True
                else:
                    logger.error(f"[LAYER 0] ❌ Failed to sell {symbol}")
        
        return executed
    
    def _get_mode_for_current_time(self) -> str:
        """
        Determine which trading mode should be active based on current time.
        
        Returns:
            Mode string ('gradual', 'st-exchange', 'scheduled-single') or None
        """
        now = get_kst_now()
        current_time = now.hour * 60 + now.minute  # Minutes since midnight
        
        for zone in self.schedule_zones:
            start_str = zone.get('start', '00:00')
            end_str = zone.get('end', '23:59')
            mode = zone.get('mode', 'gradual')
            
            # Parse times
            start_h, start_m = map(int, start_str.split(':'))
            end_h, end_m = map(int, end_str.split(':'))
            
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m
            
            # Handle overnight zones (e.g., 22:30 - 01:00)
            if end_mins < start_mins:
                # Overnight zone
                if current_time >= start_mins or current_time < end_mins:
                    logger.debug(f"[AUTO SCHEDULE] Matched zone: {zone.get('name', mode)}")
                    return mode
            else:
                # Same-day zone
                if start_mins <= current_time < end_mins:
                    logger.debug(f"[AUTO SCHEDULE] Matched zone: {zone.get('name', mode)}")
                    return mode
        
        return None  # No matching zone
        
    def start_bot(self):
        self.is_running = True
        self.start_time = get_kst_now()
        if self.notifier: self.notifier.send("[BOT STARTED] (REAL)")
        
    def stop_bot(self):
        self.is_running = False
        if self.notifier: self.notifier.send("Paused.")
        
    def get_status(self):
        return {
            'is_running': self.is_running,
            'status': 'RUNNING' if self.is_running else 'STOPPED',
            'trading_symbol': self.trading_symbol,
            'market_open': True, # Simple assumption or check logic
            'market_status': "OPEN",
            'mode': "[REAL TRADING]", # HARDCODED
            'uptime': str(get_kst_now() - self.start_time).split('.')[0] if self.start_time else "0:00",
            'next_open': "OPEN",
            'last_update': "Now"
        }
    
    def get_balance(self):
        if not self.trader: return {'total': 0, 'cash': 0}
        cash, qty, avg = self.trader.get_balance()
        price = self.trader.get_price("TQQQ")
        val = qty * price
        return {
            'cash': cash,
            'stock_val': val,
            'total': cash + val,
            'qty': qty,
            'avg_price': avg,
            'profit': val - (qty * avg),
            'return_rate': 0.0 # simple
        }

    def get_target_portfolio(self):
        """Get target portfolio allocation from runtime_config.json"""
        import json
        import os
        
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime_config.json')
            if not os.path.exists(config_path):
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config.get('target_portfolio', None)
        except Exception as e:
            logger.warning(f"Failed to read target portfolio: {e}")
            return None

    def sync_with_config(self):
        """Sync running state and mode with runtime_config.json"""
        import json
        import os
        
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime_config.json')
            if not os.path.exists(config_path):
                return
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 1. Sync Running State
            command = config.get('command', 'stop')
            if command == 'start' and not self.is_running:
                self.start_bot()
            elif command == 'stop' and self.is_running:
                self.stop_bot()
                
            # 2. Sync Strategy Mode
            self.strategy_mode = config.get('strategy_mode', 'neutral')
            
            # 3. Sync Buy Mode (accelerated/daily) - legacy
            new_buy_mode = config.get('dip_buy_mode', 'accelerated')
            if new_buy_mode != self.dip_buy_mode:
                logger.info(f"[SYNC] Buy mode changed: {self.dip_buy_mode} -> {new_buy_mode}")
                self.dip_buy_mode = new_buy_mode
            
            # 4. Sync Trading Mode (gradual/st-exchange)
            new_trading_mode = config.get('trading_mode', 'gradual')
            if not hasattr(self, 'trading_mode') or new_trading_mode != self.trading_mode:
                logger.info(f"[SYNC] Trading mode changed to: {new_trading_mode}")
                self.trading_mode = new_trading_mode
            
            # 5. Sync Gradual Interval (minutes)
            self.gradual_interval = config.get('gradual_interval', 5)
            
            # 6. Sync Daily Time (for S-T exchange mode)
            self.daily_time = config.get('daily_time', '22:00')
            
            # 7. Sync Portfolio Targets
            target_portfolio = config.get('target_portfolio', {})
            if target_portfolio and self.portfolio_manager:
                 # Ensure MAGS and JEPI are included if missing (default logic)
                 # But user might only send TQQQ/SHV/SCHD. We need to handle this.
                 # For now, just pass what we get, PortfolioManager validation handles 100% check.
                 try:
                     self.portfolio_manager.update_target_allocation(target_portfolio)
                 except Exception as e:
                     logger.warning(f"Target sync failed (likely sum!=1.0): {e}")
            
        except Exception as e:
            logger.error(f"Failed to sync config: {e}")

    def _send_trade_summary(self, mode: str, sold_symbol: str = None, sold_qty: int = 0,
                            sold_price: float = 0, bought_symbol: str = None,
                            bought_qty: int = 0, bought_price: float = 0,
                            cash_used: float = 0):
        """
        모든 매매 모드 공통 요약 알림 전송
        
        Args:
            mode: 거래 모드 이름 ('S-T 교환', '등시점진', '예약매매' 등)
            sold_symbol: 매도 종목
            sold_qty: 매도 수량
            sold_price: 매도 가격
            bought_symbol: 매수 종목
            bought_qty: 매수 수량
            bought_price: 매수 가격
            cash_used: 사용한 현금
        """
        if not self.notifier:
            return
        
        now = get_kst_now()
        summary_msg = (
            f"✅ [거래 완료] {now.strftime('%Y-%m-%d %H:%M')} KST\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        
        if sold_symbol and sold_qty > 0:
            summary_msg += f"📤 매도: {sold_symbol} {sold_qty}주 @ ${sold_price:.2f}\n"
        
        if cash_used > 0:
            summary_msg += f"💵 현금 사용: ${cash_used:.2f}\n"
        
        if bought_symbol and bought_qty > 0:
            summary_msg += f"📥 매수: {bought_symbol} {bought_qty}주 @ ${bought_price:.2f}\n"
            total_amt = bought_qty * bought_price
            summary_msg += f"💰 총 금액: ${total_amt:.2f}\n"
        
        summary_msg += f"🏷️ 모드: {mode}\n"
        summary_msg += f"━━━━━━━━━━━━━━━━━━"
        
        self.notifier.send(summary_msg)
        
        # 다음 주기 체결 확인용 저장
        self._last_trade = {
            'timestamp': now,
            'mode': mode,
            'bought_symbol': bought_symbol,
            'bought_qty': bought_qty,
            'verified': False
        }
        logger.info(f"[TRADE SUMMARY] Sent: {mode} - {bought_symbol} {bought_qty}주")

    def _verify_last_trade(self):
        """
        다음 주기에 이전 거래 체결 여부 확인 (옵션 C)
        보유량 변화를 확인하여 체결 성공/실패 알림
        """
        last_trade = getattr(self, '_last_trade', None)
        if not last_trade or last_trade.get('verified', True):
            return  # 확인할 거래 없음
        
        if not self.trader:
            return
        
        try:
            now = get_kst_now()
            elapsed = (now - last_trade['timestamp']).total_seconds() / 60
            
            if elapsed >= 1:  # 최소 1분 경과 후 확인
                all_holdings = self.trader.get_all_holdings()
                if all_holdings is None:
                    return  # API 오류, 다음 주기에 재시도
                
                holdings_dict = {h['symbol']: h for h in all_holdings}
                bought_symbol = last_trade.get('bought_symbol')
                bought_qty = last_trade.get('bought_qty', 0)
                
                if not bought_symbol:
                    last_trade['verified'] = True
                    return
                
                current_qty = holdings_dict.get(bought_symbol, {}).get('qty', 0)
                
                if current_qty >= bought_qty:
                    logger.info(f"[VERIFY] {bought_symbol} 체결 확인: {current_qty}주 보유")
                    if self.notifier:
                        self.notifier.send(
                            f"✅ [체결 확인] {bought_symbol} 체결 완료\n"
                            f"현재 보유: {current_qty}주"
                        )
                else:
                    logger.warning(f"[VERIFY] {bought_symbol} 체결 미확인: 예상 {bought_qty}주, 현재 {current_qty}주")
                    if self.notifier:
                        self.notifier.send(
                            f"⚠️ [체결 확인 필요] {bought_symbol}\n"
                            f"예상: +{bought_qty}주, 현재: {current_qty}주"
                        )
                
                last_trade['verified'] = True
                
        except Exception as e:
            logger.error(f"[VERIFY] 체결 확인 오류: {e}")
