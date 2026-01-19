# -*- coding: utf-8 -*-
"""
Trader Module (Production Only / Clean Version)
"""
import logging
import time
from infinite_buying_bot.api import kis_api as api
from infinite_buying_bot.api import kis_auth as ka

logger = logging.getLogger(__name__)

class Trader:
    def __init__(self, config, notifier):
        self.config = config
        self.notifier = notifier
        
        logger.info("[REAL] TRADER STARTING...")
        
        # Authenticate
        try:
            self.trenv = ka.auth() # No args needed, defaults to prod
        except Exception as e:
            logger.critical(f"FATAL: Auth Failed: {e}")
            raise e
            
        # Config
        self.symbol = "TQQQ" # Default
        self.symbols = ["TQQQ", "MAGS", "SHV", "JEPI"]
        self.exchange = "NAS"
        self.currency = "USD"
        
        # Force Real Mode
        self.env_mode = 'real'

    def get_price(self, symbol):
        # Use correct exchange code for each symbol
        # NAS for NASDAQ, AMS for NYSE American
        PRICE_EXCHANGES = {
            'TQQQ': 'NAS', 'QQQ': 'NAS', 'SHV': 'NAS', 'SOXL': 'NAS',
            'MAGS': 'AMS', 'JEPI': 'AMS', 'SPY': 'AMS', 'SCHD': 'AMS'
        }
        exchange = PRICE_EXCHANGES.get(symbol, 'NAS')
        return api.get_current_price(self.trenv, exchange, symbol)

    def get_balance(self):
        """Returns: (cash, quantity_of_main_symbol, avg_price_of_main_symbol)"""
        cash = 0.0
        qty = 0
        avg = 0.0
        try:
            # 1. Cash using dummy price 100
            df = api.inquire_psamount(
                self.trenv.my_acct, 
                self.trenv.my_prod, 
                self.exchange, 
                "100.0", 
                self.symbol
            )
            if df is not None:
                # Check known columns
                for col in ['frcr_ord_psbl_amt1', 'ovrs_ord_psbl_amt']:
                    if col in df.columns:
                        cash = float(df[col].iloc[0])
                        break
        except Exception as e:
            logger.error(f"Balance(Cash) Error: {e}")
            cash = None # Signal error

        try:
            # 2. Holdings
            df1, _ = api.inquire_balance(
                self.trenv.my_acct, 
                self.trenv.my_prod, 
                self.exchange, 
                self.currency
            )
            if df1 is not None and not df1.empty:
                row = df1[df1['ovrs_pdno'] == self.symbol]
                if not row.empty:
                    qty = int(float(row['ovrs_cblc_qty'].iloc[0]))
                    avg = float(row['pchs_avg_pric'].iloc[0])
        except Exception as e:
            logger.error(f"Balance(Holdings) Error: {e}")
            qty = None # Signal error
            
        return cash, qty, avg

    def buy(self, amount, symbol=None, reason=None, **kwargs):
        target = symbol or self.symbol
        price = self.get_price(target)
        
        if price <= 0:
            self.notifier.send(f"❌ Buy Failed: Invalid Price for {target}")
            return False
            
        qty = int(amount // price)
        if qty <= 0:
            logger.info(f"Buy skipped: Insufficient funds (${amount} vs ${price})")
            return False
            
        logger.info(f"Buying {target}: {qty} @ ${price}")
        logger.info(f"[ORDER] Type: MARKET, Symbol: {target}, Qty: {qty}, Price: ${price:.2f}")
        self.notifier.send(f"[BUYING] {target}\nQty: {qty}\nPrice: ${price}\nAmt: ${amount:.2f}")
        
        # Use limit order at current price + $0.01 for immediate fill
        limit_price = price + 0.01
        
        # IMPORTANT: Order API uses different exchange codes than price API
        # NASD for NASDAQ stocks (TQQQ, SHV, QQQ)
        # AMEX for NYSE American stocks (MAGS, JEPI, SPY)
        ORDER_EXCHANGES = {
            'TQQQ': 'NASD', 'QQQ': 'NASD', 'SHV': 'NASD', 'SOXL': 'NASD',
            'MAGS': 'AMEX', 'JEPI': 'AMEX', 'SPY': 'AMEX', 'SCHD': 'AMEX'
        }
        order_exchange = ORDER_EXCHANGES.get(target, 'NASD')
        logger.info(f"[ORDER] Using exchange: {order_exchange} for {target}")
        
        res = api.order(
            "buy",
            self.trenv.my_acct,
            self.trenv.my_prod,
            order_exchange,  # Use NASD for orders
            target,
            qty,
            f"{limit_price:.2f}",  # Limit price +1 tick for immediate fill
            "00"  # Limit Order
        )
        
        if res is not None and not res.empty:
            logger.info(f"[ORDER SUCCESS] {target} {qty} shares sent")
            self.notifier.send(f"[ORDER SENT] {target}")
            return True
        else:
            logger.error(f"[ORDER FAILED] {target} order rejected")
            self.notifier.send(f"[ORDER REJECTED] {target}")
            return False

    def sell(self, qty, symbol=None, reason=None, fallback_price=None):
        """
        Sell a specific quantity of shares.
        
        Args:
            qty: Number of shares to sell
            symbol: Stock symbol (default: self.symbol)
            reason: Reason for selling (for logging)
            fallback_price: Price to use if API fails (e.g., from holdings data)
        
        Returns:
            bool: True if order was sent successfully
        """
        target = symbol or self.symbol
        price = self.get_price(target)
        
        # Use fallback price if API price fetch failed
        if price <= 0 and fallback_price and fallback_price > 0:
            logger.warning(f"[SELL] Using fallback price ${fallback_price} for {target} (API returned {price})")
            price = fallback_price
        
        if price <= 0:
            self.notifier.send(f"❌ Sell Failed: Invalid Price for {target}")
            return False
        
        if qty <= 0:
            logger.info(f"Sell skipped: Invalid quantity {qty}")
            return False
        
        logger.info(f"Selling {target}: {qty} @ ${price}")
        reason_str = f" ({reason})" if reason else ""
        self.notifier.send(f"[SELLING] {target}{reason_str}\nQty: {qty}\nPrice: ${price}")
        
        # Use limit order at current price - $0.01 for immediate fill
        limit_price = price - 0.01
        
        # IMPORTANT: Order API uses different exchange codes than price API
        ORDER_EXCHANGES = {
            'TQQQ': 'NASD', 'QQQ': 'NASD', 'SHV': 'NASD', 'SOXL': 'NASD',
            'MAGS': 'AMEX', 'JEPI': 'AMEX', 'SPY': 'AMEX', 'SCHD': 'AMEX'
        }
        order_exchange = ORDER_EXCHANGES.get(target, 'NASD')
        logger.info(f"[ORDER] Using exchange: {order_exchange} for {target}")
        
        res = api.order(
            "sell",
            self.trenv.my_acct,
            self.trenv.my_prod,
            order_exchange,
            target,
            qty,
            f"{limit_price:.2f}",
            "00"  # Limit Order
        )
        
        if res is not None and not res.empty:
            logger.info(f"[ORDER SUCCESS] Sold {target} {qty} shares")
            self.notifier.send(f"[SELL ORDER SENT] {target}")
            return True
        else:
            logger.error(f"[ORDER FAILED] {target} sell order rejected")
            self.notifier.send(f"[SELL ORDER REJECTED] {target}")
            return False

    def get_all_holdings(self):
        """Get all holdings from both NASD and AMEX exchanges"""
        out = []
        exchanges = ["NASD", "AMEX"]  # Query both exchanges for all ETFs
        
        for exchange in exchanges:
            try:
                df1, _ = api.inquire_balance(
                    self.trenv.my_acct, 
                    self.trenv.my_prod, 
                    exchange, 
                    self.currency
                )
                if df1 is not None and not df1.empty:
                    for _, r in df1.iterrows():
                        symbol = r.get('ovrs_pdno', '')
                        qty = int(float(r.get('ovrs_cblc_qty', 0)))
                        if symbol and qty > 0:
                            out.append({
                                'symbol': symbol,
                                'qty': qty,
                                'avg_price': float(r.get('pchs_avg_pric', 0)),
                                'current_price': float(r.get('now_pric2', 0))
                            })
                            logger.info(f"[HOLDINGS] {symbol}: {qty}주 @ ${r.get('pchs_avg_pric')} ({exchange})")
            except Exception as e:
                logger.error(f"[HOLDINGS] Failed to query {exchange}: {e}")
                # If API fails completely, return None to prevent '0 holdings' misunderstanding
                return None
        
        return out
