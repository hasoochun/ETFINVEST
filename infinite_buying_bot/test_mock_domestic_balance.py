"""
모의투자 국내주식 잔고 조회 (원화)
- 어제 1억 잔고가 국내주식 잔고였는지 확인
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

# 국내 주식/예수금 잔고 조회
tr_id = "VTTC8434R"  # 모의투자 국내 잔고
api_url = "/uapi/domestic-stock/v1/trading/inquire-balance"

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
    "CTX_AREA_NK100": "",
}

headers = {
    "Content-Type": "application/json",
    "authorization": ka._base_headers.get('authorization', ''),
    "appkey": trenv.my_app,
    "appsecret": trenv.my_sec,
    "tr_id": tr_id,
    "custtype": "P",
}

print("\n📊 국내 주식/예수금 잔고 조회...")
r = requests.get(f"{trenv.my_url}{api_url}", headers=headers, params=params)
res = r.json()

rt_cd = res.get('rt_cd', '')
msg1 = res.get('msg1', '')

if rt_cd == "0":
    print(f"✅ 조회 성공!")
    if 'output2' in res:
        for item in res.get('output2', []):
            dnca = item.get('dnca_tot_amt', '0')  # 예수금
            tot_evlu = item.get('tot_evlu_amt', '0')  # 총평가
            print(f"   예수금: ₩{int(dnca):,}")
            print(f"   총평가: ₩{int(tot_evlu):,}")
else:
    print(f"❌ 실패: {msg1}")

print(f"\n전체 응답:")
print(json.dumps(res, indent=2, ensure_ascii=False))
