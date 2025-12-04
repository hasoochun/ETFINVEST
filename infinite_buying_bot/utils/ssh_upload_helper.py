import base64
import sys
import os

def generate_upload_commands(local_path, remote_path):
    """
    Generates a list of shell commands to upload a file via SSH MCP
    using Base64 encoding and chunking to avoid length limits.
    """
    try:
        with open(local_path, 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        return [f"# Error: File not found: {local_path}"]

    # Encode to Base64
    b64_content = base64.b64encode(content).decode('utf-8')
    
    # Chunk size (safe margin below 1000 chars, considering command overhead)
    # echo -n '...' >> /path/to/file.b64
    CHUNK_SIZE = 500 
    chunks = [b64_content[i:i+CHUNK_SIZE] for i in range(0, len(b64_content), CHUNK_SIZE)]
    
    commands = []
    temp_file = f"/tmp/{os.path.basename(remote_path)}.b64"
    
    # 1. Initialize temp file
    commands.append(f"echo -n '' > {temp_file}")
    
    # 2. Append chunks
    for i, chunk in enumerate(chunks):
        commands.append(f"echo -n '{chunk}' >> {temp_file}")
        
    # 3. Decode and move to final destination
    # Ensure directory exists
    remote_dir = os.path.dirname(remote_path)
    if remote_dir and remote_dir != ".":
        commands.append(f"mkdir -p {remote_dir}")
        
    commands.append(f"base64 -d {temp_file} > {remote_path}")
    
    # 4. Cleanup
    commands.append(f"rm {temp_file}")
    
    return commands

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ssh_upload_helper.py <local_path> <remote_path>")
        sys.exit(1)
        
    local_path = sys.argv[1]
    remote_path = sys.argv[2]
    
    cmds = generate_upload_commands(local_path, remote_path)
    
    print(f"# Commands to upload {local_path} to {remote_path}")
    print(f"# Total chunks: {len(cmds) - 3}") # Subtract init, decode, cleanup
    for cmd in cmds:
        print(cmd)
