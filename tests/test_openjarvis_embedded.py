import sys
import types
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import openjarvis_embedded as mod
from plugins import openjarvis_agent


class FakeJarvis:
    instances = []
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        self.closed = False
        self.version = 'test'
        self.instances.append(self)
    def ask_full(self, query, **kwargs):
        self.calls.append((query,kwargs))
        return {'content':'Hello from embedded SDK'}
    def close(self): self.closed = True


class EmbeddedTests(unittest.TestCase):
    def setUp(self):
        FakeJarvis.instances.clear()
        self.modpatch = mock.patch.object(mod.importlib, 'import_module', return_value=types.SimpleNamespace(Jarvis=FakeJarvis))
        self.modpatch.start()
    def tearDown(self): self.modpatch.stop()

    def test_no_network_server_and_agent_dispatch(self):
        bridge = mod.EmbeddedOpenJarvis(engine='ollama', model='demo')
        self.assertIn('no OpenJarvis server required',bridge.status())
        self.assertEqual(bridge.ask('hello',agent='orchestrator',tools='calculator,think'), 'Hello from embedded SDK')
        inst = FakeJarvis.instances[-1]
        self.assertEqual(inst.kwargs, {'engine_key':'ollama','model':'demo'})
        self.assertEqual(inst.calls[0][1],{'agent':'orchestrator','tools':['calculator','think'],'context':True})
        bridge.close()
        self.assertTrue(inst.closed)

    def test_denies_unapproved_actions_without_calling_sdk(self):
        bridge=mod.EmbeddedOpenJarvis()
        for kwargs in ({'agent':'native_openhands'},{'tools':'shell'},{'tools':'file_write'}):
            with self.assertRaises(ValueError): bridge.ask('test',**kwargs)
        self.assertEqual(FakeJarvis.instances, [])

    def test_limits(self):
        bridge=mod.EmbeddedOpenJarvis()
        with self.assertRaises(ValueError): bridge.ask('x'*4001)
        with self.assertRaises(ValueError): bridge.ask('')

    def test_missing_sdk_message(self):
        with mock.patch.object(mod.importlib, 'import_module', side_effect=ImportError('missing')):
            with self.assertRaisesRegex(mod.EmbeddedOpenJarvisError, 'Python SDK'):
                mod.EmbeddedOpenJarvis().status()

    def test_plugin_entrypoint(self):
        with mock.patch.object(openjarvis_agent, 'get_plugin_setting', return_value=''):
            with mock.patch.object(openjarvis_agent.sdk, 'instance') as factory:
                factory.return_value.ask.return_value = 'hello'
                self.assertEqual(openjarvis_agent.run({'action':'ask','question':'Hi'}), 'hello')
                factory.return_value.ask.assert_called_once()
                self.assertIn('Unknown',openjarvis_agent.run({'action':'shell'}))


if __name__ == '__main__': unittest.main()
