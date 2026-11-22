# Security and responsible disclosure

**Do not open a public issue with API keys, OAuth tokens, screenshots containing secrets, email bodies, local conversation history or Google credentials.**

Before publishing, rotate credentials that were previously pasted into chat, screenshots or terminals. Keep keys in local configuration files excluded by `.gitignore` and never store them in source code.

Local secret paths that must remain untracked include `config/api_keys.json`, `config/gmail_credentials.json`, `config/gmail_token.json`, `.env*`, `memory/conversation_history.jsonl`, and local logs.

`gitignore` only protects untracked files. If you commit a secret, deleting the file later does not remove it from Git history. Revoke/rotate the key and remove it from Git history before publishing.

Desktop automation actions should be explicitly supervised when they can delete, send, publish or modify important content.
