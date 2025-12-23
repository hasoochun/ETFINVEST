"""
🚨 실전투자 TQQQ 1주 시장가 매수 테스트 🚨
- 실제 돈이 사용됩니다!
- TR ID: TTTS0308U (실전 해외주식 매수)
- 현재가 약 $56 기준 1주 주문
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
print("  🚨 실전투자 TQQQ 1주 시장가 매수 테스트 🚨")
print("  ⚠️  실제 돈이 사용됩니다!")
print("="*70)

# 실전투자 인증 (svr='prod')
print("\n📋 Step 1: 실전투자 인증")
ka.auth(svr="prod", product="01")  # prod = 실전투자
trenv = ka.getTREnv()
print(f"✅ 인증 성공!")
print(f"   - 계좌번호: {trenv.my_acct}")
print(f"   - URL: {trenv.my_url}")
print(f"   - 실전투자 서버 확인: {'prod' in trenv.my_url or '9443' in trenv.my_url}")

time.sleep(2)

# TQQQ 1주 시장가 매수
symbol = "TQQQ"
exchange = "NASD"
tr_id = "TTTS0308U"  # 실전투자 해외주식 정규장 매수
api_url = "/uapi/overseas-stock/v1/trading/order"

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": exchange,
    "PDNO": symbol,
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": "0",  # 시장가
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "01",  # 01: 시장가 (00은 지정가)
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

print(f"\n📋 Step 2: 주문 정보")
print(f"   - 종목: {symbol}")
print(f"   - 수량: 1주")
print(f"   - 가격: 시장가")
print(f"   - TR_ID: {tr_id} (실전투자)")

print(f"\n🚀 Step 3: 주문 전송...")
response = requests.post(f"{trenv.my_url}{api_url}", headers=headers, data=json.dumps(params))

print(f"\n📋 응답:")
print(f"Status: {response.status_code}")
res_json = response.json()
print(json.dumps(res_json, indent=2, ensure_ascii=False))

rt_cd = res_json.get('rt_cd', '')
msg_cd = res_json.get('msg_cd', '')
msg1 = res_json.get('msg1', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 주문 성공!")
    print(f"   - 메시지: {msg1}")
    if 'output' in res_json:
        output = res_json['output']
        print(f"   - 주문번호: {output.get('ODNO', 'N/A')}")
        print(f"   - 주문시간: {output.get('ORD_TMD', 'N/A')}")
else:
    print(f"❌ 주문 실패!")
    print(f"   - 에러 코드: {msg_cd}")
    print(f"   - 메시지: {msg1}")
print(f"{'='*60}\n")
