$ErrorActionPreference = "Stop"

# Configuration
$ServerIP = "3.104.117.219"
$User = "ubuntu"
$KeyPath = "aws_key.pem"
$RemoteHome = "/home/ubuntu"

Write-Host "🚀 Starting Deployment (Script Strategy)..."

# 1. Zip
Write-Host "📦 Zipping..."
if (Test-Path "bot_deploy.zip") { Remove-Item "bot_deploy.zip" }
Get-ChildItem -Exclude ".git", ".venv", "venv", "__pycache__" | Compress-Archive -DestinationPath "bot_deploy.zip"

# 2. Create Setup Script
$SetupScript = @"
#!/bin/bash
set -e

echo "🔧 Starting Remote Setup..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv unzip

# Unzip Bot
mkdir -p $RemoteHome/open-trading-api
cd $RemoteHome
unzip -o bot_deploy.zip -d open-trading-api

# Dashboard Setup
cd $RemoteHome/us-stockanalysis
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install gunicorn Flask-Login
pkill -f flask_app.py || true
nohup ./venv/bin/gunicorn -w 2 -b 0.0.0.0:8000 flask_app:app > dashboard.log 2>&1 &

# Bot Setup
cd $RemoteHome/open-trading-api
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
pkill -f main_portfolio.py || true
# Use explicit python3 from venv or system
# If bot needs system site packages (apt), use system python? No, use venv.
nohup ./venv/bin/python infinite_buying_bot/main_portfolio.py > bot.log 2>&1 &

echo "✅ All Services Started!"
ps aux | grep python
"@

Set-Content -Path "setup.sh" -Value $SetupScript -Encoding Ascii

# 3. Upload Files
Write-Host "📤 Uploading Zip and Script..."
scp -o StrictHostKeyChecking=no -i $KeyPath bot_deploy.zip setup.sh "${User}@${ServerIP}:${RemoteHome}/"

# 4. Execute Script (Fix Line Endings)
Write-Host "▶️ Executing Remote Script..."
ssh -o StrictHostKeyChecking=no -i $KeyPath "${User}@${ServerIP}" "sed -i 's/\r$//' setup.sh && chmod +x setup.sh && bash setup.sh"

Write-Host "🎉 Done!"
