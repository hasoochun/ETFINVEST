def format_status(data):
    return (
        f"🤖 **BOT STATUS**\n"
        f"State: `{data.get('status')}`\n"
        f"Mode: `{data.get('mode')}`\n"
        f"Symbol: `{data.get('trading_symbol')}`"
    )

def format_balance(data):
    return (
        f"💰 **BALANCE (REAL)**\n"
        f"Cash: `${data.get('cash'):,.2f}`\n"
        f"Stock Value: `${data.get('stock_val'):,.2f}`\n"
        f"Total: `${data.get('total'):,.2f}`\n"
        f"Qty: `{data.get('qty')}`\n"
        f"Avg Price: `${data.get('avg_price'):,.2f}`"
    )
