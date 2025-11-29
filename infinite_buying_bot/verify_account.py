import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Add path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api

def verify():
    print("=== KIS API Account Verification ===")
    
    # Check Env Vars
    paper_acct = os.getenv("KIS_ACCT_PAPER")
    prod_acct = os.getenv("KIS_ACCT_PROD")
    print(f"Env KIS_ACCT_PAPER: {paper_acct}")
    print(f"Env KIS_ACCT_PROD: {prod_acct}")
    
    # Auth
    print("\nAuthenticating for Mock Trading (vps)...")
    ka.auth(svr='vps', product='01')
    trenv = ka.getTREnv()
    
    print(f"Authenticated Account: {trenv.my_acct}")
    print(f"Authenticated Product: {trenv.my_prod}")
    print(f"Base URL: {trenv.my_url}")
    
    # Check Balance for multiple product codes
    import time
    for prod_code in ['01', '02', '03']:
        print(f"\nChecking Balance for Product Code: {prod_code}...")
        df1, df2 = api.inquire_balance(
            cano=trenv.my_acct, 
            acnt_prdt_cd=prod_code, 
            ovrs_excg_cd="NASD", 
            tr_crcy_cd="USD",
            env_dv="demo"
        )
        
        if not df1.empty:
            print(f"\n[SUCCESS] Balance Data found for Product Code {prod_code}!")
            print(df1.iloc[0].to_dict())
            break
        else:
            print(f"[FAILED] Product Code {prod_code} returned no data.")
        
        time.sleep(1)
        
    if not df2.empty:
        print("\nHoldings Data (df2):")
        print(df2.head())
    else:
        print("\nHoldings Data (df2) is EMPTY.")

if __name__ == "__main__":
    verify()
