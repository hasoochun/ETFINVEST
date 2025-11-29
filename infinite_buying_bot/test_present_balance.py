"""
Test inquire_present_balance API (alternative to inquire_balance)
This API uses different parameters and may work better for mock accounts
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  Testing inquire_present_balance API")
print("="*70)

# Authenticate
print("\n[1] Authenticating...")
ka.auth(svr='vps', product='01')
trenv = ka.getTREnv()
print(f"Account: {trenv.my_acct}")

# Make API call with correct parameters for inquire_present_balance
print("\n[2] Calling inquire_present_balance API...")

api_url = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
tr_id = "VTTC8908R"  # Demo version (V prefix for mock)

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "WCRC_FRCR_DVSN_CD": "02",  # 02: Foreign currency
    "NATN_CD": "840",  # 840: USA
    "TR_MKET_CD": "01",  # 01: NASDAQ
    "INQR_DVSN_CD": "00",  # 00: All
}

print(f"\nRequest Parameters:")
print(json.dumps(params, indent=2))

# Call API
res = ka._url_fetch(api_url=api_url, ptr_id=tr_id, tr_cont="", params=params)

print(f"\n[3] API Response:")
print(f"Is OK: {res.isOK()}")
print(f"Error Code: {res.getErrorCode()}")
print(f"Error Message: {res.getErrorMessage()}")

if res.isOK():
    print("\n✅ SUCCESS!")
    body = res.getBody()
    
    # Check outputs
    print("\n[4] Response Structure:")
    for attr in ['output1', 'output2', 'output3']:
        if hasattr(body, attr):
            data = getattr(body, attr)
            print(f"\n{attr.upper()}:")
            if data:
                if isinstance(data, list):
                    print(f"  Type: list with {len(data)} items")
                    if len(data) > 0:
                        print(f"  First item keys: {list(data[0].keys())[:10]}")
                elif isinstance(data, dict):
                    print(f"  Type: dict")
                    print(f"  Keys: {list(data.keys())[:10]}")
                else:
                    print(f"  Type: {type(data)}")
                    print(f"  Value: {data}")
            else:
                print(f"  Empty or None")
    
    # Save response
    print("\n[5] Saving response...")
    response_data = {
        "output1": body.output1 if hasattr(body, 'output1') else None,
        "output2": body.output2 if hasattr(body, 'output2') else None,
        "output3": body.output3 if hasattr(body, 'output3') else None,
    }
    
    with open("present_balance_response.json", 'w', encoding='utf-8') as f:
        json.dump(response_data, f, indent=2, ensure_ascii=False)
    
    print("Saved to: present_balance_response.json")
    
else:
    print("\n❌ API call failed!")

print("\n" + "="*70)
