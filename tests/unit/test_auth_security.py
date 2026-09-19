"""Unit tests for auth.security."""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.security import (  # noqa: E402
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_verify_succeeds_for_correct_password(self):
        hashed = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", hashed) is True

    def test_verify_fails_for_wrong_password(self):
        hashed = hash_password("correct horse battery staple")
        assert verify_password("wrong password", hashed) is False

    def test_hash_is_not_the_plain_password(self):
        hashed = hash_password("hunter2")
        assert hashed != "hunter2"

    def test_hashing_the_same_password_twice_gives_different_hashes(self):
        # bcrypt salts each hash, so two hashes of the same password differ,
        # but both must still verify correctly.
        h1 = hash_password("same password")
        h2 = hash_password("same password")
        assert h1 != h2
        assert verify_password("same password", h1) is True
        assert verify_password("same password", h2) is True


class TestAccessTokens:
    def test_round_trip_decodes_the_subject(self):
        token = create_access_token("user-123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"

    def test_extra_claims_are_included(self):
        token = create_access_token("user-123", extra_claims={"role": "manager"})
        payload = decode_access_token(token)
        assert payload["role"] == "manager"

    def test_garbage_token_raises_token_error(self):
        with pytest.raises(TokenError):
            decode_access_token("this.is.not.a.valid.jwt")

    def test_tampered_token_raises_token_error(self):
        token = create_access_token("user-123")
        tampered = token[:-3] + ("abc" if not token.endswith("abc") else "xyz")
        with pytest.raises(TokenError):
            decode_access_token(tampered)
