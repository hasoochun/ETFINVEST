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
        f"🤖 <b>봇 상태</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"상태: <code>{status_icon} {data.get('status', 'UNKNOWN').upper()}</code>\n"
        f"종목: <code>🎯 {data.get('trading_symbol', 'UNKNOWN')}</code>\n"
        f"시장: <code>{market_icon} {data.get('market_status', 'UNKNOWN')}</code>\n"
        f"모드: <code>📝 {data.get('mode', 'UNKNOWN').upper()}</code>\n"
        f"가동시간: <code>{data.get('uptime', 'N/A')}</code>\n\n"
        f"다음 개장: <code>{data.get('next_open', 'N/A')}</code>\n"
        f"마지막 업데이트: <code>{data.get('last_update', 'N/A')}</code>\n"
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
        f"💰 <b>계좌 잔고</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"현금:        <code>${data.get('cash', 0):,.2f}</code>\n"
        f"주식:        <code>${data.get('stocks', 0):,.2f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"총액:        <code>${data.get('total', 0):,.2f}</code>\n"
        f"손익:        <code>{pnl_icon} {pnl_sign}${pnl:,.2f} ({pnl_sign}{data.get('pnl_pct', 0):.2f}%)</code>\n"
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
            "📈 <b>현재 포지션</b>\n"
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
    
    source = data.get('price_source', 'KIS')
    source_icon = "🇺🇸" if source == 'YF' else "🇰🇷"
    
    message = (
        f"📈 <b>현재 포지션</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"종목:        <code>{data.get('symbol', 'N/A')}</code>\n"
        f"수량:        <code>{data.get('quantity', 0)} 주</code>\n"
        f"평균가:      <code>${avg_price:.2f}</code>\n"
        f"현재가:      <code>${current_price:.2f} {price_icon} ({price_sign}{price_change:.2f}%) {source_icon}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"평가액:      <code>${data.get('value', 0):,.2f}</code>\n"
        f"손익:        <code>{pnl_icon} {pnl_sign}${pnl:,.2f} ({pnl_sign}{data.get('pnl_pct', 0):.2f}%)</code>\n"
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
        f"{icon} <b>{trade_type} ORDER FILLED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Symbol:      <code>{data.get('symbol', 'N/A')}</code>\n"
        f"Quantity:    <code>{data.get('quantity', 0)} shares</code>\n"
        f"Price:       <code>${data.get('price', 0):.2f}</code>\n"
        f"Total:       <code>${data.get('total', 0):.2f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Position:    <code>{data.get('position_qty', 0)} shares @ ${data.get('position_avg', 0):.2f}</code>\n"
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
        f"🎉 <b>PROFIT TARGET REACHED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Target:      <code>{data.get('target', 0):.1f}%</code>\n"
        f"Achieved:    <code>{data.get('achieved', 0):.1f}%</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Avg Buy:     <code>${data.get('avg_buy', 0):.2f}</code>\n"
        f"Current:     <code>${data.get('current', 0):.2f}</code>\n"
        f"Profit:      <code>+${data.get('profit', 0):.2f}</code>\n"
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
        f"⚠️ <b>ERROR OCCURRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<code>{error}</code>\n"
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
    message = f"📊 <b>Daily Performance (Last {days} days)</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    
    total_pnl = 0
    for day_data in data:
        pnl = day_data.get('pnl', 0)
        pnl_pct = day_data.get('pnl_pct', 0)
        date = day_data.get('date', 'N/A')
        sign = "+" if pnl >= 0 else ""
        
        message += f"{date}:  <code>{sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%)</code>\n"
        total_pnl += pnl
    
    total_pct = sum(d.get('pnl_pct', 0) for d in data)
    sign = "+" if total_pnl >= 0 else ""
    
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += f"Total:       <code>{sign}${total_pnl:.2f} ({sign}{total_pct:.1f}%)</code>\n"
    message += "━━━━━━━━━━━━━━━━━━━━"
    
    return message
