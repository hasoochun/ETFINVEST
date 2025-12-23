import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()

time.sleep(1)

tr_id = "TTTS3012R"
api_url = "/uapi/overseas-stock/v1/trading/inquire-balance"

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NYSE",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": "",
}

headers = {
    "Content-Type": "application/json",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": tr_id,
    "custtype": "P",
}

r = requests.get(f"{trenv.my_url}{api_url}", headers=headers, params=params)
res = r.json()

# Save to file
with open("balance_output.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print("Saved to balance_output.json")
print(f"rt_cd: {res.get('rt_cd')}")
print(f"msg1: {res.get('msg1')}")

if res.get('output1'):
    print(f"Holdings count: {len(res['output1'])}")
    for item in res['output1']:
        print(f"  - {item.get('ovrs_pdno', 'N/A')}: {item.get('ovrs_cblc_qty', 0)} shares")
