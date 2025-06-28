# Ghost MCP Server - Complete Guide

A FastMCP-based Instagram automation server for the ghost vhs bot. This guide consolidates all documentation for easy reference.

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Installation & Setup](#installation--setup)
5. [Available MCP Tools](#available-mcp-tools)
6. [Core Systems](#core-systems)
7. [Campaign Workflow](#campaign-workflow)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Overview

The Ghost MCP Server is a comprehensive Instagram automation platform that enables LLMs to execute viral marketing campaigns through personalized videos and targeted DMs. Built for the Instagram DM MCP Hackathon by Gala Labs.
## Features

- 🤖 **Multi-Account Management** - Rotate between accounts with session persistence
- 📹 **Two-Stage Video Processing** - Efficient chunk creation and personalization
- 📨 **Advanced DM Operations** - Text, photos, videos, and post sharing
- 🎯 **Campaign Orchestration** - Automated workflows with tracking
- 🔍 **User Discovery** - Integration with Bright Data for targeting
- 🔒 **Security Features** - 2FA support, proxy configuration, rate limiting

## Architecture

### Directory Structure
```
ghost_mcp/
├── src/
│   ├── mcp_server.py              # Main MCP server with 30+ tools
│   ├── account_pool.py            # Multi-account management
│   ├── chunk_processor.py         # Video chunk creation (Stage 1)
│   ├── personalization_processor.py # Username overlays (Stage 2)
│   └── logger.py                  # Logging configuration
├── media/
│   ├── raw/                       # Source videos (11 files, 5.3GB)
│   ├── chunks/                    # Pre-made chunks (57 files, 422MB)
│   ├── campaign_videos/           # Personalized videos
│   └── gst.png                    # Logo overlay
├── sessions/                      # Instagram session persistence
├── accounts.json                  # Multi-account configuration
├── campaigns.json                 # Campaign tracking
└── requirements.txt               # Python dependencies
```

### Two-Stage Video Processing

1. **Stage 1 (Pre-processing)**: Create 13-20 second chunks with GST logo (7s onwards)
2. **Stage 2 (On-demand)**: Add username personalization during campaigns (0-8s flashing text)

This reduces processing time from 30-60s to 5-10s per video.

## Installation & Setup

### Prerequisites
- Python 3.10+
- FFmpeg (for video processing)
- Git
- 8GB+ RAM recommended

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/ghost-vhs.git
cd ghost-vhs/ghost_mcp
```

2. **Set up Python environment**
```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

3. **Configure Instagram credentials**
```bash
# Copy example files
cp .env.example .env
cp accounts.json.example accounts.json

# Edit .env with your primary account
# Edit accounts.json for multi-account setup (optional)
```

4. **Add to Claude Code**

Using Claude Code CLI:
```bash
# Single account mode
claude mcp add ghost ghost_mcp/venv/bin/python ghost_mcp/src/mcp_server.py

# Multi-account mode (recommended)
claude mcp add ghost ghost_mcp/venv/bin/python ghost_mcp/src/mcp_server.py --use-account-pool
```

Or manually add to `.mcp.json`:
```json
{
  "mcpServers": {
    "ghost": {
      "type": "stdio",
      "command": "ghost_mcp/venv/bin/python",
      "args": ["ghost_mcp/src/mcp_server.py", "--use-account-pool"],
      "env": {
        "PYTHONPATH": "/path/to/ghost-vhs"
      }
    }
  }
}
```

5. **Verify installation**
```bash
# List configured servers
claude mcp list

# Check server details
claude mcp get ghost
```

### Configuration Files

#### .env (Single Account)
```bash
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
INSTAGRAM_TOTP_SECRET=optional_2fa_secret  # For 2FA
GHOST_LINK_DOMAIN=vhs-ghost.com
```

#### accounts.json (Multi-Account)
```json
{
  "accounts": [
    {
      "username": "account1",
      "password": "password1",
      "totp_secret": "optional_2fa_secret",
      "proxy": "http://proxy1:port"
    },
    {
      "username": "account2",
      "password": "password2"
    }
  ],
  "settings": {
    "session_timeout": 86400,
    "max_daily_actions": 200,
    "rotation_strategy": "round_robin"
  }
}
```

## Available MCP Tools

All tools are accessed with the prefix `mcp__ghost__`. Total: 19 optimized tools.

### Campaign Management (6 tools)
- `create_campaign` - Initialize new campaign with target users
- `get_campaign_status` - Monitor progress and statistics
- `delete_campaigns` - Remove campaigns
- `fetch_bright_data_users` - Query user database
- `download_bright_data_snapshot` - Retrieve user data
- `select_random_users` - Pick users with filtering

### Video Processing (5 tools)
- `create_video_chunks` - Generate base video chunks
- `list_video_chunks` - View available chunks
- `get_chunk_info` - Get chunk metadata
- `personalize_specific_chunk` - Add username overlay
- `prepare_campaign_videos` - Batch personalization

### Instagram Operations (4 tools)
- `send_message` - Send text DMs
- `upload_video_post` - Upload reel with user tag
- `share_post_to_dm` - Share posts to DMs
- `send_ghost_video_with_specific_chunk` - Complete ghost workflow

### User Information (3 tools)
- `get_user_info` - Comprehensive user data
- `get_user_id_from_username` - Convert username to ID
- `get_user_posts` - Fetch user's recent posts

### Account Management (1 tool)
- `get_account_status` - Check all accounts and limits

## Core Systems

### Account Pool System
- **Round-robin selection** for load distribution
- **Session persistence** to avoid repeated logins
- **Daily action tracking** (200 actions/day limit)
- **Automatic re-authentication** on session expiry
- **2FA support** via TOTP secrets

### Campaign System
1. Load users from Bright Data or custom lists
2. Pre-create video chunks if needed
3. For each user:
   - Personalize video with username
   - Upload as public reel with tag
   - Share to user's DM
   - Send cryptic follow-up message
4. Track progress in campaigns.json

### Video Processing System
- **Chunk Creation**: 13-20s clips with GST logo (7s+)
- **Personalization**: Username flash text (0-8s)
- **Text Cycle**: @username → YOUVE BEEN CHOSEN → FIND THE GHOST → FOLLOW THE TRACE
- **Processing Time**: ~5-10 seconds per video

## Campaign Workflow

### Complete Example
```python
# 1. Get target users
snapshot_id = mcp__ghost__fetch_bright_data_users(
    hashtags=["nostalgia", "liminalspaces", "vhsaesthetic"],
    min_followers=100,
    max_followers=50000,
    count=200
)

# 2. Wait and download (1-5 minutes)
users = mcp__ghost__download_bright_data_snapshot(snapshot_id)

# 3. Create campaign
campaign = mcp__ghost__create_campaign(
    name="ghost_haunting_v1",
    user_list=users["usernames"],
    message_template="SYSTEM DIAGNOSTIC INITIATED\nACCESS: vhs-ghost.com/{username}\nTIME REMAINING: 72:00:00"
)

# 4. Prepare videos (optional)
mcp__ghost__create_video_chunks(count=20)

# 5. Execute for each user manually
for username in users["usernames"][:10]:
    mcp__ghost__send_ghost_video_with_specific_chunk(
        username=username,
        chunk_id="auto",  # Auto-select chunk
        message_template=campaign["message_template"]
    )
    # Wait 2 minutes between users
    time.sleep(120)
```

## Advanced Configuration

### Proxy Support
```bash
# In .env or accounts.json
HTTP_PROXY=http://proxy:port
HTTPS_PROXY=https://proxy:port
```

### Custom Domain
```bash
# In .env
GHOST_LINK_DOMAIN=your-domain.com
```

## Troubleshooting

### Common Issues

#### Virtual Environment Issues
```bash
# Python 3.10+ required
python3 --version

# Missing distutils (Ubuntu/Debian)
sudo apt install python3-distutils python3-dev python3-pip

# ARM64 devices (Jetson, etc) - venv required
python3 -m venv venv
source venv/bin/activate
```

#### Session/Login Issues
```bash
# Clear sessions and re-authenticate
rm -rf sessions/
python src/mcp_server.py --use-account-pool

# Check account status
mcp__ghost__get_account_status()
```

#### Video Processing Errors
```bash
# Verify FFmpeg
ffmpeg -version

# Check media directories
ls -la media/raw/
ls -la media/chunks/

# Create test chunk
mcp__ghost__create_video_chunks(count=1)
```

#### Campaign Issues
```python
# Check campaign status
status = mcp__ghost__get_campaign_status()

# Delete stuck campaigns
mcp__ghost__delete_campaigns()  # Deletes ALL campaigns
```

## Best Practices

1. **Use Multi-Account Mode** - Essential for production scale
2. **Pre-Create Video Chunks** - Process during off-peak hours
3. **Rate Limiting** - 2 minute delays between users minimum
4. **Monitor Daily Limits** - 200 actions per account per day
5. **Handle Errors Gracefully** - Implement retries with backoff
6. **Test Small First** - Start with 5-10 users before scaling
7. **Session Management** - Let the system handle re-authentication
8. **Proxy Usage** - Consider proxies for multiple accounts

## Rate Limits & Safety

- **Actions per account**: 200/day total
- **DMs per hour**: ~50-60 maximum
- **Delay between actions**: 5-10 seconds minimum
- **Delay between users**: 2 minutes recommended
- **Campaign batch size**: 10 users recommended

## Dependencies

### Core (5 packages)
- **fastmcp** (2.8.1) - MCP server framework
- **mcp** (1.9.4) - Model Context Protocol
- **instagrapi** (2.1.5) - Instagram API client
- **moviepy** (1.0.3+) - Video processing
- **pydantic** (2.11.5) - Data validation

### Supporting (38 packages)
Including HTTP clients, authentication, async support, CLI tools, and security libraries.

Total: 43 dependencies providing a complete Instagram automation platform.

## Platform-Specific Notes

### NVIDIA Jetson / ARM64
- Virtual environment **required** due to distutils issues
- Some packages compile from source (slower install)
- Tested on Jetson Orin Nano Dev Kit

### Windows
- Use `venv\Scripts\activate` for virtual environment
- May need Visual C++ build tools for some packages

### Docker
- No virtual environment needed
- Use system Python in container

## Quick Reference

### Start Server
```bash
# Single account
python src/mcp_server.py

# Multi-account (recommended)
python src/mcp_server.py --use-account-pool
```

### Check Status
```python
# Account status
mcp__ghost__get_account_status()

# Campaign status
mcp__ghost__get_campaign_status()

# Available chunks
mcp__ghost__list_video_chunks(limit=50)
```

### Emergency Stop
```bash
# Kill server
Ctrl+C

# Clear all sessions
rm -rf sessions/

# Delete all campaigns
mcp__ghost__delete_campaigns()
```

---

Built for Instagram DM MCP Hackathon by Gala Labs - June 2025