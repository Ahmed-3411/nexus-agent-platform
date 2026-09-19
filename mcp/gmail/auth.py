"""
Gmail OAuth2 credential management for the Gmail MCP server.

This module only *uses* a refresh token that was obtained once via an
OAuth consent flow (that one-time setup is out of scope for this server —
see Google's "Desktop app" OAuth quickstart to obtain
GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN).
"""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]

_service = None


def get_gmail_service():
    """Return a cached, authenticated Gmail API service client."""
    global _service
    if _service is not None:
        return _service

    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "Gmail credentials are not configured. Set GMAIL_CLIENT_ID, "
            "GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN in the environment."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )

    _service = build("gmail", "v1", credentials=creds)
    return _service


def reset_service_cache() -> None:
    """Force a fresh service to be built on the next call. Used by tests."""
    global _service
    _service = None
