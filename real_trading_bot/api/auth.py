import requests
import json
import os
import yaml
from datetime import datetime, timedelta

# Production Only Data
URL_BASE = "https://openapi.koreainvestment.com:9443"

class KisAuth:
    def __init__(self, config):
        self.app_key = config['my_app']
        self.app_secret = config['my_sec']
        self.acc_no = config['my_acct_stock']
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.token_path = os.path.join(self.base_dir, 'config', 'token_real.yaml')
        self.access_token = None
        
    def auth(self):
        self.access_token = self._get_token()
        return {
            'token': f"Bearer {self.access_token}",
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'cano': self.acc_no,
            'acnt_prdt_cd': '01',
            'url': URL_BASE
        }
        
    def _get_token(self):
        # Try load
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'r', encoding='utf-8') as f:
                    data = yaml.load(f, Loader=yaml.FullLoader)
                if datetime.strptime(data['exp'], "%Y-%m-%d %H:%M:%S") > datetime.now():
                    return data['token']
            except:
                pass
                
        print("Issuing New Real Token...")
        # Issue
        res = requests.post(f"{URL_BASE}/oauth2/tokenP", json={
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        })
        res.raise_for_status()
        data = res.json()
        token = data['access_token']
        
        # Save
        exp = datetime.now() + timedelta(hours=23)
        with open(self.token_path, 'w', encoding='utf-8') as f:
            yaml.dump({'token': token, 'exp': exp.strftime("%Y-%m-%d %H:%M:%S")}, f)
            
        return token
