import sys
import os
from datetime import datetime
import yaml

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from infinite_buying_bot.api.bot_controller import BotController
from infinite_buying_bot.utils.scheduler import MarketScheduler

def test_status():
    print("Testing BotController Timezone Logic...")
    
    # Initialize real scheduler
    scheduler = MarketScheduler()
    tz = scheduler.tz
    now = datetime.now(tz)
    print(f"Current Time (US/Eastern): {now}")
    print(f"Is Market Open (Scheduler): {scheduler.is_market_open()}")
    print(f"Time until open: {scheduler.get_time_until_open()}")
    
    # Initialize controller
    controller = BotController()
    controller.set_scheduler(scheduler)
    
    status = controller.get_status()
    print("\nBot Controller Status:")
    print(f"Market Status: {status['market_status']}")
    print(f"Next Open: {status['next_open']}")
    
    # Validation
    if scheduler.is_market_open():
        assert "OPEN" in status['market_status']
    else:
        assert "CLOSED" in status['market_status']
        if "Market is Open" not in status['next_open']:
             print(f"Countdown verified: {status['next_open']}")

if __name__ == "__main__":
    test_status()
