"""
모의투자 지원 종목 테스트
- 여러 종목으로 테스트하여 거래 가능 종목 확인
- SPY, MSFT, GOOGL, NVDA 등 주요 종목 테스트
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
print("  🧪 모의투자 지원 종목 테스트")
print("="*70)

# 인증
ka.auth(svr="vps", product="01")
trenv = ka.getTREnv()
print(f"✅ 인증 성공: 계좌 {trenv.my_acct}")
print(f"   URL: {trenv.my_url}")

time.sleep(2)

# 테스트할 종목 목록
# ETF와 개별 주식 모두 포함
test_symbols = [
    ("SPY", "NASD", "S&P 500 ETF"),      # 가장 유명한 ETF
    ("QQQ", "NASD", "Nasdaq 100 ETF"),    # 나스닥 ETF
    ("MSFT", "NASD", "Microsoft"),        # 대형주
    ("NVDA", "NASD", "NVIDIA"),           # 반도체
    ("GOOGL", "NASD", "Google"),          # 대형주
    ("AMZN", "NASD", "Amazon"),           # 대형주
    ("TQQQ", "NASD", "3x Nasdaq ETF"),    # 레버리지 ETF
    ("SOXL", "NASD", "3x 반도체 ETF"),   # 레버리지 ETF
    ("SHV", "NASD", "단기채권 ETF"),     # 채권 ETF
    ("SCHD", "NYSE", "배당 ETF"),        # 배당 ETF
]

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

print(f"\n{'='*70}")
print(f"{'종목':<8} {'거래소':<6} {'설명':<20} {'결과'}")
print(f"{'='*70}")

results = []

for symbol, exchange, desc in test_symbols:
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
    
    try:
        response = requests.post(f"{trenv.my_url}{api_url}", headers=headers, data=json.dumps(params))
        res_json = response.json()
        
        rt_cd = res_json.get('rt_cd', '')
        msg_cd = res_json.get('msg_cd', '')
        msg1 = res_json.get('msg1', '')
        
        if rt_cd == "0":
            status = "✅ 성공"
            results.append((symbol, exchange, desc, "SUCCESS", msg1))
        else:
            if "매매불가" in msg1:
                status = "❌ 매매불가"
            elif "초과" in msg1:
                status = "⚠️ Rate Limit"
            else:
                status = f"❌ {msg_cd}"
            results.append((symbol, exchange, desc, "FAIL", msg1))
            
        print(f"{symbol:<8} {exchange:<6} {desc:<20} {status}")
        
    except Exception as e:
        print(f"{symbol:<8} {exchange:<6} {desc:<20} ❌ 에러: {str(e)[:30]}")
        results.append((symbol, exchange, desc, "ERROR", str(e)))
    
    # Rate limit 방지
    time.sleep(0.6)

print(f"{'='*70}")

# 결과 요약
print("\n📊 결과 요약:")
success_count = sum(1 for r in results if r[3] == "SUCCESS")
fail_count = sum(1 for r in results if r[3] == "FAIL")

print(f"   - 성공: {success_count}개")
print(f"   - 실패: {fail_count}개")

if success_count > 0:
    print("\n✅ 거래 가능 종목:")
    for r in results:
        if r[3] == "SUCCESS":
            print(f"   - {r[0]} ({r[2]})")

print("\n" + "="*70)
print("  테스트 완료")
print("="*70 + "\n")
