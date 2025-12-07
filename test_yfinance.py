import yfinance as yf
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

symbols = ['TQQQ', 'SHV', 'SCHD']

print("Starting yfinance test...")
for symbol in symbols:
    print(f"\nTesting {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        print(f"✅ {symbol}: ${price}")
    except Exception as e:
        print(f"❌ {symbol} Failed: {e}")
        
print("\nTest Complete.")
