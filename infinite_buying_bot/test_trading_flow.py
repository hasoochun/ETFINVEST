import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Add path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.utils.notifier import Notifier
from infinite_buying_bot.core.strategy import InfiniteBuyingStrategy
from infinite_buying_bot.core.trader import Trader
import yaml

def test_trading_flow():
    print("=" * 60)
    print("MOCK TRADING FLOW TEST")
    print("=" * 60)
    
    # Load config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'kis_devlp.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Override notification settings
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        if 'notification' not in config: config['notification'] = {}
        config['notification']['telegram_token'] = os.getenv("TELEGRAM_BOT_TOKEN")
    if os.getenv("TELEGRAM_CHAT_ID"):
        if 'notification' not in config: config['notification'] = {}
        config['notification']['telegram_chat_id'] = os.getenv("TELEGRAM_CHAT_ID")
    
    # Initialize components
    notifier = Notifier(config)
    trader = Trader(config, notifier)
    trader.env_mode = "demo"  # Force demo mode
    
    # Re-authenticate with demo mode
    from infinite_buying_bot.api import kis_auth as ka
    ka.auth(svr='vps', product='01')
    trader.trenv = ka.getTREnv()
    
    print("\n1. Testing Balance Retrieval...")
    buying_power, quantity, avg_price = trader.get_balance()
    print(f"   ✓ Buying Power: ${buying_power:,.2f}")
    print(f"   ✓ Quantity: {quantity}")
    print(f"   ✓ Avg Price: ${avg_price:.2f}")
    
    if buying_power == 0:
        print("\n   ❌ ERROR: Buying power is 0!")
        return False
    
    print("\n2. Testing Price Retrieval...")
    current_price = trader.get_price()
    if current_price:
        print(f"   ✓ Current Price of {trader.symbol}: ${current_price:.2f}")
    else:
        print(f"   ❌ ERROR: Failed to get price for {trader.symbol}")
        return False
    
    print("\n3. Testing Buy Logic (DRY RUN - No actual order)...")
    split_count = 40
    buy_amount = buying_power / split_count
    print(f"   ✓ Would buy ${buy_amount:,.2f} worth of {trader.symbol}")
    print(f"   ✓ At price ${current_price:.2f}, that's ~{int(buy_amount / current_price)} shares")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Account has ${buying_power:,.2f} available")
    print(f"  - {trader.symbol} is trading at ${current_price:.2f}")
    print(f"  - Bot is ready to trade!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_trading_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
