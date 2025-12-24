"""
Rebalancing Engine - Infinite Buying Strategy Logic
Implements TQQQ 40/80 split buying using SHV as cash buffer
- Price < Avg: Buy SHV/40 (aggressive)
- Price >= Avg: Buy SHV/80 (conservative)
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RebalancingEngine:
    """Implements infinite buying strategy with dynamic rebalancing"""
    
    def __init__(self, portfolio_manager, bot_controller=None, config=None):
        """
        Initialize rebalancing engine
        
        Args:
            portfolio_manager: PortfolioManager instance
            bot_controller: BotController instance (for dip buy mode)
            config: Configuration dictionary (optional)
        """
        self.portfolio = portfolio_manager
        self.bot_controller = bot_controller
        self.config = config or {}
        
        # Load accelerated test settings if available
        accel_config = self.config.get('accelerated_test', {})
        self.accel_test_enabled = accel_config.get('enabled', False)
        self.accel_interval_minutes = accel_config.get('interval_minutes', 5)
        self.accel_fixed_quantity = accel_config.get('fixed_quantity', 1)
        self.accel_profit_target = accel_config.get('profit_target_pct', 3.0) / 100.0
        
        # TQQQ strategy parameters (use accelerated if enabled)
        if self.accel_test_enabled:
            self.tqqq_target_profit = self.accel_profit_target
            logger.info(f"⚡ Accelerated Test Mode: {self.accel_interval_minutes}min, {self.accel_fixed_quantity} share, {self.accel_profit_target*100}% target")
        else:
            self.tqqq_target_profit = 0.10  # +10% profit target
        
        # 40/80 split strategy (using SHV as buffer)
        # - Price < Avg: SHV / 40 (aggressive)
        # - Price >= Avg: SHV / 80 (conservative)
        
        # Track TQQQ average price for infinite buying
        self.tqqq_entry_avg = 0.0
        self.tqqq_total_invested = 0.0
        
        logger.info("Rebalancing Engine initialized with 40/80 split strategy")
    
    def update_tqqq_average(self, quantity: int, price: float):
        """
        Update TQQQ average price after purchase
        
        Args:
            quantity: Shares bought
            price: Purchase price
        """
        current_qty = self.portfolio.positions['TQQQ']['quantity']
        current_avg = self.portfolio.positions['TQQQ']['avg_price']
        
        if current_qty == 0:
            self.tqqq_entry_avg = price
        else:
            total_cost = (current_qty * current_avg) + (quantity * price)
            total_qty = current_qty + quantity
            self.tqqq_entry_avg = total_cost / total_qty
        
        self.tqqq_total_invested += quantity * price
        logger.info(f"TQQQ avg updated: {self.tqqq_entry_avg:.2f}, total invested: {self.tqqq_total_invested:,.0f}")
    
    def check_tqqq_profit_target(self) -> Optional[Dict]:
        """
        Check if TQQQ reached profit target
        
        Returns:
            Trade action dict if target reached, None otherwise
        """
        tqqq_pos = self.portfolio.positions['TQQQ']
        if tqqq_pos['quantity'] == 0:
            return None
        
        current_price = tqqq_pos['current_price']
        avg_price = tqqq_pos['avg_price']
        
        if avg_price == 0:
            return None
        
        profit_pct = (current_price - avg_price) / avg_price
        
        if profit_pct >= self.tqqq_target_profit:
            # Sell all TQQQ, buy JEPI with profits
            profit_amount = tqqq_pos['quantity'] * (current_price - avg_price)
            
            # Floor profit amount to integer
            profit_amount = int(profit_amount)
            
            logger.info(f"🎯 TQQQ profit target reached: +{profit_pct*100:.1f}%")
            
            return {
                'action': 'profit_taking',
                'sell_symbol': 'TQQQ',
                'sell_quantity': tqqq_pos['quantity'],
                'buy_symbol': 'JEPI',
                'profit_amount': profit_amount,
                'profit_pct': profit_pct * 100,
                'reason': f'Profit target +{self.tqqq_target_profit*100:.0f}% reached'
            }
        
        return None
    
    def check_tqqq_dip_buying(self) -> Optional[Dict]:
        """
        Check if TQQQ should be bought using SHV buffer
        Uses 40/80 split strategy based on average price
        Includes time-based conditions for daily/accelerated modes
        
        Returns:
            Trade action dict if buying needed, None otherwise
        """
        # === TIME-BASED CHECK ===
        if self.bot_controller:
            import pytz
            from datetime import timedelta
            
            mode = self.bot_controller.dip_buy_mode
            last_buy_time = self.bot_controller.last_dip_buy_time
            now = datetime.now()
            
            if mode == 'daily':
                # Check if it's 15:55-16:00 ET
                et = pytz.timezone('US/Eastern')
                now_et = now.astimezone(et)
                
                if not (now_et.hour == 15 and 55 <= now_et.minute < 60):
                    # logger.debug(f"Daily mode: Not in buy window (current: {now_et.strftime('%H:%M')} ET)")
                    return None
                
                # Check if already bought today
                if last_buy_time and last_buy_time.date() == now.date():
                    logger.debug("Daily mode: Already bought today")
                    return None
                
                logger.info(f"✅ Daily mode: In buy window ({now_et.strftime('%H:%M')} ET)")
            
            elif mode == 'accelerated':
                # Use configurable interval (default 5 min for accelerated test)
                interval = self.accel_interval_minutes if self.accel_test_enabled else 10
                if last_buy_time:
                    elapsed_minutes = (now - last_buy_time).total_seconds() / 60
                    if elapsed_minutes < interval:
                        # logger.debug(f"Accelerated mode: Only {elapsed_minutes:.1f} min elapsed (need {interval})")
                        return None
                
                logger.info(f"✅ Accelerated mode: {interval} minutes elapsed or first buy")
        else:
            logger.warning("BotController not set, skipping time-based check")

        tqqq_pos = self.portfolio.positions['TQQQ']
        shv_pos = self.portfolio.positions['SHV']
        
        # Need SHV to buy TQQQ (unless in accel_test mode - uses cash directly)
        if shv_pos['quantity'] == 0 and not self.accel_test_enabled:
            return None
        
        current_price = tqqq_pos['current_price']
        avg_price = tqqq_pos['avg_price']
        
        # Calculate SHV total value
        shv_value = shv_pos['quantity'] * shv_pos['current_price']
        
        # Determine split count based on price vs average
        # Determine split count based on price vs average AND Strategy Mode
        # Default (Neutral): 40 (Below Avg) / 80 (Above Avg)
        base_aggressive = 40
        base_conservative = 80
        
        if self.bot_controller:
            mode = self.bot_controller.strategy_mode
            if mode == 'aggressive':
                base_aggressive = 20
                base_conservative = 40
                logger.debug("🔥 Aggressive Mode: Split counts reduced to 20/40")
            elif mode == 'defensive':
                base_aggressive = 60
                base_conservative = 100
                logger.debug("🛡️ Defensive Mode: Split counts increased to 60/100")

        if tqqq_pos['quantity'] == 0:
            # Initial entry: aggressive base
            split_count = base_aggressive
            reason = "Initial TQQQ entry"
        elif avg_price > 0 and current_price < avg_price:
            # Below average: aggressive base
            split_count = base_aggressive
            reason = f"Price below avg (${current_price:.2f} < ${avg_price:.2f})"
        elif avg_price > 0 and current_price >= avg_price:
            # Above average: conservative base
            split_count = base_conservative
            reason = f"Price above avg (${current_price:.2f} ≥ ${avg_price:.2f})"
        else:
            # No position yet
            split_count = base_aggressive
            reason = "No average price yet"
        
        # Calculate buy amount from SHV (all modes use same strategy)
        buy_amount = shv_value / split_count
        # Floor to avoid decimal issues in trading
        buy_amount = int(buy_amount)
        # Minimum buy threshold ($100)
        if buy_amount < 100:
            return None
        
        logger.info(f"📉 TQQQ buy signal: {reason}, buying ${buy_amount:,.0f}")
        
        return {
            'action': 'dip_buying',
            'sell_symbol': 'SHV' if shv_pos['quantity'] > 0 else None,
            'sell_amount': buy_amount,
            'buy_symbol': 'TQQQ',
            'split_count': split_count,
            'current_price': current_price,
            'avg_price': avg_price,
            'reason': reason
        }
    
    def check_shv_interest_reinvest(self, monthly_interest: float) -> Optional[Dict]:
        """
        Check if SHV interest should be reinvested into JEPI
        
        Args:
            monthly_interest: Monthly interest earned from SHV
        
        Returns:
            Trade action dict
        """
        # Floor to integer
        monthly_interest = int(monthly_interest)
        
        if monthly_interest > 100:  # Minimum $100
            logger.info(f"💰 SHV interest reinvest: {monthly_interest:,.0f} KRW → JEPI")
            
            return {
                'action': 'interest_reinvest',
                'source': 'SHV_interest',
                'buy_symbol': 'JEPI',
                'amount': monthly_interest,
                'reason': 'SHV interest reinvestment'
            }
        
        return None
    
    def get_rebalancing_actions(self) -> List[Dict]:
        """
        Get all pending rebalancing actions
        
        Returns:
            List of trade action dicts
        """
        actions = []
        
        # 1. Check TQQQ profit target (highest priority)
        profit_action = self.check_tqqq_profit_target()
        if profit_action:
            actions.append(profit_action)
            return actions  # Execute profit-taking immediately
        
        # 2. Check TQQQ dip buying
        dip_action = self.check_tqqq_dip_buying()
        if dip_action:
            actions.append(dip_action)
        
        # 3. Check periodic rebalancing (if no other actions and not in accel_test)
        if not actions and not self.accel_test_enabled:
            if self.portfolio.needs_rebalancing(threshold=0.10):
                rebalance_trades = self.portfolio.calculate_rebalancing_trades()
                for trade in rebalance_trades:
                    actions.append({
                        'action': 'rebalance',
                        'trade_action': trade['action'],  # 'buy' or 'sell'
                        'symbol': trade['symbol'],
                        'amount_krw': trade['amount_krw'],
                        'reason': trade['reason']
                    })

        
        return actions
    
    def execute_action(self, action: Dict, trader) -> bool:
        """
        Execute a rebalancing action
        
        Args:
            action: Trade action dict
            trader: Trader instance
        
        Returns:
            True if successful
        """
        try:
            action_type = action['action']
            
            if action_type == 'profit_taking':
                # Sell all TQQQ
                trader.sell(action['sell_symbol'], action['sell_quantity'])
                # Buy SCHD with profits
                trader.buy(action['buy_symbol'], action['profit_amount'])
                # Reset TQQQ tracking
                self.tqqq_entry_avg = 0.0
                self.tqqq_total_invested = 0.0
                logger.info(f"✅ Profit taking executed: {action['profit_pct']:.1f}%")
                
            elif action_type == 'dip_buying':
                # Sell SHV
                trader.sell(action['sell_symbol'], action['sell_amount'])
                # Buy TQQQ
                trader.buy(action['buy_symbol'], action['sell_amount'])
                logger.info(f"✅ Dip buying executed at {action['dip_pct']:.1f}%")
                
            elif action_type == 'interest_reinvest':
                # Buy SCHD with interest
                trader.buy(action['buy_symbol'], action['amount'])
                logger.info(f"✅ Interest reinvested: {action['amount']:,.0f} KRW")
                
            elif action_type == 'rebalance':
                # Execute rebalancing trade
                import time
                trade_action = action.get('trade_action', 'buy')
                if trade_action == 'buy':
                    trader.buy(action['symbol'], action['amount_krw'])
                else:
                    trader.sell(action['symbol'], action['amount_krw'])
                logger.info(f"✅ Rebalance executed: {trade_action} {action['symbol']}")
                # Rate limit: wait 1 second between orders
                time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute action {action_type}: {e}")
            return False
