import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def read_doc():
    creds_path = "/Users/talasuSubudhi/Gen AI Projects/INDMoney_Pulse_Generator/google_credentials.json"
    doc_id = "1ixFN5nneYrmhdKjbUovKWiAl1AS-OwLc_LLphIdVWbU"
    
    creds = service_account.Credentials.from_service_account_file(creds_path)
    service = build('docs', 'v1', credentials=creds)
    
    doc = service.documents().get(documentId=doc_id).execute()
    body = doc.get('body').get('content')
    
    full_text = ""
    for element in body:
        if 'paragraph' in element:
            for run in element.get('paragraph').get('elements'):
                full_text += run.get('textRun', {}).get('content', '')
    
    print(f"--- DOC CONTENT (Length: {len(full_text)}) ---")
    print(full_text[:2000])
    print("--- END CONTENT ---")

if __name__ == "__main__":
    read_doc()
