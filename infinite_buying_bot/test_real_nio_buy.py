"""
🚨 실전투자 NIO 1주 시장가 매수 테스트 🚨
- NIO 현재가: ~$5 (원화 약 7,000원)
- 예수금 5만원으로 테스트 가능
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
print("  🚨 실전투자 NIO 1주 시장가 매수 테스트 🚨")
print("="*70)

# 실전투자 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 인증 성공: 계좌 {trenv.my_acct}")

# NIO 현재가 조회
ticker = yf.Ticker("NIO")
current_price = ticker.fast_info.last_price
print(f"📊 NIO 현재가: ${current_price:.2f} (약 ₩{current_price * 1400:,.0f})")

time.sleep(1)

# NIO 주문 (NYSE 상장)
symbol = "NIO"
exchange = "NYSE"  # NIO는 NYSE 상장

# 시장가 주문 시도 (ORD_DVSN='00', 가격 입력)
# 현재가 +5%로 지정가 주문 (시장가가 안되므로)
order_price = round(current_price * 1.05, 2)

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": exchange,
    "PDNO": symbol,
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(order_price),
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00",  # 지정가
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

print(f"\n📋 주문 정보:")
print(f"   - 종목: {symbol} (거래소: {exchange})")
print(f"   - 수량: 1주")
print(f"   - 주문가격: ${order_price} (현재가 +5%)")

print(f"\n🚀 주문 전송...")
response = requests.post(
    f"{trenv.my_url}/uapi/overseas-stock/v1/trading/order",
    headers=headers,
    data=json.dumps(params)
)

res_json = response.json()
print(f"\n📋 응답:")
print(json.dumps(res_json, indent=2, ensure_ascii=False))

rt_cd = res_json.get('rt_cd', '')
msg1 = res_json.get('msg1', '')
msg_cd = res_json.get('msg_cd', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 주문 성공!")
    print(f"   - 메시지: {msg1}")
    if 'output' in res_json:
        output = res_json['output']
        print(f"   - 주문번호: {output.get('ODNO', 'N/A')}")
else:
    print(f"❌ 주문 실패!")
    print(f"   - 에러 코드: {msg_cd}")
    print(f"   - 메시지: {msg1}")
print(f"{'='*60}\n")
