"""
Gmail MCP server.

Exposes four tools over MCP (using the official `mcp` SDK's FastMCP
helper), served over SSE on MCP_GMAIL_PORT (default 9102):

    - search_emails(query)              LOW risk
    - read_email(message_id)            MEDIUM risk
    - draft_email(to, subject, body)    MEDIUM risk
    - send_email(to, subject, body)     HIGH risk, requires_approval=True

send_email performs the send immediately once called — this server does
NOT itself enforce human approval. In production, the Policy Engine in
front of the MCP Gateway (Phase 3/5) must gate any call to send_email on
an approved request; this server should never be reachable directly by
an agent.

Run standalone (requires GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET /
GMAIL_REFRESH_TOKEN in the environment, see auth.py):
    python server.py

Inside docker-compose this file is the container's CMD (see Dockerfile).
"""
import os

from mcp.server.fastmcp import FastMCP

import tools as gmail_tools
from auth import get_gmail_service

PORT = int(os.environ.get("MCP_GMAIL_PORT", "9102"))

mcp = FastMCP("gmail-mcp", host="0.0.0.0", port=PORT)


@mcp.tool()
async def search_emails(query: str) -> dict:
    """Search the mailbox and return matching message ids."""
    service = get_gmail_service()
    return gmail_tools.search_emails(service, query)


@mcp.tool()
async def read_email(message_id: str) -> dict:
    """Read a single email by id, returning key headers and a snippet."""
    service = get_gmail_service()
    return gmail_tools.read_email(service, message_id)


@mcp.tool()
async def draft_email(to: str, subject: str, body: str) -> dict:
    """Create a draft email. Does not send anything."""
    service = get_gmail_service()
    return gmail_tools.draft_email(service, to, subject, body)


@mcp.tool()
async def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email immediately. HIGH risk — must be gated by human approval upstream."""
    service = get_gmail_service()
    return gmail_tools.send_email(service, to, subject, body)


if __name__ == "__main__":
    print(f"[mcp-gmail] starting on 0.0.0.0:{PORT}")
    mcp.run(transport="sse")
