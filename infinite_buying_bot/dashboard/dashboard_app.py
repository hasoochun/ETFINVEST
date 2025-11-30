"""
Trading Dashboard - Simple & Visual MVP
Shows: Total Return, Win Rate, Daily Performance, Recent Trades
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dashboard.database import (
    get_current_stats, get_daily_stats, get_recent_trades,
    get_initial_capital, set_initial_capital
)

# Page config
st.set_page_config(
    page_title="Infinite Buying Strategy",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better visuals
st.markdown("""
<style>
    .big-metric {
        font-size: 3rem !important;
        font-weight: bold;
        color: #1f77b4;
    }
    .positive {
        color: #2ecc71 !important;
    }
    .negative {
        color: #e74c3c !important;
    }
    .metric-label {
        font-size: 1.2rem;
        color: #7f8c8d;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🎯 Infinite Buying Strategy Dashboard")
st.markdown("---")

# Get current stats
stats = get_current_stats()
initial_capital = get_initial_capital()

# Calculate values
total_value = stats['total_value']
total_profit = total_value - initial_capital
total_return_pct = stats['cumulative_return_pct']
daily_return_pct = stats['daily_return_pct']
win_rate = stats['win_rate']
target_achieved = stats.get('target_achieved', 0)  # Safe get with default

# KPI Cards - Big Numbers
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<p class="metric-label">💰 총 자산</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="big-metric">${total_value:,.0f}</p>', unsafe_allow_html=True)
    profit_color = "positive" if total_profit >= 0 else "negative"
    st.markdown(f'<p class="{profit_color}">{"↑" if total_profit >= 0 else "↓"} ${abs(total_profit):,.0f} ({total_return_pct:+.2f}%)</p>', unsafe_allow_html=True)

with col2:
    st.markdown('<p class="metric-label">📊 총 수익률</p>', unsafe_allow_html=True)
    return_color = "positive" if total_return_pct >= 0 else "negative"
    st.markdown(f'<p class="big-metric {return_color}">{total_return_pct:+.2f}%</p>', unsafe_allow_html=True)
    st.markdown(f'<p>수익: ${total_profit:,.0f}</p>', unsafe_allow_html=True)

with col3:
    st.markdown('<p class="metric-label">🎯 승률</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="big-metric">{win_rate:.1f}%</p>', unsafe_allow_html=True)
    st.markdown(f'<p>{stats["winning_trades"]}승 / {stats["total_trades"]}전</p>', unsafe_allow_html=True)

with col4:
    st.markdown('<p class="metric-label">✅ 목표달성</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="big-metric">{target_achieved}회</p>', unsafe_allow_html=True)
    st.markdown(f'<p>10% 이상 수익</p>', unsafe_allow_html=True)

st.markdown("---")

# Portfolio Allocation Pie Chart
st.subheader("💼 자산 구성")

col1, col2 = st.columns([2, 1])

with col1:
    # Calculate allocation
    position_value = stats['position_quantity'] * stats['position_avg_price']
    cash = total_value - position_value
    
    # Create pie chart
    if total_value > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['현금 💵', '주식 📈'],
            values=[cash, position_value],
            hole=0.4,
            marker=dict(colors=['#3498db', '#2ecc71']),
            textinfo='label+percent',
            textfont=dict(size=14),
            hovertemplate='<b>%{label}</b><br>금액: $%{value:,.0f}<br>비율: %{percent}<extra></extra>'
        )])
        
        fig_pie.update_layout(
            height=300,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("📊 거래 데이터가 없습니다.")

with col2:
    st.markdown("### 상세 내역")
    st.metric("현금", f"${cash:,.0f}", f"{(cash/total_value*100):.1f}%" if total_value > 0 else "0%")
    
    # Get detailed holdings from database
    from dashboard.database import get_current_holdings
    holdings = get_current_holdings()
    
    # If no detailed holdings (e.g. bot not running), use the single position data
    if not holdings and stats['position_quantity'] > 0:
        # Fallback to single position
        st.metric("주식 (통합)", f"${position_value:,.0f}", f"{(position_value/total_value*100):.1f}%" if total_value > 0 else "0%")
    else:
        # Show each holding
        for holding in holdings:
            symbol = holding['symbol']
            value = holding['value']
            pct = (value / total_value * 100) if total_value > 0 else 0
            st.metric(f"주식 ({symbol})", f"${value:,.0f}", f"{pct:.1f}%")
            
    st.metric("총 자산", f"${total_value:,.0f}")

st.markdown("---")

# Cumulative Return Chart
st.subheader("📈 누적 수익률 추이")

daily_stats = get_daily_stats()

if not daily_stats.empty:
    fig = go.Figure()
    
    # Main line - cumulative return
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['cumulative_return_pct'],
        mode='lines+markers',
        name='누적 수익률',
        line=dict(color='#2ecc71', width=3),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(46, 204, 113, 0.1)'
    ))
    
    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        height=400,
        hovermode='x unified',
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=14),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📊 거래 데이터가 쌓이면 차트가 표시됩니다.")

st.markdown("---")

# Secondary Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("일일 수익률", f"{daily_return_pct:+.2f}%")

with col2:
    st.metric("총 거래 횟수", f"{stats['total_trades']}회")

with col3:
    position_value = stats['position_quantity'] * stats['position_avg_price']
    st.metric("현재 포지션 가치", f"${position_value:,.0f}")

with col4:
    cash = total_value - position_value
    st.metric("현금", f"${cash:,.0f}")

st.markdown("---")

# Recent Trades Table
st.subheader("📋 최근 거래 내역")

recent_trades = get_recent_trades(10)

if not recent_trades.empty:
    # Format the dataframe for display
    display_df = recent_trades[['timestamp', 'type', 'symbol', 'quantity', 'price', 'pnl_pct', 'trade_count', 'mdd_pct']].copy()
    
    # Format timestamp
    display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Format numbers
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:.2f}")
    display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "-")
    display_df['trade_count'] = display_df['trade_count'].apply(lambda x: f"{int(x)}회" if pd.notna(x) else "-")
    display_df['mdd_pct'] = display_df['mdd_pct'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
    
    # Rename columns
    display_df.columns = ['시간', '유형', '종목', '수량', '가격', '실제수익률', '매매횟수', 'MDD']
    
    # Style the dataframe
    def color_pnl(val):
        if val == "-":
            return ''
        elif val.startswith('+'):
            return 'color: #2ecc71; font-weight: bold'
        elif val.startswith('-') and '%' in val:
            return 'color: #e74c3c; font-weight: bold'
        return ''
    
    styled_df = display_df.style.applymap(color_pnl, subset=['실제수익률'])
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Add explanation
    st.caption("💡 **실제수익률**: 목표 10% 대비 실제 달성한 수익률 (수수료, 시장가 매매 반영)")
    st.caption("💡 **매매횟수**: 목표 수익률 달성까지 소요된 총 매매 횟수")
    st.caption("💡 **MDD**: 목표 달성까지 발생한 최대 낙폭 (Maximum Drawdown)")
else:
    st.info("📊 거래 내역이 없습니다. 봇을 실행하면 데이터가 쌓입니다.")

st.markdown("---")

# Current Position
st.subheader("💼 현재 포지션")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("보유 종목", "SOXL")
    
with col2:
    st.metric("보유 수량", f"{stats['position_quantity']}주")
    
with col3:
    st.metric("평균 단가", f"${stats['position_avg_price']:.2f}")

# Footer
st.markdown("---")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 이 대시보드는 실시간으로 업데이트됩니다. 페이지를 새로고침하세요.")
