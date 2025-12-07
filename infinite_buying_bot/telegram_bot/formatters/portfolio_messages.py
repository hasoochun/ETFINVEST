
# Portfolio message formatter

def format_portfolio(portfolio_summary: dict) -> str:
    """
    Format portfolio summary message for 3-asset display
    
    Args:
        portfolio_summary: Dict from PortfolioManager.get_portfolio_summary()
        
    Returns:
        Formatted portfolio message
    """
    total_value = portfolio_summary['total_value']
    cash = portfolio_summary['cash']
    positions = portfolio_summary['positions']
    current_alloc = portfolio_summary['current_allocation']
    target_alloc = portfolio_summary['target_allocation']
    drift = portfolio_summary['allocation_drift']
    
    # Get position values
    tqqq_qty = positions.get('TQQQ', {}).get('quantity', 0)
    tqqq_price = positions.get('TQQQ', {}).get('current_price', 0)
    tqqq_value = tqqq_qty * tqqq_price
    
    shv_qty = positions.get('SHV', {}).get('quantity', 0)
    shv_price = positions.get('SHV', {}).get('current_price', 0)
    shv_value = shv_qty * shv_price
    
    schd_qty = positions.get('SCHD', {}).get('quantity', 0)
    schd_price = positions.get('SCHD', {}).get('current_price', 0)
    schd_value = schd_qty * schd_price
    
    # Format drift indicators
    def drift_indicator(drift_pct):
        if abs(drift_pct) < 0.05:  # < 5%
            return "✅"
        elif abs(drift_pct) < 0.10:  # < 10%
            return "⚠️"
        else:
            return "🔴"
    
    price_sources = portfolio_summary.get('price_sources', {})
    
    def get_source_icon(symbol):
        source = price_sources.get(symbol, 'KIS')
        return "🇺🇸" if source == 'YF' else "🇰🇷"
    
    message = (
        f"📊 <b>현재 포트폴리오 현황</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>💡 포트폴리오란?</b> 현재 보유 중인 모든 자산의 현황입니다.\n"
        f"• 각 ETF의 보유 수량과 현재가\n"
        f"• 목표 비중 대비 현재 비중\n"
        f"• 비중 이탈 정도 (✅ 정상, ⚠️ 주의, 🔴 조정 필요)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"총 자산: `${total_value:,.2f}`\n"
        f"수익률: `{portfolio_summary.get('total_return_pct', 0):+.2f}%`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"*TQQQ (나스닥 3x)* {get_source_icon('TQQQ')}\n"
        f"보유: `{tqqq_qty} 주 @ ${tqqq_price:.2f}`\n"
        f"가치: `${tqqq_value:,.2f}`\n"
        f"비중: `{current_alloc.get('TQQQ', 0)*100:.1f}%` (목표: {target_alloc.get('TQQQ', 0)*100:.0f}%) {drift_indicator(drift.get('TQQQ', 0))}\n\n"
        
        f"*SHV (단기 국채)* {get_source_icon('SHV')}\n"
        f"보유: `{shv_qty} 주 @ ${shv_price:.2f}`\n"
        f"가치: `${shv_value:,.2f}`\n"
        f"비중: `{current_alloc.get('SHV', 0)*100:.1f}%` (목표: {target_alloc.get('SHV', 0)*100:.0f}%) {drift_indicator(drift.get('SHV', 0))}\n\n"
        
        f"*SCHD (배당 성장)* {get_source_icon('SCHD')}\n"
        f"보유: `{schd_qty} 주 @ ${schd_price:.2f}`\n"
        f"가치: `${schd_value:,.2f}`\n"
        f"비중: `{current_alloc.get('SCHD', 0)*100:.1f}%` (목표: {target_alloc.get('SCHD', 0)*100:.0f}%) {drift_indicator(drift.get('SCHD', 0))}\n\n"
        
        f"*현금*\n"
        f"잔액: `${cash:,.2f}`\n"
        f"비중: `{current_alloc.get('CASH', 0)*100:.1f}%`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    return message


def format_rebalancing_plan(actions: list, portfolio_summary: dict = None) -> str:
    """
    Format rebalancing plan message
    
    Args:
        actions: List of rebalancing actions from RebalancingEngine
        portfolio_summary: Optional portfolio summary for showing current allocations
        
    Returns:
        Formatted rebalancing plan message
    """
    if not actions:
        # Show current allocation status even when no rebalancing needed
        if portfolio_summary:
            current_alloc = portfolio_summary.get('current_allocation', {})
            target_alloc = portfolio_summary.get('target_allocation', {})
            
            message = (
                "⚖️ <b>리밸런싱 실행엔진</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<b>💡 리밸런싱이란?</b> 목표 비중에서 벗어난 자산을 자동 조정합니다.\n\n"
                "<b>📊 현재 비중 vs 목표 비중:</b>\n"
            )
            
            for symbol in ['TQQQ', 'SHV', 'SCHD']:
                current = current_alloc.get(symbol, 0) * 100
                target = target_alloc.get(symbol, 0) * 100
                diff = current - target
                diff_sign = "+" if diff >= 0 else ""
                
                # Add indicator
                if abs(diff) >= 10:
                    indicator = "🔴"
                elif abs(diff) >= 5:
                    indicator = "⚠️"
                else:
                    indicator = "✅"
                
                message += f"• {symbol}: `{current:.1f}%` (목표: {target:.0f}%) {diff_sign}{diff:.1f}% {indicator}\n"
            
            message += (
                "\n━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>✅ 현재 상태:</b> 리밸런싱이 필요하지 않습니다.\n"
                "포트폴리오가 목표 배분에 근접합니다.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            return message
        else:
            return (
                "⚖️ <b>리밸런싱 실행엔진</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<b>💡 리밸런싱이란?</b> 목표 비중에서 벗어난 자산을 자동 조정합니다.\n\n"
                "<b>📊 실행 조건:</b> 비중이 목표에서 ±10% 이상 벗어날 때\n"
                "• 예: TQQQ 목표 30% → 현재 20% 또는 40%\n\n"
                "<b>🎯 실행 예시:</b>\n"
                "• TQQQ가 40%로 상승 → 10% 매도\n"
                "• SHV가 40%로 하락 → 10% 매수\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>✅ 현재 상태:</b> 리밸런싱이 필요하지 않습니다.\n"
                "포트폴리오가 목표 배분에 근접합니다.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
    
    # Show allocation comparison when actions exist
    message = (
        f"⚖️ <b>리밸런싱 실행엔진</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    # Show current vs target allocation if portfolio summary is available
    if portfolio_summary:
        current_alloc = portfolio_summary.get('current_allocation', {})
        target_alloc = portfolio_summary.get('target_allocation', {})
        
        message += f"<b>현재 비중 vs 목표 비중:</b>\n"
        for symbol in ['TQQQ', 'SHV', 'SCHD']:
            current = current_alloc.get(symbol, 0) * 100
            target = target_alloc.get(symbol, 0) * 100
            diff = current - target
            diff_sign = "+" if diff >= 0 else ""
            
            # Add indicator
            if abs(diff) >= 10:
                indicator = "🔴"
            elif abs(diff) >= 5:
                indicator = "⚠️"
            else:
                indicator = "✅"
            
            message += f"• {symbol}: `{current:.1f}%` (목표: {target:.0f}%) {diff_sign}{diff:.1f}% {indicator}\n"
        
        message += f"\n총 {len(actions)}개의 액션이 대기 중입니다:\n\n"
    else:
        message += f"총 {len(actions)}개의 액션이 대기 중입니다:\n\n"
    
    for i, action in enumerate(actions, 1):
        action_type = action['action']
        
        if action_type == 'profit_taking':
            message += (
                f"{i}. 🎯 *수익 실현*\n"
                f"   매도: {action['sell_symbol']} (전량)\n"
                f"   수익: +{action['profit_pct']:.1f}%\n"
                f"   재투자: {action['buy_symbol']}\n\n"
            )
        
        elif action_type == 'dip_buying':
            message += (
                f"{i}. 📉 *추가 매수*\n"
                f"   매도: {action.get('sell_symbol')} ({action.get('sell_amount', 0):,.0f})\n"
                f"   매수: {action['buy_symbol']}\n"
                f"   이유: {action.get('reason', '')}\n\n"
            )
        
        elif action_type == 'interest_reinvest':
            message += (
                f"{i}. 💰 *이자 재투자*\n"
                f"   매수: {action['buy_symbol']}\n"
                f"   금액: ${action.get('amount', 0):,.0f}\n\n"
            )
        
        elif action_type == 'rebalance':
            message += (
                f"{i}. ⚖️ *리밸런싱*\n"
                f"   {action.get('action', 'buy').upper()}: {action['symbol']}\n"
                f"   금액: ${action.get('amount_krw', 0):,.0f}\n\n"
            )
    
    message += "━━━━━━━━━━━━━━━━━━━━"
    
    return message
