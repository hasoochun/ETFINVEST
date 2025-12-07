"""Bot Controller API for Telegram bot integration"""

import logging
import pytz
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
        self.portfolio_manager = None
        self.rebalancing_engine = None
        self.is_simulation = False
        self.is_accelerated = False  # Accelerated testing mode (10 min = 1 day, 3% profit)
        self.last_update_time = datetime.now()
        
        # Dip buying mode settings
        self.dip_buy_mode = 'accelerated'  # 'daily' or 'accelerated'
        self.last_dip_buy_time = None
        
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
        # Update heartbeat to refresh last_update_time
        self.update_heartbeat()
        
        # Calculate uptime
        uptime = "0h 0m 0s"
        if self.start_time:
            delta = datetime.now() - self.start_time
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            seconds = delta.seconds % 60
            uptime = f"{hours}h {minutes}m {seconds}s"
        
        # Determine market status
        if self.is_simulation:
            market_open = True
            market_status = "🟢 SIMULATION (OPEN)"
            next_open = "Running..."
        elif self.is_accelerated:
            # Accelerated mode: check actual market hours
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            is_weekday = now.weekday() < 5
            current_hour = now.hour
            current_minute = now.minute
            
            is_market_time = (23 <= current_hour or current_hour < 6)
            if current_hour == 23 and current_minute < 30:
                is_market_time = False
                
            market_open = is_weekday and is_market_time
            market_status = "⚡ ACCELERATED" + (" (OPEN)" if market_open else " (CLOSED)")
            
            if market_open:
                next_open = "Market is Open"
            else:
                target = now.replace(hour=23, minute=30, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)
                while target.weekday() >= 5:
                    target += timedelta(days=1)
                
                diff = target - now
                hours = diff.seconds // 3600
                minutes = (diff.seconds % 3600) // 60
                next_open = f"{hours}h {minutes}m"
        else:
            # TODO: Link with actual scheduler if possible, for now use simple time check
            # This is a simplified check, ideally we should ask the scheduler
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            is_weekday = now.weekday() < 5
            # US Market hours in KST (approximate for display)
            # Winter time: 23:30 - 06:00
            current_hour = now.hour
            current_minute = now.minute
            
            # Simple check for display purposes
            is_market_time = (23 <= current_hour or current_hour < 6)
            if current_hour == 23 and current_minute < 30:
                is_market_time = False
                
            market_open = is_weekday and is_market_time
            market_status = "🟢 OPEN" if market_open else "🔴 CLOSED"
            
            if market_open:
                next_open = "Market is Open"
            else:
                # Calculate time until 23:30
                target = now.replace(hour=23, minute=30, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)
                while target.weekday() >= 5: # Skip weekends
                    target += timedelta(days=1)
                
                diff = target - now
                total_seconds = int(diff.total_seconds())
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                minutes = (total_seconds % 3600) // 60
                
                if days > 0:
                    next_open = f"{days}d {hours}h {minutes}m"
                else:
                    next_open = f"{hours}h {minutes}m"

        # Calculate last update time
        update_delta = datetime.now() - self.last_update_time
        if update_delta.seconds < 60:
            last_update_str = f"{update_delta.seconds}s ago"
        else:
            last_update_str = f"{update_delta.seconds // 60}m ago"

        # Determine mode display
        if self.is_simulation:
            mode_str = '🧪 SIMULATION'
        elif self.is_accelerated:
            mode_str = '⚡ ACCELERATED (10min=1day, 3%)'
        else:
            mode_str = '📝 PAPER TRADING'

        return {
            'is_running': self.is_running,
            'status': 'RUNNING' if self.is_running else 'STOPPED',
            'trading_symbol': self.trading_symbol,
            'market_open': market_open,
            'market_status': market_status,
            'mode': mode_str,
            'uptime': uptime,
            'next_open': next_open,
            'last_update': last_update_str
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
    def update_heartbeat(self):
        """Update the last update timestamp"""
        self.last_update_time = datetime.now()

    def set_dip_buy_mode(self, mode: str):
        """
        Set dip buying mode
        
        Args:
            mode: 'daily' or 'accelerated'
        """
        if mode not in ['daily', 'accelerated']:
            raise ValueError("Mode must be 'daily' or 'accelerated'")
        self.dip_buy_mode = mode
        logger.info(f"Dip buy mode changed to: {mode}")
    
    def get_next_dip_buy_time(self) -> str:
        """
        Calculate next dip buy time based on mode
        
        Returns:
            String describing next buy time
        """
        from datetime import timedelta
        import pytz
        
        if self.dip_buy_mode == 'daily':
            # Next market close - 5 minutes (15:55 ET)
            et = pytz.timezone('US/Eastern')
            now_et = datetime.now(et)
            
            # Create buy window time (15:55)
            buy_time = now_et.replace(hour=15, minute=55, second=0, microsecond=0)
            
            # If past buy time today, show tomorrow
            if now_et >= buy_time:
                buy_time += timedelta(days=1)
            
            return buy_time.strftime("%H:%M ET")
        else:
            # Accelerated: 10 minutes from last buy
            if self.last_dip_buy_time:
                next_time = self.last_dip_buy_time + timedelta(minutes=10)
                now = datetime.now()
                
                if next_time > now:
                    remaining = (next_time - now).total_seconds() / 60
                    return f"{int(remaining)}분 후"
                else:
                    return "즉시"
            return "즉시"

