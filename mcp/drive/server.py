"""
Google Drive MCP server.

Exposes three read-only tools over MCP (using the official `mcp` SDK's
FastMCP helper), served over SSE on MCP_DRIVE_PORT (default 9103):

    - search_files(query)              LOW risk
    - list_files(folder_id)            LOW risk
    - read_file(file_id)               LOW risk

No write, delete, or share operation is exposed by this server at all —
the underlying credentials are scoped to drive.readonly (see auth.py).

Run standalone (requires DRIVE_CLIENT_ID / DRIVE_CLIENT_SECRET /
DRIVE_REFRESH_TOKEN in the environment, see auth.py):
    python server.py

Inside docker-compose this file is the container's CMD (see Dockerfile).
"""
import os

from mcp.server.fastmcp import FastMCP

import tools as drive_tools
from auth import get_drive_service

PORT = int(os.environ.get("MCP_DRIVE_PORT", "9103"))

mcp = FastMCP("drive-mcp", host="0.0.0.0", port=PORT)


@mcp.tool()
async def search_files(query: str) -> dict:
    """Search Drive for files whose name or content matches the query."""
    service = get_drive_service()
    return drive_tools.search_files(service, query)


@mcp.tool()
async def list_files(folder_id: str | None = None) -> dict:
    """List files, optionally within a single folder (by folder_id)."""
    service = get_drive_service()
    return drive_tools.list_files(service, folder_id)


@mcp.tool()
async def read_file(file_id: str) -> dict:
    """Read a file's metadata and, where possible, its text content."""
    service = get_drive_service()
    return drive_tools.read_file(service, file_id)


if __name__ == "__main__":
    print(f"[mcp-drive] starting on 0.0.0.0:{PORT}")
    mcp.run(transport="sse")
