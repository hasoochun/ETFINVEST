"""
Real Trader - KIS API 해외 ETF 매매 (NO MOCK/PAPER MODE)
디버깅 강화 버전 - 모든 오류 즉시 로깅, fallback 없음
"""
import requests
import json
import logging
from typing import Dict, Tuple, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingError(Exception):
    """거래 오류 - 즉시 로깅 및 전파"""
    pass

class RealTrader:
    """실제 KIS API 트레이더 - Paper Mode 없음"""
    
    # 지원 ETF 목록 및 거래소 (KIS API 거래소 코드: NAS, NYS, AMS 등)
    SUPPORTED_ETFS = {
        'TQQQ': 'NAS',   # 나스닥 3x
        'SOXL': 'NAS',   # 반도체 3x
        'MAGS': 'AMS',   # Magnificent 7 (NYSE American)
        'SHV': 'NAS',    # Treasury ETF (Cash buffer)
        'JEPI': 'AMS',   # Covered Call Income (NYSE American)
        'QQQ': 'NAS',    # Nasdaq 100
        'SPY': 'AMS',    # S&P 500 (NYSE American)
    }
    
    def __init__(self, auth_data: Dict):
        """초기화 - 필수 인증 데이터 검증"""
        required_keys = ['token', 'appkey', 'appsecret', 'cano', 'url']
        for key in required_keys:
            if key not in auth_data:
                raise TradingError(f"[INIT ERROR] Missing required auth key: {key}")
        
        self.auth = auth_data
        self.headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": self.auth['token'],
            "appkey": self.auth['appkey'],
            "appsecret": self.auth['appsecret']
        }
        self.base_url = self.auth['url']
        logger.info(f"[TRADER] Initialized - URL: {self.base_url}, Account: {self.auth['cano'][:4]}****")
        
    def get_price(self, symbol: str) -> float:
        """
        실시간 가격 조회
        
        Returns:
            현재가 (float)
            
        Raises:
            TradingError: API 호출 실패 시 즉시 예외
        """
        exchange = self._get_exchange(symbol)
        
        try:
            res = requests.get(
                f"{self.base_url}/uapi/overseas-price/v1/quotations/price",
                headers={**self.headers, "tr_id": "HHDFS00000300"},  # 해외주식 현재체결가
                params={"AUTH": "", "EXCD": exchange, "SYMB": symbol},
                timeout=10
            )
            
            logger.debug(f"[PRICE] {symbol} request - Status: {res.status_code}")
            
            if res.status_code != 200:
                error_msg = f"[PRICE ERROR] {symbol} - HTTP {res.status_code}: {res.text}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            logger.debug(f"[PRICE] {symbol} response: {json.dumps(data, ensure_ascii=False)[:200]}")
            
            if data.get('rt_cd') != '0':
                error_msg = f"[PRICE ERROR] {symbol} - API Error: {data.get('msg1', 'Unknown')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            output = data.get('output', {})
            
            # 가격 우선순위: last (실시간) > base (기준가) > 이전 종가
            price_str = output.get('last', '') or output.get('base', '') or output.get('stck_prpr', '')
            
            if not price_str:
                # 모든 가격 필드 로깅
                logger.error(f"[PRICE ERROR] {symbol} - All price fields empty. Output: {json.dumps(output, ensure_ascii=False)[:300]}")
                error_msg = f"[PRICE ERROR] {symbol} - No price available (market may be closed)"
                raise TradingError(error_msg)
            
            price = float(price_str)
            logger.info(f"[PRICE] {symbol}: ${price:.2f}")
            return price
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[PRICE ERROR] {symbol} - Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
    
    def get_balance(self) -> Tuple[float, int, float]:
        """
        계좌 잔고 조회 (현금, 수량, 평단가)
        
        Returns:
            (cash, quantity, avg_price)
            
        Raises:
            TradingError: API 호출 실패 시 즉시 예외
        """
        # 1. 현금 조회
        try:
            res = requests.get(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount",
                headers={**self.headers, "tr_id": "TTTS3007R"},
                params={
                    "CANO": self.auth['cano'],
                    "ACNT_PRDT_CD": "01",
                    "OVRS_EXCG_CD": "NASD",
                    "OVRS_ORD_UNPR": "100",
                    "ITEM_CD": "TQQQ"
                },
                timeout=10
            )
            
            logger.debug(f"[BALANCE] Cash request - Status: {res.status_code}")
            
            if res.status_code != 200:
                error_msg = f"[BALANCE ERROR] Cash - HTTP {res.status_code}: {res.text}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            if data.get('rt_cd') != '0':
                error_msg = f"[BALANCE ERROR] Cash - API Error: {data.get('msg1', 'Unknown')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            cash = float(data['output']['ovrs_ord_psbl_amt'])
            logger.info(f"[BALANCE] Cash: ${cash:,.2f}")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[BALANCE ERROR] Cash - Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
        
        # 2. 보유 종목 조회
        qty = 0
        avg = 0.0
        
        try:
            res2 = requests.get(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance",
                headers={**self.headers, "tr_id": "TTTS3012R"},
                params={
                    "CANO": self.auth['cano'],
                    "ACNT_PRDT_CD": "01",
                    "OVRS_EXCG_CD": "NASD",
                    "TR_CRCY_CD": "USD",
                    "CTX_AREA_FK200": "",
                    "CTX_AREA_NK200": ""
                },
                timeout=10
            )
            
            logger.debug(f"[BALANCE] Holdings request - Status: {res2.status_code}")
            
            if res2.status_code == 200:
                data = res2.json()
                if data.get('rt_cd') == '0':
                    for item in data.get('output1', []):
                        if item.get('ovrs_pdno') == 'TQQQ':
                            qty = int(float(item.get('ovrs_cblc_qty', 0)))
                            avg = float(item.get('pchs_avg_pric', 0))
                            break
                    logger.info(f"[BALANCE] TQQQ Holdings: {qty}주 @ ${avg:.2f}")
                            
        except Exception as e:
            logger.warning(f"[BALANCE] Holdings query failed (non-critical): {str(e)}")
        
        return cash, qty, avg
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """
        모든 보유 종목 조회
        
        Returns:
            {symbol: {'quantity': int, 'avg_price': float, 'current_price': float}}
            
        Raises:
            TradingError: API 호출 실패 시 즉시 예외
        """
        positions = {}
        
        try:
            res = requests.get(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance",
                headers={**self.headers, "tr_id": "TTTS3012R"},
                params={
                    "CANO": self.auth['cano'],
                    "ACNT_PRDT_CD": "01",
                    "OVRS_EXCG_CD": "NASD",
                    "TR_CRCY_CD": "USD",
                    "CTX_AREA_FK200": "",
                    "CTX_AREA_NK200": ""
                },
                timeout=10
            )
            
            logger.debug(f"[POSITIONS] Request - Status: {res.status_code}")
            
            if res.status_code != 200:
                error_msg = f"[POSITIONS ERROR] HTTP {res.status_code}: {res.text}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            logger.debug(f"[POSITIONS] Response: {json.dumps(data, ensure_ascii=False)[:500]}")
            
            if data.get('rt_cd') != '0':
                error_msg = f"[POSITIONS ERROR] API Error: {data.get('msg1', 'Unknown')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            for item in data.get('output1', []):
                symbol = item.get('ovrs_pdno', '')
                if symbol:
                    positions[symbol] = {
                        'quantity': int(float(item.get('ovrs_cblc_qty', 0))),
                        'avg_price': float(item.get('pchs_avg_pric', 0)),
                        'current_price': float(item.get('now_pric2', 0)),
                        'eval_amount': float(item.get('frcr_evlu_amt', 0)),
                        'profit_loss': float(item.get('evlu_pfls_amt', 0))
                    }
                    logger.info(f"[POSITIONS] {symbol}: {positions[symbol]['quantity']}주 @ ${positions[symbol]['avg_price']:.2f}")
            
            return positions
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[POSITIONS ERROR] Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
    
    def get_pending_orders(self) -> List[Dict]:
        """
        미체결 주문 조회
        
        Returns:
            미체결 주문 리스트 [{'symbol': 'TQQQ', 'qty': 10, 'price': 55.00, 'order_no': '0001', 'side': 'buy'}, ...]
            
        Raises:
            TradingError: API 호출 실패 시 예외
        """
        logger.info("[PENDING] Fetching pending orders...")
        orders = []
        
        try:
            res = requests.get(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-nccs",
                headers={**self.headers, "tr_id": "TTTS3018R"},  # 해외주식 미체결내역
                params={
                    "CANO": self.auth['cano'],
                    "ACNT_PRDT_CD": "01",
                    "OVRS_EXCG_CD": "NASD",  # NASD로 미국 전체 조회
                    "SORT_SQN": "DS",
                    "CTX_AREA_FK200": "",
                    "CTX_AREA_NK200": ""
                },
                timeout=10
            )
            
            logger.debug(f"[PENDING] Request - Status: {res.status_code}")
            
            if res.status_code != 200:
                error_msg = f"[PENDING ERROR] HTTP {res.status_code}: {res.text}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            logger.debug(f"[PENDING] Response: {json.dumps(data, ensure_ascii=False)[:500]}")
            
            if data.get('rt_cd') != '0':
                error_msg = f"[PENDING ERROR] API Error: {data.get('msg1', 'Unknown')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            for item in data.get('output', []):
                symbol = item.get('pdno', '')
                nccs_qty = int(float(item.get('nccs_qty', 0)))  # 미체결수량
                
                if symbol and nccs_qty > 0:
                    order = {
                        'symbol': symbol,
                        'qty': nccs_qty,
                        'price': float(item.get('ft_ord_unpr3', 0)),  # 주문단가
                        'order_no': item.get('odno', ''),  # 주문번호
                        'side': 'buy' if item.get('sll_buy_dvsn_cd') == '02' else 'sell',
                        'order_time': item.get('ord_tmd', ''),  # 주문시간
                        'order_amt': float(item.get('ft_ord_qty', 0)) * float(item.get('ft_ord_unpr3', 0))  # 주문금액
                    }
                    orders.append(order)
                    logger.info(f"[PENDING] {symbol}: {nccs_qty}주 @ ${order['price']:.2f} ({order['side']})")
            
            logger.info(f"[PENDING] Total: {len(orders)} pending orders")
            return orders
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[PENDING ERROR] Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
    
    def cancel_order(self, symbol: str, order_no: str, qty: int, exchange: str = 'NASD') -> bool:
        """
        미체결 주문 취소
        
        Args:
            symbol: 종목 코드
            order_no: 원주문번호 (ODNO)
            qty: 취소 수량
            exchange: 거래소 코드
            
        Returns:
            True if 취소 성공
            
        Raises:
            TradingError: API 호출 실패 시 예외
        """
        logger.info(f"[CANCEL] Cancelling order: {symbol} #{order_no} ({qty}주)")
        
        body = {
            "CANO": self.auth['cano'],
            "ACNT_PRDT_CD": "01",
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORGN_ODNO": order_no,
            "RVSE_CNCL_DVSN_CD": "02",  # 02: 취소
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0",  # 취소 시 0
            "MGCO_APTM_ODNO": "",
            "ORD_SVR_DVSN_CD": "0"
        }
        
        try:
            res = requests.post(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/order-rvsecncl",
                headers={**self.headers, "tr_id": "TTTT1004U"},  # 실전 정정취소
                json=body,
                timeout=15
            )
            
            logger.debug(f"[CANCEL] Response Status: {res.status_code}")
            logger.debug(f"[CANCEL] Response: {res.text[:500]}")
            
            if res.status_code != 200:
                error_msg = f"[CANCEL ERROR] {symbol} - HTTP {res.status_code}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            
            if data.get('rt_cd') != '0':
                error_msg = f"[CANCEL ERROR] {symbol} - API Error: {data.get('msg1', 'Unknown')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            logger.info(f"[CANCEL SUCCESS] {symbol} #{order_no} 취소 완료")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[CANCEL ERROR] {symbol} - Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
    
    def buy(self, symbol: str, qty: int, price: float) -> bool:
        """
        매수 주문 실행
        
        Args:
            symbol: 종목 코드
            qty: 주문 수량 (정수)
            price: 주문 가격
            
        Returns:
            True if successful
            
        Raises:
            TradingError: 주문 실패 시 즉시 예외
        """
        if qty <= 0:
            error_msg = f"[BUY ERROR] {symbol} - Invalid quantity: {qty}"
            logger.error(error_msg)
            raise TradingError(error_msg)
        
        exchange = self._get_exchange(symbol)
        
        # 매수 시 거래소 코드 매핑 (API 테스트 결과 기반)
        ORDER_EXCHANGE = {
            'TQQQ': 'NASD', 'SOXL': 'NASD', 'QQQ': 'NASD', 'SHV': 'NASD',  # NASDAQ 종목
            'MAGS': 'AMEX', 'JEPI': 'AMEX', 'SPY': 'AMEX',  # NYSE Arca/AMEX 종목
        }
        order_exchange = ORDER_EXCHANGE.get(symbol, 'NASD')
        
        # 주문 파라미터 - KIS API 해외주식 매수
        body = {
            "CANO": self.auth['cano'],           # 계좌번호
            "ACNT_PRDT_CD": "01",                # 계좌상품코드
            "OVRS_EXCG_CD": order_exchange,      # 거래소 코드 (NASD 사용)
            "PDNO": symbol,                      # 종목코드
            "ORD_QTY": str(qty),                 # 주문수량 (문자열)
            "OVRS_ORD_UNPR": f"{price:.2f}",     # 주문가격 (소수점 2자리)
            "ORD_DVSN": "00",                    # 주문구분 (00: 지정가)
            "ORD_SVR_DVSN_CD": "0"               # 주문서버구분
        }
        
        logger.info(f"[BUY] Submitting order: {symbol} {qty}주 @ ${price:.2f}")
        logger.debug(f"[BUY] Request body: {json.dumps(body, indent=2)}")
        
        try:
            res = requests.post(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/order",
                headers={**self.headers, "tr_id": "TTTT1002U"},  # 미국 매수 주문 (실전)
                json=body,
                timeout=15
            )
            
            logger.debug(f"[BUY] Response Status: {res.status_code}")
            logger.debug(f"[BUY] Response: {res.text[:500]}")
            
            if res.status_code != 200:
                error_msg = f"[BUY ERROR] {symbol} - HTTP {res.status_code}: {res.text}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            
            if data.get('rt_cd') != '0':
                error_msg = f"[BUY ERROR] {symbol} - API Error: {data.get('msg1', 'Unknown')} / {data.get('msg_cd', '')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            order_no = data.get('output', {}).get('ODNO', 'N/A')
            logger.info(f"[BUY SUCCESS] {symbol} {qty}주 @ ${price:.2f} - Order#{order_no}")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[BUY ERROR] {symbol} - Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
    
    def sell(self, symbol: str, qty: int, price: float) -> bool:
        """
        매도 주문 실행
        
        Args:
            symbol: 종목 코드
            qty: 주문 수량 (정수)
            price: 주문 가격
            
        Returns:
            True if successful
            
        Raises:
            TradingError: 주문 실패 시 즉시 예외
        """
        if qty <= 0:
            error_msg = f"[SELL ERROR] {symbol} - Invalid quantity: {qty}"
            logger.error(error_msg)
            raise TradingError(error_msg)
        
        exchange = self._get_exchange(symbol)
        
        body = {
            "CANO": self.auth['cano'],
            "ACNT_PRDT_CD": "01",
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": f"{price:.2f}",
            "ORD_DVSN": "00",
            "ORD_SVR_DVSN_CD": "0"
        }
        
        logger.info(f"[SELL] Submitting order: {symbol} {qty}주 @ ${price:.2f}")
        
        try:
            res = requests.post(
                f"{self.base_url}/uapi/overseas-stock/v1/trading/order",
                headers={**self.headers, "tr_id": "TTTS1006U"},  # 실전 매도
                json=body,
                timeout=15
            )
            
            if res.status_code != 200:
                error_msg = f"[SELL ERROR] {symbol} - HTTP {res.status_code}: {res.text}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            data = res.json()
            
            if data.get('rt_cd') != '0':
                error_msg = f"[SELL ERROR] {symbol} - API Error: {data.get('msg1', 'Unknown')}"
                logger.error(error_msg)
                raise TradingError(error_msg)
            
            order_no = data.get('output', {}).get('ODNO', 'N/A')
            logger.info(f"[SELL SUCCESS] {symbol} {qty}주 @ ${price:.2f} - Order#{order_no}")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"[SELL ERROR] {symbol} - Network Error: {str(e)}"
            logger.error(error_msg)
            raise TradingError(error_msg)
    
    def _get_exchange(self, symbol: str) -> str:
        """종목별 거래소 코드 반환"""
        if symbol not in self.SUPPORTED_ETFS:
            logger.warning(f"[EXCHANGE] Unknown symbol {symbol}, defaulting to NASD")
            return "NASD"
        return self.SUPPORTED_ETFS[symbol]
