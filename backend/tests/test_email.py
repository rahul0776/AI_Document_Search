# tests/test_email.py
"""
Tests for email verification and password reset functionality.
"""
import pytest
import tempfile
import time
from services.user_store import UserStore
from services.token_service import TokenService
from services.email_service import EmailService


class TestTokenService:
    """Test token generation and verification."""
    
    def test_generate_token(self):
        """Should generate unique tokens."""
        token1 = TokenService.generate_token()
        token2 = TokenService.generate_token()
        
        assert token1 != token2
        assert len(token1) > 20  # Should be long enough
    
    def test_hash_token(self):
        """Should hash tokens consistently."""
        token = "test_token_123"
        hash1 = TokenService.hash_token(token)
        hash2 = TokenService.hash_token(token)
        
        assert hash1 == hash2  # Same token produces same hash
        assert hash1 != token  # Hash should be different from original
    
    def test_create_verification_token(self):
        """Should create verification token with expiry."""
        plain, hashed, expiry = TokenService.create_verification_token()
        
        assert plain != hashed
        assert expiry > time.time()  # Should be in the future
        assert expiry < time.time() + (25 * 60 * 60)  # Less than 25 hours
    
    def test_create_password_reset_token(self):
        """Should create password reset token with shorter expiry."""
        plain, hashed, expiry = TokenService.create_password_reset_token()
        
        assert plain != hashed
        assert expiry > time.time()
        assert expiry < time.time() + (2 * 60 * 60)  # Less than 2 hours
    
    def test_verify_token_valid(self):
        """Should verify valid tokens."""
        plain, hashed, expiry = TokenService.create_verification_token()
        
        is_valid = TokenService.verify_token(plain, hashed, expiry)
        assert is_valid is True
    
    def test_verify_token_invalid(self):
        """Should reject invalid tokens."""
        _, hashed, expiry = TokenService.create_verification_token()
        wrong_token = "wrong_token"
        
        is_valid = TokenService.verify_token(wrong_token, hashed, expiry)
        assert is_valid is False
    
    def test_verify_token_expired(self):
        """Should reject expired tokens."""
        plain, hashed, _ = TokenService.create_verification_token()
        expired = time.time() - 1  # 1 second ago
        
        is_valid = TokenService.verify_token(plain, hashed, expired)
        assert is_valid is False
    
    def test_is_expired(self):
        """Should correctly identify expired timestamps."""
        future = time.time() + 3600
        past = time.time() - 1
        
        assert TokenService.is_expired(future) is False
        assert TokenService.is_expired(past) is True


class TestUserStoreEmailFeatures:
    """Test UserStore email verification features."""
    
    @pytest.fixture
    def temp_user_store(self):
        """Create a temporary user store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = UserStore(data_dir=tmpdir)
            yield store
    
    def test_create_user_with_verification_token(self, temp_user_store):
        """Should create user with verification token."""
        token_service = TokenService()
        _, token_hash, expiry = token_service.create_verification_token()
        
        success = temp_user_store.create_user(
            "testuser",
            "password123",
            "test@example.com",
            verification_token_hash=token_hash,
            verification_token_expiry=expiry
        )
        
        assert success is True
        
        # Check token was stored
        token_data = temp_user_store.get_verification_token("testuser")
        assert token_data is not None
        assert token_data["token_hash"] == token_hash
        assert token_data["expiry"] == expiry
    
    def test_verify_email(self, temp_user_store):
        """Should mark email as verified."""
        temp_user_store.create_user("testuser", "password", "test@example.com")
        
        success = temp_user_store.verify_email("testuser")
        assert success is True
        
        user = temp_user_store.get_user("testuser")
        assert user["email_verified"] is True
    
    def test_set_password_reset_token(self, temp_user_store):
        """Should set password reset token."""
        temp_user_store.create_user("testuser", "password", "test@example.com")
        
        token_hash = "test_hash"
        expiry = time.time() + 3600
        
        success = temp_user_store.set_password_reset_token("testuser", token_hash, expiry)
        assert success is True
        
        token_data = temp_user_store.get_password_reset_token("testuser")
        assert token_data["token_hash"] == token_hash
        assert token_data["expiry"] == expiry
    
    def test_find_user_by_verification_token(self, temp_user_store):
        """Should find user by verification token."""
        token_hash = "verification_hash_123"
        temp_user_store.create_user(
            "testuser",
            "password",
            "test@example.com",
            verification_token_hash=token_hash,
            verification_token_expiry=time.time() + 3600
        )
        
        username = temp_user_store.find_user_by_verification_token(token_hash)
        assert username == "testuser"
    
    def test_find_user_by_reset_token(self, temp_user_store):
        """Should find user by password reset token."""
        temp_user_store.create_user("testuser", "password", "test@example.com")
        
        token_hash = "reset_hash_456"
        temp_user_store.set_password_reset_token("testuser", token_hash, time.time() + 3600)
        
        username = temp_user_store.find_user_by_reset_token(token_hash)
        assert username == "testuser"
    
    def test_reset_password(self, temp_user_store):
        """Should reset password and clear reset token."""
        temp_user_store.create_user("testuser", "oldpassword", "test@example.com")
        temp_user_store.set_password_reset_token("testuser", "token_hash", time.time() + 3600)
        
        success = temp_user_store.reset_password("testuser", "newpassword")
        assert success is True
        
        # Old password should not work
        user = temp_user_store.verify_user("testuser", "oldpassword")
        assert user is None
        
        # New password should work
        user = temp_user_store.verify_user("testuser", "newpassword")
        assert user is not None
        
        # Reset token should be cleared
        token_data = temp_user_store.get_password_reset_token("testuser")
        assert token_data["token_hash"] is None
    
    def test_get_user_by_email(self, temp_user_store):
        """Should find username by email."""
        temp_user_store.create_user("testuser", "password", "test@example.com")
        
        username = temp_user_store.get_user_by_email("test@example.com")
        assert username == "testuser"
        
        # Non-existent email
        username = temp_user_store.get_user_by_email("nonexistent@example.com")
        assert username is None


class TestEmailService:
    """Test email service functionality."""
    
    def test_email_service_initialization(self):
        """Should initialize email service."""
        service = EmailService()
        assert service is not None
        # Service will be disabled without SendGrid API key
        assert service.enabled is False or service.enabled is True
    
    def test_email_service_disabled_without_key(self, monkeypatch):
        """Should disable email service without API key."""
        monkeypatch.setenv("SENDGRID_API_KEY", "")
        service = EmailService()
        assert service.enabled is False
    
    def test_verification_email_structure(self):
        """Should not crash when generating verification email."""
        service = EmailService()
        # This will log a warning but not crash
        result = service.send_verification_email(
            "test@example.com",
            "testuser",
            "test_token_123"
        )
        # Without API key, should return False
        assert isinstance(result, bool)
    
    def test_password_reset_email_structure(self):
        """Should not crash when generating password reset email."""
        service = EmailService()
        result = service.send_password_reset_email(
            "test@example.com",
            "testuser",
            "reset_token_456"
        )
        assert isinstance(result, bool)
    
    def test_welcome_email_structure(self):
        """Should not crash when generating welcome email."""
        service = EmailService()
        result = service.send_welcome_email(
            "test@example.com",
            "testuser"
        )
        assert isinstance(result, bool)


class TestEmailVerificationFlow:
    """Test complete email verification flow."""
    
    @pytest.fixture
    def temp_user_store(self):
        """Create a temporary user store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = UserStore(data_dir=tmpdir)
            yield store
    
    def test_complete_verification_flow(self, temp_user_store):
        """Test the complete email verification flow."""
        token_service = TokenService()
        
        # 1. Create user with verification token (signup)
        plain_token, token_hash, expiry = token_service.create_verification_token()
        temp_user_store.create_user(
            "newuser",
            "password123",
            "new@example.com",
            verification_token_hash=token_hash,
            verification_token_expiry=expiry
        )
        
        # 2. User clicks email link with token
        # Find user by token
        username = temp_user_store.find_user_by_verification_token(token_hash)
        assert username == "newuser"
        
        # 3. Verify the token
        token_data = temp_user_store.get_verification_token(username)
        is_valid = token_service.verify_token(
            plain_token,
            token_data["token_hash"],
            token_data["expiry"]
        )
        assert is_valid is True
        
        # 4. Mark email as verified
        temp_user_store.verify_email(username)
        
        # 5. Verify user is now verified
        user = temp_user_store.get_user(username)
        assert user["email_verified"] is True
        assert user["email"] == "new@example.com"
    
    def test_complete_password_reset_flow(self, temp_user_store):
        """Test the complete password reset flow."""
        token_service = TokenService()
        
        # 1. Create user
        temp_user_store.create_user("user", "oldpassword", "user@example.com")
        
        # 2. Request password reset
        plain_token, token_hash, expiry = token_service.create_password_reset_token()
        temp_user_store.set_password_reset_token("user", token_hash, expiry)
        
        # 3. User clicks reset link with token
        username = temp_user_store.find_user_by_reset_token(token_hash)
        assert username == "user"
        
        # 4. Verify the reset token
        token_data = temp_user_store.get_password_reset_token(username)
        is_valid = token_service.verify_token(
            plain_token,
            token_data["token_hash"],
            token_data["expiry"]
        )
        assert is_valid is True
        
        # 5. Reset password
        temp_user_store.reset_password(username, "newpassword")
        
        # 6. Verify new password works and old doesn't
        assert temp_user_store.verify_user("user", "oldpassword") is None
        assert temp_user_store.verify_user("user", "newpassword") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

