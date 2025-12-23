"""
AAPL 1주 시장가 매수 테스트
- TQQQ는 모의투자에서 매매불가
- AAPL로 테스트하여 API 정상 작동 확인
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  🧪 AAPL 1주 시장가 매수 테스트")
print("  ⚠️  TQQQ는 모의투자 매매불가 → AAPL로 테스트")
print("="*70)

# 인증
ka.auth(svr="vps", product="01")
trenv = ka.getTREnv()
print(f"✅ 인증 성공: 계좌 {trenv.my_acct}")

time.sleep(2)

# AAPL 테스트
symbol = "AAPL"
exchange = "NASD"
tr_id = "VTTS0308U"
api_url = "/uapi/overseas-stock/v1/trading/order"

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": exchange,
    "PDNO": symbol,
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": "0",  # 시장가
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
    "tr_id": tr_id,
    "custtype": "P",
    "tr_cont": "",
}

print(f"\n🚀 {symbol} 1주 시장가 매수 요청...")
response = requests.post(f"{trenv.my_url}{api_url}", headers=headers, data=json.dumps(params))

res_json = response.json()
print(f"\n응답:")
print(json.dumps(res_json, indent=2, ensure_ascii=False))

rt_cd = res_json.get('rt_cd', '')
msg1 = res_json.get('msg1', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 주문 성공! {msg1}")
else:
    print(f"❌ 주문 실패: {msg1}")
print(f"{'='*60}\n")
