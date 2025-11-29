"""
Sample data generator for testing dashboard
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.append(str(Path(__file__).parent.parent))

from dashboard.database import (
    set_initial_capital, log_trade, log_daily_stats
)

def generate_sample_data():
    """Generate sample trading data for testing"""
    
    # Set initial capital
    initial_capital = 100000000  # 1억
    set_initial_capital(initial_capital)
    
    print("Generating sample data...")
    
    # Simulate 30 days of trading
    current_value = initial_capital
    position_qty = 0
    position_avg = 0
    trade_counter = 0  # Track trades since last sell
    max_drawdown = 0  # Track MDD
    entry_value = 0
    
    start_date = datetime.now() - timedelta(days=30)
    
    for day in range(30):
        date = start_date + timedelta(days=day)
        
        # Simulate 1-3 trades per day
        num_trades = random.randint(0, 3)
        
        for _ in range(num_trades):
            # Random price between $28-$35
            price = random.uniform(28, 35)
            
            if position_qty == 0 or random.random() < 0.7:  # 70% buy
                # Buy
                quantity = random.randint(50, 150)
                log_trade(
                    trade_type="buy",
                    symbol="SOXL",
                    quantity=quantity,
                    price=price,
                    reason="Strategy signal"
                )
                
                # Update position
                total_cost = position_qty * position_avg + quantity * price
                position_qty += quantity
                position_avg = total_cost / position_qty if position_qty > 0 else 0
                trade_counter += 1
                
                if entry_value == 0:
                    entry_value = current_value
                
                # Track drawdown
                current_position_value = position_qty * price
                cash = current_value - (position_qty * position_avg)
                total_now = cash + current_position_value
                drawdown = ((total_now - entry_value) / entry_value) * 100
                max_drawdown = min(max_drawdown, drawdown)
                
            else:
                # Sell
                quantity = position_qty
                pnl = (price - position_avg) * quantity
                pnl_pct = ((price - position_avg) / position_avg) * 100
                
                log_trade(
                    trade_type="sell",
                    symbol="SOXL",
                    quantity=quantity,
                    price=price,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    trade_count=trade_counter,
                    mdd_pct=max_drawdown,
                    reason="Profit target" if pnl_pct >= 10 else "Stop loss"
                )
                
                # Update current value
                current_value += pnl
                
                # Reset position and counters
                position_qty = 0
                position_avg = 0
                trade_counter = 0
                max_drawdown = 0
                entry_value = 0
        
        # Log daily stats
        position_value = position_qty * (position_avg * random.uniform(0.98, 1.02))  # Slight variation
        total_value = current_value + position_value
        
        daily_return = ((total_value - initial_capital) / initial_capital) * 100 if day == 0 else random.uniform(-2, 3)
        cumulative_return = ((total_value - initial_capital) / initial_capital) * 100
        
        log_daily_stats(
            total_value=total_value,
            daily_return_pct=daily_return,
            cumulative_return_pct=cumulative_return,
            position_quantity=position_qty,
            position_avg_price=position_avg
        )
    
    print(f"✅ Sample data generated!")
    print(f"   - 30 days of data")
    print(f"   - Final value: ${total_value:,.0f}")
    print(f"   - Return: {cumulative_return:+.2f}%")

if __name__ == "__main__":
    generate_sample_data()
