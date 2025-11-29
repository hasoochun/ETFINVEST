# MVP Project Structure

The project is organized as follows:

```
infinite_buying_bot/
├── config/             # Configuration files
│   └── kis_devlp.yaml  # API credentials (template)
├── core/               # Core business logic
│   ├── strategy.py     # Infinite buying strategy logic
│   └── trader.py       # Trading execution logic
├── api/                # API wrappers
│   ├── kis_api.py      # KIS API client
│   └── kis_auth.py     # Authentication
├── utils/              # Utility functions
│   ├── time_utils.py   # Market time calculations
│   └── logger.py       # Logging setup
├── logs/               # Log files
├── main.py             # Entry point
└── requirements.txt    # Dependencies
```
