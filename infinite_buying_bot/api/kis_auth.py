# -*- coding: utf-8 -*-
"""
KIS API Authentication Module (Production Only / Clean Version)
"""
import logging
import os
import yaml
import requests
import json
from datetime import datetime, timedelta
from collections import namedtuple

logger = logging.getLogger(__name__)

# --- CONFIG & CONSTANTS ---
# Use a unique token file name to avoid conflict with legacy files
TOKEN_FILE_NAME = "token_prod_v2.yaml" 
# Fix Path: api/kis_auth.py -> api -> infinite_buying_bot -> open-trading-api (ROOT)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN_PATH = os.path.join(ROOT_DIR, 'infinite_buying_bot', 'config', TOKEN_FILE_NAME)

# Global Auth Object
TREnv = namedtuple('TREnv', ['my_app', 'my_sec', 'my_acct', 'my_prod', 'my_token', 'my_url'])
_trenv = None

def getTREnv():
    """Get TREnv with automatic token refresh if expired.
    
    [FIX 2026-01-10] 기존: 메모리의 오래된 토큰 그대로 반환
    수정: 토큰 만료 시 자동으로 재인증하여 새 토큰 반환
    """
    global _trenv
    
    if _trenv is None:
        return None
    
    # Check if token file exists and verify expiry
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'r', encoding='utf-8') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
            
            exp = datetime.strptime(data['expired_at'], "%Y-%m-%d %H:%M:%S")
            
            # If token expired or will expire in 30 minutes, re-auth
            if exp <= datetime.now() + timedelta(minutes=30):
                logger.warning(f"[Auth] Token expired or expiring soon (exp: {exp}), re-authenticating...")
                auth()  # Re-authenticate with fresh token
                
        except Exception as e:
            logger.error(f"[Auth] Token expiry check failed: {e}")
    
    return _trenv


def auth(svr='prod', product='01'):
    """Authenticate to KIS (PROD ONLY)"""
    global _trenv
    
    # 1. Load Config
    # Priority: Project Root based on this file location
    # this file: infinite_buying_bot/api/kis_auth.py
    # root: open-trading-api/
    
    config_path = os.path.join(ROOT_DIR, 'kis_devlp.yaml')
    logger.info(f"?뵎[Auth] Looking for config at: {config_path}")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
        
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        
    app_key = cfg.get('my_app')
    app_secret = cfg.get('my_sec')
    acc_no = cfg.get('my_acct_stock')
    
    if not app_key or not app_secret:
        raise ValueError("API Keys (my_app, my_sec) are missing in kis_devlp.yaml")

    base_url = "https://openapi.koreainvestment.com:9443" # Hardcoded PROD URL

    # 2. Get Token
    token = _get_valid_token(app_key, app_secret, base_url)
    
    # 3. Build TRENV
    _trenv = TREnv(
        my_app=app_key,
        my_sec=app_secret,
        my_acct=acc_no,
        my_prod=product,
        my_token=f"Bearer {token}",
        my_url=base_url
    )
    
    logger.info(f"??Authentication Success (Account: {acc_no})")
    return _trenv

def _get_valid_token(app_key, app_secret, base_url):
    """Read cached token or issue new one"""
    # Ensure config dir exists
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    
    # Try reading
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'r', encoding='utf-8') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                
            exp = datetime.strptime(data['expired_at'], "%Y-%m-%d %H:%M:%S")
            if exp > datetime.now():
                logger.info("Using cached token")
                return data['token']
        except Exception:
            logger.warning("Token file invalid, issuing new one")

    # Issue new
    logger.info("Issuing NEW token...")
    return _issue_token(app_key, app_secret, base_url)

def _issue_token(app_key, app_secret, base_url):
    url = f"{base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()
    
    access_token = data['access_token']
    
    # Save (valid for ~24h, save for 23h)
    expired_at = datetime.now() + timedelta(hours=23)
    
    with open(TOKEN_PATH, 'w', encoding='utf-8') as f:
        yaml.dump({
            'token': access_token,
            'expired_at': expired_at.strftime("%Y-%m-%d %H:%M:%S")
        }, f)
        
    return access_token

