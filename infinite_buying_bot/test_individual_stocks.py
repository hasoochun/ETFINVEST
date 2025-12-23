"""
해외 개별주식 모의투자 테스트 (KIS 문서 기반)
- ETF가 아닌 개별 주식으로 테스트
- 미국장 정규시간 중이므로 테스트 가능
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
print("  🧪 해외 개별주식 모의투자 테스트")
print("="*70)

# 인증
ka.auth(svr="vps", product="01")
trenv = ka.getTREnv()
print(f"✅ 인증 성공: 계좌 {trenv.my_acct}")

time.sleep(1)

# 개별 주식 테스트 (ETF 제외)
test_symbols = [
    ("AAPL", "NASD", "Apple"),
    ("TSLA", "NASD", "Tesla"),
    ("META", "NASD", "Meta"),
    ("INTC", "NASD", "Intel"),
    ("AMD", "NASD", "AMD"),
    ("COST", "NASD", "Costco"),
    ("KO", "NYSE", "Coca-Cola"),
    ("JPM", "NYSE", "JPMorgan"),
]

# 정규장 해외주식 주문 API
tr_id = "VTTS0308U"
api_url = "/uapi/overseas-stock/v1/trading/order"

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

print(f"\n{'종목':<8} {'거래소':<6} {'설명':<15} {'결과'}")
print("-"*60)

for symbol, exchange, desc in test_symbols:
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "OVRS_EXCG_CD": exchange,
        "PDNO": symbol,
        "ORD_QTY": "1",
        "OVRS_ORD_UNPR": "0",
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": "00",
    }
    
    try:
        response = requests.post(f"{trenv.my_url}{api_url}", headers=headers, data=json.dumps(params))
        res = response.json()
        
        rt_cd = res.get('rt_cd', '')
        msg1 = res.get('msg1', '')
        msg_cd = res.get('msg_cd', '')
        
        if rt_cd == "0":
            print(f"{symbol:<8} {exchange:<6} {desc:<15} ✅ 성공!")
        else:
            short_msg = msg1[:25] if len(msg1) > 25 else msg1
            print(f"{symbol:<8} {exchange:<6} {desc:<15} ❌ {msg_cd}: {short_msg}")
            
    except Exception as e:
        print(f"{symbol:<8} {exchange:<6} {desc:<15} ❌ 에러")
    
    time.sleep(0.6)

print("-"*60)
print("\n테스트 완료")
