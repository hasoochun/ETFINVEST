"""
프로젝트 ETF 시세 조회 및 소수점 매매 테스트
- TQQQ, SHV, SCHD 시세 조회
- 소수점 주문 가능 여부 확인 (실전투자)
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import yfinance as yf
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

print("="*70)
print("  📊 프로젝트 ETF 시세 조회 및 소수점 매매 테스트")
print("="*70)

# 실전투자 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 계좌: {trenv.my_acct} (실전투자)")

# 프로젝트 ETF 목록
etfs = [
    ("TQQQ", "NASD", "3배 레버리지 QQQ"),
    ("SHV", "NASD", "단기국채 ETF"),
    ("SCHD", "NYSE", "배당성장 ETF"),
]

print("\n" + "="*70)
print("  1️⃣ ETF 시세 조회")
print("="*70)

for symbol, exchange, desc in etfs:
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        
        # 40분할, 80분할 계산
        split_40 = price / 40
        split_80 = price / 80
        
        print(f"\n📈 {symbol} ({desc})")
        print(f"   현재가: ${price:.2f}")
        print(f"   40분할: ${split_40:.4f}/주")
        print(f"   80분할: ${split_80:.4f}/주")
    except Exception as e:
        print(f"❌ {symbol} 조회 실패: {e}")
    time.sleep(0.3)

print("\n" + "="*70)
print("  2️⃣ 소수점 주문 테스트 (TQQQ 0.1주)")
print("="*70)

time.sleep(1)

# TQQQ 0.1주 소수점 주문 테스트
ticker = yf.Ticker("TQQQ")
price = ticker.fast_info.last_price
order_price = str(round(price * 1.02, 2))

# 소수점 주문
params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "TQQQ",
    "ORD_QTY": "0.1",  # 소수점!
    "OVRS_ORD_UNPR": order_price,
    "CTAC_TLNO": "",
    "MGCO_APTM_ODNO": "",
    "SLL_TYPE": "",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00",
}

headers = {
    "Content-Type": "application/json",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": "TTTT1002U",
    "custtype": "P",
}

print(f"📋 주문: TQQQ 0.1주 @ ${order_price}")
r = requests.post(f"{trenv.my_url}/uapi/overseas-stock/v1/trading/order",
                  headers=headers, data=json.dumps(params))
res = r.json()

print(f"\n📋 응답:")
print(json.dumps(res, indent=2, ensure_ascii=False))

rt_cd = res.get('rt_cd', '')
msg1 = res.get('msg1', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 소수점 주문 성공! {msg1}")
    if 'output' in res:
        print(f"   주문번호: {res['output'].get('ODNO', 'N/A')}")
else:
    print(f"❌ 주문 실패: {res.get('msg_cd', '')} - {msg1}")
print(f"{'='*60}\n")
