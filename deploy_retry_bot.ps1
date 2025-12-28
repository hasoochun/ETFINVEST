$ErrorActionPreference = "Stop"

# Configuration
$ServerIP = "3.104.117.219"
$User = "ubuntu"
$KeyPath = "aws_key.pem"
$RemoteHome = "/home/ubuntu"

Write-Host "🚀 Starting Retry Deployment for Bot..."

# 1. Zip open-trading-api (Excluding .git)
Write-Host "📦 Zipping open-trading-api..."
if (Test-Path "bot_deploy.zip") { Remove-Item "bot_deploy.zip" }
# Compressing contents of current folder
Get-ChildItem -Exclude ".git", ".venv", "venv", "__pycache__" | Compress-Archive -DestinationPath "bot_deploy.zip"

# 2. Upload Zip
Write-Host "📤 Uploading bot_deploy.zip..."
scp -o StrictHostKeyChecking=no -i $KeyPath bot_deploy.zip "${User}@${ServerIP}:${RemoteHome}/"

# 3. Remote Setup
Write-Host "🔧 Remote Setup & Restart..."

$RemoteScript = @"
set -e
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv unzip

# Clean old bot folder (safely)
# Setup directory
mkdir -p $RemoteHome/open-trading-api
cd $RemoteHome

# Unzip
echo "Unzipping..."
unzip -o bot_deploy.zip -d open-trading-api

# Dashboard Setup (Quick check)
cd $RemoteHome/us-stockanalysis
if [ ! -d "venv" ]; then python3 -m venv venv; fi
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn Flask-Login
# Reject SIGHUP to keep running
nohup gunicorn -w 2 -b 0.0.0.0:8000 flask_app:app > dashboard.log 2>&1 &

# Bot Setup
cd $RemoteHome/open-trading-api
pip install -r requirements.txt

# Start Bot
echo "Starting Bot..."
# Kill old if exists
pkill -f main_portfolio.py || true
nohup python3 infinite_buying_bot/main_portfolio.py > bot.log 2>&1 &

echo "✅ Deployment Success!"
ps aux | grep python
"@

ssh -o StrictHostKeyChecking=no -i $KeyPath "${User}@${ServerIP}" "$RemoteScript"

Write-Host "🎉 Retry Complete!"
