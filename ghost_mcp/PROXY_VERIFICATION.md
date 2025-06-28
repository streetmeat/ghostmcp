# Proxy Verification Guide

## Overview
This guide explains how to ensure proxies are properly configured and used by the Instagram sessions.

## Key Changes Made

1. **Proxy Always Applied**: Updated `account_pool.py` to ALWAYS set proxy even when loading existing sessions
2. **Enhanced Logging**: Added verification logging to confirm proxy is applied to the session
3. **Test Script**: Created `test_proxy_verification.py` to verify proxy usage

## How Proxies Work

1. **Configuration**: Add proxy URL to each account in `accounts.json`:
```json
{
  "username": "account1",
  "password": "password1",
  "proxy": "http://username:password@proxy.host:port"
}
```

2. **Application**: Proxy is now applied in this order:
   - Client is created
   - Existing session is loaded (if available)
   - **Proxy is ALWAYS set** (even with existing session)
   - Login happens only if needed

3. **Verification**: The system now logs:
   - When proxy is set: `"Set proxy for username: http://..."`
   - Session proxy verification: `"Verified session proxies for username: {...}"`

## Testing Proxy Usage

### 1. Run the Test Script
```bash
cd ghost_mcp
python test_proxy_verification.py

# Test specific account
python test_proxy_verification.py account1
```

### 2. Check Logs
When running the MCP server, look for these log messages:
```
INFO - Set proxy for account1: http://proxy.host:port
DEBUG - Verified session proxies for account1: {'http': '...', 'https': '...'}
```

### 3. Verify Different IP
The test script checks if your proxy provides a different IP address than direct connection.

## Proxy Format Examples

### HTTP Proxy
```
http://proxy.host:port
http://username:password@proxy.host:port
```

### HTTPS Proxy
```
https://proxy.host:port
https://username:password@proxy.host:port
```

### SOCKS5 Proxy
```
socks5://proxy.host:port
socks5://username:password@proxy.host:port
```

## Troubleshooting

### Proxy Not Working
1. Check proxy format is correct
2. Verify proxy credentials
3. Test proxy with curl: `curl -x http://proxy:port https://api.ipify.org`
4. Check firewall/network settings

### Session Issues
1. Delete existing session: `rm sessions/username.json`
2. Force re-login with proxy
3. Check logs for proxy confirmation

### Debug Mode
Enable debug logging to see all proxy details:
```python
logging.getLogger('account_pool').setLevel(logging.DEBUG)
```

## Best Practices

1. **Use Different Proxies**: Each account should have its own proxy
2. **Residential Proxies**: Preferred over datacenter proxies
3. **Rotating Proxies**: Consider services that rotate IPs
4. **Monitor IP**: Regularly verify proxy IPs are different
5. **Session Management**: Clear sessions if switching proxies

## Security Note

Never commit proxy credentials to git. Keep them in:
- `accounts.json` (gitignored)
- Environment variables
- Secure credential storage