"""
일반 ETF 1주 매수 테스트 (SPY, QQQ, 또는 MAGS)
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api

print("=" * 60)
print("🧪 일반 ETF 1주 매수 테스트")
print("=" * 60)

# 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 계좌: {trenv.my_acct}")

# 테스트할 ETF 목록 (레버리지 아님)
test_etfs = [
    ("MAGS", 45.0),   # Magnificent Seven ETF
    ("SPY", 600.0),   # S&P 500 ETF
    ("QQQ", 530.0),   # Nasdaq 100 ETF
]

for symbol, default_price in test_etfs:
    print(f"\n{'='*60}")
    print(f"[{symbol}] 테스트")
    print("=" * 60)
    
    time.sleep(1)
    
    # 가격 조회 시도
    try:
        df = api.price(auth="", excd="NASD", symb=symbol, env_dv="real")
        if not df.empty and df['last'].iloc[0]:
            price = float(df['last'].iloc[0])
            print(f"   현재가: ${price:.2f}")
        else:
            price = default_price
            print(f"   가격 조회 실패, 기본값 사용: ${price:.2f}")
    except Exception as e:
        price = default_price
        print(f"   가격 조회 오류: {e}, 기본값 사용: ${price:.2f}")
    
    time.sleep(1)
    
    # 매수 주문
    print(f"\n   📤 {symbol} 1주 지정가 매수 주문...")
    result = api.order(
        order_dv="buy",
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        ovrs_excg_cd="NASD",
        pdno=symbol,
        ord_qty="1",
        ovrs_ord_unpr=str(price),
        ord_dvsn="00",
        env_dv="real"
    )
    
    if not result.empty:
        print(f"   ✅ {symbol} 주문 성공!")
        print(f"      결과: {result.to_dict()}")
        break  # 성공하면 종료
    else:
        print(f"   ❌ {symbol} 주문 실패 - 다음 ETF 시도...")
        # 로그에서 에러 확인됨

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
