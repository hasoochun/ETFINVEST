"""
KIS Mock Trading API Diagnosis - Simple Version
Tests API connectivity and logs responses
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

# Import KIS API modules
from infinite_buying_bot.api import kis_api as api
from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  KIS Mock Trading API Diagnosis")
print("="*70)

# Test 1: Authentication
print("\n[TEST 1] Authentication")
try:
    ka.auth(svr='vps', product='01')
    trenv = ka.getTREnv()
    print(f"SUCCESS - Account: {trenv.my_acct}, Product: {trenv.my_prod}")
except Exception as e:
    print(f"FAILED - {e}")
    sys.exit(1)

# Test 2: Balance Inquiry
print("\n[TEST 2] Balance Inquiry (Overseas Stock)")
try:
    df1, df2 = api.inquire_balance(
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        ovrs_excg_cd='NASD',
        tr_crcy_cd='USD',
        env_dv='demo'
    )
    
    print(f"\nOutput1 (Account Info):")
    if df1 is None:
        print("  Result: None")
    elif df1.empty:
        print("  Result: EMPTY DataFrame")
        print("  ISSUE: API returned empty response for account info")
    else:
        print(f"  Rows: {len(df1)}, Columns: {len(df1.columns)}")
        print(f"  Columns: {list(df1.columns)[:5]}...")
        print(f"\n  Sample data (first row):")
        for key, value in list(df1.iloc[0].to_dict().items())[:10]:
            print(f"    {key}: {value}")
    
    print(f"\nOutput2 (Holdings):")
    if df2 is None:
        print("  Result: None")
    elif df2.empty:
        print("  Result: EMPTY (no holdings)")
    else:
        print(f"  Rows: {len(df2)}, Columns: {len(df2.columns)}")
        
except Exception as e:
    print(f"FAILED - {e}")
    import traceback
    traceback.print_exc()

# Test 3: Price Inquiry
print("\n[TEST 3] Price Inquiry (SOXL)")
try:
    df = api.price(
        auth="",
        excd='NASD',
        symb='SOXL',
        env_dv='demo'
    )
    
    if df is None:
        print("  Result: None")
    elif df.empty:
        print("  Result: EMPTY DataFrame")
    else:
        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        if 'last' in df.columns:
            price = float(df['last'].iloc[0])
            print(f"  SOXL Price: ${price:.2f}")
        else:
            print(f"  Columns: {df.columns.tolist()}")
            
except Exception as e:
    print(f"FAILED - {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*70)
print("  Diagnosis Summary")
print("="*70)
print("\nISSUE IDENTIFIED:")
print("  - Balance inquiry returns empty DataFrame (df1)")
print("  - This prevents getting buying power for trading")
print("\nPOSSIBLE CAUSES:")
print("  1. Mock trading account not funded")
print("  2. API parameter mismatch")
print("  3. API endpoint or response format changed")
print("\nNEXT STEPS:")
print("  1. Check mock account funding on KIS website")
print("  2. Verify API parameters match documentation")
print("  3. Test with different exchange codes (NYSE, AMEX)")
print("="*70)
