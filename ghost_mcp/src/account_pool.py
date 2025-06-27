"""
Simplified account pool management with lazy authentication
"""
import json
import os
import logging
from typing import Dict, Optional, List
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired

logger = logging.getLogger(__name__)


class AccountPool:
    """Manages multiple Instagram accounts with lazy authentication and round-robin rotation"""
    
    def __init__(self, config_path: str = "accounts.json", sessions_dir: str = "sessions"):
        self.config_path = config_path
        self.sessions_dir = sessions_dir
        
        # Account management
        self.account_configs: Dict[str, Dict[str, any]] = {}  # Raw credentials
        self.clients: Dict[str, Client] = {}  # Authenticated clients (lazy loaded)
        self.account_index = 0  # For round-robin rotation
        
        # Create sessions directory if it doesn't exist
        Path(self.sessions_dir).mkdir(exist_ok=True)
        
        # Load account configurations (but don't authenticate yet)
        self._load_account_configs()
        logger.info(f"Initialized account pool with {len(self.account_configs)} accounts (lazy authentication)")
    
    def _load_account_configs(self) -> None:
        """Load account configurations without authenticating"""
        if not os.path.exists(self.config_path):
            # Check environment for single account (backwards compatibility)
            username = os.getenv("INSTAGRAM_USERNAME")
            password = os.getenv("INSTAGRAM_PASSWORD")
            
            if username and password:
                logger.info(f"Loading single account from environment: {username}")
                self.account_configs[username] = {
                    "username": username,
                    "password": password
                }
                return
            else:
                logger.error(f"No accounts configuration found at {self.config_path}")
                return
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            accounts = data.get("accounts", [])
            logger.info(f"Loading {len(accounts)} account configuration(s) from {self.config_path}")
            
            for account in accounts:
                username = account.get("username")
                if not username:
                    logger.error("Account missing username, skipping")
                    continue
                
                # Store account config only (no authentication)
                self.account_configs[username] = account
                logger.debug(f"Loaded config for {username}")
                
        except Exception as e:
            logger.error(f"Failed to load accounts configuration: {e}")
    
    def _authenticate_account(self, username: str) -> Optional[Client]:
        """Authenticate a single account on demand"""
        if username not in self.account_configs:
            logger.error(f"Account {username} not found in configs")
            return None
            
        account_data = self.account_configs[username]
        
        try:
            # Create client
            client = Client()
            
            # Set proxy if provided
            if account_data.get("proxy"):
                client.set_proxy(account_data["proxy"])
                logger.info(f"Set proxy for {username}")
            
            # Try to load existing session
            session_file = os.path.join(self.sessions_dir, f"{username}.json")
            session_loaded = False
            
            if os.path.exists(session_file):
                try:
                    client.load_settings(session_file)
                    client.get_timeline_feed(1)  # Quick validation
                    session_loaded = True
                    logger.info(f"Loaded existing session for {username}")
                except Exception as e:
                    logger.warning(f"Session invalid for {username}, will re-login: {e}")
            
            # Login if no valid session
            if not session_loaded:
                password = account_data.get("password")
                if not password:
                    logger.error(f"No password provided for {username}")
                    return None
                
                try:
                    client.login(username, password)
                    logger.info(f"Successfully logged in: {username}")
                except TwoFactorRequired:
                    # Handle 2FA if TOTP secret is provided
                    if account_data.get("totp_secret"):
                        import pyotp
                        totp = pyotp.TOTP(account_data["totp_secret"])
                        code = totp.now()
                        client.login(username, password, verification_code=code)
                        logger.info(f"Successfully logged in with 2FA: {username}")
                    else:
                        logger.error(f"2FA required for {username} but no TOTP secret provided")
                        return None
                
                # Save session after successful login
                client.dump_settings(session_file)
                logger.info(f"Saved session for {username}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to authenticate {username}: {e}")
            return None
    
    def get_client(self, username: Optional[str] = None) -> Optional[Client]:
        """Get a client instance with lazy authentication and round-robin rotation"""
        # If specific username requested
        if username:
            # Check if already authenticated
            if username in self.clients:
                logger.debug(f"Returning cached client for {username}")
                return self.clients[username]
            
            # Authenticate on demand
            logger.info(f"Authenticating {username} on demand")
            client = self._authenticate_account(username)
            if client:
                self.clients[username] = client
            return client
        
        # Get list of all account usernames for round-robin
        all_usernames = list(self.account_configs.keys())
        if not all_usernames:
            logger.error("No accounts available")
            return None
        
        # Round-robin selection through all accounts
        self.account_index = self.account_index % len(all_usernames)
        selected_username = all_usernames[self.account_index]
        self.account_index += 1
        
        # Check if already authenticated
        if selected_username in self.clients:
            logger.info(f"Selected account (cached): {selected_username}")
            return self.clients[selected_username]
        
        # Authenticate on demand
        logger.info(f"Selected account (authenticating): {selected_username}")
        client = self._authenticate_account(selected_username)
        if client:
            self.clients[selected_username] = client
            return client
        else:
            # Try next account if this one fails
            logger.warning(f"Failed to authenticate {selected_username}, trying next account")
            return self.get_client()
    
    def mark_operation_complete(self) -> bool:
        """Compatibility method - no longer needed but kept for API compatibility"""
        logger.debug("mark_operation_complete called (no-op in simplified version)")
        return True
    
    def get_status(self) -> Dict[str, Dict[str, any]]:
        """Get current status of all accounts"""
        status = {}
        
        for username in self.account_configs:
            status[username] = {
                "state": "authenticated" if username in self.clients else "not_authenticated",
                "cached": username in self.clients
            }
        
        return status
    
    def track_action(self, username: str, action_type: str) -> None:
        """Compatibility method - no longer needed but kept for API compatibility"""
        logger.debug(f"track_action called: {username} - {action_type} (no-op)")
    
    def get_account_status(self) -> Dict[str, Dict[str, any]]:
        """Get account status - alias for get_status for compatibility"""
        return self.get_status()
    
    def relogin_account(self, username: str) -> bool:
        """Force re-authentication of an account"""
        logger.info(f"Force re-authenticating account: {username}")
        try:
            # Remove from cache if exists
            if username in self.clients:
                del self.clients[username]
            
            # Re-authenticate
            client = self._authenticate_account(username)
            if client:
                self.clients[username] = client
                logger.info(f"Successfully re-authenticated {username}")
                return True
            else:
                logger.error(f"Failed to re-authenticate {username}")
                return False
        except Exception as e:
            logger.error(f"Error during re-authentication for {username}: {e}")
            return False
    
    @property
    def active_username(self) -> Optional[str]:
        """Get the last selected username for compatibility"""
        all_usernames = list(self.account_configs.keys())
        if all_usernames and self.account_index > 0:
            # Return the last selected username
            return all_usernames[(self.account_index - 1) % len(all_usernames)]
        return None
    
    @property
    def active_client(self) -> Optional[Client]:
        """Get the last selected client for compatibility"""
        username = self.active_username
        return self.clients.get(username) if username else None
    
    @property
    def accounts(self) -> Dict[str, Dict[str, any]]:
        """Property for backwards compatibility - returns account info"""
        result = {}
        for username in self.account_configs:
            result[username] = {
                "username": username,
                "authenticated": username in self.clients
            }
        return result