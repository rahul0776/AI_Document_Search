# tests/test_security.py
"""
Security tests for password hashing and authentication.
"""
import pytest
from services.user_store import hash_password, verify_password, UserStore
import tempfile
from pathlib import Path


class TestPasswordHashing:
    """Test password hashing with bcrypt."""
    
    def test_hash_password_returns_different_values(self):
        """Each hash should be unique due to random salt."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to different salts
        assert hash1 != hash2
        
        # Both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)
    
    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        password = "correct_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        password = "correct_password"
        hashed = hash_password(password)
        
        assert verify_password("wrong_password", hashed) is False
    
    def test_verify_password_empty(self):
        """Empty password should fail verification."""
        password = "test_password"
        hashed = hash_password(password)
        
        assert verify_password("", hashed) is False
    
    def test_hash_contains_bcrypt_signature(self):
        """Hash should start with $2b$ (bcrypt signature)."""
        password = "test_password"
        hashed = hash_password(password)
        
        assert hashed.startswith("$2b$")
    
    def test_password_with_special_characters(self):
        """Should handle special characters correctly."""
        password = "p@ssw0rd!#$%^&*(){}[]<>?"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("p@ssw0rd", hashed) is False
    
    def test_long_password(self):
        """Should handle long passwords."""
        password = "a" * 100
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_unicode_password(self):
        """Should handle unicode characters."""
        password = "пароль密码🔐"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True


class TestUserStore:
    """Test UserStore with bcrypt hashing."""
    
    @pytest.fixture
    def temp_user_store(self):
        """Create a temporary user store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = UserStore(data_dir=tmpdir)
            yield store
    
    def test_create_user(self, temp_user_store):
        """Should create user with hashed password."""
        success = temp_user_store.create_user(
            "testuser",
            "testpassword123",
            "test@example.com"
        )
        
        assert success is True
        assert temp_user_store.user_exists("testuser") is True
    
    def test_create_duplicate_user(self, temp_user_store):
        """Should not allow duplicate usernames."""
        temp_user_store.create_user("testuser", "password123", "test@example.com")
        
        success = temp_user_store.create_user("testuser", "different_pass", "other@example.com")
        
        assert success is False
    
    def test_verify_user_correct_password(self, temp_user_store):
        """Should verify user with correct password."""
        temp_user_store.create_user("testuser", "correct_password", "test@example.com")
        
        user = temp_user_store.verify_user("testuser", "correct_password")
        
        assert user is not None
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
    
    def test_verify_user_wrong_password(self, temp_user_store):
        """Should reject wrong password."""
        temp_user_store.create_user("testuser", "correct_password", "test@example.com")
        
        user = temp_user_store.verify_user("testuser", "wrong_password")
        
        assert user is None
    
    def test_verify_nonexistent_user(self, temp_user_store):
        """Should reject non-existent user."""
        user = temp_user_store.verify_user("nonexistent", "password")
        
        assert user is None
    
    def test_password_not_stored_in_plaintext(self, temp_user_store):
        """Password should never be stored in plaintext."""
        password = "secret_password"
        temp_user_store.create_user("testuser", password, "test@example.com")
        
        # Read the raw file
        users_file = Path(temp_user_store.data_dir) / "users.json"
        content = users_file.read_text()
        
        # Password should NOT appear in plaintext
        assert password not in content
        # Should contain bcrypt hash signature
        assert "$2b$" in content


class TestAuthEndpoints:
    """Test authentication endpoints with bcrypt."""
    
    @pytest.fixture
    def temp_user_store(self):
        """Create a temporary user store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = UserStore(data_dir=tmpdir)
            yield store
    
    def test_signup_creates_secure_hash(self, temp_user_store):
        """Signup should create user with bcrypt hash."""
        temp_user_store.create_user("newuser", "StrongPass123!", "new@example.com")
        
        # Verify the hash is bcrypt format
        users = temp_user_store._load_users()
        stored_hash = users["newuser"]["password_hash"]
        
        assert stored_hash.startswith("$2b$")
        assert len(stored_hash) == 60  # bcrypt hashes are always 60 chars
    
    def test_login_with_bcrypt_hash(self, temp_user_store):
        """Login should work with bcrypt hashed passwords."""
        password = "MySecurePassword123"
        temp_user_store.create_user("testuser", password, "test@example.com")
        
        # Should verify successfully
        user = temp_user_store.verify_user("testuser", password)
        assert user is not None
        
        # Wrong password should fail
        user = temp_user_store.verify_user("testuser", "WrongPassword")
        assert user is None


def test_password_security_best_practices():
    """Verify password hashing follows security best practices."""
    password = "test_password"
    hashed = hash_password(password)
    
    # Should use bcrypt (2b is the bcrypt identifier)
    assert hashed.startswith("$2b$")
    
    # Should be 60 characters (standard bcrypt length)
    assert len(hashed) == 60
    
    # Should have cost factor (rounds) embedded
    # Format: $2b$12$... where 12 is the cost factor
    parts = hashed.split("$")
    cost_factor = int(parts[2])
    assert cost_factor >= 10  # Minimum recommended
    assert cost_factor <= 14  # Maximum practical
    
    # Each hash should be unique (includes random salt)
    hash2 = hash_password(password)
    assert hashed != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

