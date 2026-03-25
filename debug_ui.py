import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Mock configuration and state
from phase6_approval.approval_ui import app, launch_approval_ui

class MockConfig:
    google_doc_id = "mock_doc_id"
    mcp_command = "npx"
    mcp_args = "-y @modelcontextprotocol/server-everything"
    gmail_user = "mock@gmail.com"
    email_to = "mock_to@gmail.com"
    google_docs_credentials = "{}"
    gmail_app_password = "mock"
    gmail_client_id = "mock"
    gmail_client_secret = "mock"
    gmail_refresh_token = "mock"

mock_config = MockConfig()
mock_pulse_note = "## Mock Pulse\nThis is a mock note for UI verification."
mock_themes = []
mock_action_ideas = []

if __name__ == "__main__":
    print("🚀 Launching Analytics Debug UI...")
    launch_approval_ui(
        config=mock_config,
        router=None,
        pulse_note=mock_pulse_note,
        themes=mock_themes,
        action_ideas=mock_action_ideas,
        review_count=100,
        port=5051
    )
