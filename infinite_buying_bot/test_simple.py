"""
Simple test to verify KIS API connection and basic functionality
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.telegram_bot.notifications import TelegramNotifier

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
    print(f"Telegram enabled: {chat_id}")
    notifier = TelegramNotifier(bot_token, chat_id)
else:
    print("Telegram disabled - using mock")
    class MockNotifier:
        def send(self, message):
            print(f"[NOTIFICATION] {message}")
    notifier = MockNotifier()

# Initialize trader
print("\n=== Initializing Trader ===")
trader = Trader(config, notifier)

# Test 1: Get current price
print("\n=== Test 1: Get Current Price ===")
price = trader.get_price()
print(f"Current SOXL price: ${price:.2f}" if price else "Failed to get price")

# Test 2: Get balance
print("\n=== Test 2: Get Balance ===")
buying_power, quantity, avg_price = trader.get_balance()
print(f"Buying Power: ${buying_power:,.2f}")
print(f"Holdings: {quantity} shares")
print(f"Average Price: ${avg_price:.2f}")

# Test 3: Send test notification
print("\n=== Test 3: Send Test Notification ===")
notifier.send("🧪 Test notification from accelerated E2E test")

print("\n=== All Tests Completed ===")
