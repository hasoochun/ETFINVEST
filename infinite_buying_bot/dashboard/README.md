# Trading Dashboard

Simple, visual dashboard for tracking the Infinite Buying Strategy performance.

## Features

- 💰 **Big KPI Cards**: Total Assets, Total Return %, Win Rate
- 📈 **Cumulative Return Chart**: Visual performance over time
- 📋 **Recent Trades**: Last 10 trades with P&L
- 💼 **Current Position**: Holdings and average price

## Installation

```bash
pip install streamlit plotly
```

## Usage

### 1. Generate Sample Data (for testing)

```bash
python dashboard/generate_sample_data.py
```

### 2. Run Dashboard

```bash
streamlit run dashboard/dashboard_app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Integration with Trading Bot

To integrate with your live trading bot, add this to `main.py`:

```python
from dashboard.database import log_trade, log_daily_stats, set_initial_capital

# At startup (once)
set_initial_capital(100000000)  # 1억

# After each buy
log_trade("buy", "SOXL", quantity, price, reason="Strategy signal")

# After each sell
log_trade("sell", "SOXL", quantity, price, pnl=profit, pnl_pct=profit_pct, reason="Profit target")

# At end of day
log_daily_stats(total_value, daily_return_pct, cumulative_return_pct, position_qty, position_avg)
```

## Deployment

### Option 1: Streamlit Cloud (Free)
1. Push code to GitHub
2. Go to https://streamlit.io/cloud
3. Connect your repo
4. Deploy!

### Option 2: Local Network
```bash
streamlit run dashboard/dashboard_app.py --server.address 0.0.0.0
```
Access from any device on your network at `http://YOUR_IP:8501`

## Customization

Edit `dashboard_app.py` to:
- Change colors in the CSS section
- Add more metrics
- Modify chart styles
- Add filters/date ranges
