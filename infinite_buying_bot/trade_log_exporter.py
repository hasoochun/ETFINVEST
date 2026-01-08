#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade Log Exporter (AWS 서버용)
실행 시간: 매매 완료 후 또는 05:30 KST (장 마감 후)

목적: 오늘 매매 결과를 last_trade.json에 저장하고 GitHub에 push
→ 05:50에 로컬 PC가 git pull로 가져감
"""

import os
import sys
import json
import sqlite3
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 설정
PROJECT_DIR = Path(__file__).parent
TRADING_DB = PROJECT_DIR / "trading.db"
LAST_TRADE_JSON = PROJECT_DIR / "data" / "last_trade.json"   # 매매 로그 (성공)
LAST_ERROR_JSON = PROJECT_DIR / "data" / "last_error.json"   # 오류 로그 (실패/경고)
BOT_LOG_FILE = PROJECT_DIR / "bot.log"                       # 봇 실행 로그
STRATEGY_CONTEXT = PROJECT_DIR / "runtime_config.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_DIR / 'trade_export.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_today_trades():
    """오늘 매매 내역 조회"""
    if not TRADING_DB.exists():
        logger.warning(f"trading.db not found: {TRADING_DB}")
        return []
    
    try:
        conn = sqlite3.connect(TRADING_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # trades 테이블에서 오늘 거래 조회
        cursor.execute("""
            SELECT timestamp, symbol, action, quantity, price, reason, profit_pct
            FROM trades
            WHERE date(timestamp) = ?
            ORDER BY timestamp
        """, (today,))
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
    except Exception as e:
        logger.error(f"DB 조회 오류: {e}")
        return []


def get_current_strategy():
    """현재 사용 중인 전략 정보"""
    if not STRATEGY_CONTEXT.exists():
        return {}
    
    try:
        with open(STRATEGY_CONTEXT, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"전략 파일 읽기 오류: {e}")
        return {}


def get_portfolio_summary():
    """현재 포트폴리오 상태 요약"""
    try:
        conn = sqlite3.connect(TRADING_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, quantity, avg_price, current_price
            FROM positions
            WHERE quantity > 0
        """)
        
        positions = [
            {
                'symbol': row[0],
                'quantity': row[1],
                'avg_price': row[2],
                'current_price': row[3],
                'profit_pct': round((row[3] - row[2]) / row[2] * 100, 2) if row[2] > 0 else 0
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return positions
    except Exception as e:
        logger.error(f"포트폴리오 조회 오류: {e}")
        return []


def generate_6w_summary(trade):
    """매매 내역을 6하원칙 문장으로 변환"""
    timestamp = trade.get('timestamp', '')
    symbol = trade.get('symbol', 'UNKNOWN')
    action = trade.get('action', 'trade')
    quantity = trade.get('quantity', 0)
    price = trade.get('price', 0)
    reason = trade.get('reason', '')
    profit_pct = trade.get('profit_pct', 0)
    
    # 시간 파싱
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = dt.strftime('%Y-%m-%d %H:%M KST')
    except:
        time_str = timestamp
    
    # 6하원칙 문장 생성
    when = f"**언제**: {time_str}"
    where = "**어디서**: 한국투자증권(KIS) API를 통한 나스닥 시장"
    who = "**누가**: 시멘틱 매매 봇이"
    
    if action == 'buy':
        what = f"**무엇을**: {symbol} {quantity}주를 ${price:.2f}에 매수"
    elif action == 'sell':
        what = f"**무엇을**: {symbol} {quantity}주를 ${price:.2f}에 매도"
    else:
        what = f"**무엇을**: {symbol} {quantity}주 {action} (${price:.2f})"
    
    if 'profit' in reason.lower():
        how = f"**어떻게**: profit_target 도달로 인한 자동 익절 (+{profit_pct:.1f}%)"
    elif 'dip' in reason.lower():
        how = f"**어떻게**: 하락장 분할 매수 전략 실행 (split_count 기준)"
    else:
        how = f"**어떻게**: {reason}"
    
    why = f"**왜**: {reason}"
    
    return {
        'when': when,
        'where': where,
        'who': who,
        'what': what,
        'how': how,
        'why': why,
        'formatted': f"{when}\n{where}\n{who}\n{what}\n{how}\n{why}"
    }


def export_trade_log():
    """매매 로그를 JSON으로 내보내기"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 데이터 수집
    trades = get_today_trades()
    strategy = get_current_strategy()
    portfolio = get_portfolio_summary()
    
    # 6하원칙 요약 생성
    trade_summaries = [generate_6w_summary(t) for t in trades]
    
    # 결과 JSON 구성
    export_data = {
        'date': today,
        'export_time': datetime.now().isoformat(),
        'strategy': {
            'mode': strategy.get('strategy_mode', 'UNKNOWN'),
            'split_count': strategy.get('split_count', 'N/A'),
            'profit_target': strategy.get('profit_target', 'N/A'),
            'profit_reinvest_symbol': strategy.get('profit_reinvest_symbol', 'N/A')
        },
        'trades': trades,
        'trade_summaries_6w': trade_summaries,
        'portfolio': portfolio,
        'statistics': {
            'total_trades': len(trades),
            'buy_count': sum(1 for t in trades if t.get('action') == 'buy'),
            'sell_count': sum(1 for t in trades if t.get('action') == 'sell'),
            'profit_taking_count': sum(1 for t in trades if 'profit' in (t.get('reason') or '').lower())
        }
    }
    
    # JSON 저장
    try:
        LAST_TRADE_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_TRADE_JSON, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        logger.info(f"📊 매매 로그 저장 완료: {LAST_TRADE_JSON}")
        return True
    except Exception as e:
        logger.error(f"JSON 저장 오류: {e}")
        return False


def get_today_errors():
    """오늘 발생한 오류 로그 수집"""
    errors = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. bot.log에서 오류 추출
    if BOT_LOG_FILE.exists():
        try:
            with open(BOT_LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if today in line and ('ERROR' in line or 'WARNING' in line or 'Exception' in line):
                        errors.append({
                            'source': 'bot.log',
                            'level': 'ERROR' if 'ERROR' in line else 'WARNING',
                            'message': line.strip(),
                            'timestamp': today
                        })
        except Exception as e:
            logger.warning(f"bot.log 읽기 실패: {e}")
    
    # 2. trading.db에서 실패한 거래 조회
    if TRADING_DB.exists():
        try:
            conn = sqlite3.connect(TRADING_DB)
            cursor = conn.cursor()
            
            # failed_orders 테이블이 있다면 조회
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='failed_orders'")
            if cursor.fetchone():
                cursor.execute("""
                    SELECT timestamp, symbol, error_message, retry_count
                    FROM failed_orders
                    WHERE date(timestamp) = ?
                """, (today,))
                
                for row in cursor.fetchall():
                    errors.append({
                        'source': 'trading.db',
                        'level': 'ERROR',
                        'symbol': row[1],
                        'message': row[2],
                        'retry_count': row[3],
                        'timestamp': row[0]
                    })
            conn.close()
        except Exception as e:
            logger.warning(f"DB 오류 조회 실패: {e}")
    
    return errors


def export_error_log():
    """오류 로그를 JSON으로 내보내기"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    errors = get_today_errors()
    
    # 오류 분류
    api_errors = [e for e in errors if 'API' in e.get('message', '') or 'timeout' in e.get('message', '').lower()]
    network_errors = [e for e in errors if 'network' in e.get('message', '').lower() or 'connection' in e.get('message', '').lower()]
    order_errors = [e for e in errors if e.get('source') == 'trading.db']
    other_errors = [e for e in errors if e not in api_errors + network_errors + order_errors]
    
    export_data = {
        'date': today,
        'export_time': datetime.now().isoformat(),
        'total_errors': len(errors),
        'errors_by_type': {
            'api_errors': len(api_errors),
            'network_errors': len(network_errors),
            'order_errors': len(order_errors),
            'other_errors': len(other_errors)
        },
        'errors': errors,
        'summary': {
            'has_critical': any(e.get('level') == 'ERROR' for e in errors),
            'requires_attention': len(errors) > 5,
            'recommendation': _generate_error_recommendation(errors)
        }
    }
    
    # JSON 저장
    try:
        LAST_ERROR_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_ERROR_JSON, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        logger.info(f"⚠️ 오류 로그 저장 완료: {LAST_ERROR_JSON} ({len(errors)}건)")
        return True
    except Exception as e:
        logger.error(f"오류 로그 저장 실패: {e}")
        return False


def _generate_error_recommendation(errors):
    """오류에 따른 권장 사항 생성"""
    if not errors:
        return "시스템 정상 작동 중. 오류 없음."
    
    recommendations = []
    
    api_count = sum(1 for e in errors if 'API' in e.get('message', ''))
    if api_count > 0:
        recommendations.append(f"API 오류 {api_count}건 발생. API 키/권한 확인 필요.")
    
    timeout_count = sum(1 for e in errors if 'timeout' in e.get('message', '').lower())
    if timeout_count > 0:
        recommendations.append(f"타임아웃 {timeout_count}건 발생. 네트워크 상태 확인 및 주문 간격 조정 권장.")
    
    order_fail = sum(1 for e in errors if e.get('source') == 'trading.db')
    if order_fail > 0:
        recommendations.append(f"주문 실패 {order_fail}건. 잔고/호가 확인 필요.")
    
    return " ".join(recommendations) if recommendations else "경미한 오류 발생. 모니터링 지속."


def push_to_github():
    """GitHub에 push (매매로그 + 오류로그)"""
    try:
        os.chdir(PROJECT_DIR)
        
        # Git add (매매로그 + 오류로그)
        subprocess.run(['git', 'add', 'data/last_trade.json'], capture_output=True, text=True)
        subprocess.run(['git', 'add', 'data/last_error.json'], capture_output=True, text=True)
        
        # Git commit
        today = datetime.now().strftime('%Y-%m-%d %H:%M')
        result = subprocess.run(
            ['git', 'commit', '-m', f'auto: trade + error log {today}'],
            capture_output=True, text=True
        )
        
        if 'nothing to commit' in result.stdout:
            logger.info("변경 사항 없음 - push 스킵")
            return True
        
        # Git push
        result = subprocess.run(
            ['git', 'push', 'origin', 'main'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ GitHub push 성공 (매매로그 + 오류로그)!")
            return True
        else:
            logger.error(f"Push 오류: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Git 오류: {e}")
        return False


def main():
    logger.info("=" * 50)
    logger.info("📊 Trade & Error Log Exporter (AWS)")
    logger.info("=" * 50)
    
    # 1. 매매 로그 내보내기
    if not export_trade_log():
        logger.error("❌ 매매 로그 내보내기 실패")
        # 계속 진행 (오류로그라도 전송)
    
    # 2. 오류 로그 내보내기
    if not export_error_log():
        logger.error("❌ 오류 로그 내보내기 실패")
        # 계속 진행
    
    # 3. GitHub push (매매로그 + 오류로그)
    if not push_to_github():
        logger.error("❌ GitHub push 실패")
        return False
    
    logger.info("✅ 매매로그 + 오류로그 GitHub 동기화 완료!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
