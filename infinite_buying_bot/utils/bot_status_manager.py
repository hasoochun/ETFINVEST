
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BotStatusManager:
    """
    Manages the real-time status of the trading bot.
    Writes status to a JSON file for the dashboard to read without polling KIS API.
    """
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.logs_dir = os.path.join(root_path, 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        self.status_file = os.path.join(self.logs_dir, 'bot_status.json')
        
        # Initial state
        self.state: Dict[str, Any] = {
            'system': {
                'status': 'initializing',  # initializing, running, paused, stopped, error
                'pid': os.getpid(),
                'start_time': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat(),
                'heartbeat_ago': 0
            },
            'config': {
                'mode': 'unknown',
                'strategy': 'unknown',
                'interval': 0
            },
            'schedule': {
                'last_run': None,
                'next_run': None,
                'time_remaining': None,
                'message': 'Initializing...'
            },
            'logic': {
                'current_action': 'Starting up',
                'market_status': 'Unknown',
                'description': 'System is booting up'
            },
            'last_updated': datetime.now().isoformat()
        }
        
    def update_heartbeat(self):
        """Update only the heartbeat timestamp"""
        self.state['system']['last_heartbeat'] = datetime.now().isoformat()
        self.state['system']['heartbeat_ago'] = 0
        self.state['last_updated'] = datetime.now().isoformat()
        self._save()

    def set_config_info(self, mode: str, strategy: str, interval: int):
        """Update static config info"""
        self.state['config']['mode'] = mode
        self.state['config']['strategy'] = strategy
        self.state['config']['interval'] = interval
        self._save()

    def set_schedule(self, next_run: datetime, message: str = ""):
        """Update schedule information"""
        self.state['schedule']['next_run'] = next_run.isoformat()
        self.state['schedule']['message'] = message
        
        # Calculate remaining time
        now = datetime.now()
        remaining = (next_run - now).total_seconds()
        self.state['schedule']['time_remaining'] = max(0, int(remaining))
        self._save()

    def update_logic(self, action: str, description: str, market_status: str = ""):
        """Update current logic/activity description"""
        self.state['logic']['current_action'] = action
        self.state['logic']['description'] = description
        if market_status:
            self.state['logic']['market_status'] = market_status
        self._save()

    def update_market_data(self, price, cash, qty, avg):
        """Update market data for dashboard display"""
        if 'market' not in self.state:
            self.state['market'] = {}
            
        self.state['market']['current_price'] = price
        self.state['market']['details'] = {
            'cash': cash,
            'holdings_qty': qty,
            'avg_price': avg
        }
        self._save()

    def set_status(self, status: str):
        """Set detailed system status"""
        self.state['system']['status'] = status
        self._save()

    def _save(self):
        """Save state to JSON file using atomic write"""
        try:
            # Update last_updated
            self.state['last_updated'] = datetime.now().isoformat()
            
            # Recalculate time_remaining if next_run is set
            if self.state['schedule']['next_run']:
                try:
                    next_run = datetime.fromisoformat(self.state['schedule']['next_run'])
                    remaining = (next_run - datetime.now()).total_seconds()
                    self.state['schedule']['time_remaining'] = max(0, int(remaining))
                except:
                    pass

            # Write to temp file first
            temp_file = self.status_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_file, self.status_file)
            
        except Exception as e:
            logger.error(f"Failed to save bot status: {e}")

