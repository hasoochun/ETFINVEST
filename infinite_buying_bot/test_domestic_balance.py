"""
Test domestic stock balance inquiry
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_api as api
from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  Testing Domestic Stock Balance Inquiry")
print("="*70)

# Authenticate
print("\n[1] Authentication")
ka.auth(svr='vps', product='01')
trenv = ka.getTREnv()
print(f"Account: {trenv.my_acct}, Product: {trenv.my_prod}")

# Test domestic stock balance
print("\n[2] Domestic Stock Balance Inquiry")
try:
    # Note: Need to check kis_api.py for domestic stock balance function
    # The function name might be different
    
    print("Checking available functions in kis_api...")
    
    # List all functions in kis_api
    import inspect
    functions = [name for name, obj in inspect.getmembers(api) if inspect.isfunction(obj)]
    
    print(f"\nAvailable functions ({len(functions)}):")
    balance_funcs = [f for f in functions if 'balance' in f.lower() or 'inquire' in f.lower()]
    for func in balance_funcs[:10]:
        print(f"  - {func}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
