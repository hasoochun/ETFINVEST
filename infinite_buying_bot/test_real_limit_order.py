"""
🚨 실전투자 TQQQ 1주 지정가 매수 테스트 🚨
- 현재가 조회 후 지정가 주문
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import yfinance as yf
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  🚨 실전투자 TQQQ 1주 지정가 매수 테스트 🚨")
print("="*70)

# 실전투자 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 인증 성공: 계좌 {trenv.my_acct}")

# 현재가 조회 (Yahoo Finance)
ticker = yf.Ticker("TQQQ")
current_price = ticker.fast_info.last_price
# 현재가보다 약간 높게 (확실하게 체결되도록)
order_price = round(current_price * 1.01, 2)  
print(f"📊 TQQQ 현재가: ${current_price:.2f}")
print(f"📊 주문가격: ${order_price:.2f} (현재가 +1%)")

time.sleep(1)

# TQQQ 1주 지정가 매수
params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "TQQQ",
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(order_price),  # 지정가
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00",  # 00: 지정가
}

headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": "TTTS0308U",
    "custtype": "P",
    "tr_cont": "",
}

print(f"\n🚀 TQQQ 1주 ${order_price} 지정가 매수 주문...")
response = requests.post(
    f"{trenv.my_url}/uapi/overseas-stock/v1/trading/order",
    headers=headers,
    data=json.dumps(params)
)

res_json = response.json()
print(f"\n응답:")
print(json.dumps(res_json, indent=2, ensure_ascii=False))

rt_cd = res_json.get('rt_cd', '')
msg1 = res_json.get('msg1', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 주문 성공! {msg1}")
    if 'output' in res_json:
        print(f"   주문번호: {res_json['output'].get('ODNO', 'N/A')}")
else:
    print(f"❌ 주문 실패: {res_json.get('msg_cd', '')} - {msg1}")
print(f"{'='*60}\n")
