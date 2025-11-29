import os
import sys
import yaml
import logging
from dotenv import load_dotenv

# Add project root to path (parent of infinite_buying_bot)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trader import Trader
from api import kis_auth as ka

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockNotifier:
    def send(self, msg):
        print(f"NOTIFICATION: {msg}")

def main():
    # Load env
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
    
    # Load config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kis_devlp.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    # Init Trader
    trader = Trader(config, MockNotifier())
    
    print("\n" + "="*50)
    print("DEBUGGING BALANCE")
    print("="*50)
    
    # Call get_balance which has our debug logging, but we also print here
    print(f"Using Account: {trader.trenv.my_acct}")
    print(f"Using Product Code: {trader.trenv.my_prod}")
    print(f"Using URL: {trader.trenv.my_url}")
    
    buying_power, quantity, avg_price = trader.get_balance()
    
    print(f"\nResult: Buying Power={buying_power}, Qty={quantity}, Avg Price={avg_price}")
    
if __name__ == "__main__":
    main()
