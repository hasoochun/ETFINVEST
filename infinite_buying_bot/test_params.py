import os
import sys
import logging
import time
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Add path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infinite_buying_bot.api import kis_auth as ka
from infinite_buying_bot.api import kis_api as api

def test_params():
    print("=== KIS API Parameter Test ===")
    
    # Auth
    ka.auth(svr='vps', product='01')
    trenv = ka.getTREnv()
    
    base_params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "WCRC_FRCR_DVSN": "02",
        "NATN_CD": "840",
        "TR_MKET_CD": "00",
        "INQR_DVSN": "00",
    }
    
    # Test cases
    test_cases = [
        {"AFHR_FLPR_YN": "N", "OFL_YN": "N", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "01", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""},
    ]
    
    api_url = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
    tr_id = "VTTC8434R"
    
    for i, extra_params in enumerate(test_cases):
        print(f"\nTest Case {i+1}: Extra Params = {extra_params}")
        
        params = base_params.copy()
        params.update(extra_params)
        
        try:
            res = ka._url_fetch(api_url=api_url, ptr_id=tr_id, tr_cont="", params=params)
            
            if res.isOK():
                print(">>> SUCCESS!")
                # Print all fields in body
                body = res.getBody()
                for field in body._fields:
                    print(f"{field}: {getattr(body, field)}")
                break
            else:
                print(f">>> FAILED: {res.getErrorCode()} - {res.getErrorMessage()}")
        except Exception as e:
            print(f">>> EXCEPTION: {e}")
            
        time.sleep(1) # Avoid rate limit

if __name__ == "__main__":
    test_params()
