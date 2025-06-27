#!/bin/bash
# Quick setup script for vhs-ghost.com Cloudflare Worker

echo "🔒 VHS Ghost - Cloudflare Worker Setup"
echo "====================================="

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "Installing Wrangler CLI..."
    npm install -g wrangler
fi

echo ""
echo "1. First, login to Cloudflare:"
echo "   wrangler login"
echo ""
echo "2. Create KV namespaces (optional for dynamic data):"
echo "   wrangler kv:namespace create USERS_KV"
echo "   wrangler kv:namespace create EMAILS_KV"
echo ""
echo "3. Update wrangler.toml with your KV namespace IDs"
echo ""
echo "4. Deploy the worker:"
echo "   wrangler deploy"
echo ""
echo "5. Add some test data:"
echo "   wrangler kv:key put --binding=USERS_KV \"testuser-abc123\" '{\"username\":\"testuser\",\"video\":\"ghost_1.mp4\"}'"
echo ""
echo "Your site will be live at: https://vhs-ghost.com"
echo ""
echo "Test URLs:"
echo "  - https://vhs-ghost.com (access denied page)"
echo "  - https://vhs-ghost.com/testuser-abc123 (mystery page)"