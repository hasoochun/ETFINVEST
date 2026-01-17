#!/usr/bin/env python3
"""
Unit Test: Rotation Priority Logic in RebalancingEngine
Tests the new funding source selection logic:
1. SHV first
2. JEPI/MAGS only if in profit and above 20% allocation
3. Skip assets in loss
"""
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock

class MockPortfolioManager:
    """Mock portfolio manager for testing"""
    def __init__(self):
        # Total value: TQQQ 450 + JEPI 6000 + MAGS 2850 = 9300
        # JEPI allocation: 6000/9300 = 64.5% (above 20%)
        self.positions = {
            'TQQQ': {'quantity': 10, 'avg_price': 50.0, 'current_price': 45.0},  # 450 USD, In loss
            'SHV': {'quantity': 0, 'avg_price': 110.0, 'current_price': 110.5},  # 0 USD, Depleted
            'JEPI': {'quantity': 100, 'avg_price': 55.0, 'current_price': 60.0},  # 6000 USD, In profit
            'MAGS': {'quantity': 30, 'avg_price': 100.0, 'current_price': 95.0},  # 2850 USD, In loss
        }
    
    def get_total_value(self):
        total = 0
        for pos in self.positions.values():
            total += pos['quantity'] * pos['current_price']
        return total

class MockBotController:
    """Mock bot controller for testing"""
    def __init__(self):
        self.dip_buy_mode = 'accelerated'
        # Set to very old time to pass interval check
        from datetime import datetime, timedelta
        self.last_dip_buy_time = datetime.now() - timedelta(hours=1)  # 1 hour ago
        self.strategy_mode = 'neutral'
        self.runtime_config = {
            'rotation_priority': ['SHV', 'JEPI', 'MAGS']
        }

def test_rotation_priority():
    """Test that rotation priority selects correct funding source"""
    from infinite_buying_bot.core.rebalancing_engine import RebalancingEngine
    
    portfolio = MockPortfolioManager()
    bot_controller = MockBotController()
    
    engine = RebalancingEngine(portfolio, bot_controller)
    
    # Test: SHV is depleted, MAGS is in loss → should select JEPI
    action = engine.check_tqqq_dip_buying()
    
    print("\n" + "="*60)
    print("🧪 ROTATION PRIORITY TEST")
    print("="*60)
    print(f"📊 Portfolio State:")
    for symbol, pos in portfolio.positions.items():
        profit = ((pos['current_price'] - pos['avg_price']) / pos['avg_price'] * 100) if pos['avg_price'] > 0 else 0
        print(f"   {symbol}: qty={pos['quantity']}, profit={profit:+.1f}%")
    
    print(f"\n🎯 Expected: JEPI (SHV depleted, MAGS in loss)")
    
    if action:
        print(f"✅ Result: sell_symbol={action.get('sell_symbol')}")
        assert action['sell_symbol'] == 'JEPI', f"Expected JEPI, got {action['sell_symbol']}"
        print("✅ TEST PASSED: Correct funding source selected!")
    else:
        print("❌ Result: No action (unexpected)")
        print("❌ TEST FAILED")
        return False
    
    return True

def test_skip_loss_assets():
    """Test that assets in loss are skipped"""
    from infinite_buying_bot.core.rebalancing_engine import RebalancingEngine
    
    portfolio = MockPortfolioManager()
    # Make all non-SHV assets in loss
    portfolio.positions['JEPI']['current_price'] = 50.0  # avg=55, now in loss
    portfolio.positions['MAGS']['current_price'] = 90.0  # avg=100, in loss
    
    bot_controller = MockBotController()
    engine = RebalancingEngine(portfolio, bot_controller)
    
    action = engine.check_tqqq_dip_buying()
    
    print("\n" + "="*60)
    print("🧪 SKIP LOSS ASSETS TEST")
    print("="*60)
    print(f"📊 All assets in loss or depleted")
    print(f"🎯 Expected: None (no valid funding source)")
    
    if action is None:
        print("✅ Result: None")
        print("✅ TEST PASSED: Correctly skipped all loss assets!")
        return True
    else:
        print(f"❌ Result: {action.get('sell_symbol')} selected (should be None)")
        print("❌ TEST FAILED")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 STARTING ROTATION PRIORITY UNIT TESTS")
    print("="*60)
    
    results = []
    results.append(("Rotation Priority", test_rotation_priority()))
    results.append(("Skip Loss Assets", test_skip_loss_assets()))
    
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("✅ ALL TESTS PASSED!" if all_passed else "❌ SOME TESTS FAILED"))
    sys.exit(0 if all_passed else 1)
