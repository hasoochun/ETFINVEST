"""
잔고 조회 + MAGS ETF 1주 매수 테스트
- 원화(KRW) 및 외화(USD) 잔고 확인
- MAGS ETF 1주 매수 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_krw_balance(trenv):
    """원화 잔고 조회 (국내주식 잔고 API 사용)"""
    print("\n[원화 잔고 조회]")
    
    # 국내주식 잔고 조회 API
    url = f"{trenv.my_url}/uapi/domestic-stock/v1/trading/inquire-balance"
    
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {trenv.my_token}",
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "tr_id": "TTTC8434R",  # 국내주식 잔고조회
        "custtype": "P"
    }
    
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        
        if data.get('rt_cd') == '0':
            output2 = data.get('output2', [])
            if output2:
                item = output2[0] if isinstance(output2, list) else output2
                print(f"  예수금총액: {item.get('dnca_tot_amt', 'N/A')} 원")
                print(f"  출금가능금액: {item.get('nxdy_excc_amt', 'N/A')} 원")
                print(f"  외화예수금: {item.get('frcr_pchs_amt1', 'N/A')}")
                return item
            else:
                print("  ⚠️ 잔고 데이터 없음")
        else:
            print(f"  ❌ 조회 실패: {data.get('msg1', 'Unknown')}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    return None

def check_overseas_balance_detail(trenv):
    """해외주식 잔고 상세 조회"""
    print("\n[해외주식 잔고 상세 조회]")
    
    url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
    
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {trenv.my_token}",
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "tr_id": "CTRP6504R",  # 해외주식 체결기준현재잔고
        "custtype": "P"
    }
    
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "WCRC_FRCR_DVSN_CD": "02",  # 외화
        "NATN_CD": "840",  # 미국
        "TR_MKET_CD": "00",
        "INQR_DVSN_CD": "00"
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        print(f"  응답 코드: {data.get('rt_cd')}")
        print(f"  메시지: {data.get('msg1')}")
        
        if data.get('rt_cd') == '0':
            output1 = data.get('output1')
            output2 = data.get('output2')
            
            if output1:
                print(f"\n  [계좌 정보]")
                if isinstance(output1, dict):
                    for key, val in output1.items():
                        if val and val != '0' and val != '0.00000000':
                            print(f"    {key}: {val}")
            
            if output2:
                print(f"\n  [보유종목]")
                items = output2 if isinstance(output2, list) else [output2]
                for item in items:
                    if isinstance(item, dict):
                        symbol = item.get('ovrs_pdno', 'N/A')
                        qty = item.get('ovrs_cblc_qty', '0')
                        if qty != '0':
                            print(f"    {symbol}: {qty}주")
    except Exception as e:
        print(f"  ❌ 오류: {e}")

def check_krw_to_usd_available(trenv):
    """원화 통합증거금(자동환전) 가능 여부 확인"""
    print("\n[해외주식 주문가능금액 조회 (원화/외화)]")
    
    url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
    
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {trenv.my_token}",
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "tr_id": "TTTS3007R",  # 해외주식 주문가능금액
        "custtype": "P"
    }
    
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "OVRS_EXCG_CD": "NASD",
        "OVRS_ORD_UNPR": "80",  # 예상 주문가격 (MAGS 대략)
        "ITEM_CD": "MAGS"
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        print(f"  응답 코드: {data.get('rt_cd')}")
        print(f"  메시지: {data.get('msg1')}")
        
        if data.get('rt_cd') == '0':
            output = data.get('output', {})
            print(f"\n  [주문가능금액]")
            print(f"    외화주문가능금액: ${output.get('ovrs_ord_psbl_amt', 'N/A')}")
            print(f"    외화주문가능수량: {output.get('max_ord_psbl_qty', 'N/A')}주")
            print(f"    원화환산금액: {output.get('frcr_ord_psbl_amt1', 'N/A')}원")
            return output
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    return None

def test_mags_buy(trenv, price):
    """MAGS ETF 1주 매수 테스트"""
    print("\n" + "=" * 60)
    print("🧪 MAGS ETF 1주 매수 테스트")
    print("=" * 60)
    
    print(f"    종목: MAGS (Roundhill Magnificent Seven ETF)")
    print(f"    수량: 1주")
    print(f"    가격: ${price:.2f} (지정가)")
    
    try:
        result = api.order(
            order_dv="buy",
            cano=trenv.my_acct,
            acnt_prdt_cd=trenv.my_prod,
            ovrs_excg_cd="NASD",
            pdno="MAGS",
            ord_qty="1",
            ovrs_ord_unpr=str(price),
            ord_dvsn="00",
            env_dv="real"
        )
        
        if not result.empty:
            print("\n✅ 주문 전송 성공!")
            print(f"   결과: {result.to_dict()}")
        else:
            print("\n❌ 주문 실패 (빈 응답)")
        
    except Exception as e:
        print(f"\n❌ 주문 실패: {e}")

def main():
    print("=" * 60)
    print("🔍 계좌 상태 진단 + MAGS 매수 테스트")
    print("=" * 60)
    
    # 1. 인증
    print("\n[인증]")
    try:
        ka.auth(svr='prod', product='01')
        trenv = ka.getTREnv()
        print(f"✅ 인증 성공! 계좌: {trenv.my_acct}")
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        return
    
    # 2. 원화 잔고 조회
    check_krw_balance(trenv)
    
    # 3. 해외주식 잔고 상세 조회
    check_overseas_balance_detail(trenv)
    
    # 4. 주문가능금액 조회 (통합증거금 확인)
    order_info = check_krw_to_usd_available(trenv)
    
    # 5. MAGS 가격 조회
    print("\n[MAGS 현재가 조회]")
    try:
        df = api.price(auth="", excd="NASD", symb="MAGS", env_dv="real")
        if not df.empty:
            mags_price = float(df['last'].iloc[0])
            print(f"  ✅ MAGS 현재가: ${mags_price:.2f}")
        else:
            mags_price = 45.0  # 대략적 예상가
            print(f"  ⚠️ 가격 조회 실패, 예상가 사용: ${mags_price:.2f}")
    except Exception as e:
        mags_price = 45.0
        print(f"  ⚠️ 가격 조회 실패: {e}")
    
    # 6. MAGS 매수 테스트
    test_mags_buy(trenv, mags_price)
    
    print("\n" + "=" * 60)
    print("진단 완료")
    print("=" * 60)

if __name__ == "__main__":
    main()
