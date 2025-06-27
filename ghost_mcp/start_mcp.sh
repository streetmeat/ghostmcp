#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
exec python src/mcp_server.py --use-account-pool