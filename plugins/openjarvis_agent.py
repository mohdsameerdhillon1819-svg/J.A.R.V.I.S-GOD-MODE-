"""Embedded OpenJarvis AI capabilities inside Mark-LVII (no second server)."""
from __future__ import annotations

from core import openjarvis_embedded as sdk
from memory.config_manager import get_plugin_setting

PLUGIN = {
    'name': 'openjarvis_agent',
    'description': ('Use OpenJarvis agents IN PROCESS inside JARVIS for research, '
                    'reasoning, retrieval or a simple answer. Requires the upstream '
                    'OpenJarvis Python SDK and a configured inference engine. '
                    'No OpenJarvis localhost API server is used.'),
    'parameters': {'type': 'OBJECT', 'properties': {
        'action': {'type': 'STRING', 'enum': ['ask', 'status']},
        'question': {'type': 'STRING'},
        'agent': {'type': 'STRING', 'enum': ['simple', 'orchestrator', 'native_react', 'deep_research']},
        'tools': {'type': 'STRING', 'description': 'Comma-separated tool names: calculator, think, web_search, retrieval, file_read'}
    }, 'required': []},
    'tier': 'extra',
    'brief': 'Run safe OpenJarvis agents inside JARVIS; no separate server.',
    'behavior': 'NON_BLOCKING'
}

PLUGIN_SETTINGS = {
    'namespace': 'openjarvis_agent',
    'title': 'OpenJarvis Embedded AI (no server)',
    'fields': [
        {'key':'engine', 'label':'Engine key (blank = OpenJarvis default)', 'type':'text', 'default':'', 'placeholder':'ollama'},
        {'key':'model', 'label':'Model ID (blank = OpenJarvis default)', 'type':'text', 'default':'', 'placeholder':'qwen3:8b'},
    ],
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = str(params.get('action') or 'status').lower()
    engine = str(get_plugin_setting('openjarvis_agent', 'engine', '') or '').strip()
    model = str(get_plugin_setting('openjarvis_agent', 'model', '') or '').strip()
    try:
        embedded = sdk.instance(engine=engine, model=model)
        if action == 'status':
            return embedded.status()
        if action == 'ask':
            return embedded.ask(params.get('question', ''),
                                agent=params.get('agent', 'simple'),
                                tools=params.get('tools', ''))
        return 'Unknown OpenJarvis action; choose ask or status.'
    except (sdk.EmbeddedOpenJarvisError, ValueError) as exc:
        return f'Embedded OpenJarvis unavailable: {exc}'
