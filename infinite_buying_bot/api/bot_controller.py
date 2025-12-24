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
        
        # Strategy settings (synced from runtime_config.json)
        self.strategy_mode = "neutral"  # aggressive, neutral, defensive
        self.dip_buy_mode = "accelerated"  # CHANGED: 'accelerated' for test (was 'daily')
        self.last_dip_buy_time = None
        self.entry_allowed = True
        self.accel_interval_minutes = 5  # NEW: 5-minute interval for accelerated test
        
    def set_trader(self, trader):
        self.trader = trader
        
    def set_notifier(self, notifier):
        self.notifier = notifier
        
    def start_bot(self):
        self.is_running = True
        self.start_time = datetime.now()
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
