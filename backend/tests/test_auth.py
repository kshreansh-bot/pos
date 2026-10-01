"""Tests for authentication service."""
import pytest
from datetime import datetime, timedelta
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    extract_token_from_header,
)
from app.utils.errors import AuthenticationError


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        password = "testpassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_same_password(self):
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestTokenCreation:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        data = {"sub": "123"}
        token, expires_in = create_access_token(data)

        assert token is not None
        assert len(token) > 0
        assert expires_in > 0
        assert isinstance(expires_in, int)

    def test_decode_token(self):
        data = {"sub": "123"}
        token, _ = create_access_token(data)

        decoded = decode_token(token)
        assert decoded["sub"] == "123"
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        with pytest.raises(AuthenticationError):
            decode_token("invalid_token")

    def test_decode_expired_token(self):
        # Create token that expires immediately
        data = {"sub": "123"}
        token, _ = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(AuthenticationError):
            decode_token(token)

    def test_custom_expiry(self):
        data = {"sub": "123"}
        custom_delta = timedelta(hours=2)
        token, expires_in = create_access_token(data, expires_delta=custom_delta)

        # 2 hours = 7200 seconds (approximately)
        assert 7000 <= expires_in <= 7400


class TestExtractToken:
    """Test token extraction from authorization header."""

    def test_extract_valid_bearer_token(self):
        header = "Bearer test_token_123"
        token = extract_token_from_header(header)
        assert token == "test_token_123"

    def test_extract_case_insensitive(self):
        header = "bearer test_token_123"
        token = extract_token_from_header(header)
        assert token == "test_token_123"

    def test_extract_missing_header(self):
        with pytest.raises(AuthenticationError):
            extract_token_from_header(None)

    def test_extract_malformed_header(self):
        with pytest.raises(AuthenticationError):
            extract_token_from_header("InvalidFormat")

    def test_extract_no_bearer(self):
        with pytest.raises(AuthenticationError):
            extract_token_from_header("JustTokenWithoutBearer")

    def test_extract_empty_token(self):
        with pytest.raises(AuthenticationError):
            extract_token_from_header("Bearer ")