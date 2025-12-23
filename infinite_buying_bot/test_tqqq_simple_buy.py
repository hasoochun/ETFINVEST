"""
TQQQ 1주 시장가 매수 테스트 V2
- KIS API 해외주식 정규장 주문 (올바른 TR ID 사용)
- TR ID: VTTS0308U (모의투자 해외주식 매수)
- Endpoint: /uapi/overseas-stock/v1/trading/order
"""

import sys
import os
import json
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import requests

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load config
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  🧪 TQQQ 1주 시장가 매수 테스트 V2")
print("  📋 올바른 TR ID: VTTS0308U 사용")
print("="*70)

# ===== Step 1: 설정 로드 및 인증 =====
print("\n📋 Step 1: 설정 로드 및 인증")
print("-"*50)

# 모의투자 인증
svr = "vps"  # 모의투자
product = "01"  # 종합계좌

print(f"서버: {svr} (모의투자)")
print(f"상품코드: {product}")

try:
    ka.auth(svr=svr, product=product)
    trenv = ka.getTREnv()
    print(f"✅ 인증 성공!")
    print(f"   - 계좌번호: {trenv.my_acct}")
    print(f"   - 상품코드: {trenv.my_prod}")
    print(f"   - API URL: {trenv.my_url}")
except Exception as e:
    print(f"❌ 인증 실패: {e}")
    sys.exit(1)

# Rate limit delay
print("\n⏳ Rate Limit 방지를 위해 2초 대기...")
time.sleep(2)

# ===== Step 2: 현재 가격 조회 =====
print("\n📋 Step 2: TQQQ 현재 가격 조회")
print("-"*50)

symbol = "TQQQ"
exchange = "NASD"

try:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    current_price = ticker.fast_info.last_price
    print(f"✅ TQQQ 현재가 (YF): ${current_price:.2f}")
except Exception as e:
    print(f"⚠️ 가격 조회 실패: {e}")
    current_price = 56.0  # 폴백 가격
    print(f"⚠️ 폴백 가격 사용: ${current_price:.2f}")

# ===== Step 3: 주문 파라미터 준비 =====
print("\n📋 Step 3: 주문 파라미터 준비")
print("-"*50)

# 1주 시장가 매수
order_qty = "1"
order_price = "0"  # 시장가

# 모의투자 TR ID (수정됨!)
# 해외주식 정규장 매수: VTTS0308U
# 해외주식 정규장 매도: VTTS0307U
tr_id = "VTTS0308U"

# 올바른 API 엔드포인트
api_url = "/uapi/overseas-stock/v1/trading/order"

# 파라미터 (해외주식 주문 API 규격)
params = {
    "CANO": trenv.my_acct,          # 계좌번호
    "ACNT_PRDT_CD": trenv.my_prod,  # 계좌상품코드
    "OVRS_EXCG_CD": exchange,        # 해외거래소코드 (NASD, NYSE, AMEX 등)
    "PDNO": symbol,                  # 종목코드
    "ORD_QTY": order_qty,            # 주문수량
    "OVRS_ORD_UNPR": order_price,    # 주문단가 (0 = 시장가)
    "ORD_SVR_DVSN_CD": "0",          # 주문서버구분코드
    "ORD_DVSN": "00",                # 주문구분 (00:지정가/시장가)
}

print(f"주문 정보:")
print(f"   - 심볼: {symbol}")
print(f"   - 거래소: {exchange}")
print(f"   - 수량: {order_qty}주")
print(f"   - 가격: 시장가 (0)")
print(f"   - TR_ID: {tr_id} (모의투자 해외주식 매수)")
print(f"   - API URL: {api_url}")
print(f"\n주문 파라미터 (JSON):")
print(json.dumps(params, indent=2, ensure_ascii=False))

# ===== Step 4: 직접 API 호출 =====
print("\n📋 Step 4: KIS API 직접 호출")
print("-"*50)

# 헤더 구성
auth_token = ka._base_headers.get('authorization', '')
if auth_token.startswith('Bearer '):
    auth_token = auth_token

headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    "authorization": auth_token,
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": tr_id,
    "custtype": "P",
    "tr_cont": "",
}

full_url = f"{trenv.my_url}{api_url}"

print(f"요청 URL: {full_url}")
print(f"\n요청 헤더:")
for k, v in headers.items():
    if k in ['authorization', 'appsecret']:
        print(f"   - {k}: {v[:30]}...{v[-10:]}" if len(str(v)) > 40 else f"   - {k}: {v}")
    else:
        print(f"   - {k}: {v}")

# 실제 API 호출
print("\n🚀 주문 전송 중...")
try:
    response = requests.post(
        full_url,
        headers=headers,
        data=json.dumps(params)
    )
    
    print(f"\n응답 상태 코드: {response.status_code}")
    
    print(f"\n응답 헤더 (주요):")
    for k in ['Content-Type', 'tr_id', 'gt_uid']:
        if k in response.headers:
            print(f"   - {k}: {response.headers[k]}")
    
    print(f"\n응답 본문 (Raw):")
    print(response.text[:500])
    
    # JSON 파싱
    try:
        res_json = response.json()
        print(f"\n응답 본문 (JSON, formatted):")
        print(json.dumps(res_json, indent=2, ensure_ascii=False))
        
        # 결과 분석
        rt_cd = res_json.get('rt_cd', '')
        msg_cd = res_json.get('msg_cd', '')
        msg1 = res_json.get('msg1', '')
        
        print(f"\n{'='*60}")
        if rt_cd == "0":
            print(f"✅ 주문 성공!")
            print(f"   - 메시지 코드: {msg_cd}")
            print(f"   - 메시지: {msg1}")
            if 'output' in res_json:
                output = res_json['output']
                print(f"   - 주문번호 (ODNO): {output.get('ODNO', 'N/A')}")
                print(f"   - 주문시간 (ORD_TMD): {output.get('ORD_TMD', 'N/A')}")
        else:
            print(f"❌ 주문 실패!")
            print(f"   - 에러 코드: {msg_cd}")
            print(f"   - 에러 메시지: {msg1}")
            
            # 흔한 에러 원인 분석
            print(f"\n🔍 에러 원인 분석:")
            if "시간" in msg1.lower() or "time" in msg1.lower() or "장시간" in msg1:
                print("   → 주문 가능 시간이 아닙니다")
                print("   → 미국장 정규시간: 한국시간 기준 23:30~06:00 (서머타임 22:30~05:00)")
            elif "잔고" in msg1 or "balance" in msg1.lower() or "부족" in msg1:
                print("   → 잔고 부족")
            elif "권한" in msg1 or "auth" in msg1.lower():
                print("   → 인증/권한 문제")
            elif "TR" in msg1 or "tr_id" in msg1.lower():
                print("   → TR ID 관련 문제")
            elif "주문수량" in msg1 or "quantity" in msg1.lower():
                print("   → 주문 수량 관련 문제")
            else:
                print(f"   → 상세 원인: {msg1}")
        print(f"{'='*60}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ 요청 실패: {e}")

print("\n" + "="*70)
print("  테스트 완료")
print("="*70 + "\n")
