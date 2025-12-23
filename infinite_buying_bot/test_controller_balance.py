"""
BotController.get_balance() 직접 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

import yaml
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.utils.notifier import Notifier
from infinite_buying_bot.api.bot_controller import BotController

print("=" * 70)
print("🔍 BotController.get_balance() 직접 테스트")
print("=" * 70)

# Load config
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'kis_devlp.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print(f"Trading Mode: {config.get('trading_mode', 'demo')}")
print(f"Symbol: {config.get('strategy', {}).get('symbol', 'TQQQ')}")

# Create objects
notifier = Notifier(config)
trader = Trader(config, notifier)
controller = BotController(config)
controller.set_trader(trader)

print(f"\nTrader env_mode: {trader.env_mode}")
print(f"Trader exchange: {trader.exchange}")
print(f"Trader symbol: {trader.symbol}")

# Test get_balance
print("\n" + "=" * 70)
print("Calling controller.get_balance()...")
print("=" * 70)

result = controller.get_balance()
print(f"\n결과:")
for key, val in result.items():
    print(f"  {key}: {val}")

# Test trader.get_balance() directly
print("\n" + "=" * 70)
print("Calling trader.get_balance() directly...")
print("=" * 70)

buying_power, quantity, avg_price = trader.get_balance()
print(f"\n  💰 buying_power: ${buying_power}")
print(f"  📊 quantity: {quantity}")
print(f"  📈 avg_price: ${avg_price}")

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)
