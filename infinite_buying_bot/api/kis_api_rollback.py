import logging
import pandas as pd
from typing import Optional, Tuple
from . import kis_auth as ka

logger = logging.getLogger(__name__)

def price(
        auth: str,  # ?ъ슜?먭텒?쒖젙蹂?        excd: str,  # 嫄곕옒?뚯퐫??        symb: str,  # 醫낅ぉ肄붾뱶
        env_dv: str = "real",  # ?ㅼ쟾紐⑥쓽援щ텇
        tr_cont: str = "",
        dataframe: Optional[pd.DataFrame] = None,
        depth: int = 0,
        max_depth: int = 10
) -> Optional[pd.DataFrame]:
    """
    [?댁쇅二쇱떇] 湲곕낯?쒖꽭 > ?댁쇅二쇱떇 ?꾩옱泥닿껐媛[v1_?댁쇅二쇱떇-009]
    """
    if not excd: raise ValueError("excd is required")
    if not symb: raise ValueError("symb is required")

    if depth >= max_depth:
        logger.warning("Max recursion depth reached")
        return dataframe if dataframe is not None else pd.DataFrame()

    if env_dv == "real" or env_dv == "demo":
        tr_id = "HHDFS00000300"
    else:
        raise ValueError("env_dv must be 'real' or 'demo'")

    api_url = "/uapi/overseas-price/v1/quotations/price"
    params = {"AUTH": auth, "EXCD": excd, "SYMB": symb}

    res = ka._url_fetch(api_url, tr_id, tr_cont, params)

    if res.isOK():
        if hasattr(res.getBody(), 'output'):
            output_data = res.getBody().output
            if not isinstance(output_data, list):
                output_data = [output_data]
            current_data = pd.DataFrame(output_data)
        else:
            current_data = pd.DataFrame()

        if dataframe is not None:
            dataframe = pd.concat([dataframe, current_data], ignore_index=True)
        else:
            dataframe = current_data

        return dataframe
    else:
        logger.error(f"API call failed: {res.getErrorCode()} - {res.getErrorMessage()}")
        return pd.DataFrame()

def order(
        order_dv: str,  # 二쇰Ц援щ텇 buy(留ㅼ닔) / sell(留ㅻ룄)
        cano: str,  # 醫낇빀怨꾩쥖踰덊샇
        acnt_prdt_cd: str,  # 怨꾩쥖?곹뭹肄붾뱶
        ovrs_excg_cd: str,  # ?댁쇅嫄곕옒?뚯퐫??        pdno: str,  # ?곹뭹踰덊샇
        ord_qty: str,  # 二쇰Ц?섎웾
        ovrs_ord_unpr: str,  # ?댁쇅二쇰Ц?④?
        ord_dvsn: str = "00",  # 二쇰Ц援щ텇 (00: 吏?뺢?/?쒖옣媛)
        ctac_tlno: str = "",
        mgco_aptm_odno: str = "",
        ord_svr_dvsn_cd: str = "0",
        env_dv: str = "real",
) -> Optional[pd.DataFrame]:
    """
    [?댁쇅二쇱떇] 二쇰Ц/怨꾩쥖 > ?댁쇅二쇱떇 誘멸뎅二쇨컙二쇰Ц [v1_?댁쇅二쇱떇-026]
    """
    if env_dv == "real":
        if order_dv == "buy":
            tr_id = "TTTS6036U"
        elif order_dv == "sell":
            tr_id = "TTTS6037U"
        else:
            raise ValueError("Invalid order_dv")
    elif env_dv == "demo":
        if order_dv == "buy":
            tr_id = "VTTS1002U"  # Mock trading buy
        elif order_dv == "sell":
            tr_id = "VTTS1001U"  # Mock trading sell
        else:
            raise ValueError("Invalid order_dv")
    else:
        raise ValueError("env_dv must be 'real' or 'demo'")

    api_url = "/uapi/overseas-stock/v1/trading/daytime-order"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "PDNO": pdno,
        "ORD_QTY": ord_qty,
        "OVRS_ORD_UNPR": ovrs_ord_unpr,
        "CTAC_TLNO": ctac_tlno,
        "MGCO_APTM_ODNO": mgco_aptm_odno,
        "ORD_SVR_DVSN_CD": ord_svr_dvsn_cd,
        "ORD_DVSN": ord_dvsn,
    }

    res = ka._url_fetch(api_url=api_url, ptr_id=tr_id, tr_cont="", params=params, postFlag=True)

    if res.isOK():
        if hasattr(res.getBody(), 'output'):
            output_data = res.getBody().output
            if not isinstance(output_data, list):
                output_data = [output_data]
            return pd.DataFrame(output_data)
        return pd.DataFrame()
    else:
        logger.error(f"Order failed: {res.getErrorCode()} - {res.getErrorMessage()}")
        return pd.DataFrame()

def inquire_balance(
        cano: str,
        acnt_prdt_cd: str,
        ovrs_excg_cd: str,
        tr_crcy_cd: str,
        env_dv: str = "real",
        tr_cont: str = "",
        dataframe1: Optional[pd.DataFrame] = None,
        dataframe2: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    [?댁쇅二쇱떇] 二쇰Ц/怨꾩쥖 > ?댁쇅二쇱떇 ?붽퀬 [v1_?댁쇅二쇱떇-006]
    FIXED: Use correct TR_ID for mock trading
    """
    if env_dv == "real":
        tr_id = "TTTC8434R"  # Real trading
    elif env_dv == "demo":
        tr_id = "VTTC8434R"  # Mock trading (FIXED!)
    else:
        raise ValueError("env_dv must be 'real' or 'demo'")

    api_url = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
    
    # Mock trading and real trading use DIFFERENT parameter names
    if env_dv == "demo":
        # Mock trading uses shorter field names and requires additional fields
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "WCRC_FRCR_DVSN": "02",  # Foreign currency (no _CD suffix)
            "NATN_CD": "840" if ovrs_excg_cd in ["NASD", "NYSE", "AMEX"] else "000",
            "TR_MKET_CD": "00",
            "INQR_DVSN": "00",  # No _CD suffix
            "AFHR_FLPR_YN": "N",  # After-hours price Y/N
            "OFL_YN": "N",  # Offline Y/N
            "UNPR_DVSN": "01",  # Unit price division
            "FUND_STTL_ICLD_YN": "N",  # Fund settlement include Y/N
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # Financing amount auto redemption Y/N
            "PRCS_DVSN": "01",  # Process division
            "CTX_AREA_FK100": "",  # Pagination key
            "CTX_AREA_NK100": "",  # Pagination key
        }
    else:
        # Real trading uses longer field names
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "WCRC_FRCR_DVSN_CD": "02",
            "NATN_CD": "840" if ovrs_excg_cd in ["NASD", "NYSE", "AMEX"] else "000",
            "TR_MKET_CD": "00",
            "INQR_DVSN_CD": "00",
        }

    # DEBUG: Log exact request details
    logger.info(f"DEBUG: Balance Request - URL: {api_url}, TR_ID: {tr_id}")
    logger.info(f"DEBUG: Balance Request - CANO: '{cano}', PRDT: '{acnt_prdt_cd}'")
    logger.info(f"DEBUG: Balance Request - Params: {params}")

    res = ka._url_fetch(api_url=api_url, ptr_id=tr_id, tr_cont=tr_cont, params=params)

    if res.isOK():
        # IMPORTANT: Mock trading API returns data in OPPOSITE order from real trading
        # Mock: output1 = Holdings, output2 = Account Info
        # Real: output1 = Account Info, output2 = Holdings
        
        if env_dv == "demo":
            # For mock trading: swap output1 and output2
            # Output 1 (Holdings in mock trading)
            if hasattr(res.getBody(), 'output1'):
                d2 = res.getBody().output1
                if d2:
                    current_data2 = pd.DataFrame(d2 if isinstance(d2, list) else [d2])
                    dataframe2 = pd.concat([dataframe2, current_data2], ignore_index=True) if dataframe2 is not None else current_data2
                else:
                    dataframe2 = dataframe2 if dataframe2 is not None else pd.DataFrame()
            
            # Output 2 (Account Info in mock trading)
            if hasattr(res.getBody(), 'output2'):
                d1 = res.getBody().output2
                if d1:
                    current_data1 = pd.DataFrame([d1] if not isinstance(d1, list) else d1)
                    dataframe1 = pd.concat([dataframe1, current_data1], ignore_index=True) if dataframe1 is not None else current_data1
                else:
                    dataframe1 = dataframe1 if dataframe1 is not None else pd.DataFrame()
        else:
            # For real trading: normal order
            # Output 1 (Account Info)
            if hasattr(res.getBody(), 'output1'):
                d1 = res.getBody().output1
                if d1:
                    current_data1 = pd.DataFrame([d1] if not isinstance(d1, list) else d1)
                    dataframe1 = pd.concat([dataframe1, current_data1], ignore_index=True) if dataframe1 is not None else current_data1
                else:
                    dataframe1 = dataframe1 if dataframe1 is not None else pd.DataFrame()
            
            # Output 2 (Holdings)
            if hasattr(res.getBody(), 'output2'):
                d2 = res.getBody().output2
                if d2:
                    current_data2 = pd.DataFrame(d2 if isinstance(d2, list) else [d2])
                    dataframe2 = pd.concat([dataframe2, current_data2], ignore_index=True) if dataframe2 is not None else current_data2
                else:
                    dataframe2 = dataframe2 if dataframe2 is not None else pd.DataFrame()
                
        return dataframe1, dataframe2
    else:
        logger.error(f"Balance check failed: {res.getErrorCode()} - {res.getErrorMessage()}")
        return pd.DataFrame(), pd.DataFrame()
