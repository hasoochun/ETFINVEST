import logging
import time
from infinite_buying_bot.api import kis_api as api
from infinite_buying_bot.api import kis_auth as ka

logger = logging.getLogger(__name__)

class Trader:
    def __init__(self, config, notifier):
        self.config = config
        self.notifier = notifier
        self.env_mode = "demo" # Default to demo, user should change in main or config
        
        # Load Account Info
        self.svr = 'vps' if self.env_mode == 'demo' else 'prod'
        self.product = config.get('my_prod', '01')
        
        # Authenticate
        ka.auth(svr=self.svr, product=self.product)
        self.trenv = ka.getTREnv()
        
        self.symbol = config.get('strategy', {}).get('symbol', 'SOXL')
        self.exchange = config.get('strategy', {}).get('exchange', 'NASD')
        self.currency = config.get('strategy', {}).get('currency', 'USD')

    def get_price(self):
        df = api.price(auth="", excd=self.exchange, symb=self.symbol, env_dv=self.env_mode)
        if not df.empty:
            return self._safe_float(df['last'].iloc[0])
        return None

    def _safe_float(self, value):
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, value):
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    def get_balance(self):
        """Returns (buying_power, quantity, avg_price)"""
        df1, df2 = api.inquire_balance(
            cano=self.trenv.my_acct, 
            acnt_prdt_cd=self.trenv.my_prod, 
            ovrs_excg_cd=self.exchange, 
            tr_crcy_cd=self.currency,
            env_dv=self.env_mode
        )
        
        buying_power = 0.0
        quantity = 0
        avg_price = 0.0
        
        if not df1.empty:
            # DEBUG: Log available columns and first row to find correct balance field
            print(f"DEBUG: Balance DF1 Columns: {df1.columns.tolist()}")
            try:
                print(f"DEBUG: Balance DF1 Row 0: {df1.iloc[0].to_dict()}")
            except Exception as e:
                print(f"DEBUG: Failed to log DF1 row: {e}")
            
            # Try to find buying power column (varies by API version/account)
            # Common: frcr_ord_psbl_amt1 (Foreign Currency Order Possible Amount)
            # Also check: dnca_tot_amt (Deposit Total Amount), tot_evlu_amt (Total Evaluation Amount)
            if 'frcr_ord_psbl_amt1' in df1.columns:
                buying_power = self._safe_float(df1['frcr_ord_psbl_amt1'].iloc[0])
            elif 'ovrs_ord_psbl_amt' in df1.columns:
                buying_power = self._safe_float(df1['ovrs_ord_psbl_amt'].iloc[0])
            elif 'dnca_tot_amt' in df1.columns:
                buying_power = self._safe_float(df1['dnca_tot_amt'].iloc[0])
            elif 'nxdy_excc_amt' in df1.columns:
                buying_power = self._safe_float(df1['nxdy_excc_amt'].iloc[0])
            elif 'tot_evlu_amt' in df1.columns:
                buying_power = self._safe_float(df1['tot_evlu_amt'].iloc[0])
        else:
            print("DEBUG: Balance DF1 is EMPTY - API returned no data for output1")
                
        if not df2.empty:
            target = df2[df2['ovrs_pdno'] == self.symbol]
            if not target.empty:
                quantity = self._safe_int(target['ovrs_cblc_qty'].iloc[0])
                avg_price = self._safe_float(target['pchs_avg_pric'].iloc[0])
                
        return buying_power, quantity, avg_price

    def buy(self, amount, split_count=None, reason=None):
        """Execute buy order with detailed notifications
        
        Args:
            amount: Dollar amount to buy
            split_count: Split count for strategy (e.g., 40 or 80)
            reason: Reason for buying (e.g., 'Initial Entry', 'Below Average')
        """
        current_price = self.get_price()
        if not current_price:
            error_msg = "❌ Cannot buy: Failed to get current price"
            logger.error(error_msg)
            self.notifier.send(error_msg)
            return

        qty = int(amount // current_price)
        if qty <= 0:
            logger.info(f"Buy amount ${amount:.2f} is too small for price ${current_price}")
            return

        # Get current position before buy
        _, old_qty, old_avg = self.get_balance()
        
        logger.info(f"🟢 Executing BUY: {qty} shares of {self.symbol} @ ${current_price:.2f}")
        
        # Send pre-trade notification
        pre_msg = (
            f"🟢 **BUY ORDER SUBMITTED**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Symbol:      `{self.symbol}`\n"
            f"Quantity:    `{qty} shares`\n"
            f"Price:       `${current_price:.2f}`\n"
            f"Amount:      `${amount:.2f}`\n"
        )
        if split_count:
            pre_msg += f"Split:       `1/{split_count}`\n"
        if reason:
            pre_msg += f"Reason:      `{reason}`\n"
        pre_msg += f"━━━━━━━━━━━━━━━━━━━━"
        
        self.notifier.send(pre_msg)
        
        # Execute order
        res = api.order(
            order_dv="buy",
            cano=self.trenv.my_acct,
            acnt_prdt_cd=self.trenv.my_prod,
            ovrs_excg_cd=self.exchange,
            pdno=self.symbol,
            ord_qty=str(qty),
            ovrs_ord_unpr="0", # Market
            ord_dvsn="00",
            env_dv=self.env_mode
        )
        
        # Wait a moment for order to settle
        time.sleep(2)
        
        if not res.empty:
            # Get updated position
            _, new_qty, new_avg = self.get_balance()
            
            # Send success notification with position update
            success_msg = (
                f"✅ **BUY ORDER FILLED**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Executed:    `{qty} shares @ ${current_price:.2f}`\n"
                f"Total Cost:  `${qty * current_price:.2f}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"**Position Update:**\n"
                f"Before:      `{old_qty} shares @ ${old_avg:.2f}`\n"
                f"After:       `{new_qty} shares @ ${new_avg:.2f}`\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            logger.info(f"✅ BUY ORDER FILLED: {qty} shares")
            self.notifier.send(success_msg)
        else:
            error_msg = f"❌ **BUY ORDER FAILED** for {self.symbol}"
            logger.error(error_msg)
            self.notifier.send(error_msg)

    def sell_all(self, quantity, reason=None):
        """Execute sell all order with detailed notifications
        
        Args:
            quantity: Number of shares to sell
            reason: Reason for selling (e.g., 'Profit Target 10%')
        """
        current_price = self.get_price()
        if not current_price:
            error_msg = "❌ Cannot sell: Failed to get current price"
            logger.error(error_msg)
            self.notifier.send(error_msg)
            return
        
        # Get current position
        _, _, avg_price = self.get_balance()
        
        # Calculate P&L
        total_value = quantity * current_price
        total_cost = quantity * avg_price if avg_price > 0 else 0
        pnl = total_value - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0
        
        logger.info(f"🔴 Executing SELL: {quantity} shares of {self.symbol} @ ${current_price:.2f}")
        
        # Send pre-trade notification
        pre_msg = (
            f"🔴 **SELL ORDER SUBMITTED**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Symbol:      `{self.symbol}`\n"
            f"Quantity:    `{quantity} shares (ALL)`\n"
            f"Avg Price:   `${avg_price:.2f}`\n"
            f"Sell Price:  `${current_price:.2f}`\n"
        )
        if reason:
            pre_msg += f"Reason:      `{reason}`\n"
        pre_msg += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Expected P&L: `${pnl:+,.2f} ({pnl_pct:+.2f}%)`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        self.notifier.send(pre_msg)
        
        # Execute order
        res = api.order(
            order_dv="sell",
            cano=self.trenv.my_acct,
            acnt_prdt_cd=self.trenv.my_prod,
            ovrs_excg_cd=self.exchange,
            pdno=self.symbol,
            ord_qty=str(quantity),
            ovrs_ord_unpr="0", # Market
            ord_dvsn="00",
            env_dv=self.env_mode
        )
        
        # Wait a moment for order to settle
        time.sleep(2)
        
        if not res.empty:
            # Send success notification
            success_msg = (
                f"✅ **SELL ORDER FILLED**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Sold:        `{quantity} shares @ ${current_price:.2f}`\n"
                f"Total Value: `${total_value:,.2f}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"**Realized P&L:**\n"
                f"Profit:      `${pnl:+,.2f} ({pnl_pct:+.2f}%)`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔄 Position closed - Strategy reset\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            logger.info(f"✅ SELL ORDER FILLED: {quantity} shares")
            self.notifier.send(success_msg)
        else:
            error_msg = f"❌ **SELL ORDER FAILED** for {self.symbol}"
            logger.error(error_msg)
            self.notifier.send(error_msg)
