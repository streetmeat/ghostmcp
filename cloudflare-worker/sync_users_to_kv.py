#!/usr/bin/env python3
"""
Sync users_data.json to Cloudflare KV
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
    print("Set: CF_API_TOKEN, CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID")
    exit(1)

# API endpoint
API_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/storage/kv/namespaces/{CF_KV_NAMESPACE_ID}"

# Headers
headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

# Load users data
users_file = Path(__file__).parent.parent / "users_data.json"
with open(users_file, 'r') as f:
    users_data = json.load(f)

print(f"🔄 Syncing {len(users_data)} users to Cloudflare KV...")
print("=" * 50)

success_count = 0
error_count = 0

# Sync each user
for username, user_data in users_data.items():
    try:
        # Prepare the data
        kv_data = {
            "username": user_data.get("username", username),
            "user_id": user_data.get("user_id"),
            "followers": user_data.get("followers"),
            "following": user_data.get("following"),
            "posts_count": user_data.get("posts_count"),
            "avg_engagement": user_data.get("avg_engagement"),
            "full_name": user_data.get("full_name"),
            "biography": user_data.get("biography"),
            "video": user_data.get("video"),
            "video_sent": user_data.get("video_sent"),
            "sent_at": user_data.get("sent_at"),
            "campaign_id": user_data.get("campaign_id"),
            "clicked": user_data.get("clicked", False)
        }
        
        # Make API request
        response = requests.put(
            f"{API_BASE}/values/{username}",
            headers=headers,
            json=kv_data
        )
        
        if response.status_code == 200:
            success_count += 1
            print(f"✅ {username}")
        else:
            error_count += 1
            print(f"❌ {username}: {response.status_code} - {response.text}")
            
    except Exception as e:
        error_count += 1
        print(f"❌ {username}: Error - {str(e)}")

print("=" * 50)
print(f"✅ Successfully synced: {success_count} users")
if error_count > 0:
    print(f"❌ Errors: {error_count} users")
print(f"📊 Total: {len(users_data)} users")