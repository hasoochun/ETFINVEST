"""
실전투자 해외주식 잔고 조회 테스트
- Ford 1주가 잔고에 있는지 확인
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

# 실전투자 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"계좌: {trenv.my_acct}")

time.sleep(1)

# 해외주식 잔고 조회
tr_id = "TTTS3012R"  # 실전투자 해외주식 잔고
api_url = "/uapi/overseas-stock/v1/trading/inquire-balance"

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NYSE",  # Ford는 NYSE
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

print(f"\n[INFO] 해외주식 잔고 조회 (NYSE - Ford)...")
r = requests.get(f"{trenv.my_url}{api_url}", headers=headers, params=params)
res = r.json()

print(f"\n응답 (Status: {r.status_code}):")
print(json.dumps(res, indent=2, ensure_ascii=False))

# NASD 거래소도 확인
time.sleep(1)
params["OVRS_EXCG_CD"] = "NASD"
print(f"\n[INFO] 해외주식 잔고 조회 (NASD)...")
r = requests.get(f"{trenv.my_url}{api_url}", headers=headers, params=params)
res = r.json()
print(f"\n응답 (Status: {r.status_code}):")
print(json.dumps(res, indent=2, ensure_ascii=False))
