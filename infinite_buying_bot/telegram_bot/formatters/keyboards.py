"""Keyboard layouts for Telegram bot"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_status_keyboard() -> InlineKeyboardMarkup:
    """
    Get status message keyboard with action buttons
    
    Returns:
        InlineKeyboardMarkup with status action buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("▶️ 매매 시작", callback_data='start_bot'),
            InlineKeyboardButton("⏸️ 매매 중지", callback_data='stop_bot')
        ],
        [
            InlineKeyboardButton("🎯 ETF 선택", callback_data='show_etf_selection'),
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh_status')
        ],
        [
            InlineKeyboardButton("💰 Balance", callback_data='show_balance'),
            InlineKeyboardButton("📈 Position", callback_data='show_position')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_etf_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Get ETF selection keyboard
    
    Returns:
        InlineKeyboardMarkup with ETF selection buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 SOXL (반도체 3x)", callback_data='select_etf_SOXL')
        ],
        [
            InlineKeyboardButton("📈 TQQQ (나스닥 3x)", callback_data='select_etf_TQQQ')
        ],
        [
            InlineKeyboardButton("💎 SCHD (배당)", callback_data='select_etf_SCHD')
        ],
        [
            InlineKeyboardButton("◀️ 뒤로", callback_data='back_to_status')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_control_keyboard() -> InlineKeyboardMarkup:
    """
    Get control keyboard with bot control buttons
    
    Returns:
        InlineKeyboardMarkup with control buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start Bot", callback_data='start_bot'),
            InlineKeyboardButton("⏸️ Stop Bot", callback_data='stop_bot')
        ],
        [
            InlineKeyboardButton("🚫 Stop Entry", callback_data='stop_entry'),
            InlineKeyboardButton("💸 Force Exit", callback_data='force_exit')
        ],
        [
            InlineKeyboardButton("🚨 Emergency Stop", callback_data='emergency_stop')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Get confirmation keyboard for dangerous actions
    
    Args:
        action: Action to confirm
        
    Returns:
        InlineKeyboardMarkup with confirmation buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f'confirm_{action}'),
            InlineKeyboardButton("❌ Cancel", callback_data='cancel')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
