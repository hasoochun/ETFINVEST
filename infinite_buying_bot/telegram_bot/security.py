"""Security Manager for Telegram Bot"""

import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages authorized users for Telegram bot"""
    
    def __init__(self, allowed_chat_ids: list):
        """
        Initialize security manager
        
        Args:
            allowed_chat_ids: List of authorized Telegram chat IDs
        """
        self.allowed_chat_ids = [int(id) for id in allowed_chat_ids if id]
        logger.info(f"Security initialized with {len(self.allowed_chat_ids)} allowed chat IDs")
    
    def is_authorized(self, chat_id: int) -> bool:
        """
        Check if chat ID is authorized
        
        Args:
            chat_id: Telegram chat ID to check
            
        Returns:
            True if authorized, False otherwise
        """
        authorized = chat_id in self.allowed_chat_ids
        
        if not authorized:
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
        
        return authorized
    
    def add_authorized_user(self, chat_id: int):
        """
        Add new authorized user
        
        Args:
            chat_id: Telegram chat ID to authorize
        """
        if chat_id not in self.allowed_chat_ids:
            self.allowed_chat_ids.append(chat_id)
            logger.info(f"Added authorized user: {chat_id}")
    
    def remove_authorized_user(self, chat_id: int):
        """
        Remove authorized user
        
        Args:
            chat_id: Telegram chat ID to remove
        """
        if chat_id in self.allowed_chat_ids:
            self.allowed_chat_ids.remove(chat_id)
            logger.info(f"Removed authorized user: {chat_id}")
