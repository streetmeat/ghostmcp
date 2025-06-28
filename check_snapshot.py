#!/usr/bin/env python3
import time
import subprocess
import json

snapshot_id = "snap_mcfmi4d12bad43358"
attempt = 0
max_attempts = 30  # 30 minutes max

print(f"Monitoring snapshot {snapshot_id}...")
print("Will check every minute for up to 30 minutes...")

while attempt < max_attempts:
    attempt += 1
    print(f"\nAttempt {attempt}/{max_attempts} at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Use the MCP tool via Python
    result = subprocess.run([
        'python', '-c', 
        f'''
import sys
sys.path.append("/home/streetmeat/ghost/ghost_mcp/src")
from mcp_server import download_bright_data_snapshot
result = download_bright_data_snapshot("{snapshot_id}")
print(json.dumps(result))
'''
    ], capture_output=True, text=True, cwd="/home/streetmeat/ghost")
    
    try:
        response = json.loads(result.stdout)
        if response.get("success"):
            print(f"\n✓ Snapshot ready! Downloaded to: {response.get('raw_file', 'N/A')}")
            print(f"Filtered file: {response.get('filtered_file', 'N/A')}")
            print(f"Total users: {response.get('total_users', 0)}")
            print(f"Filtered users: {response.get('filtered_users', 0)}")
            break
        else:
            print(f"Status: {response.get('status', 'unknown')} - {response.get('message', 'Waiting...')}")
    except:
        print(f"Error checking status: {result.stderr}")
    
    if attempt < max_attempts:
        time.sleep(60)  # Wait 1 minute
    
if attempt >= max_attempts:
    print("\n✗ Timeout: Snapshot did not complete within 30 minutes")