"""
Portfolio Manager - Multi-Asset Allocation Management
Manages 3-asset portfolio: TQQQ (30%), SHV (50%), SCHD (20%)
"""
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manages multi-asset portfolio allocation and tracking"""
    
    def __init__(self, initial_capital: float = 100000000.0):
        """
        Initialize portfolio manager
        
        Args:
            initial_capital: Initial capital in KRW (default: 1억)
        """
        self.initial_capital = initial_capital
        
        # Target allocation (percentages)
        self.target_allocation = {
            'TQQQ': 0.30,  # 30% - Short-term trading
            'SHV': 0.50,   # 50% - Cash buffer
            'SCHD': 0.20   # 20% - Long-term accumulation (grows over time)
        }
        
        # Current positions (will be updated from Trader)
        self.positions = {
            'TQQQ': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0},
            'SHV': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0},
            'SCHD': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0}
        }
        
        self.cash = initial_capital
        
        logger.info(f"Portfolio Manager initialized with {initial_capital:,.0f} KRW")
    
    def update_positions(self, positions: Dict[str, Dict]):
        """
        Update current positions from Trader
        
        Args:
            positions: Dict of {symbol: {quantity, avg_price, current_price}}
        """
        for symbol in ['TQQQ', 'SHV', 'SCHD']:
            if symbol in positions:
                self.positions[symbol] = positions[symbol]
        
        logger.debug(f"Positions updated: {self.positions}")
    
    def update_cash(self, cash: float):
        """Update current cash balance"""
        self.cash = cash
    
    def get_total_value(self) -> float:
        """Calculate total portfolio value"""
        stock_value = sum(
            pos['quantity'] * pos['current_price']
            for pos in self.positions.values()
        )
        return self.cash + stock_value
    
    def get_current_allocation(self) -> Dict[str, float]:
        """
        Get current allocation percentages
        
        Returns:
            Dict of {symbol: percentage}
        """
        total_value = self.get_total_value()
        if total_value == 0:
            return {symbol: 0.0 for symbol in self.target_allocation}
        
        allocation = {}
        for symbol, pos in self.positions.items():
            value = pos['quantity'] * pos['current_price']
            allocation[symbol] = value / total_value
        
        allocation['CASH'] = self.cash / total_value
        
        return allocation
    
    def get_allocation_drift(self) -> Dict[str, float]:
        """
        Calculate drift from target allocation
        
        Returns:
            Dict of {symbol: drift_percentage}
        """
        current = self.get_current_allocation()
        drift = {}
        
        for symbol, target in self.target_allocation.items():
            current_pct = current.get(symbol, 0.0)
            drift[symbol] = current_pct - target
        
        return drift
    
    def needs_rebalancing(self, threshold: float = 0.05) -> bool:
        """
        Check if portfolio needs rebalancing
        
        Args:
            threshold: Drift threshold (default: 5%)
        
        Returns:
            True if any asset drifted more than threshold
        """
        drift = self.get_allocation_drift()
        return any(abs(d) > threshold for d in drift.values())
    
    def calculate_rebalancing_trades(self) -> List[Dict]:
        """
        Calculate trades needed to rebalance to target allocation
        
        Returns:
            List of {symbol, action (buy/sell), amount_usd}
        """
        total_value = self.get_total_value()
        current_alloc = self.get_current_allocation()
        trades = []
        
        for symbol, target_pct in self.target_allocation.items():
            current_pct = current_alloc.get(symbol, 0.0)
            drift = current_pct - target_pct
            
            if abs(drift) > 0.01:  # 1% minimum
                target_value = total_value * target_pct
                current_value = self.positions[symbol]['quantity'] * self.positions[symbol]['current_price']
                diff_value = target_value - current_value
                
                if diff_value > 0:
                    trades.append({
                        'symbol': symbol,
                        'action': 'buy',
                        'amount_krw': diff_value,
                        'reason': f'Rebalance: {current_pct:.1%} → {target_pct:.1%}'
                    })
                else:
                    trades.append({
                        'symbol': symbol,
                        'action': 'sell',
                        'amount_krw': abs(diff_value),
                        'reason': f'Rebalance: {current_pct:.1%} → {target_pct:.1%}'
                    })
        
        return trades
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        total_value = self.get_total_value()
        current_alloc = self.get_current_allocation()
        drift = self.get_allocation_drift()
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'positions': self.positions,
            'current_allocation': current_alloc,
            'target_allocation': self.target_allocation,
            'allocation_drift': drift,
            'needs_rebalancing': self.needs_rebalancing(),
            'total_return_pct': ((total_value - self.initial_capital) / self.initial_capital) * 100
        }
    
    def update_target_allocation(self, new_allocation: Dict[str, float]):
        """
        Update target allocation (for user customization)
        
        Args:
            new_allocation: Dict of {symbol: percentage}
        """
        # Validate sum = 1.0
        total = sum(new_allocation.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Allocation must sum to 100%, got {total*100:.1f}%")
        
        self.target_allocation = new_allocation
        logger.info(f"Target allocation updated: {new_allocation}")
