"""
Bot Controller (Production Only / Clean Version)
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

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
        
    def set_trader(self, trader):
        self.trader = trader
        
    def set_notifier(self, notifier):
        self.notifier = notifier
        
    def start_bot(self):
        self.is_running = True
        self.start_time = datetime.now()
        if self.notifier: self.notifier.send("🔴 **BOT STARTED** (REAL)")
        
    def stop_bot(self):
        self.is_running = False
        if self.notifier: self.notifier.send("Paused.")
        
    def get_status(self):
        return {
            'is_running': self.is_running,
            'status': 'RUNNING' if self.is_running else 'STOPPED',
            'trading_symbol': self.trading_symbol,
            'market_open': True, # Simple assumption or check logic
            'market_status': "🟢 OPEN",
            'mode': "💰 REAL TRADING", # HARDCODED
            'uptime': str(datetime.now() - self.start_time).split('.')[0] if self.start_time else "0:00",
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
