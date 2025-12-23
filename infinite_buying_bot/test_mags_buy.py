"""
MAGS ETF 1주 매수 테스트 (일반 ETF, 레버리지 아님)
Roundhill Magnificent Seven ETF
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api

print("=" * 60)
print("🧪 MAGS ETF 1주 매수 테스트")
print("=" * 60)

# 1. 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 계좌: {trenv.my_acct}")

time.sleep(1)

# 2. MAGS 현재가 조회
print("\n[1] MAGS 현재가 조회...")
try:
    df = api.price(auth="", excd="NASD", symb="MAGS", env_dv="real")
    if not df.empty:
        mags_price = float(df['last'].iloc[0])
        print(f"   ✅ MAGS 현재가: ${mags_price:.2f}")
    else:
        mags_price = 45.0
        print(f"   ⚠️ 가격 조회 실패, 예상가 사용: ${mags_price}")
except Exception as e:
    mags_price = 45.0
    print(f"   ⚠️ 가격 조회 실패: {e}")

time.sleep(1)

# 3. 주문가능금액 확인
print("\n[2] MAGS 주문가능금액 조회...")
url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
headers = {
    "Content-Type": "application/json",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": "TTTS3007R",
    "custtype": "P",
}
params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NASD",
    "OVRS_ORD_UNPR": str(mags_price),
    "ITEM_CD": "MAGS"
}

r = requests.get(url, headers=headers, params=params)
res = r.json()
print(f"   응답: {res.get('rt_cd')} - {res.get('msg1')}")
if res.get('output'):
    out = res['output']
    print(f"   외화주문가능금액: ${out.get('ovrs_ord_psbl_amt', 'N/A')}")
    print(f"   최대주문가능수량: {out.get('max_ord_psbl_qty', 'N/A')}주")

time.sleep(1)

# 4. MAGS 1주 매수 주문
print("\n[3] MAGS 1주 매수 주문...")
print(f"   종목: MAGS (Roundhill Magnificent Seven ETF)")
print(f"   수량: 1주")
print(f"   가격: ${mags_price:.2f} (지정가)")
print(f"   거래소: NASD")

result = api.order(
    order_dv="buy",
    cano=trenv.my_acct,
    acnt_prdt_cd=trenv.my_prod,
    ovrs_excg_cd="NASD",
    pdno="MAGS",
    ord_qty="1",
    ovrs_ord_unpr=str(mags_price),
    ord_dvsn="00",  # 지정가
    env_dv="real"
)

print("\n" + "=" * 60)
if not result.empty:
    print("✅ 주문 전송 성공!")
    print(f"   결과: {result.to_dict()}")
else:
    print("❌ 주문 실패")
    print("   로그에서 에러 코드 확인 필요")
print("=" * 60)
