"""
Google Drive OAuth2 credential management for the Drive MCP server.

Like the Gmail server, this module only *uses* a refresh token obtained
once via an OAuth consent flow (one-time setup out of scope here — see
Google's "Desktop app" OAuth quickstart to obtain DRIVE_CLIENT_ID /
DRIVE_CLIENT_SECRET / DRIVE_REFRESH_TOKEN).
"""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Read-only scope only — this server never writes to Drive.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_service = None


def get_drive_service():
    """Return a cached, authenticated Drive API service client."""
    global _service
    if _service is not None:
        return _service

    client_id = os.environ.get("DRIVE_CLIENT_ID")
    client_secret = os.environ.get("DRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("DRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "Drive credentials are not configured. Set DRIVE_CLIENT_ID, "
            "DRIVE_CLIENT_SECRET, and DRIVE_REFRESH_TOKEN in the environment."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )

    _service = build("drive", "v3", credentials=creds)
    return _service


def reset_service_cache() -> None:
    """Force a fresh service to be built on the next call. Used by tests."""
    global _service
    _service = None
