# -*- coding: utf-8 -*-
# ====|  (REST) 접근 토큰 / (Websocket) 웹소켓 접속키 발급 에 필요한 API 호출 샘플 아래 참고하시기 바랍니다.  |=====================
# ====|  API 호출 공통 함수 포함                                  |=====================

import asyncio
import copy
import json
import logging
import os
import time
from base64 import b64decode
from collections import namedtuple
from collections.abc import Callable
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
import websockets
import yaml
from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

clearConsole = lambda: os.system("cls" if os.name in ("nt", "dos") else "clear")

key_bytes = 32
# Modified config_root to point to ../config relative to this file
# Also check project root if not found in config dir
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
token_tmp = os.path.join(config_dir, f"KIS{datetime.today().strftime('%Y%m%d')}")

# Load .env file
load_dotenv(os.path.join(project_root, ".env"))

# 접근토큰 관리하는 파일 존재여부 체크, 없으면 생성
if os.path.exists(config_dir) == False:
    try:
        os.makedirs(config_dir, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create config dir at {config_dir}: {e}")

if os.path.exists(token_tmp) == False:
    try:
        f = open(token_tmp, "w+")
        f.close()
    except Exception as e:
        logging.error(f"Failed to create token file at {token_tmp}: {e}")

# 앱키, 앱시크리트, 토큰, 계좌번호 등 저장관리
_cfg = {}
try:
    # Try loading from config dir first
    config_path = os.path.join(config_dir, "kis_devlp.yaml")
    if not os.path.exists(config_path):
        # Fallback to project root
        config_path = os.path.join(project_root, "kis_devlp.yaml")
    
    with open(config_path, encoding="UTF-8") as f:
        _cfg = yaml.load(f, Loader=yaml.FullLoader)
except Exception as e:
    logging.error(f"Failed to load config from {config_path}: {e}")

# Override with Environment Variables if present
if os.getenv("KIS_APP_KEY_PROD"): _cfg["my_app"] = os.getenv("KIS_APP_KEY_PROD").strip()
if os.getenv("KIS_APP_SECRET_PROD"): _cfg["my_sec"] = os.getenv("KIS_APP_SECRET_PROD").strip()
if os.getenv("KIS_ACCT_PROD"): _cfg["my_acct_stock"] = os.getenv("KIS_ACCT_PROD").strip()

if os.getenv("KIS_APP_KEY_PAPER"): _cfg["paper_app"] = os.getenv("KIS_APP_KEY_PAPER").strip()
if os.getenv("KIS_APP_SECRET_PAPER"): _cfg["paper_sec"] = os.getenv("KIS_APP_SECRET_PAPER").strip()
if os.getenv("KIS_ACCT_PAPER"): _cfg["my_paper_stock"] = os.getenv("KIS_ACCT_PAPER").strip()

_TRENV = tuple()
_last_auth_time = datetime.now()
_autoReAuth = False
_DEBUG = False
_isPaper = False
_smartSleep = 0.1

# 기본 헤더값 정의
_base_headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    "User-Agent": _cfg.get("my_agent", ""),
}


# 토큰 발급 받아 저장 (토큰값, 토큰 유효시간,1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송)
def save_token(my_token, my_expired):
    valid_date = datetime.strptime(my_expired, "%Y-%m-%d %H:%M:%S")
    with open(token_tmp, "w", encoding="utf-8") as f:
        f.write(f"token: {my_token}\n")
        f.write(f"valid-date: {valid_date}\n")


# 토큰 확인 (토큰값, 토큰 유효시간_1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송)
def read_token():
    try:
        with open(token_tmp, encoding="UTF-8") as f:
            tkg_tmp = yaml.load(f, Loader=yaml.FullLoader)

        exp_dt = datetime.strftime(tkg_tmp["valid-date"], "%Y-%m-%d %H:%M:%S")
        now_dt = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        if exp_dt > now_dt:
            return tkg_tmp["token"]
        else:
            return None
    except Exception:
        return None


# 토큰 유효시간 체크해서 만료된 토큰이면 재발급처리
def _getBaseHeader():
    if _autoReAuth:
        reAuth()
    return copy.deepcopy(_base_headers)


# 가져오기 : 앱키, 앱시크리트, 종합계좌번호(계좌번호 중 숫자8자리), 계좌상품코드(계좌번호 중 숫자2자리), 토큰, 도메인
def _setTRENV(cfg):
    nt1 = namedtuple(
        "KISEnv",
        ["my_app", "my_sec", "my_acct", "my_prod", "my_htsid", "my_token", "my_url", "my_url_ws"],
    )
    d = {
        "my_app": cfg["my_app"],  # 앱키
        "my_sec": cfg["my_sec"],  # 앱시크리트
        "my_acct": cfg["my_acct"],  # 종합계좌번호(8자리)
        "my_prod": cfg["my_prod"],  # 계좌상품코드(2자리)
        "my_htsid": cfg["my_htsid"],  # HTS ID
        "my_token": cfg["my_token"],  # 토큰
        "my_url": cfg["my_url"],  # 실전 도메인
        "my_url_ws": cfg["my_url_ws"], # 모의 도메인
    }

    global _TRENV
    _TRENV = nt1(**d)


def isPaperTrading():  # 모의투자 매매
    return _isPaper


# 실전투자면 'prod', 모의투자면 'vps'를 셋팅 하시기 바랍니다.
def changeTREnv(token_key, svr="prod", product=_cfg.get("my_prod", "01")):
    cfg = dict()

    global _isPaper
    if svr == "prod":  # 실전투자
        ak1 = "my_app"  # 실전투자용 앱키
        ak2 = "my_sec"  # 실전투자용 앱시크리트
        _isPaper = False
        _smartSleep = 0.05
    elif svr == "vps":  # 모의투자
        ak1 = "paper_app"  # 모의투자용 앱키
        ak2 = "paper_sec"  # 모의투자용 앱시크리트
        _isPaper = True
        _smartSleep = 0.5

    cfg["my_app"] = _cfg[ak1]
    cfg["my_sec"] = _cfg[ak2]

    if svr == "prod" and product == "01":  # 실전투자 주식투자, 위탁계좌, 투자계좌
        cfg["my_acct"] = _cfg["my_acct_stock"]
    elif svr == "prod" and product == "03":  # 실전투자 선물옵션(파생)
        cfg["my_acct"] = _cfg["my_acct_future"]
    elif svr == "prod" and product == "08":  # 실전투자 해외선물옵션(파생)
        cfg["my_acct"] = _cfg["my_acct_future"]
    elif svr == "prod" and product == "22":  # 실전투자 개인연금저축계좌
        cfg["my_acct"] = _cfg["my_acct_stock"]
    elif svr == "prod" and product == "29":  # 실전투자 퇴직연금계좌
        cfg["my_acct"] = _cfg["my_acct_stock"]
    elif svr == "vps" and product == "01":  # 모의투자 주식투자, 위탁계좌, 투자계좌
        cfg["my_acct"] = _cfg["my_paper_stock"]
    elif svr == "vps" and product == "03":  # 모의투자 선물옵션(파생)
        cfg["my_acct"] = _cfg["my_paper_future"]

    cfg["my_prod"] = product
    cfg["my_htsid"] = _cfg["my_htsid"]
    cfg["my_url"] = _cfg[svr]

    try:
        my_token = _TRENV.my_token
    except AttributeError:
        my_token = ""
    cfg["my_token"] = my_token if token_key else token_key
    cfg["my_url_ws"] = _cfg["ops" if svr == "prod" else "vops"]

    _setTRENV(cfg)


def _getResultObject(json_data):
    _tc_ = namedtuple("res", json_data.keys())
    return _tc_(**json_data)


# Token 발급
def auth(svr="prod", product=_cfg.get("my_prod", "01"), url=None):
    p = {
        "grant_type": "client_credentials",
    }
    if svr == "prod":  # 실전투자
        ak1 = "my_app"
        ak2 = "my_sec"
    elif svr == "vps":  # 모의투자
        ak1 = "paper_app"
        ak2 = "paper_sec"

    p["appkey"] = _cfg[ak1]
    p["appsecret"] = _cfg[ak2]

    saved_token = read_token()
    if saved_token is None:
        url = f"{_cfg[svr]}/oauth2/tokenP"
        res = requests.post(
            url, data=json.dumps(p), headers=_getBaseHeader()
        )
        rescode = res.status_code
        if rescode == 200:
            my_token = _getResultObject(res.json()).access_token
            my_expired = _getResultObject(
                res.json()
            ).access_token_token_expired
            save_token(my_token, my_expired)
        else:
            print("Get Authentification token fail!\nYou have to restart your app!!!")
            return
    else:
        my_token = saved_token

    changeTREnv(my_token, svr, product)

    _base_headers["authorization"] = f"Bearer {my_token}"
    _base_headers["appkey"] = _TRENV.my_app
    _base_headers["appsecret"] = _TRENV.my_sec

    global _last_auth_time
    _last_auth_time = datetime.now()

    if _DEBUG:
        print(f"[{_last_auth_time}] => get AUTH Key completed!")


def reAuth(svr="prod", product=_cfg.get("my_prod", "01")):
    n2 = datetime.now()
    if (n2 - _last_auth_time).seconds >= 86400:
        auth(svr, product)


def getEnv():
    return _cfg


def smart_sleep():
    if _DEBUG:
        print(f"[RateLimit] Sleeping {_smartSleep}s ")
    time.sleep(_smartSleep)


def getTREnv():
    return _TRENV


class APIResp:
    def __init__(self, resp):
        self._rescode = resp.status_code
        self._resp = resp
        self._header = self._setHeader()
        self._body = self._setBody()
        self._err_code = self._body.msg_cd
        self._err_message = self._body.msg1

    def getResCode(self):
        return self._rescode

    def _setHeader(self):
        fld = dict()
        for x in self._resp.headers.keys():
            if x.islower():
                fld[x] = self._resp.headers.get(x)
        _th_ = namedtuple("header", fld.keys())
        return _th_(**fld)

    def _setBody(self):
        _tb_ = namedtuple("body", self._resp.json().keys())
        return _tb_(**self._resp.json())

    def getHeader(self):
        return self._header

    def getBody(self):
        return self._body

    def getResponse(self):
        return self._resp

    def isOK(self):
        try:
            if self.getBody().rt_cd == "0":
                return True
            else:
                return False
        except:
            return False

    def getErrorCode(self):
        return self._err_code

    def getErrorMessage(self):
        return self._err_message

    def printAll(self):
        print("<Header>")
        for x in self.getHeader()._fields:
            print(f"\t-{x}: {getattr(self.getHeader(), x)}")
        print("<Body>")
        for x in self.getBody()._fields:
            print(f"\t-{x}: {getattr(self.getBody(), x)}")

    def printError(self, url):
        print(
            "-------------------------------\nError in response: ",
            self.getResCode(),
            " url=",
            url,
        )
        print(
            "rt_cd : ",
            self.getBody().rt_cd,
            "/ msg_cd : ",
            self.getErrorCode(),
            "/ msg1 : ",
            self.getErrorMessage(),
        )
        print("-------------------------------")


class APIRespError(APIResp):
    def __init__(self, status_code, error_text):
        self.status_code = status_code
        self.error_text = error_text
        self._error_code = str(status_code)
        self._error_message = error_text

    def isOK(self):
        return False

    def getErrorCode(self):
        return self._error_code

    def getErrorMessage(self):
        return self._error_message

    def getBody(self):
        class EmptyBody:
            def __getattr__(self, name):
                return None
        return EmptyBody()

    def getHeader(self):
        class EmptyHeader:
            tr_cont = ""
            def __getattr__(self, name):
                return ""
        return EmptyHeader()

    def printAll(self):
        print(f"=== ERROR RESPONSE ===")
        print(f"Status Code: {self.status_code}")
        print(f"Error Message: {self.error_text}")
        print(f"======================")

    def printError(self, url=""):
        print(f"Error Code : {self.status_code} | {self.error_text}")
        if url:
            print(f"URL: {url}")


def _url_fetch(
        api_url, ptr_id, tr_cont, params, appendHeaders=None, postFlag=False, hashFlag=True
):
    url = f"{getTREnv().my_url}{api_url}"

    headers = _getBaseHeader()

    tr_id = ptr_id
    if ptr_id[0] in ("T", "J", "C"):
        if isPaperTrading():
            tr_id = "V" + ptr_id[1:]

    headers["tr_id"] = tr_id
    headers["custtype"] = "P"
    headers["tr_cont"] = tr_cont

    if appendHeaders is not None:
        if len(appendHeaders) > 0:
            for x in appendHeaders.keys():
                headers[x] = appendHeaders.get(x)

    if _DEBUG:
        print("< Sending Info >")
        print(f"URL: {url}, TR: {tr_id}")
        print(f"<header>\n{headers}")
        print(f"<body>\n{params}")

    if postFlag:
        res = requests.post(url, headers=headers, data=json.dumps(params))
    else:
        res = requests.get(url, headers=headers, params=params)

    if res.status_code == 200:
        ar = APIResp(res)
        if _DEBUG:
            ar.printAll()
        return ar
    else:
        print("Error Code : " + str(res.status_code) + " | " + res.text)
        return APIRespError(res.status_code, res.text)
