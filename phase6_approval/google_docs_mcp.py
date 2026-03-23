import os
import json
import logging
from typing import Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("google-docs-mcp")

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Google Docs (Internal)")

def get_docs_service():
    """Authenticate and return the Google Docs API service."""
    creds_json = os.getenv("GOOGLE_DOCS_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_DOCS_CREDENTIALS not found in .env")
    
    try:
        # Some users might paste it with extra quotes or as a path
        if creds_json.startswith("{"):
            info = json.loads(creds_json)
        else:
            # Assume it's a file path
            with open(creds_json, 'r') as f:
                info = json.load(f)
                
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/documents"]
        )
        return build("docs", "v1", credentials=credentials)
    except Exception as e:
        logger.error(f"Failed to authenticate Google Docs Service: {e}")
        raise

@mcp.tool()
async def append_to_doc(document_id: str, content: str) -> str:
    """
    Append text to the end of a Google Document.
    
    Args:
        document_id: The ID of the Google Doc (from the URL).
        content: The text content to append.
    """
    logger.info(f"Appending content to Doc ID: {document_id}")
    service = get_docs_service()
    
    try:
        # We now use index 1 (beginning of document) to ensure 
        # the user always sees the latest updates at the top!
        target_index = 1
        
        # Prepare the batchUpdate request to prepend text
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': target_index,
                    },
                    'text': content
                }
            }
        ]
        
        service.documents().batchUpdate(
            documentId=document_id, 
            body={'requests': requests}
        ).execute()
        
        return f"Successfully appended {len(content)} characters to Doc {document_id}"
        
    except Exception as e:
        import googleapiclient.errors
        error_msg = str(e)
        if isinstance(e, googleapiclient.errors.HttpError):
            if e.resp.status == 404:
                error_msg = f"Document not found ({document_id}). Please check your GOOGLE_DOC_ID secret for typos (e.g., 'I' vs 'l')."
            elif e.resp.status == 403:
                error_msg = f"Permission denied for Doc {document_id}. Please share the document with: pulse-generator@indmoney-pulse.iam.gserviceaccount.com"
        
        logger.error(f"Error appending to Google Doc: {error_msg}")
        return f"Error: {error_msg}"

if __name__ == "__main__":
    # Run the server using the fastmcp runner
    mcp.run()
