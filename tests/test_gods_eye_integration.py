"""Offline-only integration checks. No real provider calls or installs."""
import json
from pathlib import Path
from unittest.mock import MagicMock
import unittest
from unittest.mock import patch
from urllib.request import urlopen
from urllib.error import HTTPError
from core import world_map_server as map_server
from core import gods_eye_bridge as bridge

class GodsEyeIntegrationTests(unittest.TestCase):
    def tearDown(self):
        map_server.shutdown_map()

    def test_original_world_map_plugin_opens_official_three_d(self):
        from plugins import world_map
        self.assertEqual(world_map.PLUGIN["name"], "world_map")
        self.assertIn("gesture", world_map.PLUGIN["description"])
        with patch.object(world_map, "launch", return_value=(True, "Official 3D started")) as launch:
            result = world_map.run({"action": "open"})
        self.assertIn("3D", result)
        launch.assert_called_once_with(open_browser=True)

    def test_gesture_overlay_is_opt_in_not_keyed(self):
        root = Path(__file__).resolve().parents[1]
        code = (root / "integrations" / "gods_eye_gestures.js").read_text(encoding="utf-8")
        install = (root / "INSTALL_GODS_EYE_WINDOWS.ps1").read_text(encoding="utf-8")
        self.assertIn("getUserMedia", code)
        self.assertIn("HandLandmarker", code)
        self.assertIn("button.addEventListener('click'", code)
        self.assertIn("jarvis_gesture_overlay.js", install)
        self.assertIn("</body>", install)
        self.assertNotIn("aisstream_api_key", code.lower())

    def test_upstream_link_requires_actual_install(self):
        with patch.object(bridge, "installed", return_value=False):
            ok, message = bridge.launch(open_browser=False)
        self.assertFalse(ok)
        self.assertIn('INSTALL_GODS_EYE_WINDOWS.ps1', message)

    def test_diag_never_exposes_credentials(self):
        with patch.object(map_server, '_key', side_effect=lambda name: 'private-placeholder-secret'):
            with urlopen(map_server.start_map().replace('/world-map', '/api/diagnostics'), timeout=3) as response:
                result = json.loads(response.read())
        self.assertTrue(result['keys_configured']['aisstream'])
        self.assertNotIn('private-placeholder-secret', json.dumps(result))

    def test_maptiler_client_style_is_opt_in(self):
        url = map_server.start_map().replace('/world-map', '/api/maptiler-style')
        with patch.object(map_server, '_key', return_value=''):
            with self.assertRaises(HTTPError) as err:
                urlopen(url, timeout=3)
            self.assertEqual(err.exception.code, 400)
        with patch.object(map_server, '_key', return_value='test-public-browser-token'):
            with urlopen(url, timeout=3) as response:
                result = json.loads(response.read())
            self.assertIn('streets-v2', result['style'])
            self.assertNotIn('TOMTOM_API_KEY', json.dumps(result))

if __name__ == '__main__': unittest.main()
