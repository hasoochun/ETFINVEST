import datetime
import pytz

def get_current_time_et():
    """Get current time in US Eastern Time."""
    # US Eastern Timezone
    et_tz = pytz.timezone('US/Eastern')
    return datetime.datetime.now(et_tz)

def is_market_open():
    """Check if US market is currently open (09:30 - 16:00 ET, Mon-Fri)."""
    now_et = get_current_time_et()
    
    # Check weekday (0=Mon, 4=Fri)
    if now_et.weekday() > 4:
        return False
        
    # Market hours: 09:30 - 16:00
    market_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_start <= now_et <= market_end

def is_near_market_close(minutes=5):
    """Check if it is within 'minutes' before market close."""
    now_et = get_current_time_et()
    
    if now_et.weekday() > 4:
        return False
        
    market_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    check_start = market_end - datetime.timedelta(minutes=minutes)
    
    return check_start <= now_et < market_end

def get_seconds_until_close():
    """Get seconds remaining until market close."""
    now_et = get_current_time_et()
    market_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    
    delta = market_end - now_et
    return max(0, delta.total_seconds())
