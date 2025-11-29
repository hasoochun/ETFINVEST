"""
Accelerated E2E Integration Test for Infinite Buying Bot
10 seconds = 1 day simulation
Tests split buying strategy with KIS mock trading API
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import bot components
from infinite_buying_bot.core.trader import Trader
from infinite_buying_bot.core.strategy import InfiniteBuyingStrategy
from infinite_buying_bot.telegram_bot.notifications import TelegramNotifier

class AcceleratedTestRunner:
    """Run accelerated E2E test with 10-second intervals"""
    
    def __init__(self, config_path):
        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Add strategy config if not present
        if 'strategy' not in self.config:
            self.config['strategy'] = {
                'symbol': 'SOXL',
                'exchange': 'NASD',
                'currency': 'USD',
                'profit_target_pct': 10.0,
                'split_count_low': 80,
                'split_count_high': 40
            }
        
        # Initialize Telegram notifier
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.warning("⚠️ Telegram credentials not found in .env - notifications disabled")
            # Use mock notifier as fallback
            class MockNotifier:
                def send(self, message):
                    logger.info(f"[NOTIFICATION] {message}")
            self.notifier = MockNotifier()
        else:
            logger.info(f"✅ Telegram notifier enabled for chat_id: {chat_id}")
            self.notifier = TelegramNotifier(bot_token, chat_id)
        
        # Initialize components
        self.trader = Trader(self.config, self.notifier)
        self.strategy = InfiniteBuyingStrategy(self.config)
        
        # Test state
        self.test_day = 0
        self.test_results = []
        
    def print_header(self, title):
        """Print formatted header"""
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def print_balance(self):
        """Print current balance information"""
        buying_power, quantity, avg_price = self.trader.get_balance()
        current_price = self.trader.get_price()
        
        print(f"\n💰 Account Balance:")
        print(f"   Cash Available: ${buying_power:,.2f}")
        print(f"   Holdings: {quantity} shares")
        print(f"   Average Price: ${avg_price:.2f}")
        print(f"   Current Price: ${current_price:.2f}" if current_price else "   Current Price: N/A")
        
        if quantity > 0 and current_price:
            position_value = quantity * current_price
            total_value = buying_power + position_value
            pnl = (current_price - avg_price) * quantity
            pnl_pct = (pnl / (avg_price * quantity)) * 100 if avg_price > 0 else 0
            
            print(f"   Position Value: ${position_value:,.2f}")
            print(f"   Total Value: ${total_value:,.2f}")
            print(f"   P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
        
        return buying_power, quantity, avg_price, current_price
    
    def simulate_day(self):
        """Simulate one trading day (10 seconds in real time)"""
        self.test_day += 1
        
        print(f"\n{'─'*70}")
        print(f"📅 DAY {self.test_day} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'─'*70}")
        
        # Get current state
        buying_power, quantity, avg_price, current_price = self.print_balance()
        
        if not current_price:
            logger.error("❌ Failed to get current price - skipping this day")
            return
        
        # Check sell condition first
        should_sell = self.strategy.should_sell(current_price, avg_price, quantity)
        
        if should_sell:
            print(f"\n🎯 SELL SIGNAL TRIGGERED!")
            print(f"   Profit target reached (10%)")
            print(f"   Selling ALL {quantity} shares at ${current_price:.2f}")
            
            # Execute sell with reason
            self.trader.sell_all(quantity, reason="Profit Target 10%")
            
            self.test_results.append({
                'day': self.test_day,
                'action': 'SELL',
                'quantity': quantity,
                'price': current_price,
                'reason': 'Profit target 10%'
            })
            
            print(f"   ✅ Sell order executed - Strategy reset")
            return
        
        # Check buy condition (assume near close for testing)
        should_buy, split_count = self.strategy.should_buy(
            current_price, avg_price, quantity, is_near_close=True
        )
        
        if should_buy:
            buy_amount = buying_power / split_count
            
            print(f"\n📈 BUY SIGNAL TRIGGERED!")
            
            # Determine reason
            if quantity == 0:
                reason = "Initial Entry"
                print(f"   Initial Entry")
            elif current_price < avg_price:
                reason = "Below Average Price"
                print(f"   Price BELOW average (${current_price:.2f} < ${avg_price:.2f})")
            else:
                reason = "Above Average Price"
                print(f"   Price ABOVE average (${current_price:.2f} > ${avg_price:.2f})")
            
            print(f"   Split Count: 1/{split_count}")
            print(f"   Buy Amount: ${buy_amount:,.2f}")
            
            # Execute buy with split_count and reason
            if buy_amount >= 10:  # Minimum order amount
                self.trader.buy(buy_amount, split_count=split_count, reason=reason)
                
                self.test_results.append({
                    'day': self.test_day,
                    'action': 'BUY',
                    'amount': buy_amount,
                    'split': split_count,
                    'price': current_price,
                    'reason': 'Initial' if quantity == 0 else ('Below Avg' if current_price < avg_price else 'Above Avg')
                })
                
                print(f"   ✅ Buy order executed")
            else:
                print(f"   ⚠️ Buy amount too small (${buy_amount:.2f} < $10) - skipping")
        else:
            print(f"\n⏸️ NO ACTION - Not near market close")
    
    def run_test(self, num_days=5):
        """Run accelerated test for specified number of days"""
        self.print_header("ACCELERATED E2E INTEGRATION TEST")
        print(f"⏱️  Time Scale: 10 seconds = 1 trading day")
        print(f"📊 Strategy: Infinite Buying (Updated)")
        print(f"   - Below Average: 1/40 split (Aggressive)")
        print(f"   - Above Average: 1/80 split (Conservative)")
        print(f"   - Profit Target: 10%")
        print(f"🎯 Symbol: {self.trader.symbol}")
        print(f"🏦 Mode: Mock Trading")
        
        # Initial balance check
        self.print_header("INITIAL STATE")
        self.print_balance()
        
        # Run simulation
        self.print_header(f"RUNNING {num_days}-DAY SIMULATION")
        
        for day in range(num_days):
            self.simulate_day()
            
            # Wait 10 seconds (1 simulated day)
            if day < num_days - 1:
                print(f"\n⏳ Waiting 10 seconds for next day...")
                time.sleep(10)
        
        # Final results
        self.print_header("FINAL STATE")
        self.print_balance()
        
        # Summary
        self.print_header("TEST SUMMARY")
        print(f"\n📋 Actions Taken:")
        
        if not self.test_results:
            print("   No actions executed during test period")
        else:
            for result in self.test_results:
                if result['action'] == 'BUY':
                    print(f"   Day {result['day']}: BUY ${result['amount']:.2f} "
                          f"(1/{result['split']} split) - {result['reason']} - "
                          f"Price: ${result['price']:.2f}")
                else:
                    print(f"   Day {result['day']}: SELL {result['quantity']} shares - "
                          f"{result['reason']} - Price: ${result['price']:.2f}")
        
        print(f"\n✅ Test completed successfully!")
        print(f"📊 Total days simulated: {self.test_day}")
        print(f"📈 Total actions: {len(self.test_results)}")

def main():
    """Main test entry point"""
    print("\n" + "="*70)
    print("  🚀 Infinite Buying Bot - Accelerated E2E Test")
    print("="*70)
    
    # Find config file
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        '..', 
        'kis_devlp.yaml'
    )
    
    if not os.path.exists(config_path):
        print(f"\n❌ Error: Config file not found at {config_path}")
        return
    
    try:
        # Create test runner
        runner = AcceleratedTestRunner(config_path)
        
        # Run 5-day simulation (50 seconds total)
        runner.run_test(num_days=5)
        
    except KeyboardInterrupt:
        print("\n\n⏸️ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")

if __name__ == '__main__':
    main()
