"""
Unit tests for auth.dependencies.get_current_user.

Uses real JWTs from auth.security.create_access_token rather than
mocking token decoding, so these tests also catch a mismatch between
what create_access_token embeds and what get_current_user expects.
"""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.dependencies import get_current_user  # noqa: E402
from auth.security import create_access_token  # noqa: E402


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_current_user(self):
        token = create_access_token("user-123", extra_claims={"role": "manager", "email": "a@b.com"})
        user = await get_current_user(authorization=f"Bearer {token}")
        assert user.id == "user-123"
        assert user.role == "manager"
        assert user.email == "a@b.com"

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_header_without_bearer_prefix_raises_401(self):
        token = create_access_token("user-123", extra_claims={"role": "admin"})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=token)  # missing "Bearer " prefix
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_bearer_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer ")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_garbage_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer not.a.valid.jwt")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_missing_role_claim_raises_401(self):
        # create_access_token with no extra_claims produces a token with
        # only "sub" and "exp" — no "role".
        token = create_access_token("user-123")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=f"Bearer {token}")
        assert exc_info.value.status_code == 401
