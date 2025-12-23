"""
현재 봇의 trader.env_mode 확인
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

import yaml
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.utils.notifier import Notifier

config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'kis_devlp.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("=" * 50)
print("Config 확인")
print("=" * 50)
print(f"trading_mode from config: '{config.get('trading_mode', 'NOT SET')}'")

print("\n" + "=" * 50)
print("Trader 생성 후 확인")
print("=" * 50)

notifier = Notifier(config)
trader = Trader(config, notifier)

print(f"trader.env_mode: '{trader.env_mode}'")
print(f"trader.svr: '{trader.svr}'")
print(f"trader.trenv.my_acct: '{trader.trenv.my_acct}'")
print(f"trader.trenv.my_url: '{trader.trenv.my_url}'")

print("\n" + "=" * 50)
print("모드 판별")
print("=" * 50)
if trader.env_mode == 'real':
    print("✅ REAL TRADING MODE")
else:
    print(f"❌ PAPER TRADING MODE (env_mode='{trader.env_mode}')")
