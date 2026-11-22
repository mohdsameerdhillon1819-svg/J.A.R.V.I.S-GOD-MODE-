"""Native JARVIS Gmail plugin using Google OAuth 2.0 (never a Gmail password).

Requires CONNECT_GMAIL_WINDOWS.py once and optional pip dependencies.
No email is sent without an explicit, short-lived confirmation code.
"""
from __future__ import annotations

import base64
import re
import secrets
import threading
import time
from email.message import EmailMessage
from email.utils import getaddresses
from html import unescape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OAUTH_TOKEN = PROJECT_ROOT / 'config' / 'gmail_token.json'
OAUTH_CLIENT = PROJECT_ROOT / 'config' / 'gmail_credentials.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.compose']

PLUGIN = {
    'name': 'gmail_control',
    'description': (
        'Use for Gmail inbox, check email, find emails, read an email, create a Gmail draft, '
        'prepare to send a Gmail draft or confirm sending it. Requires Google OAuth setup. '
        'Never send without user-provided one-time confirmation code.'
    ),
    'parameters': {'type': 'OBJECT', 'properties': {
        'action': {'type': 'STRING', 'enum': ['status','inbox','search','read','draft','prepare_send','send'],
                   'description': 'Use prepare_send before send; send needs a code typed or spoken by the user.'},
        'query': {'type': 'STRING', 'description': 'Gmail search query, e.g. from:person@example.com or is:unread'},
        'message_id': {'type': 'STRING', 'description': 'Exact Gmail message ID returned by search'},
        'to': {'type': 'STRING', 'description': 'Recipient email address, comma-separated for multiple'},
        'subject': {'type': 'STRING'},
        'body': {'type': 'STRING', 'description': 'Plain text message body'},
        'draft_id': {'type': 'STRING', 'description': 'Exact Gmail draft ID returned by draft'},
        'confirmation_code': {'type': 'STRING', 'description': 'One-time code provided by the user after prepare_send'},
        'limit': {'type': 'INTEGER', 'description': 'Number of messages, 1 to 10'},
    }, 'required': ['action']},
    'behavior': 'NON_BLOCKING', 'tier': 'extra',
    'brief': 'Search and read Gmail, make drafts, and send only after explicit confirmation.'
}

PLUGIN_SETTINGS = {
    'namespace': 'gmail_control', 'title': 'Gmail (Google OAuth)',
    'fields': []
}

# In-memory pending sends only; no auto-send on restart. One active code per process.
_lock = threading.Lock()
_pending = {}


def _service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError('Install Gmail dependencies: python -m pip install google-api-python-client google-auth-oauthlib') from exc
    if not OAUTH_TOKEN.is_file():
        raise RuntimeError('Gmail not connected. Run python CONNECT_GMAIL_WINDOWS.py in the VS Code terminal first.')
    creds = Credentials.from_authorized_user_file(str(OAUTH_TOKEN), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            OAUTH_TOKEN.write_text(creds.to_json(), encoding='utf-8')
        else:
            raise RuntimeError('Gmail sign-in expired. Run python CONNECT_GMAIL_WINDOWS.py again.')
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def _header(headers, name):
    return next((h.get('value', '') for h in headers if h.get('name', '').lower() == name.lower()), '')


def _validate_addresses(value):
    if not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value:
        raise ValueError('Provide valid recipient email address(es).')
    items = [x.strip() for x in value.split(',')]
    parsed = getaddresses(items)
    if len(items) != len(parsed) or not parsed or any(
        not addr or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', addr) for _, addr in parsed
    ):
        raise ValueError('Invalid recipient address. Use email@example.com.')
    if len(parsed) > 10:
        raise ValueError('At most 10 recipients per draft.')
    return ', '.join(addr for _, addr in parsed)


def _make_message(to, subject, body):
    to = _validate_addresses(to)
    if not isinstance(subject, str) or '\r' in subject or '\n' in subject or not subject.strip():
        raise ValueError('Subject is missing or invalid.')
    if not isinstance(body, str) or not body.strip():
        raise ValueError('Message body is empty.')
    if len(body) > 30000:
        raise ValueError('Message body too long (maximum 30,000 characters).')
    msg = EmailMessage()
    msg['To'] = to
    msg['Subject'] = subject.strip()
    msg.set_content(body)
    return {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')}


def _body_text(payload):
    """Extract plaintext, not attachment data or HTML/script content."""
    if not isinstance(payload, dict):
        return ''
    if payload.get('mimeType') == 'text/plain':
        data = (payload.get('body') or {}).get('data')
        if data:
            try:
                return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4)).decode('utf-8', 'replace')[:3500]
            except (ValueError, UnicodeError):
                return ''
    for part in payload.get('parts') or []:
        text = _body_text(part)
        if text:
            return text
    return ''


def _search(service, query, limit):
    limit = min(10, max(1, int(limit or 5)))
    result = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    ids = result.get('messages') or []
    if not ids:
        return 'No matching Gmail messages found.'
    lines = []
    for item in ids:
        m = service.users().messages().get(userId='me', id=item['id'], format='metadata',
                                            metadataHeaders=['From', 'Subject', 'Date']).execute()
        headers = (m.get('payload') or {}).get('headers') or []
        lines.append(f"ID {item['id']} | From: {_header(headers,'From')[:100]} | Subject: {_header(headers,'Subject')[:140]} | Date: {_header(headers,'Date')[:70]}")
    return '\n'.join(lines)


def _read(service, mid):
    if not re.fullmatch('[A-Za-z0-9_-]{4,128}', str(mid or '')):
        raise ValueError('Provide the exact message ID shown by Gmail search.')
    m = service.users().messages().get(userId='me', id=mid, format='full').execute()
    payload = m.get('payload') or {}
    headers = payload.get('headers') or []
    body = _body_text(payload) or (m.get('snippet') or '')[:1000]
    return (f"ID: {mid}\nFrom: {_header(headers, 'From')}\nTo: {_header(headers, 'To')}\n"
            f"Subject: {_header(headers, 'Subject')}\nDate: {_header(headers, 'Date')}\n"
            f"Message (up to 3,500 chars):\n{body}")


def _draft_info(service, draft_id):
    if not re.fullmatch('[A-Za-z0-9_-]{4,128}', str(draft_id or '')):
        raise ValueError('Provide a valid Gmail draft ID.')
    draft = service.users().drafts().get(userId='me', id=draft_id, format='full').execute()
    headers = (draft.get('message', {}).get('payload') or {}).get('headers') or []
    to = _header(headers, 'To')
    subject = _header(headers, 'Subject')
    if not to:
        raise ValueError('Draft has no recipients and cannot be sent.')
    return to, subject


def run(parameters: dict, player=None, session_memory=None) -> str:
    p = parameters or {}
    action = str(p.get('action') or 'status').strip().lower()
    try:
        if action == 'status':
            if not OAUTH_TOKEN.exists():
                return 'Gmail not connected. Run python CONNECT_GMAIL_WINDOWS.py to sign in with Google.'
            service = _service()
            profile = service.users().getProfile(userId='me').execute()
            return 'Gmail connected as ' + str(profile.get('emailAddress') or 'your Google account')
        if action not in ('inbox', 'search', 'read', 'draft', 'prepare_send', 'send'):
            return 'Unknown Gmail action.'
        service = _service()
        if action == 'inbox':
            return _search(service, 'in:inbox ' + str(p.get('query') or ''), p.get('limit'))
        if action == 'search':
            return _search(service, str(p.get('query') or ''), p.get('limit'))
        if action == 'read':
            return _read(service, p.get('message_id'))
        if action == 'draft':
            msg = _make_message(str(p.get('to') or ''), str(p.get('subject') or ''), str(p.get('body') or ''))
            result = service.users().drafts().create(userId='me', body={'message':msg}).execute()
            return f"Draft saved in Gmail. Draft ID: {result['id']}. Nothing was sent."
        if action == 'prepare_send':
            draft_id = str(p.get('draft_id') or '').strip()
            to, subject = _draft_info(service, draft_id)
            code = f'{secrets.randbelow(1000000):06d}'
            with _lock:
                _pending.clear()
                _pending.update({'draft_id': draft_id, 'code': code, 'expires': time.monotonic()+180})
            return (f'REVIEW BEFORE SENDING. Draft ID: {draft_id}. To: {to}. Subject: {subject}. '
                    f'Nothing has been sent. If you want to send this draft, explicitly say "Send Gmail draft {draft_id} with confirmation code {code}" within 3 minutes.')
        if action == 'send':
            draft_id = str(p.get('draft_id') or '').strip()
            code = str(p.get('confirmation_code') or '').strip()
            with _lock:
                valid = bool(code and _pending and _pending.get('draft_id') == draft_id and
                             secrets.compare_digest(_pending.get('code',''), code) and
                             time.monotonic() < _pending.get('expires',0))
                if valid:
                    _pending.clear() # One-use even if Gmail errors (reconfirm before retry).
            if not valid:
                return 'Not sent. First ask to prepare sending this draft, then explicitly confirm with its one-time code.'
            result = service.users().drafts().send(userId='me', body={'id':draft_id}).execute()
            return 'Gmail confirmed message sent. Message ID: ' + str(result.get('id') or '(not returned)')
    except (ValueError, RuntimeError) as exc:
        return f'Gmail: {exc}'
    except Exception as exc:
        # Do not include potentially credential-bearing raw HTTP response bodies.
        return f'Gmail request failed ({type(exc).__name__}). Check Google sign-in, Gmail API access, and connectivity.'
    return 'Unknown Gmail action.'
