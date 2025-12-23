"""
TQQQ 1주 매수 테스트 - 레버리지 ETF 거래 가능 여부 확인
실행: python test_tqqq_buy_permission.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tqqq_buy():
    """TQQQ 1주 매수 테스트"""
    
    print("=" * 60)
    print("🧪 TQQQ 1주 매수 테스트 (레버리지 ETF 거래 권한 확인)")
    print("=" * 60)
    
    # 1. 인증
    print("\n[1] KIS API 인증 중...")
    try:
        ka.auth(svr='prod', product='01')  # 실전투자
        trenv = ka.getTREnv()
        print(f"✅ 인증 성공! 계좌: {trenv.my_acct}")
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        return
    
    # 2. 현재 TQQQ 가격 확인
    print("\n[2] TQQQ 현재가 조회 중...")
    try:
        df = api.price(auth="", excd="NASD", symb="TQQQ", env_dv="real")
        if not df.empty:
            current_price = float(df['last'].iloc[0])
            print(f"✅ TQQQ 현재가: ${current_price:.2f}")
        else:
            print("⚠️ 가격 조회 실패 (빈 데이터)")
            current_price = 85.0  # 대략적인 예상가
    except Exception as e:
        print(f"⚠️ 가격 조회 실패: {e}")
        current_price = 85.0
    
    # 3. 잔고 확인
    print("\n[3] 계좌 잔고 확인 중...")
    try:
        df1, df2 = api.inquire_balance(
            cano=trenv.my_acct,
            acnt_prdt_cd=trenv.my_prod,
            ovrs_excg_cd="NASD",
            tr_crcy_cd="USD",
            env_dv="real"
        )
        if not df1.empty:
            print(f"✅ 잔고 조회 성공")
            print(f"   DF1 컬럼: {df1.columns.tolist()}")
        else:
            print("⚠️ 잔고 데이터 없음")
    except Exception as e:
        print(f"⚠️ 잔고 조회 실패: {e}")
    
    # 4. TQQQ 1주 매수 주문 테스트
    print("\n[4] TQQQ 1주 매수 주문 전송 중...")
    print(f"    주문 수량: 1주")
    print(f"    주문 가격: ${current_price:.2f} (지정가)")
    print(f"    거래소: NASD")
    print(f"    TR_ID: TTTT1002U (해외주식 매수)")
    
    try:
        result = api.order(
            order_dv="buy",
            cano=trenv.my_acct,
            acnt_prdt_cd=trenv.my_prod,
            ovrs_excg_cd="NASD",
            pdno="TQQQ",
            ord_qty="1",
            ovrs_ord_unpr=str(current_price),  # 지정가 주문
            ord_dvsn="00",  # 지정가
            env_dv="real"
        )
        
        print("\n" + "=" * 60)
        if not result.empty:
            print("✅ 주문 전송 성공!")
            print(f"   주문 결과: {result.to_dict()}")
        else:
            print("❌ 주문 실패 (빈 응답)")
            print("   가능한 원인:")
            print("   1. 레버리지 ETF 교육 이수 미완료")
            print("   2. 해외주식 거래 미신청")
            print("   3. 잔고 부족")
            print("   4. 시장 마감")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 주문 실패: {e}")
        print("   가능한 원인:")
        print("   1. 레버리지 ETF 교육 이수 미완료")
        print("   2. 해외주식 거래 미신청")  
        print("   3. API 권한 문제")
        print("=" * 60)

if __name__ == "__main__":
    test_tqqq_buy()
