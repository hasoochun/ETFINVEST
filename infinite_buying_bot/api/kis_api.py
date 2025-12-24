# -*- coding: utf-8 -*-
"""
KIS API Wrapper (Production Only / Clean Version)
"""
import requests
import json
import logging
import pandas as pd
import time

logger = logging.getLogger(__name__)

# Common Headers
def _get_headers(trenv, tr_id):
    return {
        "content-type": "application/json",
        "authorization": trenv.my_token,
        "appkey": trenv.my_app,
        "appsecret": trenv.my_sec,
        "tr_id": tr_id
    }

def get_current_price(trenv, exchange, symbol, env_dv='prod'):
    """Get Price - Returns float"""
    # KIS API: 주식현재가 시세 (HHDFS76200200)
    path = "/uapi/overseas-price/v1/quotations/price"
    url = f"{trenv.my_url}{path}"
    
    headers = _get_headers(trenv, "HHDFS76200200")
    params = {
        "AUTH": "",
        "EXCD": exchange,
        "SYMB": symbol
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        
        if data['rt_cd'] != '0':
            logger.error(f"Price API Failed: {data['msg1']}")
            return 0.0
            
        price_str = data['output'].get('last', '')
        if not price_str:
            logger.warning(f"Price API returned empty value for {symbol}")
            return 0.0
        return float(price_str)
    except Exception as e:
        logger.error(f"Price API Exception: {e}")
        return 0.0

# Alias for compatibility
def price(auth, excd, symb, env_dv='prod'):
    # This function returns a DataFrame to match legacy code expectation in Trader.py partial rewrites
    # But since we are rewriting Trader.py too, we can simplify.
    # We will keep it returning DF for safety if other modules use it.
    from infinite_buying_bot.api import kis_auth
    trenv = kis_auth.getTREnv()
    if not trenv: return pd.DataFrame()
    
    p = get_current_price(trenv, excd, symb)
    if p > 0:
        return pd.DataFrame([{'last': p}])
    return pd.DataFrame()

def inquire_psamount(cano, acnt_prdt_cd, ovrs_excg_cd, ovrs_ord_unpr, item_cd, env_dv='prod'):
    """Check Buying Power"""
    from infinite_buying_bot.api import kis_auth
    trenv = kis_auth.getTREnv()

    path = "/uapi/overseas-stock/v1/trading/inquire-psamount"
    url = f"{trenv.my_url}{path}"
    
    # TR ID for Buying Power: TTTS3007R (Prod)
    headers = _get_headers(trenv, "TTTS3007R")
    
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "OVRS_ORD_UNPR": ovrs_ord_unpr,
        "ITEM_CD": item_cd
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        if data['rt_cd'] != '0':
            logger.error(f"BuyingPower API Failed: {data.get('msg1')}")
            return None
        return pd.DataFrame([data['output']])
    except Exception as e:
        logger.error(f"BuyingPower API Exception: {e}")
        return None

def inquire_balance(cano, acnt_prdt_cd, ovrs_excg_cd, tr_crcy_cd, env_dv='prod'):
    """Check Holdings"""
    from infinite_buying_bot.api import kis_auth
    trenv = kis_auth.getTREnv()

    path = "/uapi/overseas-stock/v1/trading/inquire-balance"
    url = f"{trenv.my_url}{path}"
    
    # TR ID for Balance: TTTT3012R (REAL), TTTS3012R (Mock)
    headers = _get_headers(trenv, "TTTT3012R")
    
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "TR_CRCY_CD": tr_crcy_cd,
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        if data['rt_cd'] != '0':
            logger.error(f"Balance API Failed: {data.get('msg1')}")
            return pd.DataFrame(), pd.DataFrame()
            
        return pd.DataFrame(data['output1']), pd.DataFrame([data['output2']])
    except Exception as e:
        logger.error(f"Balance API Exception: {e}")
        return pd.DataFrame(), pd.DataFrame()

def order(order_dv, cano, acnt_prdt_cd, ovrs_excg_cd, pdno, ord_qty, ovrs_ord_unpr, ord_dvsn, env_dv='prod'):
    """Execute Order"""
    from infinite_buying_bot.api import kis_auth
    trenv = kis_auth.getTREnv()

    path = "/uapi/overseas-stock/v1/trading/order"
    url = f"{trenv.my_url}{path}"
    
    # IMPORTANT: TTTT for REAL trading, TTTS for MOCK trading
    # Real Trading: TTTT1002U (Buy), TTTT1006U (Sell)
    # Mock Trading: TTTS1002U (Buy), TTTS1006U (Sell)
    if order_dv == "buy":
        tr_id = "TTTT1002U"  # REAL trading buy
    else:
        tr_id = "TTTT1006U"  # REAL trading sell
        
    headers = _get_headers(trenv, tr_id)
    
    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "PDNO": pdno,
        "ORD_QTY": str(ord_qty),
        "OVRS_ORD_UNPR": str(ovrs_ord_unpr),
        "ORD_DVSN": ord_dvsn,
        "ORD_SVR_DVSN_CD": "0"  # Required for real trading
    }
    
    try:
        logger.info(f"Sending Order: {json.dumps(body)}")
        res = requests.post(url, headers=headers, json=body)
        res.raise_for_status()
        data = res.json()
        
        # Log full response for debugging
        logger.info(f"Order Response: rt_cd={data.get('rt_cd')}, msg_cd={data.get('msg_cd')}, msg1={data.get('msg1')}")
        
        if data['rt_cd'] != '0':
            logger.error(f"Order API Failed: {data.get('msg1')} (Code: {data.get('msg_cd')})")
            return None
            
        return pd.DataFrame([data['output']])
    except Exception as e:
        logger.error(f"Order API Exception: {e}")
        return None
