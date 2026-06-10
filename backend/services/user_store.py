# backend/services/user_store.py
"""
Production-ready user storage with secure password hashing.
Uses bcrypt for password hashing (industry standard).
"""
from __future__ import annotations
import json
import threading
import bcrypt
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with salt.
    
    Bcrypt automatically handles salt generation and includes it in the hash.
    This is secure for production use.
    
    Note: Bcrypt has a 72-byte limit. Passwords longer than 72 bytes will be
    truncated (this is a known limitation of bcrypt and is acceptable in practice).
    """
    # Generate salt and hash the password
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds = good balance of security and speed
    
    # Bcrypt has a 72-byte limit, truncate if needed
    password_bytes = password.encode('utf-8')[:72]
    
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')  # Store as string

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its bcrypt hash.
    
    Returns True if password matches, False otherwise.
    Safe against timing attacks.
    """
    try:
        # Bcrypt has a 72-byte limit, truncate if needed (same as in hash_password)
        password_bytes = password.encode('utf-8')[:72]
        return bcrypt.checkpw(password_bytes, hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


class UserStore:
    """Simple file-based user storage."""

    # Shared across instances: every read-modify-write of users.json must hold this,
    # or concurrent signups/resets overwrite each other's changes.
    _LOCK = threading.RLock()

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Create users file if it doesn't exist."""
        if not self.users_file.exists():
            self.users_file.write_text(json.dumps({}))
    
    def _load_users(self) -> Dict:
        """Load users from file."""
        try:
            return json.loads(self.users_file.read_text())
        except Exception:
            return {}
    
    def _save_users(self, users: Dict):
        """Save users to file."""
        self.users_file.write_text(json.dumps(users, indent=2))
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists."""
        users = self._load_users()
        return username in users
    
    def create_user(
        self, 
        username: str, 
        password: str, 
        email: Optional[str] = None,
        verification_token_hash: Optional[str] = None,
        verification_token_expiry: Optional[float] = None
    ) -> bool:
        """
        Create a new user with optional email verification token.
        Returns True if successful, False if user already exists.
        """
        with self._LOCK:
            users = self._load_users()

            if username in users:
                return False

            import time
            users[username] = {
                "password_hash": hash_password(password),
                "email": email,
                "email_verified": False,  # Email starts unverified
                "verification_token_hash": verification_token_hash,
                "verification_token_expiry": verification_token_expiry,
                "password_reset_token_hash": None,
                "password_reset_token_expiry": None,
                "created_at": time.time(),
            }

            self._save_users(users)
            return True
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Verify user credentials.
        Returns user data if valid, None if invalid.
        """
        users = self._load_users()
        
        if username not in users:
            return None
        
        user = users[username]
        if verify_password(password, user["password_hash"]):
            return {
                "username": username,
                "email": user.get("email"),
                "email_verified": user.get("email_verified", False),
            }
        
        return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get user data by username.
        Returns user data if found, None otherwise.
        """
        users = self._load_users()
        
        if username not in users:
            return None
        
        user = users[username]
        return {
            "username": username,
            "email": user.get("email"),
            "email_verified": user.get("email_verified", False),
            "created_at": user.get("created_at"),
        }
    
    def verify_email(self, username: str) -> bool:
        """
        Mark user's email as verified.
        Returns True if successful, False if user not found.
        """
        with self._LOCK:
            users = self._load_users()

            if username not in users:
                return False

            users[username]["email_verified"] = True
            users[username]["verification_token_hash"] = None
            users[username]["verification_token_expiry"] = None

            self._save_users(users)
            return True
    
    def set_password_reset_token(
        self, 
        username: str, 
        token_hash: str, 
        expiry: float
    ) -> bool:
        """
        Set password reset token for user.
        Returns True if successful, False if user not found.
        """
        with self._LOCK:
            users = self._load_users()

            if username not in users:
                return False

            users[username]["password_reset_token_hash"] = token_hash
            users[username]["password_reset_token_expiry"] = expiry

            self._save_users(users)
            return True
    
    def get_verification_token(self, username: str) -> Optional[Dict]:
        """
        Get verification token data for user.
        Returns dict with token_hash and expiry, or None if not found.
        """
        users = self._load_users()
        
        if username not in users:
            return None
        
        user = users[username]
        return {
            "token_hash": user.get("verification_token_hash"),
            "expiry": user.get("verification_token_expiry"),
        }
    
    def get_password_reset_token(self, username: str) -> Optional[Dict]:
        """
        Get password reset token data for user.
        Returns dict with token_hash and expiry, or None if not found.
        """
        users = self._load_users()
        
        if username not in users:
            return None
        
        user = users[username]
        return {
            "token_hash": user.get("password_reset_token_hash"),
            "expiry": user.get("password_reset_token_expiry"),
        }
    
    def find_user_by_reset_token(self, token_hash: str) -> Optional[str]:
        """
        Find username by password reset token hash.
        Returns username if found, None otherwise.
        """
        users = self._load_users()
        
        for username, user_data in users.items():
            if user_data.get("password_reset_token_hash") == token_hash:
                return username
        
        return None
    
    def find_user_by_verification_token(self, token_hash: str) -> Optional[str]:
        """
        Find username by email verification token hash.
        Returns username if found, None otherwise.
        """
        users = self._load_users()
        
        for username, user_data in users.items():
            if user_data.get("verification_token_hash") == token_hash:
                return username
        
        return None
    
    def reset_password(self, username: str, new_password: str) -> bool:
        """
        Reset user's password and clear reset token.
        Returns True if successful, False if user not found.
        """
        with self._LOCK:
            users = self._load_users()

            if username not in users:
                return False

            users[username]["password_hash"] = hash_password(new_password)
            users[username]["password_reset_token_hash"] = None
            users[username]["password_reset_token_expiry"] = None

            self._save_users(users)
            return True
    
    def get_user_by_email(self, email: str) -> Optional[str]:
        """
        Find username by email address.
        Returns username if found, None otherwise.
        """
        users = self._load_users()
        
        for username, user_data in users.items():
            if user_data.get("email") == email:
                return username
        
        return None


# Global user store instance
_user_store: Optional[UserStore] = None

def get_user_store() -> UserStore:
    """Get the global user store instance."""
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store

