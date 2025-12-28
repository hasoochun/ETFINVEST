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
    
    def __init__(self, initial_capital: float = 0.0, aggressive_etf: str = 'TQQQ'):
        """
        Initialize portfolio manager
        
        Args:
            initial_capital: Initial capital in KRW (default: 1억)
            aggressive_etf: ETF to use for aggressive position (default: TQQQ)
        """
        self.initial_capital = initial_capital
        self.aggressive_etf = aggressive_etf
        
        # Target allocation (percentages) - 4종목 구성
        self.target_allocation = {
            'TQQQ': 0.10,   # 10% - Aggressive (3x leverage)
            'MAGS': 0.20,   # 20% - Magnificent 7
            'SHV': 0.50,    # 50% - Cash buffer
            'JEPI': 0.20    # 20% - Income generation
        }
        
        # Current positions (will be updated from Trader) - DYNAMIC
        self.positions = {
            'TQQQ': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0},
            'MAGS': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0},
            'SHV': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0},
            'JEPI': {'quantity': 0, 'avg_price': 0.0, 'current_price': 0.0}
        }
        
        self.cash = initial_capital
        
        logger.info(f"Portfolio Manager initialized with {initial_capital:,.0f} KRW, 4-asset strategy")
    
    def update_positions(self, positions: Dict[str, Dict]):
        """
        Update current positions from Trader
        
        Args:
            positions: Dict of {symbol: {quantity, avg_price, current_price}}
        """
        for symbol in ['TQQQ', 'MAGS', 'SHV', 'JEPI']:
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
                    # Need to buy - no restrictions
                    trades.append({
                        'symbol': symbol,
                        'action': 'buy',
                        'amount_krw': diff_value,
                        'reason': f'Rebalance: {current_pct:.1%} → {target_pct:.1%}'
                    })
                else:
                    # Need to sell - check profit protection
                    pos = self.positions[symbol]
                    avg_price = pos['avg_price']
                    current_price = pos['current_price']
                    
                    # Calculate profit percentage
                    if avg_price > 0:
                        profit_pct = ((current_price - avg_price) / avg_price) * 100
                    else:
                        profit_pct = 0
                    
                    # [LOSS PROTECTION] Only sell if:
                    # 1. In profit (profit_pct > 0)
                    # 2. Profit >= 10%
                    if profit_pct >= 10:
                        trades.append({
                            'symbol': symbol,
                            'action': 'sell',
                            'amount_krw': abs(diff_value),  # Only excess portion
                            'reason': f'Profit taking ({profit_pct:.1f}%): {current_pct:.1%} → {target_pct:.1%}'
                        })
                        logger.info(f"[SELL] {symbol}: profit {profit_pct:.1f}% >= 10%, selling excess")
                    else:
                        # Skip sell - loss protection active
                        logger.info(f"[SKIP SELL] {symbol}: profit {profit_pct:.1f}% < 10%, protecting position")
        
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

    def calculate_split_buy_order(self, targets: List[str] = None) -> List[Dict]:
        """
        Calculate single split-buy order for Gradual Mode
        Logic: Find assets with >1% deficit and propose buying 1 share.
        
        Args:
            targets: List of ETF symbols to filter (e.g., ['TQQQ', 'MAGS'])
                     If None or ['all'], all ETFs are considered.
        
        Returns:
            List of orders (usually 1 items): [{symbol, qty, price, type='buy'}]
        """
        orders = []
        total_value = self.get_total_value()
        current_alloc = self.get_current_allocation()
        
        # Determine which symbols to process
        target_filter = targets if targets and 'all' not in targets else None
        
        for symbol, target_pct in self.target_allocation.items():
            if target_pct <= 0: continue
            
            # Apply target filter if specified
            if target_filter and symbol not in target_filter:
                logger.debug(f"[SPLIT BUY] {symbol} skipped (not in targets: {target_filter})")
                continue
            
            # Get current data from internal state (must be updated via update_positions first)
            pos = self.positions.get(symbol, {'quantity': 0, 'current_price': 0.0})
            price = pos['current_price']
            if price <= 0: continue
            
            current_pct = current_alloc.get(symbol, 0.0)
            target_pct_100 = target_pct * 100 if target_pct <= 1 else target_pct
            current_pct_100 = current_pct * 100
            
            # Custom Logic: If Deficit > 1% check, propose buying 1 share
            if target_pct_100 - current_pct_100 > 1.0:
                 orders.append({
                     'symbol': symbol,
                     'qty': 1,
                     'price': price,
                     'type': 'buy',
                     'reason': f"Gradual Split: Deficit {target_pct_100 - current_pct_100:.1f}%"
                 })
        
        logger.info(f"[SPLIT BUY] Filter={targets}, Found {len(orders)} orders")
        return orders

    def calculate_st_exchange_order(self) -> List[Dict]:
        """
        Calculate S-T Exchange orders (Sell SHV / Buy TQQQ)
        
        Returns:
             List of orders
        """
        orders = []
        shv_pos = self.positions.get('SHV', {})
        shv_qty = shv_pos.get('quantity', 0)
        
        if shv_qty > 0:
            # Sell 5% (hardcoded strategy logic for now)
            sell_qty = max(1, int(shv_qty * 0.05))
            orders.append({
                'symbol': 'SHV',
                'qty': sell_qty,
                'type': 'sell',
                'reason': "S-T Exchange: Swap Start"
            })
            # Note: Buy order for TQQQ usually happens after fill, or we can assume instant swap in mock
            
        return orders

    def calculate_single_rebalance_order(self, symbol: str, cash_available: float = 0.0) -> Dict:
        """
        Calculate order to rebalance a single ETF to its target allocation.
        
        Args:
            symbol: ETF symbol to rebalance (e.g., 'TQQQ', 'MAGS')
            cash_available: Available cash for buying
            
        Returns:
            Dict with order details:
            {
                'symbol': str,
                'qty': int,
                'price': float,
                'type': 'buy' | 'sell',
                'amount_usd': float,
                'reason': str,
                'current_pct': float,
                'target_pct': float
            }
            or empty dict if no action needed
        """
        # Validate symbol
        if symbol not in self.target_allocation:
            logger.warning(f"[SINGLE REBALANCE] Unknown symbol: {symbol}")
            return {'error': f'Unknown symbol: {symbol}'}
        
        target_pct = self.target_allocation[symbol]
        if target_pct <= 0:
            logger.info(f"[SINGLE REBALANCE] {symbol} has 0% target allocation")
            return {'error': f'{symbol} has 0% target allocation'}
        
        # Get current position
        pos = self.positions.get(symbol, {'quantity': 0, 'current_price': 0.0, 'avg_price': 0.0})
        current_qty = pos.get('quantity', 0)
        current_price = pos.get('current_price', 0.0)
        
        if current_price <= 0:
            logger.warning(f"[SINGLE REBALANCE] {symbol} price not available")
            return {'error': f'{symbol} price not available'}
        
        # Calculate values
        total_value = self.get_total_value()
        current_value = current_qty * current_price
        current_pct = (current_value / total_value) if total_value > 0 else 0
        target_value = total_value * target_pct
        
        # Calculate difference
        diff_value = target_value - current_value
        diff_qty = int(diff_value / current_price)
        
        logger.info(f"[SINGLE REBALANCE] {symbol}: Current {current_pct*100:.1f}% → Target {target_pct*100:.1f}%")
        logger.info(f"[SINGLE REBALANCE] {symbol}: Diff ${diff_value:.2f} = {diff_qty} shares @ ${current_price:.2f}")
        
        if abs(diff_qty) < 1:
            logger.info(f"[SINGLE REBALANCE] {symbol} already at target (diff < 1 share)")
            return {
                'symbol': symbol,
                'qty': 0,
                'price': current_price,
                'type': 'hold',
                'amount_usd': 0,
                'reason': 'Already at target allocation',
                'current_pct': current_pct * 100,
                'target_pct': target_pct * 100
            }
        
        if diff_qty > 0:
            # Need to buy
            # Check cash availability
            required_cash = diff_qty * current_price
            if cash_available > 0 and required_cash > cash_available:
                # Adjust quantity to available cash
                diff_qty = int(cash_available / current_price)
                if diff_qty < 1:
                    return {'error': f'Insufficient cash. Need ${required_cash:.2f}, have ${cash_available:.2f}'}
                logger.info(f"[SINGLE REBALANCE] Adjusted qty to {diff_qty} due to cash limit")
            
            return {
                'symbol': symbol,
                'qty': diff_qty,
                'price': current_price,
                'type': 'buy',
                'amount_usd': diff_qty * current_price,
                'reason': f'Rebalance: {current_pct*100:.1f}% → {target_pct*100:.1f}%',
                'current_pct': current_pct * 100,
                'target_pct': target_pct * 100
            }
        else:
            # Need to sell (diff_qty is negative)
            
            # [LOSS PROTECTION] Check profit before selling
            profit_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
            
            if profit_pct >= 10:
                # Profit >= 10%, allow sell
                logger.info(f"[SINGLE REBALANCE] {symbol}: Profit {profit_pct:.1f}% >= 10%, allow sell")
                return {
                    'symbol': symbol,
                    'qty': abs(diff_qty),
                    'price': current_price,
                    'type': 'sell',
                    'amount_usd': abs(diff_qty) * current_price,
                    'reason': f'Profit taking ({profit_pct:.1f}%): {current_pct*100:.1f}% → {target_pct*100:.1f}%',
                    'current_pct': current_pct * 100,
                    'target_pct': target_pct * 100
                }
            else:
                # Profit < 10%, protect position
                logger.info(f"[SINGLE REBALANCE] {symbol}: Profit {profit_pct:.1f}% < 10%, SKIP SELL (loss protection)")
                return {
                    'symbol': symbol,
                    'qty': 0,
                    'price': current_price,
                    'type': 'hold',
                    'amount_usd': 0,
                    'reason': f'Loss protection: profit {profit_pct:.1f}% < 10%',
                    'current_pct': current_pct * 100,
                    'target_pct': target_pct * 100,
                    'protected': True  # Flag for UI
                }

