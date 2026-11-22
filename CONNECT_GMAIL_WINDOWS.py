"""One-time OAuth setup for the native gmail_control plugin."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'config' / 'gmail_credentials.json'
TOKEN = ROOT / 'config' / 'gmail_token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.compose']


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print('Install dependencies first: py -3.12 -m pip install google-api-python-client google-auth-oauthlib')
        return 1
    if not CLIENT.is_file():
        print(f'Missing Google OAuth Desktop client JSON:\n  {CLIENT}\n')
        print('Google Cloud -> enable Gmail API -> OAuth consent -> OAuth Client ID (Desktop app) -> download JSON')
        print('Save that downloaded file as config/gmail_credentials.json, then run this script again.')
        return 1
    import json
    try:
        data = json.loads(CLIENT.read_text(encoding='utf-8'))
        if 'installed' not in data:
            print('The JSON must be an OAuth Desktop app credential, not an API key or service account.')
            return 1
    except (OSError, ValueError):
        print('Could not read gmail_credentials.json. Download the Desktop OAuth client JSON again.')
        return 1
    print('Opening Google sign-in. Google may show an unverified-app notice during private testing.')
    print('A temporary 127.0.0.1 OAuth callback is used only for login; no Gmail server runs after sign-in.')
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
    creds = flow.run_local_server(host='127.0.0.1', port=0, open_browser=True,
                                  authorization_prompt_message='Open this URL to sign in: {url}')
    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(creds.to_json(), encoding='utf-8')
    try:
        if os.name != 'nt': os.chmod(TOKEN, 0o600)
    except OSError:
        pass
    print('Gmail connected successfully. Start main.py and enable gmail_control in Plugin Settings.')
    print('Keep config/gmail_credentials.json and config/gmail_token.json private.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
