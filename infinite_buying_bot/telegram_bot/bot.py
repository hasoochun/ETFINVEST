import logging
import telegram
import asyncio

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, config):
        self.token = config.get('telegram_token')
        self.chat_id = config.get('telegram_chat_id')
        self.bot = None
        if self.token:
            try:
                self.bot = telegram.Bot(token=self.token)
            except Exception as e:
                logger.error(f"Telegram Bot Init Failed: {e}")

    def send(self, message):
        if not self.bot or not self.chat_id:
            logger.warning("Notification skipped: No token or chat_id")
            return
            
        try:
            # Sync wrapper for async send_message
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='Markdown'))
            loop.close()
        except Exception as e:
            logger.error(f"Send Message Failed: {e}")
