# Cloudflare Workers Deployment Guide for vhs-ghost.com

## Overview
This deploys the Ghost landing pages as a Cloudflare Worker - **completely free** for up to 100,000 requests/day!

## Step 1: Basic Setup (No Server Needed!)

### 1.1 Install Wrangler CLI
```bash
npm install -g wrangler
```

### 1.2 Login to Cloudflare
```bash
wrangler login
```

### 1.3 Quick Deploy (Static Data)
```bash
cd cloudflare-worker
wrangler deploy
```

This immediately makes your site live at vhs-ghost.com!

## Step 2: Add Your Domain

1. In Cloudflare Dashboard, ensure vhs-ghost.com is added
2. Go to **Workers & Pages** → Your worker → **Settings** → **Triggers**
3. Add Custom Domain: `vhs-ghost.com`
4. Add route: `vhs-ghost.com/*`

## Step 3: Test It

Visit these URLs:
- https://vhs-ghost.com (shows access denied)
- https://vhs-ghost.com/testuser1-abc123 (shows mystery page)
- https://vhs-ghost.com/johndoe-def456 (shows mystery page)

## Step 4: Dynamic Data with Workers KV (Optional)

### 4.1 Create KV Namespaces
```bash
wrangler kv:namespace create "USERS_KV"
wrangler kv:namespace create "EMAILS_KV"
```

### 4.2 Update wrangler.toml with the IDs

### 4.3 Add Users via CLI
```bash
wrangler kv:key put --namespace-id=YOUR_ID "username-abc123" '{"username":"username","video":"ghost_1.mp4"}'
```

## Step 5: Connect to MCP Server

Create a sync script that pushes campaign data to Workers KV:

```python
import requests

def sync_to_workers_kv(user_key, user_data):
    # Use Cloudflare API to update KV
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{user_key}"
    
    requests.put(url, headers=headers, json=user_data)
```

## Cost Breakdown

**Cloudflare Workers Free Tier:**
- 100,000 requests/day
- 10ms CPU time per request
- Unlimited sites

**For vhs-ghost.com:**
- Domain: ~$10/year
- Hosting: FREE
- SSL: FREE
- Global CDN: FREE

## Advantages Over Traditional Hosting

1. **No Server Management** - No nginx, no updates, no security patches
2. **Global Performance** - Runs at 200+ Cloudflare edge locations
3. **Instant Deploy** - Changes live in seconds
4. **Auto-scaling** - Handles viral traffic automatically
5. **Built-in DDoS Protection** - Cloudflare's enterprise protection

## Quick Commands

```bash
# Deploy changes
wrangler deploy

# View logs
wrangler tail

# Test locally
wrangler dev

# Add test user to KV
wrangler kv:key put --namespace-id=YOUR_ID "newuser-123456" '{"username":"newuser"}'
```

## Integration with MCP Server

The MCP server can push data to Workers KV using the Cloudflare API:

```python
# In mcp_server.py
import requests

def sync_to_cloudflare(url_key, user_data):
    cf_api = "https://api.cloudflare.com/client/v4"
    headers = {
        "Authorization": f"Bearer {os.getenv('CF_API_TOKEN')}",
        "Content-Type": "application/json"
    }
    
    # Push to Workers KV
    kv_url = f"{cf_api}/accounts/{os.getenv('CF_ACCOUNT_ID')}/storage/kv/namespaces/{os.getenv('CF_KV_NAMESPACE')}/values/{url_key}"
    
    response = requests.put(kv_url, headers=headers, json=user_data)
    return response.status_code == 200
```

## Summary

With Cloudflare Workers:
- ✅ No server costs
- ✅ No maintenance
- ✅ Instant global deployment
- ✅ Built-in security
- ✅ Scales automatically

Perfect for a hackathon project that might go viral!