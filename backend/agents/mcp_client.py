"""MCP SSE client with stable result and error normalization."""
from __future__ import annotations

import json
import re
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

from core.config import get_settings

settings = get_settings()

_SERVER_URLS: dict[str, str] = {
    "postgres": settings.mcp_postgres_url,
    "gmail": settings.mcp_gmail_url,
    "drive": settings.mcp_drive_url,
}

_SECRET_PATTERNS = (
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"), "[REDACTED_API_KEY]"),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|jwt[_-]?secret|password)"
            r"(\s*[:=]\s*)[^\s,;]+"
        ),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^\s:/]+:)[^\s@/]+(@)"), r"\1[REDACTED]\2"),
)


def _server_url(server: str) -> str:
    if server not in _SERVER_URLS:
        raise KeyError(f"Unknown MCP server '{server}'.")
    return _SERVER_URLS[server]


def _sanitize_error_text(value: Any) -> str:
    text = str(value).strip() or "Unknown MCP error"
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:4000]


def _exception_leaf_messages(exc: BaseException) -> list[str]:
    nested = getattr(exc, "exceptions", None)
    if isinstance(nested, (list, tuple)) and nested:
        messages: list[str] = []
        for child in nested:
            if isinstance(child, BaseException):
                messages.extend(_exception_leaf_messages(child))
        if messages:
            return messages

    cause = exc.__cause__ or exc.__context__
    own = str(exc).strip()
    if cause is not None and cause is not exc:
        child_messages = _exception_leaf_messages(cause)
        if child_messages and (not own or "TaskGroup" in own or "ExceptionGroup" in own):
            return child_messages
    return [own or type(exc).__name__]


def format_exception(exc: BaseException) -> str:
    """Flatten ExceptionGroup/TaskGroup wrappers and redact sensitive values."""
    messages: list[str] = []
    for message in _exception_leaf_messages(exc):
        safe = _sanitize_error_text(message)
        if safe not in messages:
            messages.append(safe)
    return "; ".join(messages) or type(exc).__name__


def _parse_tool_result(result: Any) -> Any:
    """Parse MCP text content into plain Python data (legacy helper)."""
    content = getattr(result, "content", None)
    if not content:
        return None

    parsed_blocks: list[Any] = []
    for block in content:
        text = getattr(block, "text", None)
        if text is None:
            parsed_blocks.append(block)
            continue
        try:
            parsed_blocks.append(json.loads(text))
        except (TypeError, ValueError):
            parsed_blocks.append(text)
    return parsed_blocks[0] if len(parsed_blocks) == 1 else parsed_blocks


def _error_from_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("error", "detail", "message"):
            value = payload.get(key)
            if value:
                return _sanitize_error_text(value)
        return _sanitize_error_text(json.dumps(payload, default=str))
    if isinstance(payload, list):
        return _sanitize_error_text("; ".join(str(item) for item in payload))
    return _sanitize_error_text(payload)


def failure_result(server: str, tool_name: str, error: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": _sanitize_error_text(error),
        "tool_name": tool_name,
        "server": server,
    }


def normalize_tool_result(result: Any, server: str, tool_name: str) -> dict[str, Any]:
    """Convert every MCP result into a predictable JSON-serializable dict."""
    structured = getattr(result, "structuredContent", None)
    if not isinstance(structured, (dict, list, str, int, float, bool, type(None))):
        structured = getattr(result, "structured_content", None)
    if not isinstance(structured, (dict, list, str, int, float, bool, type(None))):
        structured = None
    content_payload = _parse_tool_result(result)
    payload = structured if structured not in (None, {}, []) else content_payload

    if getattr(result, "isError", False) is True:
        return failure_result(server, tool_name, _error_from_payload(payload))

    if payload is None:
        return failure_result(server, tool_name, "MCP tool returned no content")

    if isinstance(payload, dict):
        if payload.get("ok") is False or payload.get("error"):
            return failure_result(server, tool_name, _error_from_payload(payload))
        normalized = dict(payload)
        normalized.setdefault("ok", True)
        normalized.setdefault("tool_name", tool_name)
        normalized.setdefault("server", server)
        return normalized

    # Plain text from a tool is most often FastMCP's serialized exception.
    if isinstance(payload, str):
        return failure_result(server, tool_name, payload)

    return {
        "ok": True,
        "data": payload,
        "tool_name": tool_name,
        "server": server,
    }


async def call_tool(server: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call one MCP tool and return a structured success or failure dict."""
    try:
        url = _server_url(server)
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
        return normalize_tool_result(result, server, tool_name)
    except Exception as exc:  # transport/tool failures belong in workflow state, not HTTP 500
        return failure_result(server, tool_name, format_exception(exc))
