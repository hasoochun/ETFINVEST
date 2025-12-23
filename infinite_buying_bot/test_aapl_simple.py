"""AAPL 단일 테스트"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

ka.auth(svr="vps", product="01")
trenv = ka.getTREnv()
print(f"계좌: {trenv.my_acct}")

time.sleep(2)

# AAPL 1주 시장가 매수
params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "AAPL",
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": "0",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00",
}

headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": "VTTS0308U",
    "custtype": "P",
    "tr_cont": "",
}

print("AAPL 1주 시장가 매수 테스트...")
r = requests.post(f"{trenv.my_url}/uapi/overseas-stock/v1/trading/order", headers=headers, data=json.dumps(params))
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
