"""ETF별 거래소 코드 테스트"""
import requests
import yaml
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

# Config/Token 로드
with open(os.path.join(base_dir, 'kis_devlp.yaml'), 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
with open(os.path.join(base_dir, 'real_trading_bot', 'config', 'token_real.yaml'), 'r', encoding='utf-8') as f:
    token_data = yaml.safe_load(f)

# 테스트할 조합
tests = [
    ('TQQQ', ['NASD', 'NYSE', 'AMEX']),
    ('JEPI', ['NYSE', 'NASD', 'AMEX']),
    ('MAGS', ['NASD', 'NYSE', 'AMEX']),  # Cboe BZX는 없으니 시도
]

for symbol, exchanges in tests:
    print(f"\n{'='*50}")
    print(f"Testing {symbol}...")
    
    for excd in exchanges:
        headers = {
            'content-type': 'application/json; charset=utf-8',
            'authorization': f"Bearer {token_data['token']}",
            'appkey': config['my_app'],
            'appsecret': config['my_sec'],
            'tr_id': 'TTTT1002U'  # 미국 매수
        }
        
        body = {
            "CANO": config['my_acct_stock'],
            "ACNT_PRDT_CD": "01",
            "OVRS_EXCG_CD": excd,
            "PDNO": symbol,
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": "50.00",  # 임시 가격
            "ORD_DVSN": "00",
            "ORD_SVR_DVSN_CD": "0"
        }
        
        res = requests.post(
            'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/order',
            headers=headers,
            json=body
        )
        
        data = res.json()
        rt_cd = data.get('rt_cd')
        msg_cd = data.get('msg_cd', '')
        msg1 = data.get('msg1', '')
        
        # 성공 또는 가격 관련 오류면 거래소가 맞는 것
        if rt_cd == '0':
            print(f"✅ {excd}: SUCCESS")
            break
        elif '가격' in msg1 or '단가' in msg1 or 'price' in msg1.lower():
            print(f"✅ {excd}: 거래소 OK (가격 오류)")
            break
        elif '종목정보' in msg1 or '거래소코드' in msg1:
            print(f"❌ {excd}: 종목/거래소 불일치")
        else:
            print(f"? {excd}: {msg_cd} - {msg1}")
