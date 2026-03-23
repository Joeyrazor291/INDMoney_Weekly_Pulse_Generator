import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

def main():
    """
    Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    print("\n--- Gmail API Token Generator ---")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a project and enable 'Gmail API'.")
    print("3. Go to 'Credentials' > 'Create Credentials' > 'OAuth client ID'.")
    print("4. Select Application type: 'Desktop app' (or 'Internal').")
    print("5. Download the JSON file and rename it to 'client_secrets.json' in this folder.\n")

    if not os.path.exists('client_secrets.json'):
        print("Error: 'client_secrets.json' not found. Please follow the steps above.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n--- SUCCESS! Copy these 3 values to your Hugging Face Secrets ---")
    print(f"GMAIL_CLIENT_ID: {creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET: {creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN: {creds.refresh_token}")
    print("-----------------------------------------------------------------\n")

if __name__ == '__main__':
    main()
