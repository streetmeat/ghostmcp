#!/usr/bin/env python3
"""
Sync campaign data from MCP to Cloudflare Workers KV
"""

import json
import requests
import os
from pathlib import Path
from datetime import datetime

# Cloudflare configuration
CF_API_TOKEN = os.getenv('CF_API_TOKEN', '')  # Create at dash.cloudflare.com/profile/api-tokens
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID', '')  # Found in Cloudflare dashboard
CF_KV_NAMESPACE_ID = os.getenv('CF_KV_NAMESPACE_ID', '')  # From wrangler kv:namespace list

def sync_user_to_cloudflare(url_key, user_data):
    """Push user data to Cloudflare Workers KV"""
    
    if not all([CF_API_TOKEN, CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID]):
        print("Error: Missing Cloudflare credentials. Set CF_API_TOKEN, CF_ACCOUNT_ID, and CF_KV_NAMESPACE_ID")
        return False
    
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Cloudflare KV API endpoint
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/storage/kv/namespaces/{CF_KV_NAMESPACE_ID}/values/{url_key}"
    
    # Prepare user data with all Bright Data fields
    kv_data = {
        "username": user_data.get("username"),
        "user_id": user_data.get("user_id"),
        "followers": user_data.get("followers", 0),
        "following": user_data.get("following", 0),
        "posts_count": user_data.get("posts_count", 0),
        "avg_engagement": user_data.get("avg_engagement", 0.0),
        "video": user_data.get("video", "default.mp4"),
        "video_sent": user_data.get("video", "default.mp4"),  # For UI compatibility
        "campaign_id": user_data.get("campaign_id"),
        "sent_at": user_data.get("sent_at", datetime.utcnow().isoformat() + "Z"),
        "timestamp": user_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        "clicked": False,
        "status": user_data.get("status", "active")
    }
    
    try:
        response = requests.put(url, headers=headers, json=kv_data)
        
        if response.status_code == 200:
            print(f"✅ Synced {url_key} to Cloudflare KV")
            return True
        else:
            print(f"❌ Failed to sync {url_key}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error syncing {url_key}: {str(e)}")
        return False

def sync_campaign_data():
    """Sync all campaign data to Cloudflare"""
    
    # Load campaign data
    campaign_file = Path(__file__).parent.parent / "instagram_mcp" / "campaigns.json"
    
    if not campaign_file.exists():
        print("No campaigns.json found")
        return
    
    with open(campaign_file, 'r') as f:
        campaigns = json.load(f)
    
    synced_count = 0
    for campaign_id, campaign in campaigns.items():
        print(f"\nSyncing campaign: {campaign.get('name', campaign_id)}")
        
        for username, user_data in campaign.get("users", {}).items():
            if "user_id" in user_data:
                url_key = f"{username}-{user_data['user_id'][:6]}"
                
                # Add campaign context
                user_data["campaign_id"] = campaign_id
                user_data["username"] = username
                
                if sync_user_to_cloudflare(url_key, user_data):
                    synced_count += 1
    
    print(f"\n✅ Total users synced: {synced_count}")

def add_test_users():
    """Add test users to Cloudflare KV"""
    test_users = {
        "testuser1-abc123": {
            "username": "testuser1",
            "user_id": "abc123456",
            "video": "ghost_1.mp4",
            "campaign_id": "test_campaign"
        },
        "johndoe-def456": {
            "username": "johndoe",
            "user_id": "def456789",
            "video": "ghost_2.mp4",
            "campaign_id": "test_campaign"
        }
    }
    
    for url_key, user_data in test_users.items():
        sync_user_to_cloudflare(url_key, user_data)

if __name__ == "__main__":
    print("🔒 VHS Ghost - Cloudflare KV Sync")
    print("=================================")
    
    # Check for credentials
    if not CF_API_TOKEN:
        print("\n⚠️  Missing Cloudflare credentials!")
        print("Set these environment variables:")
        print("  export CF_API_TOKEN='your-api-token'")
        print("  export CF_ACCOUNT_ID='your-account-id'")
        print("  export CF_KV_NAMESPACE_ID='your-kv-namespace-id'")
        print("\nGet these from:")
        print("  - API Token: https://dash.cloudflare.com/profile/api-tokens")
        print("  - Account ID: Cloudflare dashboard sidebar")
        print("  - KV Namespace ID: Run 'wrangler kv:namespace list'")
        exit(1)
    
    # Sync options
    print("\n1. Sync campaign data")
    print("2. Add test users")
    print("3. Both")
    
    choice = input("\nSelect option (1-3): ")
    
    if choice == "1":
        sync_campaign_data()
    elif choice == "2":
        add_test_users()
    elif choice == "3":
        add_test_users()
        sync_campaign_data()
    else:
        print("Invalid choice")