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

# Tracking last error for production debugging
LAST_MCP_ERROR = None

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import imaplib
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def append_to_notes(google_doc_id: str, pulse_note: str,
                    themes: list, review_count: int,
                    mcp_command: str = "python",
                    mcp_args: list[str] = None,
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
    command = mcp_command or "python"
    if command == "python":
        command = sys.executable
        
    args = mcp_args or ["phase6_approval/google_docs_mcp.py"]

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
        global LAST_MCP_ERROR
        result = asyncio.run(_run_mcp())
        # The result is a CallToolResult. Check content for error messages.
        if hasattr(result, "content") and result.content:
            for item in result.content:
                text = item.text if hasattr(item, "text") else str(item)
                if "Error" in text or "Exception" in text or "failed" in text.lower():
                    LAST_MCP_ERROR = text
                    raise RuntimeError(text)
        
        logger.info(f"Appended notes to Google Doc ID: {google_doc_id}")
    except Exception as e:
        LAST_MCP_ERROR = str(e)
        logger.error(f"Failed to append to Google Doc via MCP: {e}")
        raise RuntimeError(f"MCP Action Failed: {e}")

    return google_doc_id


def create_email_draft(pulse_note: str, email_to: str,
                       gmail_user: str, gmail_app_password: str,
                       fee_explanation: dict | None = None) -> str:
    """
    Create a real email draft in the user's Gmail Drafts folder via API or IMAP.

    Returns a success message with the subject.
    """
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

    # Try OAuth2 / Gmail API first (HTTPS)
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")

    if refresh_token and client_id and client_secret:
        try:
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=["https://www.googleapis.com/auth/gmail.compose"]
            )
            service = build("gmail", "v1", credentials=creds)
            
            # Create the message
            import base64
            from email.message import EmailMessage
            
            email_msg = EmailMessage()
            email_msg.set_content(body)
            email_msg["To"] = email_to
            email_msg["From"] = gmail_user
            email_msg["Subject"] = subject
            
            encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()
            create_message = {"message": {"raw": encoded_message}}
            
            draft = service.users().drafts().create(userId="me", body=create_message).execute()
            logger.info(f"Gmail draft created via API: {draft['id']}")
            return subject
        except Exception as e:
            logger.error(f"Gmail API failed, falling back to IMAP if possible. Error: {e}")

    # Fallback to IMAP (original logic)
    if not gmail_user or not gmail_app_password:
        raise ValueError("Neither GMAIL_REFRESH_TOKEN nor GMAIL_APP_PASSWORD is set. Cannot create draft.")

    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_app_password)
        
        # Append to the drafts folder
        draft_folder = '"[Gmail]/Drafts"'
        internal_date = imaplib.Time2Internaldate(time.time())
        
        # Build MIME message (re-build for IMAP compatibility)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["To"] = email_to
        msg["From"] = gmail_user
        msg["X-Unsent"] = "1"

        status, response = mail.append(
            draft_folder,
            '',  # Flags
            internal_date,
            msg.as_bytes()
        )
        
        if status != "OK":
            raise RuntimeError(f"IMAP append failed: {response}")
            
        mail.logout()
        logger.info(f"Gmail draft created via IMAP: {subject}")
        return subject
        
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP authentication failed. Error: {e}")
        raise RuntimeError(f"Failed to authenticate with Gmail: {e}")

