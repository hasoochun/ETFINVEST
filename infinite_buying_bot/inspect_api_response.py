"""
Deep API Response Inspector
Captures RAW API response to identify exact field names
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  Deep API Response Inspector")
print("="*70)

# Authenticate
print("\n[1] Authenticating...")
ka.auth(svr='vps', product='01')
trenv = ka.getTREnv()
print(f"Account: {trenv.my_acct}")

# Make raw API call
print("\n[2] Making RAW API call to balance inquiry...")

api_url = "/uapi/overseas-stock/v1/trading/inquire-balance"
tr_id = "VTTS3012R"  # Demo version

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": "",
}

print(f"\nRequest Parameters:")
print(json.dumps(params, indent=2))

# Call API
res = ka._url_fetch(api_url=api_url, ptr_id=tr_id, tr_cont="", params=params)

print(f"\n[3] API Response Status:")
print(f"Is OK: {res.isOK()}")
print(f"Error Code: {res.getErrorCode()}")
print(f"Error Message: {res.getErrorMessage()}")

if res.isOK():
    print("\n[4] Response Body Structure:")
    body = res.getBody()
    
    # List all attributes
    print(f"\nBody attributes:")
    for attr in dir(body):
        if not attr.startswith('_'):
            print(f"  - {attr}")
    
    # Check output1
    print("\n[5] OUTPUT1 (Account Info):")
    if hasattr(body, 'output1'):
        output1 = body.output1
        print(f"Type: {type(output1)}")
        
        if output1:
            print(f"\nOutput1 content:")
            if isinstance(output1, dict):
                print(json.dumps(output1, indent=2, ensure_ascii=False))
            else:
                print(output1)
        else:
            print("Output1 is None or empty")
    else:
        print("No output1 attribute")
    
    # Check output2
    print("\n[6] OUTPUT2 (Holdings):")
    if hasattr(body, 'output2'):
        output2 = body.output2
        print(f"Type: {type(output2)}")
        
        if output2:
            print(f"\nOutput2 content (first item if list):")
            if isinstance(output2, list) and len(output2) > 0:
                print(json.dumps(output2[0], indent=2, ensure_ascii=False))
            elif isinstance(output2, dict):
                print(json.dumps(output2, indent=2, ensure_ascii=False))
            else:
                print(output2)
        else:
            print("Output2 is None or empty")
    else:
        print("No output2 attribute")
    
    # Save full response
    print("\n[7] Saving full response to file...")
    response_file = "api_response_full.json"
    
    try:
        response_data = {
            "rt_cd": body.rt_cd if hasattr(body, 'rt_cd') else None,
            "msg_cd": body.msg_cd if hasattr(body, 'msg_cd') else None,
            "msg1": body.msg1 if hasattr(body, 'msg1') else None,
            "output1": output1 if hasattr(body, 'output1') else None,
            "output2": output2 if hasattr(body, 'output2') else None,
        }
        
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved to: {response_file}")
    except Exception as e:
        print(f"Failed to save: {e}")

else:
    print("\n❌ API call failed!")
    print(f"Error: {res.getErrorCode()} - {res.getErrorMessage()}")

print("\n" + "="*70)
