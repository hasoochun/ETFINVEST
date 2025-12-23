"""
모의투자 잔고 조회 테스트
- 어제 1억 잔고가 조회되었는지 확인
- 해외주식 모의투자 지원 여부 재확인
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from infinite_buying_bot.api import kis_auth as ka

print("\n" + "="*70)
print("  📊 모의투자 잔고 조회 테스트")
print("="*70)

# 모의투자 인증
print("\n1️⃣ 모의투자 서버 인증...")
ka.auth(svr="vps", product="01")  # vps = 모의투자
trenv = ka.getTREnv()
print(f"✅ 계좌: {trenv.my_acct}")
print(f"   URL: {trenv.my_url}")

time.sleep(1)

# 해외주식 잔고 조회 API
print("\n2️⃣ 해외주식 잔고 조회...")
tr_id = "VTTS3012R"  # 모의투자 해외주식 잔고
api_url = "/uapi/overseas-stock/v1/trading/inquire-balance"

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
    "Accept": "text/plain",
    "charset": "UTF-8",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": tr_id,
    "custtype": "P",
}

response = requests.get(f"{trenv.my_url}{api_url}", headers=headers, params=params)
res = response.json()

print(f"\n📋 응답 (Status: {response.status_code}):")
print(json.dumps(res, indent=2, ensure_ascii=False))

rt_cd = res.get('rt_cd', '')
msg1 = res.get('msg1', '')

print(f"\n{'='*60}")
if rt_cd == "0":
    print(f"✅ 잔고 조회 성공!")
    if 'output2' in res and res['output2']:
        output2 = res['output2'][0] if isinstance(res['output2'], list) else res['output2']
        print(f"   - 외화예수금: ${output2.get('frcr_pchs_amt1', 'N/A')}")
        print(f"   - 원화환산: ₩{output2.get('tot_evlu_pfls_amt', 'N/A')}")
else:
    print(f"❌ 조회 실패: {msg1}")
print(f"{'='*60}\n")
