"""
통합증거금 계좌 상세 진단
- 다양한 잔고 조회 API 테스트
- 원화/외화 주문가능금액 확인
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka
import requests
import json

def main():
    print("=" * 70)
    print("🔍 통합증거금 계좌 상세 진단")
    print("=" * 70)
    
    # 인증
    ka.auth(svr='prod', product='01')
    trenv = ka.getTREnv()
    print(f"✅ 계좌: {trenv.my_acct}")
    
    base_headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {trenv.my_token}",
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "custtype": "P"
    }
    
    # 1. 해외주식 주문가능금액 조회 (TTTS3007R)
    print("\n" + "=" * 70)
    print("[1] 해외주식 주문가능금액 조회 (TTTS3007R)")
    print("=" * 70)
    
    url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
    headers = {**base_headers, "tr_id": "TTTS3007R"}
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "OVRS_EXCG_CD": "NASD",
        "OVRS_ORD_UNPR": "50",
        "ITEM_CD": "QQQ"  # 일반 ETF로 테스트
    }
    
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    print(f"응답코드: {data.get('rt_cd')} | 메시지: {data.get('msg1')}")
    if data.get('output'):
        out = data['output']
        print(f"  외화주문가능금액: ${out.get('ovrs_ord_psbl_amt', 'N/A')}")
        print(f"  최대주문가능수량: {out.get('max_ord_psbl_qty', 'N/A')}주")
        print(f"  원화환산금액: {out.get('frcr_ord_psbl_amt1', 'N/A')}원")
        print(f"  전체 output: {json.dumps(out, indent=2, ensure_ascii=False)}")
    
    # 2. 해외주식 체결기준현재잔고 (TTTC8434R)
    print("\n" + "=" * 70)
    print("[2] 해외주식 체결기준현재잔고 (TTTC8434R)")
    print("=" * 70)
    
    url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
    headers = {**base_headers, "tr_id": "TTTC8434R"}
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "WCRC_FRCR_DVSN_CD": "02",
        "NATN_CD": "840",
        "TR_MKET_CD": "00",
        "INQR_DVSN_CD": "00"
    }
    
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    print(f"응답코드: {data.get('rt_cd')} | 메시지: {data.get('msg1')}")
    
    if data.get('output1'):
        print("\n[output1 - 계좌정보]")
        out1 = data['output1']
        if isinstance(out1, dict):
            for k, v in out1.items():
                if v and str(v) not in ['0', '0.00', '0.00000000', '']:
                    print(f"  {k}: {v}")
    
    if data.get('output2'):
        print("\n[output2 - 보유종목]")
        out2 = data['output2']
        items = out2 if isinstance(out2, list) else [out2]
        for item in items:
            if isinstance(item, dict):
                qty = item.get('ovrs_cblc_qty', '0')
                if qty != '0':
                    print(f"  {item.get('ovrs_pdno')}: {qty}주")
        if not any(item.get('ovrs_cblc_qty', '0') != '0' for item in items if isinstance(item, dict)):
            print("  (보유 종목 없음)")
    
    # 3. 해외주식 잔고 (CTRP6504R - 다른 API)
    print("\n" + "=" * 70)
    print("[3] 해외주식 잔고 대안 API (CTRP6504R)")
    print("=" * 70)
    
    url = f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    headers = {**base_headers, "tr_id": "CTRP6504R"}
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }
    
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    print(f"응답코드: {data.get('rt_cd')} | 메시지: {data.get('msg1')}")
    
    if data.get('output1'):
        print(f"\n[output1]: {json.dumps(data['output1'], indent=2, ensure_ascii=False)[:500]}")
    
    # 4. QQQ 1주 매수 테스트 (일반 ETF)
    print("\n" + "=" * 70)
    print("[4] QQQ 1주 매수 테스트 (일반 ETF, 레버리지 아님)")
    print("=" * 70)
    
    # 가격 조회
    from infinite_buying_bot.api import kis_api as api
    try:
        df = api.price(auth="", excd="NASD", symb="QQQ", env_dv="real")
        if not df.empty:
            price = float(df['last'].iloc[0])
            print(f"QQQ 현재가: ${price:.2f}")
        else:
            price = 520.0
    except:
        price = 520.0
    
    # 매수 주문
    result = api.order(
        order_dv="buy",
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        ovrs_excg_cd="NASD",
        pdno="QQQ",
        ord_qty="1",
        ovrs_ord_unpr=str(price),
        ord_dvsn="00",
        env_dv="real"
    )
    
    if not result.empty:
        print(f"✅ 주문 성공: {result.to_dict()}")
    else:
        print("❌ 주문 실패 (빈 응답) - 로그에서 에러 코드 확인")
    
    print("\n" + "=" * 70)
    print("진단 완료")
    print("=" * 70)

if __name__ == "__main__":
    main()
