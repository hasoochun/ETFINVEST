@echo off
REM Upload modified files to AWS server

echo Uploading files to AWS server...

REM Set variables
set LOCAL_DIR=c:\Users\user\.gemini\antigravity\scratch\open-trading-api\infinite_buying_bot
set REMOTE_USER=ubuntu
set REMOTE_HOST=YOUR_SERVER_IP
set REMOTE_DIR=/home/ubuntu/trading-bot/infinite_buying_bot

REM Upload files
echo Uploading bot_controller.py...
scp "%LOCAL_DIR%\api\bot_controller.py" %REMOTE_USER%@%REMOTE_HOST%:%REMOTE_DIR%/api/

echo Uploading rebalancing_engine.py...
scp "%LOCAL_DIR%\core\rebalancing_engine.py" %REMOTE_USER%@%REMOTE_HOST%:%REMOTE_DIR%/core/

echo Uploading main_portfolio.py...
scp "%LOCAL_DIR%\main_portfolio.py" %REMOTE_USER%@%REMOTE_HOST%:%REMOTE_DIR%/

echo.
echo Upload complete!
echo.
echo Next steps:
echo 1. SSH to server: ssh %REMOTE_USER%@%REMOTE_HOST%
echo 2. Restart bot: cd %REMOTE_DIR% ^&^& python3 main_portfolio.py --accelerated
pause
