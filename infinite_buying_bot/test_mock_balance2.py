"""
모의투자 잔고 조회 - 전체 응답 출력
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from infinite_buying_bot.api import kis_auth as ka

# 모의투자 인증
ka.auth(svr="vps", product="01")
trenv = ka.getTREnv()
print(f"계좌: {trenv.my_acct}")

time.sleep(1)

# 여러 TR ID 시도
tr_ids = [
    ("VTTS3012R", "해외주식 잔고1"),
    ("VTTC8434R", "해외주식 잔고2"),  
    ("VTTS3007R", "해외주식 미체결"),
]

for tr_id, desc in tr_ids:
    print(f"\n=== {desc} ({tr_id}) ===")
    
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": "",
    }
    
    headers = {
        "Content-Type": "application/json",
        "authorization": ka._base_headers.get('authorization', ''),
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "tr_id": tr_id,
        "custtype": "P",
    }
    
    r = requests.get(f"{trenv.my_url}/uapi/overseas-stock/v1/trading/inquire-balance", 
                    headers=headers, params=params)
    res = r.json()
    
    rt_cd = res.get('rt_cd', '')
    msg1 = res.get('msg1', '')
    
    if rt_cd == "0":
        print(f"✅ 성공")
        # output2에서 잔고 정보 찾기
        if 'output2' in res:
            for item in res.get('output2', []):
                print(f"   {item}")
    else:
        print(f"❌ 실패: {msg1}")
    
    time.sleep(0.5)
