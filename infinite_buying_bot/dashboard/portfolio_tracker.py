#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Tracker Module
Captures daily portfolio snapshots for performance reporting.
Includes benchmark comparison (S&P 500) and investment analysis metrics.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import yfinance as yf

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.database import (
    log_portfolio_history,
    get_portfolio_history,
    get_latest_portfolio_snapshot,
    get_performance_metrics,
    get_initial_capital
)

logger = logging.getLogger(__name__)


class PortfolioTracker:
    """
    Tracks portfolio performance over time and compares with benchmarks.
    Provides investment analysis feedback for decision making.
    """
    
    def __init__(self, trader=None):
        """
        Initialize Portfolio Tracker.
        
        Args:
            trader: Trader instance for fetching real-time holdings
        """
        self.trader = trader
        self.initial_capital = get_initial_capital() or 0
        self.benchmark_symbol = "^GSPC"  # S&P 500 Index
        self._benchmark_initial = None
        logger.info("[PortfolioTracker] Initialized")
    
    def capture_daily_snapshot(self) -> bool:
        """
        Capture and store daily portfolio snapshot.
        Should be called once per day (preferably at market close).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("[PortfolioTracker] Capturing daily snapshot...")
            
            # 1. Get current holdings from trader
            holdings_data = []
            total_value = 0.0
            cash_balance = 0.0
            invested_value = 0.0
            
            if self.trader:
                try:
                    # Get all holdings
                    holdings = self.trader.get_all_holdings()
                    for h in holdings:
                        qty = h.get('qty', 0)
                        current_price = h.get('current_price', 0)
                        market_value = qty * current_price
                        
                        holdings_data.append({
                            'symbol': h.get('symbol', ''),
                            'qty': qty,
                            'avg_price': h.get('avg_price', 0),
                            'current_price': current_price,
                            'market_value': market_value,
                            'pnl_pct': h.get('pnl_pct', 0)
                        })
                        invested_value += market_value
                    
                    # Get cash balance
                    balance_info = self.trader.get_balance()
                    cash_balance = balance_info.get('buying_power', 0)
                    total_value = invested_value + cash_balance
                    
                    logger.info(f"[PortfolioTracker] Holdings: {len(holdings_data)}, Total: ${total_value:.2f}")
                except Exception as e:
                    logger.error(f"[PortfolioTracker] Failed to get holdings: {e}")
                    return False
            else:
                logger.warning("[PortfolioTracker] No trader instance, using sample data")
                return False
            
            # 2. Calculate returns
            daily_return_pct = 0.0
            cumulative_return_pct = 0.0
            
            # Get previous day's data
            prev_snapshot = get_latest_portfolio_snapshot()
            if prev_snapshot:
                prev_value = prev_snapshot.get('total_value', total_value)
                if prev_value > 0:
                    daily_return_pct = ((total_value - prev_value) / prev_value) * 100
            
            # Calculate cumulative return from initial capital
            if self.initial_capital > 0:
                cumulative_return_pct = ((total_value - self.initial_capital) / self.initial_capital) * 100
            
            # 3. Get benchmark data (S&P 500)
            benchmark_value = None
            benchmark_return_pct = 0.0
            
            try:
                sp500 = yf.Ticker(self.benchmark_symbol)
                hist = sp500.history(period="1d")
                if not hist.empty:
                    benchmark_value = float(hist['Close'].iloc[-1])
                    
                    # Get benchmark initial value (30 days ago or first available)
                    if self._benchmark_initial is None:
                        hist_30d = sp500.history(period="30d")
                        if not hist_30d.empty:
                            self._benchmark_initial = float(hist_30d['Close'].iloc[0])
                    
                    if self._benchmark_initial and self._benchmark_initial > 0:
                        benchmark_return_pct = ((benchmark_value - self._benchmark_initial) / self._benchmark_initial) * 100
                    
                    logger.info(f"[PortfolioTracker] Benchmark (S&P 500): {benchmark_value:.2f}, Return: {benchmark_return_pct:.2f}%")
            except Exception as e:
                logger.warning(f"[PortfolioTracker] Could not fetch benchmark: {e}")
            
            # 4. Save to database
            log_portfolio_history(
                total_value=total_value,
                cash_balance=cash_balance,
                invested_value=invested_value,
                daily_return_pct=daily_return_pct,
                cumulative_return_pct=cumulative_return_pct,
                benchmark_value=benchmark_value,
                benchmark_return_pct=benchmark_return_pct,
                holdings=holdings_data
            )
            
            logger.info(f"[PortfolioTracker] ✅ Snapshot saved: Total=${total_value:.2f}, Daily={daily_return_pct:+.2f}%, Cumulative={cumulative_return_pct:+.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"[PortfolioTracker] Failed to capture snapshot: {e}", exc_info=True)
            return False
    
    def get_performance_report(self) -> Dict:
        """
        Generate comprehensive performance report for dashboard.
        
        Returns:
            Dict with performance data for charts and analysis
        """
        try:
            # Get historical data
            history_df = get_portfolio_history(days=30)
            metrics = get_performance_metrics()
            
            # Prepare chart data
            dates = []
            portfolio_returns = []
            benchmark_returns = []
            mdd_values = []
            
            if not history_df.empty:
                dates = history_df['date'].tolist()
                portfolio_returns = history_df['cumulative_return_pct'].fillna(0).tolist()
                benchmark_returns = history_df['benchmark_return_pct'].fillna(0).tolist()
                mdd_values = history_df['mdd_pct'].fillna(0).tolist()
            
            return {
                'status': 'success',
                'returns': {
                    'dates': dates,
                    'portfolio': portfolio_returns,
                    'benchmark': benchmark_returns
                },
                'mdd': {
                    'dates': dates,
                    'values': mdd_values
                },
                'metrics': metrics,
                'analysis': self._generate_investment_feedback(metrics, portfolio_returns, benchmark_returns)
            }
            
        except Exception as e:
            logger.error(f"[PortfolioTracker] Failed to generate report: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _generate_investment_feedback(
        self, 
        metrics: Dict, 
        portfolio_returns: List[float], 
        benchmark_returns: List[float]
    ) -> Dict:
        """
        Generate investment analysis feedback based on performance data.
        Provides actionable insights for investment decisions.
        
        Args:
            metrics: Performance metrics dict
            portfolio_returns: List of portfolio cumulative returns
            benchmark_returns: List of benchmark cumulative returns
            
        Returns:
            Dict with analysis and recommendations
        """
        feedback = {
            'overall_grade': 'N/A',
            'summary': '',
            'recommendations': [],
            'alerts': []
        }
        
        try:
            total_return = metrics.get('total_return', 0)
            mdd = metrics.get('mdd', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            win_rate = metrics.get('win_rate', 0)
            
            # Calculate alpha (excess return vs benchmark)
            alpha = 0
            if portfolio_returns and benchmark_returns:
                alpha = portfolio_returns[-1] - benchmark_returns[-1] if len(portfolio_returns) > 0 and len(benchmark_returns) > 0 else 0
            
            # Grade based on multiple factors
            score = 0
            if total_return > 5: score += 2
            elif total_return > 0: score += 1
            elif total_return < -5: score -= 2
            elif total_return < 0: score -= 1
            
            if mdd > -5: score += 2
            elif mdd > -10: score += 1
            elif mdd < -20: score -= 2
            elif mdd < -15: score -= 1
            
            if sharpe > 1: score += 2
            elif sharpe > 0.5: score += 1
            elif sharpe < 0: score -= 1
            
            if alpha > 2: score += 1
            elif alpha < -2: score -= 1
            
            # Assign grade
            if score >= 5:
                feedback['overall_grade'] = 'A'
                feedback['summary'] = '우수한 성과! 현재 전략이 효과적입니다.'
            elif score >= 3:
                feedback['overall_grade'] = 'B'
                feedback['summary'] = '양호한 성과. 일부 개선 여지가 있습니다.'
            elif score >= 1:
                feedback['overall_grade'] = 'C'
                feedback['summary'] = '평균적 성과. 전략 검토를 권장합니다.'
            elif score >= -1:
                feedback['overall_grade'] = 'D'
                feedback['summary'] = '저조한 성과. 리밸런싱을 고려하세요.'
            else:
                feedback['overall_grade'] = 'F'
                feedback['summary'] = '위험 수준! 즉각적인 전략 수정이 필요합니다.'
            
            # Generate specific recommendations
            if mdd < -15:
                feedback['recommendations'].append('MDD가 높습니다. 방어적 자산(SHV) 비중 확대를 고려하세요.')
                feedback['alerts'].append('HIGH_MDD')
            
            if alpha < -3:
                feedback['recommendations'].append('벤치마크 대비 수익률이 낮습니다. 포트폴리오 구성을 재검토하세요.')
                feedback['alerts'].append('UNDERPERFORMING')
            
            if win_rate < 40:
                feedback['recommendations'].append('승률이 낮습니다. 매수 타이밍 전략을 점검하세요.')
            
            if sharpe < 0:
                feedback['recommendations'].append('위험 대비 수익이 부정적입니다. 변동성 관리가 필요합니다.')
            
            if total_return > 10 and alpha > 5:
                feedback['recommendations'].append('훌륭한 성과! 일부 수익 실현을 고려해 볼 수 있습니다.')
            
            if not feedback['recommendations']:
                feedback['recommendations'].append('현재 포트폴리오는 안정적입니다. 기존 전략을 유지하세요.')
            
            # Add benchmark comparison
            feedback['alpha'] = round(alpha, 2)
            feedback['benchmark_comparison'] = 'outperforming' if alpha > 0 else 'underperforming'
            
        except Exception as e:
            logger.error(f"[PortfolioTracker] Failed to generate feedback: {e}")
            feedback['summary'] = '분석 데이터가 부족합니다.'
        
        return feedback


# Singleton instance
_tracker_instance: Optional[PortfolioTracker] = None


def get_tracker(trader=None) -> PortfolioTracker:
    """Get singleton PortfolioTracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = PortfolioTracker(trader)
    elif trader is not None and _tracker_instance.trader is None:
        _tracker_instance.trader = trader
    return _tracker_instance


def capture_snapshot(trader=None) -> bool:
    """Convenience function to capture daily snapshot"""
    tracker = get_tracker(trader)
    return tracker.capture_daily_snapshot()
