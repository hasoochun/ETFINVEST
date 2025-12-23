import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    @staticmethod
    def load():
        # Find kis_devlp.yaml in PROJECT ROOT
        # Current: real_trading_bot/config/config_loader.py
        # Root: real_trading_bot/../.. -> open-trading-api
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, 'kis_devlp.yaml')
        
        print(f"Loading Config from: {config_path}")
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config not found at {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
            
        # Validation
        required = ['my_app', 'my_sec', 'my_acct_stock', 'telegram_token', 'telegram_chat_id']
        for k in required:
            if not cfg.get(k):
                raise ValueError(f"Missing config key: {k}")
                
        return cfg
