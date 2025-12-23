class InfiniteBuyingStrategy:
    def __init__(self, config):
        self.symbol = config.get('strategy', {}).get('symbol', 'SOXL')
        self.exchange = config.get('strategy', {}).get('exchange', 'NASD')
        self.profit_target_pct = config.get('strategy', {}).get('profit_target_pct', 10.0)
        self.split_count_low = config.get('strategy', {}).get('split_count_low', 80)
        self.split_count_high = config.get('strategy', {}).get('split_count_high', 40)

    def should_buy(self, current_price, avg_price, quantity, is_near_close, force_buy=False):
        """
        Determine if we should buy and how much (split count).
        Returns: (should_buy, split_count)
        
        Args:
            force_buy: If True, bypass time check (for accelerated mode)
        """
        if not is_near_close and not force_buy:
            return False, 0

        # If we have no holdings, treat as "Price < Avg" (Aggressive 40 splits) or "Initial Entry"
        # Strategy says: Initial entry 1/40.
        if quantity == 0:
            return True, self.split_count_high

        if current_price < avg_price:
            return True, self.split_count_high
        else:
            return True, self.split_count_low

    def should_sell(self, current_price, avg_price, quantity):
        """
        Determine if we should sell (Profit Taking).
        Returns: should_sell
        """
        if quantity == 0 or avg_price == 0:
            return False

        profit_pct = ((current_price - avg_price) / avg_price) * 100
        return profit_pct >= self.profit_target_pct
