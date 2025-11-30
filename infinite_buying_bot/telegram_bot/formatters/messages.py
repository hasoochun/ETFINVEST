"""Message formatters for Telegram bot"""

from datetime import datetime
from typing import Dict, Optional

def format_status(data: Dict) -> str:
    """
    Format status message
    
    Args:
        data: Status data dictionary
        
    Returns:
        Formatted status message
    """
    status_icon = "●" if data.get('is_running', False) else "○"
    market_icon = "🟢" if data.get('market_open', False) else "🔴"
    
    message = (
        f"🤖 *봇 상태*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"상태: `{status_icon} {data.get('status', 'UNKNOWN').upper()}`\n"
        f"종목: `🎯 {data.get('trading_symbol', 'UNKNOWN')}`\n"
        f"시장: `{market_icon} {data.get('market_status', 'UNKNOWN')}`\n"
        f"모드: `📝 {data.get('mode', 'UNKNOWN').upper()}`\n"
        f"가동시간: `{data.get('uptime', 'N/A')}`\n\n"
        f"다음 개장: `{data.get('next_open', 'N/A')}`\n"
        f"마지막 업데이트: `{data.get('last_update', 'N/A')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return message

def format_balance(data: Dict) -> str:
    """
    Format balance message
    
    Args:
        data: Balance data dictionary
        
    Returns:
        Formatted balance message
    """
    pnl = data.get('pnl', 0)
    pnl_icon = "🟢" if pnl >= 0 else "🔴"
    pnl_sign = "+" if pnl >= 0 else ""
    
    message = (
        f"💰 *계좌 잔고*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"현금:        `${data.get('cash', 0):,.2f}`\n"
        f"주식:        `${data.get('stocks', 0):,.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"총액:        `${data.get('total', 0):,.2f}`\n"
        f"손익:        `{pnl_icon} {pnl_sign}${pnl:,.2f} ({pnl_sign}{data.get('pnl_pct', 0):.2f}%)`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return message

def format_position(data: Optional[Dict]) -> str:
    """
    Format position message
    
    Args:
        data: Position data dictionary
        
    Returns:
        Formatted position message
    """
    if not data or data.get('quantity', 0) == 0:
        return (
            "📈 *현재 포지션*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "보유 포지션 없음\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    
    pnl = data.get('pnl', 0)
    pnl_icon = "🟢" if pnl >= 0 else "🔴"
    pnl_sign = "+" if pnl >= 0 else ""
    
    avg_price = data.get('avg_price', 0)
    current_price = data.get('current_price', 0)
    price_change = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
    price_icon = "📈" if price_change >= 0 else "📉"
    price_sign = "+" if price_change >= 0 else ""
    
    message = (
        f"📈 *현재 포지션*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"종목:        `{data.get('symbol', 'N/A')}`\n"
        f"수량:        `{data.get('quantity', 0)} 주`\n"
        f"평균가:      `${avg_price:.2f}`\n"
        f"현재가:      `${current_price:.2f} {price_icon} ({price_sign}{price_change:.2f}%)`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"평가액:      `${data.get('value', 0):,.2f}`\n"
        f"손익:        `{pnl_icon} {pnl_sign}${pnl:,.2f} ({pnl_sign}{data.get('pnl_pct', 0):.2f}%)`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return message

def format_trade_notification(trade_type: str, data: Dict) -> str:
    """
    Format trade execution notification
    
    Args:
        trade_type: 'BUY' or 'SELL'
        data: Trade data dictionary
        
    Returns:
        Formatted trade notification
    """
    icon = "🟢" if trade_type == "BUY" else "🔴"
    
    message = (
        f"{icon} *{trade_type} ORDER FILLED*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Symbol:      `{data.get('symbol', 'N/A')}`\n"
        f"Quantity:    `{data.get('quantity', 0)} shares`\n"
        f"Price:       `${data.get('price', 0):.2f}`\n"
        f"Total:       `${data.get('total', 0):.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Position:    `{data.get('position_qty', 0)} shares @ ${data.get('position_avg', 0):.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ {data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
    )
    return message

def format_profit_target_notification(data: Dict) -> str:
    """
    Format profit target reached notification
    
    Args:
        data: Profit data dictionary
        
    Returns:
        Formatted profit notification
    """
    message = (
        f"🎉 *PROFIT TARGET REACHED!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Target:      `{data.get('target', 0):.1f}%`\n"
        f"Achieved:    `{data.get('achieved', 0):.1f}%`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Avg Buy:     `${data.get('avg_buy', 0):.2f}`\n"
        f"Current:     `${data.get('current', 0):.2f}`\n"
        f"Profit:      `+${data.get('profit', 0):.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Selling all positions...\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return message

def format_error_notification(error: str) -> str:
    """
    Format error notification
    
    Args:
        error: Error message
        
    Returns:
        Formatted error notification
    """
    message = (
        f"⚠️ *ERROR OCCURRED*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"`{error}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Please check the logs."
    )
    return message

def format_daily_performance(data: list, days: int) -> str:
    """
    Format daily performance message
    
    Args:
        data: List of daily performance dictionaries
        days: Number of days
        
    Returns:
        Formatted daily performance message
    """
    message = f"📊 *Daily Performance (Last {days} days)*\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    
    total_pnl = 0
    for day_data in data:
        pnl = day_data.get('pnl', 0)
        pnl_pct = day_data.get('pnl_pct', 0)
        date = day_data.get('date', 'N/A')
        sign = "+" if pnl >= 0 else ""
        
        message += f"{date}:  `{sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%)`\n"
        total_pnl += pnl
    
    total_pct = sum(d.get('pnl_pct', 0) for d in data)
    sign = "+" if total_pnl >= 0 else ""
    
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += f"Total:       `{sign}${total_pnl:.2f} ({sign}{total_pct:.1f}%)`\n"
    message += "━━━━━━━━━━━━━━━━━━━━"
    
    return message
