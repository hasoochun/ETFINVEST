"""KIS API 거래소 코드 테스트 - MAGS, JEPI"""
import requests
import yaml
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

# Config/Token 로드
with open(os.path.join(base_dir, 'kis_devlp.yaml'), 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
with open(os.path.join(base_dir, 'real_trading_bot', 'config', 'token_real.yaml'), 'r', encoding='utf-8') as f:
    token_data = yaml.safe_load(f)

headers = {
    'content-type': 'application/json',
    'authorization': f"Bearer {token_data['token']}",
    'appkey': config['my_app'],
    'appsecret': config['my_sec'],
    'tr_id': 'HHDFS00000300'
}

# 가능한 거래소 코드
exchanges = ['NAS', 'NYS', 'AMS', 'HKS', 'TSE', 'SHS', 'SZS', 'HSX', 'HNX']
symbols = ['MAGS', 'JEPI']

for symbol in symbols:
    print(f"\n{'='*50}")
    print(f"Testing {symbol} across exchanges...")
    
    for excd in exchanges:
        res = requests.get(
            'https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price',
            headers=headers,
            params={'AUTH': '', 'EXCD': excd, 'SYMB': symbol}
        )
        
        if res.status_code == 200:
            data = res.json()
            if data.get('rt_cd') == '0':
                last = data.get('output', {}).get('last', '')
                if last:
                    print(f"✅ {excd}: ${float(last):.2f}")
