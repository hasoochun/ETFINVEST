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
        
        # Dip buying interval (10 minutes for accelerated testing)
        self.dip_buy_interval_minutes = 10
        self.last_dip_buy_time = None
    
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
