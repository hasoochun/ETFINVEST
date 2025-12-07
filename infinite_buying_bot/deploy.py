"""
Automated deployment script for uploading files to AWS server
Reads configuration from .env file
"""

import os
import subprocess
from pathlib import Path

# Manually parse .env file to handle different formats
def load_env_manually(env_path):
    """Manually parse .env file, handling multiline values"""
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            i += 1
            continue
            
        # Handle lines with =
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            # Check if this is a multiline value (starts with -----)
            if value.startswith('-----'):
                # Collect all lines until we find the END marker
                multiline_value = [value]
                i += 1
                while i < len(lines):
                    next_line = lines[i].rstrip()
                    multiline_value.append(next_line)
                    if 'END' in next_line and '-----' in next_line:
                        break
                    i += 1
                value = '\n'.join(multiline_value)
            
            env_vars[key] = value
        
        i += 1
    
    return env_vars

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
env_vars = load_env_manually(env_path)

# Get configuration from .env
# For SSH key, if it's a multiline RSA key, we'll write it to a temp file
# Or if it's a path, we'll use it directly
ssh_key_value = env_vars.get('SSH_key') or env_vars.get('SSH key', '')

# Check if it's a file path or actual key content
if ssh_key_value.startswith('-----BEGIN'):
    # It's actual key content - write to temp file
    import tempfile
    temp_key = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
    temp_key.write(ssh_key_value)
    temp_key.close()
    os.chmod(temp_key.name, 0o600)  # Set proper permissions
    SSH_KEY = temp_key.name
else:
    # It's a file path
    SSH_KEY = ssh_key_value or 'C:\\Users\\user\\Desktop\\myetfbot.pem'  # Fallback

SERVER_IP = env_vars.get('server_ip') or env_vars.get('server ip')
SERVER_USER = env_vars.get('SERVER_USER', 'ubuntu')  # Default to ubuntu if not set
SERVER_PATH = env_vars.get('SERVER_PATH', '/home/ubuntu/trading-bot/infinite_buying_bot')
SERVER_USER = os.getenv('SERVER_USER', 'ubuntu')  # Default to ubuntu if not set
SERVER_PATH = os.getenv('SERVER_PATH', '/home/ubuntu/trading-bot/infinite_buying_bot')

# Files to upload
FILES_TO_UPLOAD = [
    ('api/bot_controller.py', 'api/'),
    ('core/rebalancing_engine.py', 'core/'),
    ('core/trader.py', 'core/'),  # Added for debugging
    ('main_portfolio.py', ''),
]

def upload_file(local_path, remote_subpath):
    """Upload a single file to the server using SCP"""
    remote_path = f"{SERVER_PATH}/{remote_subpath}"
    
    # Build SCP command
    cmd = [
        'scp',
        '-i', SSH_KEY,
        local_path,
        f"{SERVER_USER}@{SERVER_IP}:{remote_path}"
    ]
    
    print(f"📤 Uploading {local_path}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"   ✅ Success: {local_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {local_path}")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Main deployment function"""
    print("=" * 60)
    print("🚀 Starting deployment to AWS server")
    print("=" * 60)
    print(f"Server: {SERVER_IP}")
    print(f"SSH Key: {SSH_KEY}")
    print(f"Target Path: {SERVER_PATH}")
    print("=" * 60)
    
    # Validate configuration
    if not SSH_KEY or not SERVER_IP:
        print("❌ Error: SSH_key or server_ip not found in .env file")
        return False
    
    if not os.path.exists(SSH_KEY):
        print(f"❌ Error: SSH key file not found: {SSH_KEY}")
        return False
    
    # Change to infinite_buying_bot directory
    os.chdir(Path(__file__).parent)
    
    # Upload all files
    success_count = 0
    for local_path, remote_subpath in FILES_TO_UPLOAD:
        if upload_file(local_path, remote_subpath):
            success_count += 1
    
    # Summary
    print("=" * 60)
    print(f"✅ Successfully uploaded: {success_count}/{len(FILES_TO_UPLOAD)} files")
    print("=" * 60)
    
    if success_count == len(FILES_TO_UPLOAD):
        print("\n🎉 Deployment complete!")
        print("\n📝 Next steps:")
        print(f"   1. SSH to server: ssh -i {SSH_KEY} {SERVER_USER}@{SERVER_IP}")
        print(f"   2. Stop bot: pkill -f main_portfolio")
        print(f"   3. Start accelerated mode: cd {SERVER_PATH} && python3 main_portfolio.py --accelerated")
        return True
    else:
        print("\n⚠️ Some files failed to upload. Please check errors above.")
        return False

if __name__ == "__main__":
    main()
