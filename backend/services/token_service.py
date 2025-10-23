# backend/services/token_service.py
"""
Token generation and verification for email verification and password resets.
Uses cryptographically secure random tokens with expiration.
"""
from __future__ import annotations
import secrets
import hashlib
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta


class TokenService:
    """Service for generating and validating secure tokens."""
    
    # Token expiration times
    VERIFICATION_TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours
    PASSWORD_RESET_TOKEN_EXPIRY = 60 * 60  # 1 hour
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Length of the token in bytes (default: 32)
            
        Returns:
            URL-safe token string
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a token for secure storage.
        
        We store hashed tokens in the database so that even if the database
        is compromised, the tokens cannot be used directly.
        
        Args:
            token: Plain token to hash
            
        Returns:
            SHA256 hash of the token
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    @staticmethod
    def create_verification_token() -> Tuple[str, str, float]:
        """
        Create an email verification token.
        
        Returns:
            Tuple of (plain_token, hashed_token, expiry_timestamp)
        """
        token = TokenService.generate_token()
        hashed = TokenService.hash_token(token)
        expiry = time.time() + TokenService.VERIFICATION_TOKEN_EXPIRY
        
        return token, hashed, expiry
    
    @staticmethod
    def create_password_reset_token() -> Tuple[str, str, float]:
        """
        Create a password reset token.
        
        Returns:
            Tuple of (plain_token, hashed_token, expiry_timestamp)
        """
        token = TokenService.generate_token()
        hashed = TokenService.hash_token(token)
        expiry = time.time() + TokenService.PASSWORD_RESET_TOKEN_EXPIRY
        
        return token, hashed, expiry
    
    @staticmethod
    def verify_token(plain_token: str, stored_hash: str, expiry_timestamp: float) -> bool:
        """
        Verify a token against its stored hash and check expiration.
        
        Args:
            plain_token: The token provided by the user
            stored_hash: The hashed token stored in database
            expiry_timestamp: Unix timestamp when token expires
            
        Returns:
            True if token is valid and not expired, False otherwise
        """
        # Check expiration first (faster)
        if time.time() > expiry_timestamp:
            return False
        
        # Verify token hash
        computed_hash = TokenService.hash_token(plain_token)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    @staticmethod
    def is_expired(expiry_timestamp: float) -> bool:
        """
        Check if a timestamp has expired.
        
        Args:
            expiry_timestamp: Unix timestamp to check
            
        Returns:
            True if expired, False otherwise
        """
        return time.time() > expiry_timestamp
    
    @staticmethod
    def format_expiry_time(expiry_timestamp: float) -> str:
        """
        Format expiry timestamp as human-readable string.
        
        Args:
            expiry_timestamp: Unix timestamp
            
        Returns:
            Formatted string like "2024-01-15 14:30:00"
        """
        dt = datetime.fromtimestamp(expiry_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


# Global token service instance
_token_service: Optional[TokenService] = None

def get_token_service() -> TokenService:
    """Get the global token service instance."""
    global _token_service
    if _token_service is None:
        _token_service = TokenService()
    return _token_service

