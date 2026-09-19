"""
Tests for the /auth/register and /auth/login endpoints.

The repository layer (auth.repository) is mocked entirely, so these
don't need a real database. db.session.get_db is overridden via FastAPI's
dependency_overrides since the route handlers still declare it as a
dependency (unused once the repository calls are mocked, but FastAPI
still needs to be able to resolve it).
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from db.session import get_db  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
app.dependency_overrides[get_db] = lambda: MagicMock()


def _fake_user(email="a@b.com", role_name="analyst", user_id="user-1", full_name=None):
    role = MagicMock()
    role.name = role_name
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.full_name = full_name
    user.role = role
    user.is_active = True
    user.hashed_password = "hashed:secret123"
    return user


class TestRegister:
    def test_successful_registration_returns_token(self):
        with (
            patch("api.auth.get_user_by_email", new=AsyncMock(return_value=None)),
            patch("api.auth.create_user", new=AsyncMock(return_value=_fake_user())),
        ):
            response = client.post(
                "/auth/register",
                json={"email": "a@b.com", "password": "supersecret1", "full_name": "A B"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["role"] == "analyst"
        assert "access_token" in body

    def test_registration_always_grants_analyst_even_if_role_is_sent(self):
        # RegisterRequest has no `role` field at all, so sending one is
        # simply ignored by pydantic rather than accepted.
        with (
            patch("api.auth.get_user_by_email", new=AsyncMock(return_value=None)),
            patch("api.auth.create_user", new=AsyncMock(return_value=_fake_user())) as mock_create,
        ):
            client.post(
                "/auth/register",
                json={"email": "a@b.com", "password": "supersecret1", "role": "admin"},
            )
        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["role_name"] == "analyst"

    def test_duplicate_email_returns_409(self):
        with patch("api.auth.get_user_by_email", new=AsyncMock(return_value=_fake_user())):
            response = client.post(
                "/auth/register", json={"email": "a@b.com", "password": "supersecret1"}
            )
        assert response.status_code == 409

    def test_short_password_is_rejected_by_validation(self):
        response = client.post("/auth/register", json={"email": "a@b.com", "password": "short"})
        assert response.status_code == 422

    def test_invalid_email_is_rejected_by_validation(self):
        response = client.post(
            "/auth/register", json={"email": "not-an-email", "password": "supersecret1"}
        )
        assert response.status_code == 422


class TestLogin:
    def test_correct_credentials_returns_token_with_real_role(self):
        user = _fake_user(role_name="manager")
        with (
            patch("api.auth.get_user_by_email", new=AsyncMock(return_value=user)),
            patch("api.auth.verify_password", return_value=True),
        ):
            response = client.post("/auth/login", json={"email": "a@b.com", "password": "supersecret1"})

        assert response.status_code == 200
        assert response.json()["role"] == "manager"

    def test_wrong_password_returns_401(self):
        user = _fake_user()
        with (
            patch("api.auth.get_user_by_email", new=AsyncMock(return_value=user)),
            patch("api.auth.verify_password", return_value=False),
        ):
            response = client.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
        assert response.status_code == 401

    def test_unknown_email_returns_401_not_404(self):
        # Same status/message as a wrong password — see api/auth.py's
        # comment on why these must not be distinguishable.
        with patch("api.auth.get_user_by_email", new=AsyncMock(return_value=None)):
            response = client.post("/auth/login", json={"email": "nobody@b.com", "password": "x"})
        assert response.status_code == 401

    def test_inactive_user_returns_401(self):
        user = _fake_user()
        user.is_active = False
        with (
            patch("api.auth.get_user_by_email", new=AsyncMock(return_value=user)),
            patch("api.auth.verify_password", return_value=True),
        ):
            response = client.post("/auth/login", json={"email": "a@b.com", "password": "supersecret1"})
        assert response.status_code == 401
