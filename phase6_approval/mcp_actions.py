"""
Phase 6 — MCP Actions (Notes + Gmail Draft)

Downstream delivery actions triggered only after human approval.
Email drafts are created in the user's actual Gmail account via the Gmail API.
"""

import json
import base64
import os
import logging
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import imaplib
import time

logger = logging.getLogger(__name__)


def append_to_notes(google_doc_id: str, pulse_note: str,
                    themes: list, review_count: int,
                    fee_explanation: dict | None = None) -> str:
    """
    Append the weekly pulse to a Google Document via the MCP Server.

    Returns the google_doc_id on success.
    """
    if not google_doc_id:
        raise ValueError("google_doc_id is missing.")

    # Assemble the content block to append
    content = f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
    content += f"Reviews Analysed: {review_count}\n\n"
    content += pulse_note + "\n"

    if fee_explanation:
        content += "\n\n---\n\n"
        content += f"## 💰 Fee Explainer: {fee_explanation.get('scenario', '')}\n\n"
        for bullet in fee_explanation.get("bullets", []):
            content += f"- {bullet}\n"
        content += "\n**Sources:**\n"
        for link in fee_explanation.get("source_links", []):
            content += f"- {link}\n"
        content += f"\n*Last checked: {fee_explanation.get('last_checked', '')}*\n"

    import sys
    command = os.getenv("MCP_COMMAND", "npx")
    if command == "python":
        command = sys.executable
        
    # Parse comma separated args from env if multiple are needed
    args_str = os.getenv("MCP_ARGS", "-y,@modelcontextprotocol/server-everything")
    args = args_str.split(",")

    async def _run_mcp():
        server_params = StdioServerParameters(command=command, args=args)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Call the downstream tool exposed by the local MCP server
                # Uses internal google_docs_mcp.py tool 'append_to_doc'
                result = await session.call_tool("append_to_doc", arguments={
                    "document_id": google_doc_id,
                    "content": content
                })
                return result

    try:
        asyncio.run(_run_mcp())
        logger.info(f"Appended notes to Google Doc ID: {google_doc_id}")
    except Exception as e:
        logger.error(f"Failed to append to Google Doc via MCP: {e}")
        raise RuntimeError(f"MCP Action Failed: {e}")

    return google_doc_id


def create_email_draft(pulse_note: str, email_to: str,
                       gmail_user: str, gmail_app_password: str,
                       fee_explanation: dict | None = None) -> str:
    """
    Create a real email draft in the user's Gmail Drafts folder via IMAP.

    Returns a success message with the subject.
    """
    if not gmail_user or not gmail_app_password:
        raise ValueError("GMAIL_USER or GMAIL_APP_PASSWORD is not set. Cannot create draft.")

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"Weekly Pulse — INDMoney — {today}"

    body = pulse_note or ""

    if fee_explanation:
        body += "\n\n---\n\n"
        body += f"## 💰 Fee Explainer: {fee_explanation.get('scenario', '')}\n\n"
        for bullet in fee_explanation.get("bullets", []):
            body += f"- {bullet}\n"
        body += "\n**Sources:**\n"
        for link in fee_explanation.get("source_links", []):
            body += f"- {link}\n"
        body += f"\n*Last checked: {fee_explanation.get('last_checked', today)}*\n"

    # Build MIME message
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["To"] = email_to
    msg["From"] = gmail_user
    # X-Unsent is required by many email clients to treat this as a draft
    msg["X-Unsent"] = "1"

    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_app_password)
        
        # Append to the drafts folder
        # Note: In Gmail, the drafts folder is usually "[Gmail]/Drafts"
        draft_folder = '"[Gmail]/Drafts"'
        internal_date = imaplib.Time2Internaldate(time.time())
        
        # Append message
        status, response = mail.append(
            draft_folder,
            '',  # Flags (empty string means default)
            internal_date,
            msg.as_bytes()
        )
        
        if status != "OK":
            raise RuntimeError(f"IMAP append failed: {response}")
            
        mail.logout()
        logger.info(f"Gmail draft created via IMAP: {subject}")
        return subject
        
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP authentication failed. Ensure App Password is correct. Error: {e}")
        raise RuntimeError(f"Failed to authenticate with Gmail via IMAP: {e}")

