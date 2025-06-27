#!/usr/bin/env python3
"""
Batch sync users_data.json to Cloudflare KV
"""
import os
import json
import requests
from pathlib import Path

# Load environment variables
CF_API_TOKEN = os.getenv('CF_API_TOKEN')
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_KV_NAMESPACE_ID = os.getenv('CF_KV_NAMESPACE_ID')

if not all([CF_API_TOKEN, CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID]):
    print("❌ Missing environment variables!")
    exit(1)

# API endpoint for bulk write
API_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/storage/kv/namespaces/{CF_KV_NAMESPACE_ID}/bulk"

# Headers
headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

# Load users data
users_file = Path(__file__).parent.parent / "users_data.json"
with open(users_file, 'r') as f:
    users_data = json.load(f)

print(f"🔄 Batch syncing {len(users_data)} users to Cloudflare KV...")

# Prepare bulk data
bulk_data = []
for username, user_data in users_data.items():
    bulk_data.append({
        "key": username,
        "value": json.dumps(user_data)
    })

# Split into chunks of 100 (Cloudflare limit)
chunk_size = 100
for i in range(0, len(bulk_data), chunk_size):
    chunk = bulk_data[i:i + chunk_size]
    print(f"📦 Uploading batch {i//chunk_size + 1} ({len(chunk)} users)...")
    
    response = requests.put(
        API_BASE,
        headers=headers,
        json=chunk
    )
    
    if response.status_code == 200:
        print(f"✅ Batch {i//chunk_size + 1} complete")
    else:
        print(f"❌ Batch {i//chunk_size + 1} failed: {response.status_code}")

print(f"✅ Sync complete! {len(users_data)} users uploaded to Cloudflare KV")