"""
Tool implementations for the Gmail MCP server.

Risk levels (see backend/db/schema.sql seed data):
    search_emails -> LOW
    read_email    -> MEDIUM
    draft_email   -> MEDIUM
    send_email    -> HIGH, requires_approval=True

This server performs the Gmail action as soon as it's called — it does
NOT itself enforce human approval. That enforcement belongs to the Policy
Engine sitting in front of the MCP Gateway (Phase 3 / Phase 5); this
server should never be reachable directly by an agent in production, and
send_email in particular must only be invoked after an approval step.
"""
import base64
from email.mime.text import MIMEText
from typing import Any


def search_emails(service, query: str, max_results: int = 20) -> dict[str, Any]:
    """
    Search the mailbox and return matching message ids.

    Risk level: LOW.
    """
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = response.get("messages", [])
    return {"count": len(messages), "message_ids": [m["id"] for m in messages]}


def read_email(service, message_id: str) -> dict[str, Any]:
    """
    Read a single email by id, returning key headers and a snippet.

    Risk level: MEDIUM.
    """
    msg = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        )
        .execute()
    )

    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "snippet": msg.get("snippet"),
        "from": headers.get("From"),
        "to": headers.get("To"),
        "subject": headers.get("Subject"),
        "date": headers.get("Date"),
    }


def _build_raw_message(to: str, subject: str, body: str) -> dict[str, str]:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def draft_email(service, to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Create a draft email. Does not send anything.

    Risk level: MEDIUM.
    """
    draft_body = {"message": _build_raw_message(to, subject, body)}
    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return {
        "draft_id": draft.get("id"),
        "message_id": draft.get("message", {}).get("id"),
    }


def send_email(service, to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Send an email immediately.

    Risk level: HIGH — requires_approval=True. In production this call
    must only be reached after the Policy Engine has confirmed human
    approval (Phase 5). This function itself performs no approval check.
    """
    message = _build_raw_message(to, subject, body)
    sent = service.users().messages().send(userId="me", body=message).execute()
    return {"message_id": sent.get("id"), "thread_id": sent.get("threadId")}
