import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MockScheduler:
    """Mock Scheduler that always reports market as open"""
    def is_market_open(self):
        return True
    
    def is_near_close(self, minutes=10):
        # Randomly return True to simulate "near close" occasionally for buying logic
        return random.random() < 0.2

class MockTrader:
    """Mock Trader that simulates price movements and order execution"""
    def __init__(self, initial_balance=100000000):
        self.symbol = "SOXL" # Default
        self.cash = initial_balance
        self.holdings = {} # {symbol: {'qty': 0, 'avg_price': 0}}
        self.current_prices = {
            "SOXL": 30.0,
            "TQQQ": 50.0,
            "SCHD": 75.0
        }
        self.price_trend = {
            "SOXL": 0.0,
            "TQQQ": 0.0,
            "SCHD": 0.0
        }
        
    def get_price(self):
        """Simulate price movement"""
        # Apply random walk with momentum
        change = (random.random() - 0.5) * 0.5 # -0.25 to +0.25
        self.current_prices[self.symbol] += change
        return round(self.current_prices[self.symbol], 2)

    def get_balance(self):
        """Return current balance state"""
        qty = 0
        avg_price = 0.0
        
        if self.symbol in self.holdings:
            qty = self.holdings[self.symbol]['qty']
            avg_price = self.holdings[self.symbol]['avg_price']
            
        return self.cash, qty, avg_price

    def buy(self, amount, split_count=None, reason=None):
        price = self.get_price()
        qty = int(amount / price)
        
        if qty > 0 and self.cash >= (qty * price):
            self.cash -= (qty * price)
            
            # Update holdings
            if self.symbol not in self.holdings:
                self.holdings[self.symbol] = {'qty': 0, 'avg_price': 0.0}
            
            current = self.holdings[self.symbol]
            total_cost = (current['qty'] * current['avg_price']) + (qty * price)
            total_qty = current['qty'] + qty
            
            current['qty'] = total_qty
            current['avg_price'] = total_cost / total_qty
            
            logger.info(f"[MOCK] Bought {qty} {self.symbol} @ ${price:.2f}")
            return True
        return False

    def sell_all(self, quantity):
        if self.symbol in self.holdings:
            price = self.get_price()
            qty = self.holdings[self.symbol]['qty']
            
            revenue = qty * price
            self.cash += revenue
            
            logger.info(f"[MOCK] Sold {qty} {self.symbol} @ ${price:.2f}")
            
            del self.holdings[self.symbol]
            return True
        return False
        
    def get_all_holdings(self):
        """Return list of all holdings"""
        result = []
        for sym, data in self.holdings.items():
            current_price = self.current_prices.get(sym, 0)
            result.append({
                'symbol': sym,
                'qty': data['qty'],
                'avg_price': data['avg_price'],
                'current_price': current_price,
                'value': data['qty'] * current_price
            })
        return result
