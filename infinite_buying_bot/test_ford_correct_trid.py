"""
🚨 실전투자 Ford 1주 매수 - 올바른 TR ID 사용 🚨
- TR ID: TTTT1002U (미국 매수)
- 거래소: NYSE
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import yfinance as yf
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

print("="*60)
print("  🚨 실전투자 Ford 1주 매수 (올바른 TR ID)")
print("="*60)

# 인증
ka.auth(svr="prod", product="01")
trenv = ka.getTREnv()
print(f"✅ 계좌: {trenv.my_acct}")

# Ford 현재가
ticker = yf.Ticker("F")
price = ticker.fast_info.last_price
order_price = str(round(price * 1.02, 2))
print(f"📊 Ford 현재가: ${price:.2f}, 주문가: ${order_price}")

time.sleep(1)

# 올바른 TR ID 사용!
tr_id = "TTTT1002U"  # 미국 매수 주문 (실전)
api_url = "/uapi/overseas-stock/v1/trading/order"

params = {
    "CANO": trenv.my_acct,
    "ACNT_PRDT_CD": trenv.my_prod,
    "OVRS_EXCG_CD": "NYSE",  # Ford는 NYSE
    "PDNO": "F",
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": order_price,
    "CTAC_TLNO": "",
    "MGCO_APTM_ODNO": "",
    "SLL_TYPE": "",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00",  # 지정가
}

headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": tr_id,
    "custtype": "P",
    "tr_cont": "",
}

print(f"\n📋 주문 정보:")
print(f"   - 종목: Ford (F)")
print(f"   - 거래소: NYSE")
print(f"   - TR_ID: {tr_id} (미국 매수)")
print(f"   - 가격: ${order_price}")

print(f"\n🚀 주문 전송...")
r = requests.post(f"{trenv.my_url}{api_url}", headers=headers, data=json.dumps(params))
res = r.json()

print(f"\n📋 응답:")
print(json.dumps(res, indent=2, ensure_ascii=False))

rt_cd = res.get('rt_cd', '')
msg1 = res.get('msg1', '')
msg_cd = res.get('msg_cd', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 주문 성공! {msg1}")
    if 'output' in res:
        print(f"   주문번호: {res['output'].get('ODNO', 'N/A')}")
else:
    print(f"❌ 주문 실패: {msg_cd} - {msg1}")
print(f"{'='*60}\n")
