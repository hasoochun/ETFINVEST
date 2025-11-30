import requests
import logging

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, config):
        self.discord_url = config.get('notification', {}).get('discord_webhook_url')
        self.telegram_token = config.get('notification', {}).get('telegram_token')
        self.telegram_chat_id = config.get('notification', {}).get('telegram_chat_id')

    def send(self, message):
        """Send message to all configured channels."""
        logger.info(f"Notification: {message}")
        
        if self.discord_url:
            self._send_discord(message)
        
        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(message)

    def _send_discord(self, message):
        try:
            data = {"content": message}
            response = requests.post(self.discord_url, json=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    def _send_telegram(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {"chat_id": self.telegram_chat_id, "text": message}
            response = requests.post(url, json=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    def send_bot_started(self):
        """Send bot started notification"""
        self.send("🚀 Bot Started\nTrading bot is now running.")

    def send_bot_stopped(self):
        """Send bot stopped notification"""
        self.send("⏸️ Bot Stopped\nTrading bot has been stopped.")

    def send_error(self, error):
        """Send error notification"""
        self.send(f"❌ Error: {error}")

