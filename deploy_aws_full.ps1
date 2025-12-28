$ErrorActionPreference = "Stop"

# Configuration
$ServerIP = "3.104.117.219"
$User = "ubuntu"
$KeyPath = "aws_key.pem"
$RemoteHome = "/home/ubuntu"

Write-Host "🚀 Starting Full Deployment to $ServerIP..."

# 1. Stop Existing Services (Explicit arguments)
Write-Host "🛑 Stopping existing services..."
ssh -o StrictHostKeyChecking=no -i $KeyPath "${User}@${ServerIP}" "pkill -f flask_app.py; pkill -f main_portfolio.py; pkill -f streamlit; echo Services Stopped"

# 2. Upload us-stockanalysis
Write-Host "📦 Uploading Dashboard (us-stockanalysis)..."
scp -o StrictHostKeyChecking=no -i $KeyPath -r ../us-stockanalysis "${User}@${ServerIP}:${RemoteHome}/"

# 3. Upload open-trading-api
Write-Host "📦 Uploading Bot Core (open-trading-api)..."
scp -o StrictHostKeyChecking=no -i $KeyPath -r . "${User}@${ServerIP}:${RemoteHome}/open-trading-api"

# 4. Setup and Start (Remote Execution)
Write-Host "🔧 Setting up and Starting services..."

$RemoteScript = @"
set -e
# Update and Install Deps
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv

# Setup Dashboard
cd $RemoteHome/us-stockanalysis
if [ ! -d "venv" ]; then python3 -m venv venv; fi
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn Flask-Login

# Start Dashboard
echo "Starting Dashboard..."
nohup gunicorn -w 2 -b 0.0.0.0:8000 flask_app:app > dashboard.log 2>&1 &

# Setup Bot
cd $RemoteHome/open-trading-api
pip install -r requirements.txt

# Start Bot
echo "Starting Bot..."
# Use python3 explicit logic
nohup python3 infinite_buying_bot/main_portfolio.py > bot.log 2>&1 &

echo "✅ All Services Started!"
ps aux | grep python
"@

# Execute remote script
ssh -o StrictHostKeyChecking=no -i $KeyPath "${User}@${ServerIP}" "$RemoteScript"

Write-Host "🎉 Deployment Complete! Access at http://${ServerIP}:8000"
