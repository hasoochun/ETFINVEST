"""
Ford(F) 1주 실전 매수 테스트 - NYSE 거래소
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import yfinance as yf
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

print("="*60)
# 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 계좌: {trenv.my_acct}")

# Ford 현재가
ticker = yf.Ticker("F")
price = ticker.fast_info.last_price
order_price = round(price * 1.02, 2)
print(f"📊 Ford 현재가: ${price:.2f}, 주문가: ${order_price}")

time.sleep(1)

# 여러 거래소 코드 시도
for exchange in ["NYSE", "NYSD", "NAS", "NASD", "AMEX"]:
    print(f"\n테스트: exchange={exchange}")
    
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "OVRS_EXCG_CD": exchange,
        "PDNO": "F",
        "ORD_QTY": "1",
        "OVRS_ORD_UNPR": str(order_price),
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": "00",
    }
    
    headers = {
        "Content-Type": "application/json",
        "authorization": ka._base_headers.get('authorization', ''),
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "tr_id": "TTTS0308U",
        "custtype": "P",
    }
    
    r = requests.post(f"{trenv.my_url}/uapi/overseas-stock/v1/trading/order", 
                      headers=headers, data=json.dumps(params))
    res = r.json()
    
    rt_cd = res.get('rt_cd', '')
    msg_cd = res.get('msg_cd', '')
    msg1 = res.get('msg1', '')[:50] if res.get('msg1') else ''
    
    if rt_cd == "0":
        print(f"  ✅ 성공! {msg1}")
        break
    else:
        print(f"  ❌ {msg_cd}: {msg1}")
    
    time.sleep(0.5)
