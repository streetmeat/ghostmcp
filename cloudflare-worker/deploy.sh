#!/bin/bash

# Deploy Ghost Media Cloudflare Worker

echo "🚀 Deploying Ghost Media Worker..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ wrangler CLI not found. Please install it with: npm install -g wrangler"
    exit 1
fi

# Deploy the worker
echo "📦 Deploying worker..."
wrangler deploy

if [ $? -eq 0 ]; then
    echo "✅ Worker deployed successfully!"
    echo ""
    echo "🔧 Security measures implemented:"
    echo "  - Video serving through Worker API (no direct R2 access)"
    echo "  - Rate limiting on email API (5 per hour per IP)"
    echo "  - CORS restrictions (only vhs-ghost.com + localhost for dev)"
    echo "  - Input validation and sanitization"
    echo "  - API secret required for email list access"
    echo ""
    echo "📝 Next steps:"
    echo "  1. Test video playback at https://vhs-ghost.com/[username]"
    echo "  2. Verify email collection still works"
    echo "  3. Check that rate limiting prevents abuse"
    echo ""
    echo "🔍 If videos still don't load, check browser console (F12) for errors"
else
    echo "❌ Deployment failed!"
    exit 1
fi