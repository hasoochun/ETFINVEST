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
            InlineKeyboardButton("📊 포트폴리오", callback_data='show_portfolio'),
            InlineKeyboardButton("⚖️ 리밸런싱", callback_data='show_rebalance')
        ],
        [
            InlineKeyboardButton("🎯 ETF 선택", callback_data='show_etf_selection'),
            InlineKeyboardButton("⚙️ 매수 모드", callback_data='show_dip_mode')
        ],
        [
            InlineKeyboardButton("💰 잔고", callback_data='show_balance'),
            InlineKeyboardButton("📈 포지션", callback_data='show_position')
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
            InlineKeyboardButton("📈 TQQQ (나스닥 3x)", callback_data='select_etf_TQQQ')
        ],
        [
            InlineKeyboardButton("🌟 MAGS (M7 전용)", callback_data='select_etf_MAGS')
        ],
        [
            InlineKeyboardButton("💎 QQQ (나스닥 100)", callback_data='select_etf_QQQ')
        ],
        [
            InlineKeyboardButton("🏛️ SPY (S&P 500)", callback_data='select_etf_SPY')
        ],
        [
            InlineKeyboardButton("💰 VOO (S&P 500 저비용)", callback_data='select_etf_VOO')
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

def get_dip_mode_keyboard() -> InlineKeyboardMarkup:
    """
    Get dip buy mode selection keyboard
    
    Returns:
        InlineKeyboardMarkup with dip mode selection buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("📅 일일 모드", callback_data='set_dip_mode_daily')
        ],
        [
            InlineKeyboardButton("🏃 가속 모드", callback_data='set_dip_mode_accelerated')
        ],
        [
            InlineKeyboardButton("⚡ 가속 테스트 모드", callback_data='set_dip_mode_accel_test')
        ],
        [
            InlineKeyboardButton("◀️ 뒤로", callback_data='back_to_status')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
