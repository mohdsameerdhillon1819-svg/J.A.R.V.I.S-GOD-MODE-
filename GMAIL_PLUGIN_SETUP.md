# Gmail plugin for JARVIS Mark-LVII

Native `gmail_control` plugin. It uses Google OAuth (not your password), without a permanently running Gmail server.

## One-time setup in VS Code (Windows)

1. Open the project folder in VS Code and open **Terminal → New Terminal**.
2. Install dependencies:
   ```powershell
   py -3.12 -m pip install google-api-python-client google-auth-oauthlib
   ```
3. Open https://console.cloud.google.com/ and create/select your own Google Cloud project.
4. In **APIs & Services → Library**, enable **Gmail API**.
5. In **Google Auth Platform** (OAuth consent), configure the consent screen. If the app is in testing mode, add **your Gmail address as a test user**. Select the minimum necessary access: Gmail read-only and Gmail compose. Google may require app verification for wider public deployment.
6. Under **Clients**, create **OAuth client ID → Desktop app**. Download the OAuth client JSON. **This is not an API key.**
7. Rename the downloaded JSON to `gmail_credentials.json` and place it at `Mark-LVII/config/gmail_credentials.json`.
8. Run:
   ```powershell
   py -3.12 CONNECT_GMAIL_WINDOWS.py
   ```
   Sign into your own Google account in the browser and approve the requested permissions. A temporary localhost callback is used for sign-in only and stops automatically.
9. Start the assistant:
   ```powershell
   py -3.12 main.py
   ```
10. Enable **gmail_control** in JARVIS **Plugin Settings**.

## Example voice commands

- "Jarvis, check my last five inbox emails."
- "Jarvis, search Gmail for messages from my school."
- "Jarvis, read Gmail message ID ..."
- "Jarvis, create a Gmail draft to someone@example.com with subject Project and body Hello."
- "Jarvis, prepare to send Gmail draft ..."
- After reviewing the draft details, **explicitly repeat the one-time confirmation code** to send it.

## Safety and privacy

- No mail is automatically sent. `prepare_send` generates a short-lived one-use code; `send` requires it.
- Send operation is limited to previously created draft IDs and explicit user confirmation.
- Google OAuth tokens are stored **locally** in `config/gmail_token.json` and excluded from Git. Treat it like a password.
- The Google OAuth Desktop client JSON is also excluded from Git. Never share either file.
- Message text is limited in JARVIS tool output to prevent oversized voice replies.
- The Gmail plugin makes requests to Google's Gmail API; it does not store or copy emails to a separate remote service.
- Google may require additional app verification depending on OAuth publishing and use. Gmail and network connectivity must be tested on your PC.

Official Google reference: https://developers.google.com/workspace/gmail/api/quickstart/python
