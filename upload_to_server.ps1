$ErrorActionPreference = "Stop"

# Configuration
$ServerIP = "3.104.117.219"
$User = "ubuntu"
$KeyPath = "aws_key.pem"
$RemotePath = "/home/ubuntu/infinite_buying_bot"

Write-Host "🚀 Starting Selective Deployment to $ServerIP..."

# 1. Create remote directory if not exists
Write-Host "Checking remote directory..."
ssh -o StrictHostKeyChecking=no -i $KeyPath "$User@$ServerIP" "mkdir -p $RemotePath"

# 2. Upload Essential Files Only
Write-Host "Uploading 'infinite_buying_bot' folder..."
$Dest = "${User}@${ServerIP}:${RemotePath}"

# Upload main package
scp -o StrictHostKeyChecking=no -i $KeyPath -r ./infinite_buying_bot "$Dest"

# Upload config and env files
Write-Host "Uploading config files (.env, yaml, requirements)..."
scp -o StrictHostKeyChecking=no -i $KeyPath .env kis_devlp.yaml requirements.txt "$Dest"

# Upload simple_auth_test for verification if needed (Optional)
# scp -o StrictHostKeyChecking=no -i $KeyPath simple_auth_test.py "$Dest"

Write-Host "✅ Selective Deployment Complete!"
