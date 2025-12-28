#!/bin/bash
set -e

echo "?? Starting Remote Setup..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv unzip

# Unzip Bot
mkdir -p /home/ubuntu/open-trading-api
cd /home/ubuntu
unzip -o bot_deploy.zip -d open-trading-api

# Dashboard Setup
cd /home/ubuntu/us-stockanalysis
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install gunicorn Flask-Login
pkill -f flask_app.py || true
nohup ./venv/bin/gunicorn -w 2 -b 0.0.0.0:8000 flask_app:app > dashboard.log 2>&1 &

# Bot Setup
cd /home/ubuntu/open-trading-api
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
pkill -f main_portfolio.py || true
# Use explicit python3 from venv or system
# If bot needs system site packages (apt), use system python? No, use venv.
nohup ./venv/bin/python infinite_buying_bot/main_portfolio.py > bot.log 2>&1 &

echo "??All Services Started!"
ps aux | grep python
