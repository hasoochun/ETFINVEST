# Infinite Buying Bot - Project Structure

## Overview

Portfolio-based infinite buying bot with dual-speed trading system, Telegram control, and automatic rebalancing.

## Directory Structure

```
infinite_buying_bot/
├── api/                    # API controllers and authentication
│   ├── bot_controller.py   # Main bot controller with dip buy modes
│   ├── kis_auth.py         # KIS API authentication
│   └── kis_api.py          # KIS API wrapper
├── core/                   # Core trading logic
│   ├── portfolio_manager.py    # Portfolio tracking and management
│   ├── rebalancing_engine.py   # Rebalancing and dip buying logic
│   └── trader.py               # Trade execution
├── telegram_bot/           # Telegram bot interface
│   ├── bot.py              # Main Telegram bot class
│   ├── handlers/           # Command and callback handlers
│   │   ├── callbacks.py    # Button callback handlers
│   │   ├── status.py       # Status command handlers
│   │   └── trading.py      # Trading command handlers
│   ├── formatters/         # Message and keyboard formatters
│   │   ├── keyboards.py    # Inline keyboard layouts
│   │   ├── messages.py     # Status message formatting
│   │   └── portfolio_messages.py  # Portfolio display formatting
│   └── security.py         # Security and authorization
├── dashboard/              # Web dashboard (optional)
│   ├── app.py              # Flask application
│   └── database.py         # SQLite database
├── config/                 # Configuration files
│   └── kis_devlp.yaml      # KIS API credentials
├── logs/                   # Log files
├── main_portfolio.py       # Main entry point
└── requirements.txt        # Python dependencies
```

## Key Components

### 1. Bot Controller (`api/bot_controller.py`)
- Central control hub for the bot
- Manages bot state (running, stopped, entry allowed)
- **Dip buy mode management**: Daily vs Accelerated
- Coordinates between portfolio manager and rebalancing engine

### 2. Portfolio Manager (`core/portfolio_manager.py`)
- Tracks current positions and cash
- Calculates portfolio allocation
- Target allocation: TQQQ 30%, SHV 50%, SCHD 20%
- Dynamic ETF selection support

### 3. Rebalancing Engine (`core/rebalancing_engine.py`)
- **Profit taking**: Sell TQQQ at +10%, buy SCHD
- **Dip buying**: 40/80 split strategy
  - Price < Average: Buy SHV/40 (aggressive)
  - Price >= Average: Buy SHV/80 (conservative)
- **Rebalancing**: Maintain ±10% drift tolerance

### 4. Trader (`core/trader.py`)
- Executes buy/sell orders via KIS API
- Market order execution
- Position and balance queries
- Detailed trade notifications

### 5. Telegram Bot (`telegram_bot/`)
- User interface via Telegram
- Real-time status updates
- Interactive button controls
- Mode selection (Daily/Accelerated)

## Trading Modes

### Dual-Speed System

**Price Checking**: Every 60 seconds
- Profit taking opportunities
- Rebalancing checks
- Real-time monitoring

**Dip Buying Modes**:

1. **📅 Daily Mode** (Production)
   - Execution: 15:55-16:00 ET (market close - 5 min)
   - Frequency: Once per day
   - Use case: Live trading

2. **🏃 Accelerated Mode** (Testing)
   - Execution: Every 10 minutes
   - Frequency: 6 times per hour during market hours
   - Use case: Fast testing and development

## Data Flow

```
User (Telegram) 
    ↓
Bot Controller
    ↓
Portfolio Manager ←→ Rebalancing Engine
    ↓                       ↓
    Trader ←────────────────┘
    ↓
KIS API
```

## Configuration

### Environment Variables
- Set via `kis_devlp.yaml`
- KIS API credentials
- Account information

### Bot Settings
- Initial capital: 100,000,000 KRW
- Trading symbol: Configurable (TQQQ, MAGS, QQQ, SPY, VOO)
- Dip buy mode: User-selectable via Telegram

## Logging

- All trades logged with timestamps
- Portfolio updates tracked
- Error handling and notifications
- Log files stored in `logs/` directory

## Dependencies

- `python-telegram-bot`: Telegram interface
- `pykis`: KIS API wrapper
- `pandas`: Data manipulation
- `pytz`: Timezone handling
- `flask`: Web dashboard (optional)
- `pyyaml`: Configuration parsing
