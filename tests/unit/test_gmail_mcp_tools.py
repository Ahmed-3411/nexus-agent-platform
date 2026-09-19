"""
Unit tests for the Gmail MCP server's tool logic.

These tests mock the Gmail API service entirely — no real Gmail
credentials or network access are needed to run them.

Requires: pip install -r mcp/gmail/requirements.txt pytest pytest-asyncio

Run from the repo root:
    pytest tests/unit/test_gmail_mcp_tools.py -v
"""
import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import importlib.util

_TOOLS_PATH = Path(__file__).resolve().parents[2] / "mcp/gmail/tools.py"
_SPEC = importlib.util.spec_from_file_location("_test_gmail_tools_module", _TOOLS_PATH)
assert _SPEC is not None and _SPEC.loader is not None
gmail_tools = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gmail_tools)


def _make_fake_service(execute_result):
    """
    Build a fake Gmail API service whose deeply chained
    `.users().messages()....execute()` calls return `execute_result`.
    """
    service = MagicMock()
    # Every chained method call returns another MagicMock, so we just
    # need to control what the final .execute() returns.
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = execute_result
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = execute_result
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = execute_result
    service.users.return_value.drafts.return_value.create.return_value.execute.return_value = execute_result
    return service


class TestSearchEmails:
    def test_returns_message_ids_and_count(self):
        service = _make_fake_service({"messages": [{"id": "a1"}, {"id": "a2"}]})

        result = gmail_tools.search_emails(service, "from:boss@example.com")

        assert result["count"] == 2
        assert result["message_ids"] == ["a1", "a2"]

    def test_handles_no_results(self):
        service = _make_fake_service({})

        result = gmail_tools.search_emails(service, "subject:doesnotexist")

        assert result["count"] == 0
        assert result["message_ids"] == []


class TestReadEmail:
    def test_extracts_headers_and_snippet(self):
        raw_message = {
            "id": "msg123",
            "threadId": "thread456",
            "snippet": "Hey, just checking in...",
            "payload": {
                "headers": [
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Subject", "value": "Quick question"},
                    {"name": "Date", "value": "Mon, 14 Sep 2026 10:00:00 +0000"},
                ]
            },
        }
        service = _make_fake_service(raw_message)

        result = gmail_tools.read_email(service, "msg123")

        assert result["id"] == "msg123"
        assert result["thread_id"] == "thread456"
        assert result["from"] == "alice@example.com"
        assert result["to"] == "bob@example.com"
        assert result["subject"] == "Quick question"
        assert result["snippet"] == "Hey, just checking in..."


class TestBuildRawMessage:
    def test_encodes_to_subject_and_body(self):
        built = gmail_tools._build_raw_message(
            "carol@example.com", "Hello", "This is the body."
        )
        decoded = base64.urlsafe_b64decode(built["raw"]).decode()

        assert "carol@example.com" in decoded
        assert "Hello" in decoded
        assert "This is the body." in decoded


class TestDraftEmail:
    def test_returns_draft_and_message_id(self):
        service = _make_fake_service({"id": "draft1", "message": {"id": "msg1"}})

        result = gmail_tools.draft_email(
            service, "dave@example.com", "Subject line", "Body text"
        )

        assert result["draft_id"] == "draft1"
        assert result["message_id"] == "msg1"


class TestSendEmail:
    def test_returns_sent_message_and_thread_id(self):
        service = _make_fake_service({"id": "sent1", "threadId": "thread1"})

        result = gmail_tools.send_email(
            service, "eve@example.com", "Important", "Final body"
        )

        assert result["message_id"] == "sent1"
        assert result["thread_id"] == "thread1"

    def test_send_actually_calls_the_send_endpoint(self):
        """
        Guard against accidentally wiring send_email to draft or another
        endpoint — a HIGH-risk tool must call exactly what it says it does.
        """
        service = _make_fake_service({"id": "sent1", "threadId": "thread1"})

        gmail_tools.send_email(service, "eve@example.com", "Important", "Final body")

        service.users.return_value.messages.return_value.send.assert_called_once()
        service.users.return_value.drafts.return_value.create.assert_not_called()
