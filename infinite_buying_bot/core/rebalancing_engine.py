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
    
    def __init__(self, portfolio_manager, accelerated=False):
        """
        Initialize rebalancing engine
        
        Args:
            portfolio_manager: PortfolioManager instance
            accelerated: If True, use 3% profit target for faster testing
        """
        self.portfolio = portfolio_manager
        self.is_accelerated = accelerated
        self.aggressive_etf = portfolio_manager.aggressive_etf  # Get from portfolio manager
        
        # Aggressive ETF strategy parameters (renamed from TQQQ)
        if accelerated:
            self.aggressive_etf_target_profit = 0.03  # +3% profit target (accelerated testing)
            logger.info(f"⚡ Rebalancing Engine initialized with 3% profit target (ACCELERATED MODE), ETF: {self.aggressive_etf}")
        else:
            self.aggressive_etf_target_profit = 0.10  # +10% profit target (normal mode)
            logger.info(f"Rebalancing Engine initialized with 10% profit target, ETF: {self.aggressive_etf}")
        
        # 40/80 split strategy (using SHV as buffer)
        # - Price < Avg: SHV / 40 (aggressive)
        # - Price >= Avg: SHV / 80 (conservative)
        
        # Track aggressive ETF average price for infinite buying
        self.aggressive_etf_entry_avg = 0.0
        self.aggressive_etf_total_invested = 0.0
    
    def update_aggressive_etf_average(self, quantity: int, price: float):
        """
        Update aggressive ETF average price after purchase
        
        Args:
            quantity: Shares bought
            price: Purchase price
        """
        current_qty = self.portfolio.positions[self.aggressive_etf]['quantity']
        current_avg = self.portfolio.positions[self.aggressive_etf]['avg_price']
        
        if current_qty == 0:
            self.aggressive_etf_entry_avg = price
        else:
            total_cost = (current_qty * current_avg) + (quantity * price)
            total_qty = current_qty + quantity
            self.aggressive_etf_entry_avg = total_cost / total_qty
        
        self.aggressive_etf_total_invested += quantity * price
        logger.info(f"{self.aggressive_etf} avg updated: {self.aggressive_etf_entry_avg:.2f}, total invested: {self.aggressive_etf_total_invested:,.0f}")
    
    def check_aggressive_etf_profit_target(self) -> Optional[Dict]:
        """
        Check if aggressive ETF reached profit target
        
        Returns:
            Trade action dict if target reached, None otherwise
        """
        etf_pos = self.portfolio.positions[self.aggressive_etf]
        if etf_pos['quantity'] == 0:
            return None
        
        current_price = etf_pos['current_price']
        avg_price = etf_pos['avg_price']
        
        if avg_price == 0:
            return None
        
        profit_pct = (current_price - avg_price) / avg_price
        
        if profit_pct >= self.aggressive_etf_target_profit:
            # Sell all aggressive ETF, buy SCHD with profits
            profit_amount = etf_pos['quantity'] * (current_price - avg_price)
            
            # Floor profit amount to integer
            profit_amount = int(profit_amount)
            
            logger.info(f"🎯 {self.aggressive_etf} profit target reached: +{profit_pct*100:.1f}%")
            
            return {
                'action': 'profit_taking',
                'sell_symbol': self.aggressive_etf,
                'sell_quantity': etf_pos['quantity'],
                'buy_symbol': 'SCHD',
                'profit_amount': profit_amount,
                'profit_pct': profit_pct * 100,
                'reason': f'Profit target +{self.aggressive_etf_target_profit*100:.0f}% reached'
            }
        
        return None
    
    def check_aggressive_etf_dip_buying(self) -> Optional[Dict]:
        """
        Check if aggressive ETF should be bought using SHV buffer
        Uses 40/80 split strategy based on average price
        
        Returns:
            Trade action dict if buying needed, None otherwise
        """
        etf_pos = self.portfolio.positions[self.aggressive_etf]
        shv_pos = self.portfolio.positions['SHV']
        
        # Need SHV to buy aggressive ETF
        if shv_pos['quantity'] == 0:
            return None
        
        current_price = etf_pos['current_price']
        avg_price = etf_pos['avg_price']
        
        # Calculate SHV total value
        shv_value = shv_pos['quantity'] * shv_pos['current_price']
        
        # Determine split count based on price vs average
        if etf_pos['quantity'] == 0:
            # Initial entry: aggressive 40 split
            split_count = 40
            reason = f"Initial {self.aggressive_etf} entry"
        elif avg_price > 0 and current_price < avg_price:
            # Below average: aggressive 40 split
            split_count = 40
            reason = f"Price below avg (${current_price:.2f} < ${avg_price:.2f})"
        elif avg_price > 0 and current_price >= avg_price:
            # Above average: conservative 80 split
            split_count = 80
            reason = f"Price above avg (${current_price:.2f} ≥ ${avg_price:.2f})"
        else:
            # No position yet, use aggressive
            split_count = 40
            reason = "No average price yet"
        
        # Calculate buy amount from SHV
        buy_amount = shv_value / split_count
        
        # Floor to avoid decimal issues in trading
        buy_amount = int(buy_amount)
        
        # Minimum buy threshold ($100)
        if buy_amount < 100:
            return None
        
        logger.info(f"📉 {self.aggressive_etf} buy signal: {reason}, buying ${buy_amount:,.0f} (1/{split_count} of SHV)")
        
        return {
            'action': 'dip_buying',
            'sell_symbol': 'SHV',
            'sell_amount': buy_amount,
            'buy_symbol': self.aggressive_etf,
            'split_count': split_count,
            'current_price': current_price,
            'avg_price': avg_price,
            'reason': reason
        }
    
    def check_shv_interest_reinvest(self, monthly_interest: float) -> Optional[Dict]:
        """
        Check if SHV interest should be reinvested into SCHD
        
        Args:
            monthly_interest: Monthly interest earned from SHV
        
        Returns:
            Trade action dict
        """
        # Floor to integer
        monthly_interest = int(monthly_interest)
        
        if monthly_interest > 100:  # Minimum $100
            logger.info(f"💰 SHV interest reinvest: {monthly_interest:,.0f} KRW → SCHD")
            
            return {
                'action': 'interest_reinvest',
                'source': 'SHV_interest',
                'buy_symbol': 'SCHD',
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
        
        # 1. Check aggressive ETF profit target (highest priority)
        profit_action = self.check_aggressive_etf_profit_target()
        if profit_action:
            actions.append(profit_action)
            return actions  # Execute profit-taking immediately
        
        # 2. Check aggressive ETF dip buying
        dip_action = self.check_aggressive_etf_dip_buying()
        if dip_action:
            actions.append(dip_action)
        
        # 3. Check periodic rebalancing (if no other actions)
        if not actions and self.portfolio.needs_rebalancing(threshold=0.10):
            rebalance_trades = self.portfolio.calculate_rebalancing_trades()
            for trade in rebalance_trades:
                actions.append({
                    'action': 'rebalance',
                    **trade
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
                # Sell all aggressive ETF
                trader.sell(action['sell_symbol'], action['sell_quantity'])
                # Buy SCHD with profits
                trader.buy(action['buy_symbol'], action['profit_amount'])
                # Reset aggressive ETF tracking
                self.aggressive_etf_entry_avg = 0.0
                self.aggressive_etf_total_invested = 0.0
                logger.info(f"✅ Profit taking executed: {action['profit_pct']:.1f}%")
                
            elif action_type == 'dip_buying':
                # Sell SHV
                trader.sell(action['sell_symbol'], action['sell_amount'])
                # Buy aggressive ETF
                trader.buy(action['buy_symbol'], action['sell_amount'])
                logger.info(f"✅ Dip buying executed: {action['buy_symbol']}")
                
            elif action_type == 'interest_reinvest':
                # Buy SCHD with interest
                trader.buy(action['buy_symbol'], action['amount'])
                logger.info(f"✅ Interest reinvested: {action['amount']:,.0f} KRW")
                
            elif action_type == 'rebalance':
                # Execute rebalancing trade
                if action['action'] == 'buy':
                    trader.buy(action['symbol'], action['amount_krw'])
                else:
                    trader.sell(action['symbol'], action['amount_krw'])
                logger.info(f"✅ Rebalance executed: {action['symbol']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute action {action_type}: {e}")
            return False
