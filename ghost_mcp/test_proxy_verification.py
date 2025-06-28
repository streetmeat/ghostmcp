#!/usr/bin/env python3
"""
Test script to verify proxy usage in Instagram sessions
"""

import json
import logging
import sys
from pathlib import Path
from instagrapi import Client
import requests

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_proxy_connection(proxy_url: str):
    """Test if proxy is working by checking IP"""
    logger.info(f"Testing proxy: {proxy_url}")
    
    try:
        # Check IP without proxy
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        direct_ip = response.json()['ip']
        logger.info(f"Direct connection IP: {direct_ip}")
        
        # Check IP with proxy
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
        proxy_ip = response.json()['ip']
        logger.info(f"Proxy connection IP: {proxy_ip}")
        
        if direct_ip != proxy_ip:
            logger.info("✅ Proxy is working correctly (different IP detected)")
            return True
        else:
            logger.warning("⚠️ Proxy might not be working (same IP detected)")
            return False
            
    except Exception as e:
        logger.error(f"Failed to test proxy: {e}")
        return False

def test_instagrapi_proxy(username: str, password: str, proxy_url: str = None):
    """Test if Instagrapi is using the proxy correctly"""
    logger.info(f"Testing Instagrapi with account: {username}")
    
    try:
        client = Client()
        
        # Enable request logging to see proxy usage
        import http.client
        http.client.HTTPConnection.debuglevel = 1
        
        if proxy_url:
            logger.info(f"Setting proxy: {proxy_url}")
            client.set_proxy(proxy_url)
            
            # Check the proxy is set in the session
            if hasattr(client, 'private') and hasattr(client.private, 'session'):
                session_proxies = client.private.session.proxies
                logger.info(f"Session proxies: {session_proxies}")
        
        # Try to login (this will make requests through proxy)
        logger.info("Attempting login...")
        client.login(username, password)
        logger.info("✅ Login successful")
        
        # Make a test request to verify proxy is being used
        logger.info("Making test request...")
        user_info = client.user_info_by_username(username)
        logger.info(f"✅ Retrieved user info: {user_info.full_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

def check_account_pool_config():
    """Check accounts.json for proxy configuration"""
    accounts_file = Path("accounts.json")
    
    if not accounts_file.exists():
        logger.warning("accounts.json not found")
        return
    
    with open(accounts_file) as f:
        config = json.load(f)
    
    logger.info("\n=== Account Configuration ===")
    for account in config.get("accounts", []):
        username = account.get("username", "Unknown")
        has_proxy = "proxy" in account
        proxy_url = account.get("proxy", "Not configured")
        
        logger.info(f"Account: {username}")
        logger.info(f"  Proxy configured: {'Yes' if has_proxy else 'No'}")
        if has_proxy:
            logger.info(f"  Proxy URL: {proxy_url}")
            # Test the proxy
            test_proxy_connection(proxy_url)
        logger.info("")

def main():
    """Main test function"""
    logger.info("=== Proxy Verification Test ===\n")
    
    # Check configuration
    check_account_pool_config()
    
    # Optional: Test specific account
    if len(sys.argv) > 1:
        username = sys.argv[1]
        logger.info(f"\n=== Testing specific account: {username} ===")
        
        # Load account config
        with open("accounts.json") as f:
            config = json.load(f)
        
        for account in config.get("accounts", []):
            if account.get("username") == username:
                password = account.get("password")
                proxy = account.get("proxy")
                
                if proxy:
                    logger.info(f"Testing with proxy: {proxy}")
                    test_instagrapi_proxy(username, password, proxy)
                else:
                    logger.info("No proxy configured for this account")
                break
        else:
            logger.error(f"Account {username} not found in config")

if __name__ == "__main__":
    main()