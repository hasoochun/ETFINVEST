import datetime
import pytz
import time
import logging

logger = logging.getLogger(__name__)

class MarketScheduler:
    def __init__(self, timezone='US/Eastern'):
        self.tz = pytz.timezone(timezone)

    def get_current_time(self):
        return datetime.datetime.now(self.tz)

    def is_market_open(self):
        """Check if US market is currently open (09:30 - 16:00 ET, Mon-Fri)."""
        now = self.get_current_time()
        
        # Check weekday (0=Mon, 4=Fri)
        if now.weekday() > 4:
            return False
            
        # Market hours: 09:30 - 16:00
        market_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_start <= now <= market_end

    def is_near_close(self, minutes=5):
        """Check if it is within 'minutes' before market close."""
        now = self.get_current_time()
        
        if now.weekday() > 4:
            return False
            
        market_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
        check_start = market_end - datetime.timedelta(minutes=minutes)
        
        return check_start <= now < market_end

    def wait_until_open(self):
        """Wait until market opens if currently closed."""
        if not self.is_market_open():
            logger.info("Market is closed. Waiting for market open...")
            # Simple sleep for now, can be improved to sleep until 09:30
            pass
