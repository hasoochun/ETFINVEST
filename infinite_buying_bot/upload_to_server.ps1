# Upload modified files to AWS server using SCP

$SERVER_IP = Read-Host "Enter server IP address"
$KEY_FILE = Read-Host "Enter path to SSH key file (or press Enter if using default)"

$LOCAL_DIR = "c:\Users\user\.gemini\antigravity\scratch\open-trading-api\infinite_buying_bot"
$REMOTE_USER = "ubuntu"
$REMOTE_DIR = "/home/ubuntu/trading-bot/infinite_buying_bot"

Write-Host "`nUploading files to server..." -ForegroundColor Green

# Build SCP command
if ($KEY_FILE) {
    $scpBaseCmd = "scp -i `"$KEY_FILE`""
} else {
    $scpBaseCmd = "scp"
}

# Upload bot_controller.py
Write-Host "`n1. Uploading bot_controller.py..." -ForegroundColor Yellow
$cmd = "$scpBaseCmd `"$LOCAL_DIR\api\bot_controller.py`" ${REMOTE_USER}@${SERVER_IP}:${REMOTE_DIR}/api/"
Invoke-Expression $cmd
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ bot_controller.py uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "   ✗ Failed to upload bot_controller.py" -ForegroundColor Red
}

# Upload rebalancing_engine.py
Write-Host "`n2. Uploading rebalancing_engine.py..." -ForegroundColor Yellow
$cmd = "$scpBaseCmd `"$LOCAL_DIR\core\rebalancing_engine.py`" ${REMOTE_USER}@${SERVER_IP}:${REMOTE_DIR}/core/"
Invoke-Expression $cmd
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ rebalancing_engine.py uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "   ✗ Failed to upload rebalancing_engine.py" -ForegroundColor Red
}

# Upload main_portfolio.py
Write-Host "`n3. Uploading main_portfolio.py..." -ForegroundColor Yellow
$cmd = "$scpBaseCmd `"$LOCAL_DIR\main_portfolio.py`" ${REMOTE_USER}@${SERVER_IP}:${REMOTE_DIR}/"
Invoke-Expression $cmd
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ main_portfolio.py uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "   ✗ Failed to upload main_portfolio.py" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Upload complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. SSH to server: ssh ${REMOTE_USER}@${SERVER_IP}"
Write-Host "2. Navigate to directory: cd ${REMOTE_DIR}"
Write-Host "3. Stop running bot (if any): pkill -f main_portfolio"
Write-Host "4. Start accelerated mode: python3 main_portfolio.py --accelerated"
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
