import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infinite_buying_bot.api import kis_auth as ka
import json

ka.auth(svr='vps', product='01')
trenv = ka.getTREnv()

api_url = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
tr_id = "VTTC8908R"
params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "WCRC_FRCR_DVSN_CD": "02",
    "NATN_CD": "840",
    "TR_MKET_CD": "01",
    "INQR_DVSN_CD": "00",
}

res = ka._url_fetch(api_url=api_url, ptr_id=tr_id, tr_cont="", params=params)

with open("api_test_result.txt", 'w', encoding='utf-8') as f:
    f.write(f"Is OK: {res.isOK()}\n")
    f.write(f"Error Code: {res.getErrorCode()}\n")
    f.write(f"Error Message: {res.getErrorMessage()}\n\n")
    
    if res.isOK():
        body = res.getBody()
        for attr in ['output1', 'output2', 'output3']:
            if hasattr(body, attr):
                data = getattr(body, attr)
                f.write(f"\n{attr}:\n")
                f.write(json.dumps(data, indent=2, ensure_ascii=False))
                f.write("\n")

print("Results saved to api_test_result.txt")
