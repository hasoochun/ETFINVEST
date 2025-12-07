from datetime import datetime, timedelta
import pytz

def test_logic():
    kst = pytz.timezone('Asia/Seoul')
    # Force 'now' to be Sunday Dec 7th 2025 12:00 PM
    # Note: User says "Dec 7th Sunday". 2025 Dec 7 IS Sunday.
    now = datetime(2025, 12, 7, 12, 0, 0, tzinfo=kst)
    
    print(f"Fake Now: {now} (Weekday: {now.weekday()})")
    
    target = now.replace(hour=23, minute=30, second=0, microsecond=0)
    print(f"Initial Target: {target} (Weekday: {target.weekday()})")
    
    if now >= target:
        target += timedelta(days=1)
        print("Now >= Target, added 1 day")
        
    while target.weekday() >= 5: # Skip weekends
        print(f"Skipping weekend day: {target.strftime('%A')}")
        target += timedelta(days=1)
        
    print(f"Final Target: {target} (Weekday: {target.weekday()})")
    
    diff = target - now
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    days = diff.days
    
    print(f"Diff: {days} days, {hours}h {minutes}m")
    
    # Logic in bot_controller.py
    # hours = diff.seconds // 3600
    # minutes = (diff.seconds % 3600) // 60
    # next_open = f"{hours}h {minutes}m"
    # IT DOES NOT INCLUDE DAYS!!!!!
    
    print(f"Bot Output: {hours}h {minutes}m")

if __name__ == "__main__":
    test_logic()
