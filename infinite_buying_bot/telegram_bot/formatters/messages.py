def format_trade_notification(trade_type, data):
    return (
        f"🔔 **TRADE EXECUTION**\n"
        f"Type: {trade_type}\n"
        f"Symbol: {data.get('symbol')}\n"
        f"Qty: {data.get('qty')}\n"
        f"Price: ${data.get('price')}\n"
        f"Amount: ${data.get('amount', 0):.2f}"
    )

def format_profit_target_notification(data):
    return (
        f"💰 **PROFIT TARGET REACHED**\n"
        f"Symbol: {data.get('symbol')}\n"
        f"Profit: ${data.get('profit', 0):.2f}"
    )

def format_error_notification(error):
    return f"⚠️ **ERROR OCCURRED**\n{error}"
