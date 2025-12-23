"""Simple MAGS 1 share buy - direct API call with full error output"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

# 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"계좌: {trenv.my_acct}")

time.sleep(1)

# 직접 API 호출 (MAGS 1주 매수)
symbol = "MAGS"
price = "45.00"  # 고정 가격

url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/order"
headers = {
    "Content-Type": "application/json",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": "TTTT1002U",  # 해외주식 매수 (실전)
    "custtype": "P",
}
body = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NASD",
    "PDNO": symbol,
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": price,
    "CTAC_TLNO": "",
    "MGCO_APTM_ODNO": "",
    "SLL_TYPE": "",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00",
}

print(f"\n📤 {symbol} 1주 매수 주문 전송...")
print(f"   URL: {url}")
print(f"   TR_ID: {headers['tr_id']}")
print(f"   가격: ${price}")

r = requests.post(url, headers=headers, data=json.dumps(body))
res = r.json()

print(f"\n📥 응답 (Status: {r.status_code}):")
print(json.dumps(res, indent=2, ensure_ascii=False))
