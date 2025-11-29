# Telegram Bot Setup Guide

## 🚀 Quick Start

### 1. Install Dependencies

Already installed! ✅
- python-telegram-bot==21.9
- matplotlib==3.9.0
- pillow==11.0.0

### 2. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a name for your bot (e.g., "My Trading Bot")
   - Choose a username (must end in 'bot', e.g., "mytrading_bot")
4. Copy the **API Token** you receive

### 3. Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Send `/start` to the bot
3. Copy your **Chat ID** (it's a number)

### 4. Configure Environment Variables

Add these lines to your `.env` file:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Replace `your_bot_token_here` and `your_chat_id_here` with the values from steps 2 and 3.

### 5. Run the Bot

```bash
cd infinite_buying_bot
python main_telegram.py
```

### 6. Start Using

1. Open Telegram
2. Find your bot
3. Send `/start` to begin
4. Use `/help` to see all commands

---

## 📱 Available Commands

### Status Commands
- `/start` - Welcome message
- `/status` - Bot status with interactive buttons
- `/balance` - Account balance
- `/position` - Current position
- `/pnl` - Profit & Loss

### Control Commands
- `/stopentry` - Stop new entries (keep existing positions)
- `/forceexit` - Force exit all positions (with confirmation)
- `/emergency` - Emergency stop (with confirmation)

### Info Commands
- `/help` - Show all commands
- `/ping` - Check bot response

---

## 🎨 Features

### ✅ Interactive Buttons
Status messages include buttons for quick actions:
- 🔄 Refresh
- 💰 Balance
- 📈 Position
- 📊 Chart (coming soon)

### ✅ Real-time Notifications
Automatic notifications for:
- 🟢 Buy orders filled
- 🔴 Sell orders filled
- 🎉 Profit target reached
- ⚠️ Errors
- 🚀 Bot started/stopped
- 🟢🔴 Market open/closed

### ✅ Security
- Chat ID whitelist
- Confirmation dialogs for dangerous actions
- Unauthorized access logging

---

## 🔐 Security Best Practices

1. **Never share your bot token**
2. **Keep your chat ID private**
3. **Don't add your bot to public groups**
4. **Revoke and regenerate tokens if compromised**

---

## 🐛 Troubleshooting

### Bot doesn't respond
- Check if `main_telegram.py` is running
- Verify bot token is correct
- Verify chat ID is correct

### "Unauthorized access" message
- Make sure your chat ID is in the `.env` file
- Chat ID should be a number (no quotes in .env)

### Import errors
- Make sure you're in the `infinite_buying_bot` directory
- Check that all packages are installed

---

## 📝 Example .env File

```env
# Korea Investment Securities API Credentials
KIS_APP_KEY_PROD="PSJgF4Y36sCVBmQF4z671Jd5Vf6tGlmB53MY"
KIS_APP_SECRET_PROD="EeU80V2/UUBhNDErGUpcZYX2LkAJX3Bw9yh2uZwd3OPgTHu57EIopa64QY2H8haRVZ2Hf/M9CSPoKR"
KIS_ACCT_PROD="43430971"

KIS_APP_KEY_PAPER="PSJgF4Y36sCVBmQF4z671Jd5Vf6tGlmB53MY"
KIS_APP_SECRET_PAPER="EeU80V2/UUBhNDErGUpcZYX2LkAJX3Bw9yh2uZwd3OPgTHu57EIopa64QY2H8haRVZ2Hf/M9CSPoKR"
KIS_ACCT_PAPER="50157068"

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Notification Settings (Optional)
DISCORD_WEBHOOK_URL=
```

---

## 🎉 You're All Set!

Your trading bot now has Telegram integration! 🚀

Send `/start` to your bot to begin using it.
