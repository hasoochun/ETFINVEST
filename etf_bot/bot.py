import sys
import os
import logging
import time
import yaml

# Add parent directory to path to import kis_auth and examples_user modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'examples_user'))

import time
from etf_bot.utils import is_market_open, is_near_market_close
from overseas_stock.overseas_stock_functions import price, order, inquire_balance

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from kis_devlp.yaml"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kis_devlp.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_account_balance(trenv, exchange_code="NASD", currency="USD"):
    """Fetch account balance and holdings."""
    try:
        # inquire_balance returns two dataframes: df1 (cash/deposit), df2 (holdings)
        # Signature: inquire_balance(cano, acnt_prdt_cd, ovrs_excg_cd, tr_crcy_cd, ...)
        df1, df2 = inquire_balance(cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod, 
                                   ovrs_excg_cd=exchange_code, tr_crcy_cd=currency)
        return df1, df2
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
        return None, None

def main():
    logger.info("Starting ETF Trading Bot (Infinite Buying Strategy)...")

    # 1. Authentication
    config = load_config()
    
    # Determine environment (Mock vs Real) based on config or hardcoded for safety
    # For this implementation, we default to 'demo' (Mock) as per plan.
    # User should change this to 'prod' in code or config when ready for real money.
    ENV_MODE = "demo" 
    
    # Authenticate
    # Note: 'product' code might differ for mock (often '01' works if configured correctly in yaml)
    ka.auth(svr='vps' if ENV_MODE == 'demo' else 'prod', product='01') 
    
    trenv = ka.getTREnv()
    logger.info(f"Authenticated. Account: {trenv.my_acct}, Product: {trenv.my_prod}, Mode: {ENV_MODE}")

    # 2. Target Settings
    TARGET_SYMBOL = "SOXL" 
    EXCHANGE_CODE = "NASD" 
    CURRENCY = "USD"
    
    # Strategy Parameters
    PROFIT_TARGET_PCT = 10.0 # 10%
    SPLIT_COUNT_LOW = 80 # Price < Avg
    SPLIT_COUNT_HIGH = 40 # Price > Avg

    while True:
        try:
            # Check Market Status
            if not is_market_open():
                logger.info("Market is closed. Waiting...")
                time.sleep(60) # Check every minute
                continue

            # 3. Fetch Data
            # Current Price
            price_df = price(auth="", excd=EXCHANGE_CODE, symb=TARGET_SYMBOL, env_dv=ENV_MODE)
            if price_df.empty:
                logger.warning("Failed to fetch price. Retrying...")
                time.sleep(10)
                continue
                
            current_price = float(price_df['last'].iloc[0]) # Adjust column name if needed (usually 'last')
            logger.info(f"Current Price of {TARGET_SYMBOL}: {current_price}")

            # Balance & Holdings
            cash_df, holdings_df = get_account_balance(trenv, EXCHANGE_CODE, CURRENCY)
            
            # Parse Cash (Buying Power)
            # Column names in cash_df need verification, usually 'ovrs_ord_psbl_amt' (Overseas Order Possible Amount)
            # or 'frcr_dncl_amt_2' (Foreign Currency Deposit Amount 2)
            # Let's assume 'ovrs_ord_psbl_amt' for buying power.
            buying_power = 0.0
            if not cash_df.empty:
                # This column name is a guess based on common KIS API fields. 
                # If it fails, we might need to inspect the dataframe columns.
                # For now, we'll try to find a column that looks like buying power.
                # Common fields: 'frcr_ord_psbl_amt1' (Foreign Currency Order Possible Amount)
                if 'frcr_ord_psbl_amt1' in cash_df.columns:
                     buying_power = float(cash_df['frcr_ord_psbl_amt1'].iloc[0])
                else:
                    logger.warning(f"Could not find buying power column. Columns: {cash_df.columns}")
            
            # Parse Holdings
            avg_price = 0.0
            quantity = 0
            if not holdings_df.empty:
                # Filter for target symbol
                # Column names: 'ovrs_pdno' (Symbol), 'ovrs_item_name' (Name), 'pchs_avg_pric' (Avg Price), 'ovrs_cblc_qty' (Qty)
                target_holding = holdings_df[holdings_df['ovrs_pdno'] == TARGET_SYMBOL]
                if not target_holding.empty:
                    avg_price = float(target_holding['pchs_avg_pric'].iloc[0])
                    quantity = int(target_holding['ovrs_cblc_qty'].iloc[0])
            
            logger.info(f"Holdings: {quantity} shares @ ${avg_price:.2f}, Buying Power: ${buying_power:.2f}")

            # 4. Sell Logic (Profit Taking)
            if quantity > 0:
                profit_pct = ((current_price - avg_price) / avg_price) * 100
                logger.info(f"Current Profit: {profit_pct:.2f}%")
                
                if profit_pct >= PROFIT_TARGET_PCT:
                    logger.info(f"Profit target reached ({profit_pct:.2f}% >= {PROFIT_TARGET_PCT}%). Selling ALL.")
                    # Sell All
                    res = order(cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod, 
                                ovrs_excg_cd=EXCHANGE_CODE, pdno=TARGET_SYMBOL, 
                                ord_qty=str(quantity), ovrs_ord_unpr="0", # Market price (0)
                                ord_dv="sell", ord_dvsn="00", # Market price
                                env_dv=ENV_MODE)
                    logger.info(f"Sell Order Result: {res}")
                    time.sleep(10) # Wait a bit after order
                    continue

            # 5. Buy Logic (Split Buying at Market Close)
            if is_near_market_close(minutes=5):
                logger.info("Near market close. Checking buy conditions...")
                
                # Determine Split Count
                split_count = SPLIT_COUNT_LOW # Default 80
                if quantity > 0 and current_price > avg_price:
                    split_count = SPLIT_COUNT_HIGH # 40 if Price > Avg
                
                # Calculate Buy Amount
                # Buy Amount = Total Cash / Split Count
                # Note: "Total Cash" usually means Total Equity or Initial Capital? 
                # Strategy says "Available Funds". So we use current buying power.
                # But if we use current buying power every time, the amount decreases exponentially (Zeno's paradox).
                # "Infinite Buying" usually implies dividing the *remaining* cash.
                # Let's stick to: Buy Amount = Current Buying Power / Split Count.
                
                buy_amount = buying_power / split_count
                
                # Calculate Quantity to Buy
                # Qty = Buy Amount / Current Price
                buy_qty = int(buy_amount // current_price)
                
                if buy_qty > 0:
                    logger.info(f"Buying {buy_qty} shares (Split: 1/{split_count})...")
                    res = order(cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod, 
                                ovrs_excg_cd=EXCHANGE_CODE, pdno=TARGET_SYMBOL, 
                                ord_qty=str(buy_qty), ovrs_ord_unpr="0", # Market price
                                ord_dv="buy", ord_dvsn="00", 
                                env_dv=ENV_MODE)
                    logger.info(f"Buy Order Result: {res}")
                    
                    # Sleep to avoid multiple buys in the same 5-min window?
                    # Or just sleep for a minute.
                    time.sleep(60) 
                else:
                    logger.info(f"Calculated buy quantity is 0. (Amount: ${buy_amount:.2f}, Price: ${current_price})")
            
            time.sleep(10) # Loop delay

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
