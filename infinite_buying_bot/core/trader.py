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
        
        logger.info("🟢 TRADER (REAL) STARTING...")
        
        # Authenticate
        try:
            self.trenv = ka.auth() # No args needed, defaults to prod
        except Exception as e:
            logger.critical(f"FATAL: Auth Failed: {e}")
            raise e
            
        # Config
        self.symbol = "TQQQ" # Default
        self.symbols = ["TQQQ", "MAGS", "SHV", "JEPI"]
        self.exchange = "NASD"
        self.currency = "USD"
        
        # Force Real Mode
        self.env_mode = 'real'

    def get_price(self, symbol):
        return api.get_current_price(self.trenv, self.exchange, symbol)

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
        self.notifier.send(f"🛒 **BUYING** `{target}`\nQty: {qty}\nPrice: ${price}\nAmt: ${amount:.2f}")
        
        res = api.order(
            "buy",
            self.trenv.my_acct,
            self.trenv.my_prod,
            self.exchange,
            target,
            qty,
            f"{price:.2f}", # Limit Price
            "00" # Limit
        )
        
        if res is not None and not res.empty:
            self.notifier.send(f"✅ Order Sent: {target}")
            return True
        else:
            self.notifier.send(f"❌ Order Rejected: {target}")
            return False

    def get_all_holdings(self):
        """Simple list of dicts"""
        out = []
        try:
            df1, _ = api.inquire_balance(
                self.trenv.my_acct, 
                self.trenv.my_prod, 
                self.exchange, 
                self.currency
            )
            if df1 is not None and not df1.empty:
                for _, r in df1.iterrows():
                    out.append({
                        'symbol': r['ovrs_pdno'],
                        'qty': int(float(r['ovrs_cblc_qty'])),
                        'avg_price': float(r['pchs_avg_pric']),
                        'current_price': float(r.get('now_pric2', 0))
                    })
        except:
            pass
        return out
