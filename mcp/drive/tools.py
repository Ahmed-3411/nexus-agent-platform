"""
Tool implementations for the Google Drive MCP server.

All three tools are LOW risk by design: strictly read-only (the service
is built with the drive.readonly scope in auth.py, and no write/delete
operation is exposed here at all).
"""
from typing import Any

# MIME types Google treats as native Docs Editors files, which must be
# *exported* to a plain format rather than downloaded directly.
_EXPORTABLE_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

_MAX_CONTENT_CHARS = 20_000


def _escape_query_value(value: str) -> str:
    # Drive query strings use single quotes; escape any inside the value.
    return value.replace("'", "\\'")


def search_files(service, query: str, max_results: int = 20) -> dict[str, Any]:
    """
    Search Drive for files whose name or content matches the query.

    Risk level: LOW.
    """
    escaped = _escape_query_value(query)
    q = f"(name contains '{escaped}' or fullText contains '{escaped}') and trashed = false"

    response = (
        service.files()
        .list(
            q=q,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, size)",
        )
        .execute()
    )
    files = response.get("files", [])
    return {"count": len(files), "files": files}


def list_files(service, folder_id: str | None = None, page_size: int = 50) -> dict[str, Any]:
    """
    List files, optionally within a single folder.

    Risk level: LOW.
    """
    q = "trashed = false"
    if folder_id:
        q = f"'{_escape_query_value(folder_id)}' in parents and trashed = false"

    response = (
        service.files()
        .list(
            q=q,
            pageSize=page_size,
            fields="files(id, name, mimeType, modifiedTime, size)",
        )
        .execute()
    )
    files = response.get("files", [])
    return {"count": len(files), "files": files}


def read_file(service, file_id: str) -> dict[str, Any]:
    """
    Read a file's metadata and, where possible, its text content.

    Google Docs/Sheets/Slides are exported to plain text/CSV. Other
    files are downloaded directly and decoded as UTF-8 text when
    possible; binary files are reported with metadata only (no content).

    Risk level: LOW.
    """
    metadata = (
        service.files()
        .get(fileId=file_id, fields="id, name, mimeType, modifiedTime, size")
        .execute()
    )
    mime_type = metadata.get("mimeType", "")

    if mime_type in _EXPORTABLE_MIME_TYPES:
        export_mime = _EXPORTABLE_MIME_TYPES[mime_type]
        raw = service.files().export(fileId=file_id, mimeType=export_mime).execute()
    else:
        try:
            raw = service.files().get_media(fileId=file_id).execute()
        except Exception:
            raw = None

    content = None
    truncated = False
    if raw is not None:
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        if len(text) > _MAX_CONTENT_CHARS:
            text = text[:_MAX_CONTENT_CHARS]
            truncated = True
        content = text

    return {
        "id": metadata.get("id"),
        "name": metadata.get("name"),
        "mime_type": mime_type,
        "modified_time": metadata.get("modifiedTime"),
        "content": content,
        "truncated": truncated,
    }
