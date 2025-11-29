"""
Manual E2E Test - Execute a single buy order to test notifications
"""

import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.telegram_bot.notifications import TelegramNotifier

print("\n" + "="*70)
print("  🧪 Manual E2E Test - Single Buy Order")
print("="*70)

# Load config
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kis_devlp.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Add strategy config
config['strategy'] = {
    'symbol': 'SOXL',
    'exchange': 'NASD',
    'currency': 'USD',
    'profit_target_pct': 10.0,
    'split_count_low': 80,
    'split_count_high': 40
}

# Initialize notifier
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

if bot_token and chat_id:
    print(f"\n✅ Telegram enabled for chat_id: {chat_id}")
    notifier = TelegramNotifier(bot_token, chat_id)
    notifier.send("🧪 **Manual E2E Test Started**\nTesting split buying strategy with Telegram notifications")
else:
    print("\n⚠️ Telegram disabled - using mock")
    class MockNotifier:
        def send(self, message):
            print(f"[NOTIFICATION] {message}")
    notifier = MockNotifier()

# Initialize trader
print("\n=== Initializing Trader ===")
trader = Trader(config, notifier)

# Get current state
print("\n=== Current State ===")
price = trader.get_price()
buying_power, quantity, avg_price = trader.get_balance()

print(f"Symbol: {trader.symbol}")
print(f"Current Price: ${price:.2f}" if price else "Current Price: N/A")
print(f"Buying Power: ${buying_power:,.2f}")
print(f"Holdings: {quantity} shares @ ${avg_price:.2f}")

# Test buy order with small amount
print("\n=== Test 1: Buy Order (Initial Entry) ===")
print("Testing buy order with $100 (1/40 split)")
print("This will send detailed Telegram notification...")

time.sleep(2)

# Execute buy
trader.buy(
    amount=100.0,
    split_count=40,
    reason="Initial Entry (Test)"
)

print("\n✅ Buy order test completed!")
print("📱 Check your Telegram for detailed notification")

# Wait a moment
time.sleep(3)

# Get updated state
print("\n=== Updated State ===")
buying_power2, quantity2, avg_price2 = trader.get_balance()
print(f"Buying Power: ${buying_power2:,.2f}")
print(f"Holdings: {quantity2} shares @ ${avg_price2:.2f}")

# Send completion notification
notifier.send("✅ **Manual E2E Test Completed**\nBuy order executed successfully")

print("\n" + "="*70)
print("  Test completed - Check Telegram for notifications!")
print("="*70)
