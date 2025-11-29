import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api

ka.auth(svr='vps', product='01')
trenv = ka.getTREnv()

print("Fetching balance...")
df1, df2 = api.inquire_balance(
    cano=trenv.my_acct, 
    acnt_prdt_cd=trenv.my_prod, 
    ovrs_excg_cd="NASD", 
    tr_crcy_cd="USD",
    env_dv="demo"
)

print("\n=== DF1 (Account Info) ===")
if not df1.empty:
    print(f"Columns: {df1.columns.tolist()}")
    print(df1.head())
else:
    print("EMPTY")

print("\n=== DF2 (Holdings) ===")
if not df2.empty:
    print(f"Columns: {df2.columns.tolist()}")
    print(df2.head())
else:
    print("EMPTY (No holdings)")
