"""Execute extracted methods without importing the microphone/GUI dependencies."""
import ast
import asyncio
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import tempfile
import threading
import unittest


def _load_methods(*names):
    tree=ast.parse((Path(__file__).resolve().parent.parent / 'main.py').read_text())
    jarvis=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='JarvisLive')
    methods=[node for node in jarvis.body if isinstance(node,ast.FunctionDef) or isinstance(node,ast.AsyncFunctionDef)]
    selected=[node for node in methods if node.name in names]
    assert len(selected)==len(names),(names,[x.name for x in selected])
    ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[]))
    scope={'json':json,'datetime':datetime,'asyncio':asyncio}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<main methods>','exec'),scope)
    return scope


class MockUI:
    def __init__(self):self.logs=[]
    def write_log(self,text):self.logs.append(text)


class ConversationTests(unittest.TestCase):
    def test_journal_persists_and_bounds_history(self):
        fs=_load_methods('_record_turn','_load_conversation_history','_conversation_replay_prompt')
        with tempfile.TemporaryDirectory() as tmp:
            class Stub:pass
            x=Stub();x._history_path=Path(tmp)/'mem'/'conversation_history.jsonl'
            x._history_lock=threading.RLock();x._history_limit=40
            x._conversation_history=[];x._session_log=[];x._asst_name='JARVIS'
            x._record_turn=fs['_record_turn'].__get__(x)
            x._load_conversation_history=fs['_load_conversation_history'].__get__(x)
            x._conversation_replay_prompt=fs['_conversation_replay_prompt'].__get__(x)
            for i in range(60):x._record_turn('user',f'command {i}')
            self.assertEqual(len(x._load_conversation_history()),40)
            self.assertEqual(x._load_conversation_history()[0]['content'],'command 20')
            self.assertIn('command 59',x._conversation_replay_prompt())
            self.assertNotIn('command 42\n',x._conversation_replay_prompt())
            self.assertEqual(len(x._session_log),60)
            self.assertEqual(len(x._history_path.read_text().splitlines()),40)

    def test_typed_commands_wait_through_reconnect(self):
        fs=_load_methods('_on_text_command','_flush_typed_commands')
        class Stub:pass
        x=Stub();x.ui=MockUI();x._loop=None;x.session=None
        x._wake_enabled=False;x._awake=True
        x._pending_typed_commands=deque(maxlen=20)
        x._pending_typed_lock=threading.RLock()
        x._typed_flush_lock=asyncio.Lock()
        x._recorded=[]
        x._record_turn=lambda role,text:x._recorded.append((role,text))
        x._on_text_command=fs['_on_text_command'].__get__(x)
        x._flush_typed_commands=fs['_flush_typed_commands'].__get__(x)
        x._on_text_command('open map');x._on_text_command('previous command')
        self.assertEqual(len(x._pending_typed_commands),2)
        class FakeSession:
            def __init__(self):self.sent=[]
            async def send_client_content(self,turns,turn_complete):self.sent.append(turns['parts'][0]['text'])
        x.session=FakeSession()
        asyncio.run(x._flush_typed_commands())
        self.assertEqual(x.session.sent,['open map','previous command'])
        self.assertEqual(len(x._pending_typed_commands),0)
        self.assertEqual(x._recorded,[('user','open map'),('user','previous command')])

    def test_failed_send_is_retained(self):
        fs=_load_methods('_on_text_command','_flush_typed_commands')
        class Stub:pass
        x=Stub();x.ui=MockUI();x._loop=None;x.session=None
        x._wake_enabled=False;x._awake=True;x._pending_typed_commands=deque(maxlen=20)
        x._pending_typed_lock=threading.RLock();x._typed_flush_lock=asyncio.Lock()
        x._record_turn=lambda *args:None
        x._on_text_command=fs['_on_text_command'].__get__(x)
        x._flush_typed_commands=fs['_flush_typed_commands'].__get__(x)
        x._on_text_command('retain me')
        class Failed:
            async def send_client_content(self,**kw):raise ConnectionError('disconnected')
        x.session=Failed()
        asyncio.run(x._flush_typed_commands())
        self.assertEqual(list(x._pending_typed_commands),['retain me'])


if __name__=='__main__': unittest.main()
