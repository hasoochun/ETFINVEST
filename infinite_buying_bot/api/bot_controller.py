"""Bot Controller API for Telegram bot integration"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class BotController:
    """
    Controller for managing trading bot from Telegram
    Provides API for status queries and control commands
    """
    
    def __init__(self):
        """Initialize bot controller"""
        self.is_running = False
        self.entry_allowed = True
        self.start_time = None
        self.notifier = None
        self.trader = None
        self.trading_symbol = "TQQQ"  # Default ETF (changed from SOXL to TQQQ)
        logger.info("Bot controller initialized")
    
    def set_trader(self, trader):
        """Set trader instance"""
        self.trader = trader
    
    def set_notifier(self, notifier):
        """Set notifier instance"""
        self.notifier = notifier
    
    def get_status(self) -> Dict:
        """
        Get current bot status
        
        Returns:
            Dictionary with status information
        """
        uptime = "N/A"
        if self.start_time:
            delta = datetime.now() - self.start_time
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            seconds = delta.seconds % 60
            uptime = f"{hours}h {minutes}m {seconds}s"
        
        # TODO: Get actual market status from scheduler
        market_open = False
        market_status = "CLOSED"
        next_open = "4h 42m"
        
        return {
            'is_running': self.is_running,
            'status': 'RUNNING' if self.is_running else 'STOPPED',
            'trading_symbol': self.trading_symbol,
            'market_open': market_open,
            'market_status': market_status,
            'mode': 'PAPER TRADING',  # TODO: Get from config
            'uptime': uptime,
            'next_open': next_open,
            'last_update': '30s ago'  # TODO: Get actual last update time
        }
    
    def get_balance(self) -> Dict:
        """Return current account balance using the linked Trader.

        The Trader's ``get_balance`` method returns a tuple:
        ``(buying_power, quantity, avg_price)`` where:
        * **buying_power** – cash available for new orders
        * **quantity** – number of shares currently held
        * **avg_price** – average purchase price of the held shares
        """
        if not self.trader:
            # Fallback to placeholder if trader not set
            logger.warning("Trader not attached – returning placeholder balance")
            return {
                'cash': 0.0,
                'stocks': 0.0,
                'total': 0.0,
                'pnl': 0.0,
                'pnl_pct': 0.0,
            }
        # Retrieve raw data from Trader
        buying_power, quantity, avg_price = self.trader.get_balance()
        # Current market price for the symbol
        current_price = self.trader.get_price()
        # Calculate derived values
        stock_value = quantity * (current_price or 0)
        total = buying_power + stock_value
        pnl = (current_price - avg_price) * quantity if quantity > 0 and current_price else 0.0
        pnl_pct = (pnl / (avg_price * quantity) * 100) if quantity > 0 and avg_price else 0.0
        return {
            'cash': round(buying_power, 2),
            'stocks': round(stock_value, 2),
            'total': round(total, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        }
    
    def get_position(self) -> Optional[Dict]:
        """Return the current held position using the linked Trader.

        The returned dictionary matches the format expected by the
        Telegram ``format_position`` function.
        """
        if not self.trader:
            logger.warning("Trader not attached – returning placeholder position")
            return None
        # Get raw balance data (cash, quantity, avg_price)
        _, quantity, avg_price = self.trader.get_balance()
        if quantity == 0:
            return None
        # Current market price
        current_price = self.trader.get_price()
        # Compute derived fields
        value = quantity * (current_price or 0)
        pnl = (current_price - avg_price) * quantity if current_price else 0.0
        pnl_pct = (pnl / (avg_price * quantity) * 100) if avg_price else 0.0
        return {
            'symbol': getattr(self.trader, 'symbol', 'UNKNOWN'),
            'quantity': quantity,
            'avg_price': round(avg_price, 2),
            'current_price': round(current_price, 2) if current_price else 0.0,
            'value': round(value, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        }
    
    def get_holdings(self) -> list:
        """Get all holdings from trader"""
        if not self.trader:
            return []
        return self.trader.get_all_holdings()
    
    def get_pnl(self) -> Dict:
        """
        Get profit and loss information
        
        Returns:
            Dictionary with P&L information
        """
        # TODO: Get actual P&L from trader
        return {
            'pnl': 0.00,
            'pnl_pct': 0.00,
            'today_pnl': 0.00,
            'week_pnl': 0.00,
            'month_pnl': 0.00
        }
    
    def stop_entry(self):
        """Stop entering new positions"""
        self.entry_allowed = False
        logger.info("Entry stopped - no new positions will be opened")
    
    def resume_entry(self):
        """Resume entering new positions"""
        self.entry_allowed = True
        logger.info("Entry resumed - new positions allowed")
    
    def force_exit_all(self):
        """Force exit all positions"""
        logger.warning("Force exit all positions requested")
        # TODO: Implement actual force exit logic
        if self.trader:
            # self.trader.sell_all()
            pass
    
    def emergency_stop(self):
        """Emergency stop - stop bot and exit all positions"""
        logger.critical("EMERGENCY STOP activated")
        self.is_running = False
        self.force_exit_all()
        # TODO: Implement emergency stop logic
    
    async def start(self):
        """Start the bot controller"""
        self.is_running = True
        self.start_time = datetime.now()
        logger.info("Bot controller started")
        
        if self.notifier:
            self.notifier.send_bot_started()
    
    async def stop(self):
        """Stop the bot controller"""
        self.is_running = False
        logger.info("Bot controller stopped")
        
        if self.notifier:
            self.notifier.send_bot_stopped()
