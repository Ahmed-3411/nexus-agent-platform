"""
Unit tests for the Drive MCP server's tool logic.

These tests mock the Drive API service entirely — no real Google
credentials or network access are needed to run them.

Requires: pip install -r mcp/drive/requirements.txt pytest pytest-asyncio

Run from the repo root:
    pytest tests/unit/test_drive_mcp_tools.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import importlib.util

_TOOLS_PATH = Path(__file__).resolve().parents[2] / "mcp/drive/tools.py"
_SPEC = importlib.util.spec_from_file_location("_test_drive_tools_module", _TOOLS_PATH)
assert _SPEC is not None and _SPEC.loader is not None
drive_tools = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(drive_tools)


def _make_fake_service(list_result=None, get_result=None, export_result=None, media_result=None):
    service = MagicMock()
    files = service.files.return_value
    if list_result is not None:
        files.list.return_value.execute.return_value = list_result
    if get_result is not None:
        files.get.return_value.execute.return_value = get_result
    if export_result is not None:
        files.export.return_value.execute.return_value = export_result
    if media_result is not None:
        files.get_media.return_value.execute.return_value = media_result
    return service


class TestSearchFiles:
    def test_returns_matching_files(self):
        service = _make_fake_service(
            list_result={
                "files": [
                    {"id": "f1", "name": "Q3 Report.docx", "mimeType": "application/vnd.google-apps.document"},
                ]
            }
        )
        result = drive_tools.search_files(service, "Q3 Report")
        assert result["count"] == 1
        assert result["files"][0]["id"] == "f1"

    def test_escapes_single_quotes_in_query(self):
        service = _make_fake_service(list_result={"files": []})
        drive_tools.search_files(service, "customer's file")
        call_kwargs = service.files.return_value.list.call_args.kwargs
        assert "\\'" in call_kwargs["q"]

    def test_no_results(self):
        service = _make_fake_service(list_result={})
        result = drive_tools.search_files(service, "nonexistent")
        assert result == {"count": 0, "files": []}


class TestListFiles:
    def test_lists_files_in_folder(self):
        service = _make_fake_service(
            list_result={"files": [{"id": "f1", "name": "a.txt"}, {"id": "f2", "name": "b.txt"}]}
        )
        result = drive_tools.list_files(service, folder_id="folder123")
        assert result["count"] == 2
        call_kwargs = service.files.return_value.list.call_args.kwargs
        assert "folder123" in call_kwargs["q"]

    def test_lists_all_files_without_folder(self):
        service = _make_fake_service(list_result={"files": []})
        drive_tools.list_files(service)
        call_kwargs = service.files.return_value.list.call_args.kwargs
        assert "in parents" not in call_kwargs["q"]


class TestReadFile:
    def test_exports_google_doc_as_text(self):
        service = _make_fake_service(
            get_result={
                "id": "doc1",
                "name": "Notes",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2026-01-01T00:00:00Z",
            },
            export_result=b"Hello from a Google Doc.",
        )
        result = drive_tools.read_file(service, "doc1")

        assert result["name"] == "Notes"
        assert result["content"] == "Hello from a Google Doc."
        assert result["truncated"] is False
        service.files.return_value.export.assert_called_once()
        service.files.return_value.get_media.assert_not_called()

    def test_reads_plain_text_file_via_get_media(self):
        service = _make_fake_service(
            get_result={"id": "f1", "name": "notes.txt", "mimeType": "text/plain"},
            media_result=b"plain file contents",
        )
        result = drive_tools.read_file(service, "f1")

        assert result["content"] == "plain file contents"
        service.files.return_value.get_media.assert_called_once()
        service.files.return_value.export.assert_not_called()

    def test_truncates_long_content(self):
        long_text = ("x" * 25_000).encode()
        service = _make_fake_service(
            get_result={"id": "f1", "name": "big.txt", "mimeType": "text/plain"},
            media_result=long_text,
        )
        result = drive_tools.read_file(service, "f1")

        assert result["truncated"] is True
        assert len(result["content"]) == 20_000

    def test_binary_file_without_media_returns_no_content(self):
        service = _make_fake_service(
            get_result={"id": "f1", "name": "image.png", "mimeType": "image/png"},
        )
        service.files.return_value.get_media.return_value.execute.side_effect = Exception("not text")

        result = drive_tools.read_file(service, "f1")

        assert result["content"] is None
