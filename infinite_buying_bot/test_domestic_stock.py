"""
국내 주식 모의투자 테스트
- 해외주식이 모두 실패했으므로 국내 주식으로 계정 정상 여부 확인
- 삼성전자(005930) 1주 시장가 매수 테스트
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
print("  🧪 국내 주식 모의투자 테스트 (삼성전자)")
print("  📋 해외주식 실패 → 국내 주식으로 계정 정상 여부 확인")
print("="*70)

# 인증
ka.auth(svr="vps", product="01")
trenv = ka.getTREnv()
print(f"✅ 인증 성공: 계좌 {trenv.my_acct}")

time.sleep(2)

# 국내 주식 주문 API
# 모의투자: VTTC0801U (현금매수), VTTC0802U (현금매도)
symbol = "005930"  # 삼성전자
tr_id = "VTTC0801U"  # 국내주식 현금매수 (모의투자)
api_url = "/uapi/domestic-stock/v1/trading/order-cash"

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "PDNO": symbol,
    "ORD_DVSN": "01",  # 01: 시장가
    "ORD_QTY": "1",
    "ORD_UNPR": "0",  # 시장가이므로 0
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

print(f"\n📋 주문 정보:")
print(f"   - 종목: {symbol} (삼성전자)")
print(f"   - TR_ID: {tr_id}")
print(f"   - API: {api_url}")
print(f"   - 수량: 1주")
print(f"   - 가격: 시장가")

print(f"\n🚀 주문 전송 중...")
response = requests.post(f"{trenv.my_url}{api_url}", headers=headers, data=json.dumps(params))

print(f"\n응답 상태: {response.status_code}")
print(f"응답 본문:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

res_json = response.json()
rt_cd = res_json.get('rt_cd', '')
msg1 = res_json.get('msg1', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 국내 주식 주문 성공!")
    print(f"   → 모의투자 계정 정상 작동")
    print(f"   → 해외주식만 제한되어 있을 가능성 높음")
else:
    print(f"❌ 주문 실패: {msg1}")
    if "시간" in msg1:
        print(f"   → 장시간 외 (국내장: 09:00-15:30)")
    elif "매매불가" in msg1:
        print(f"   → 국내 주식도 매매불가 - 모의투자 신청 필요할 수 있음")
print(f"{'='*60}\n")
