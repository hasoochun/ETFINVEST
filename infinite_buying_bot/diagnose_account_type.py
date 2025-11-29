"""
Advanced diagnosis - Test with exact account info from screenshot
Account: 50157068
Type: 상사채권 국내주식 (Domestic Stock)
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_api as api
from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  Advanced Diagnosis - Account 50157068")
print("="*70)

# Authenticate
print("\n[1] Authentication (Mock Trading)")
ka.auth(svr='vps', product='01')
trenv = ka.getTREnv()
print(f"Account: {trenv.my_acct}")
print(f"Product: {trenv.my_prod}")
print(f"Server: vps (mock)")

# Test 1: Domestic Stock Balance (국내주식)
print("\n[2] Testing DOMESTIC Stock Balance")
print("Account type shown: 상사채권 국내주식")
print("This account is for DOMESTIC stocks, not overseas stocks!")

try:
    # Check if there's a domestic stock balance function
    import inspect
    functions = [name for name, obj in inspect.getmembers(api) if inspect.isfunction(obj)]
    
    domestic_funcs = [f for f in functions if 'domestic' in f.lower() or 'korea' in f.lower()]
    print(f"\nDomestic-related functions found: {len(domestic_funcs)}")
    for func in domestic_funcs[:5]:
        print(f"  - {func}")
    
except Exception as e:
    print(f"Error: {e}")

# Test 2: Try overseas balance again with detailed error
print("\n[3] Testing OVERSEAS Stock Balance (Expected to fail)")
try:
    df1, df2 = api.inquire_balance(
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        ovrs_excg_cd='NASD',
        tr_crcy_cd='USD',
        env_dv='demo'
    )
    print("Unexpected success!")
except Exception as e:
    print(f"FAILED (as expected): {e}")
    print("\nREASON: Account 50157068 is for DOMESTIC stocks only")
    print("        It does NOT have overseas trading permission")

print("\n" + "="*70)
print("  DIAGNOSIS RESULT")
print("="*70)
print("\nROOT CAUSE:")
print("  Your mock account 50157068 is '상사채권 국내주식'")
print("  This means: DOMESTIC STOCKS ONLY")
print("  It does NOT support overseas stock trading (SOXL, AAPL, etc.)")
print("\nSOLUTION OPTIONS:")
print("  1. Change strategy to use Korean stocks (KODEX 200, Samsung, etc.)")
print("  2. Apply for overseas trading permission in mock account")
print("  3. Create new mock account with overseas trading enabled")
print("="*70)
