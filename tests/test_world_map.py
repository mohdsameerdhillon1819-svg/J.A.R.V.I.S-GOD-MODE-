"""Offline tests for JARVIS's map backend; no API keys or browser required."""
import json
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core import world_map_server as m


class MapTests(unittest.TestCase):
    def setUp(self):
        m._CACHES.clear(); m._RATE.clear(); m._TILE_CACHE.clear()

    def tearDown(self):
        m.shutdown_map()

    def test_bounding_box_rejects_bad_and_large(self):
        self.assertEqual(m._bbox({"south":["10"],"west":["20"],"north":["12"],"east":["25"]}),(10.,20.,12.,25.))
        for bad in ({}, {"south":["nan"],"north":["5"],"west":["1"],"east":["3"]},
                    {"south":["-90"],"north":["90"],"west":["-180"],"east":["180"]}):
            with self.assertRaises(ValueError): m._bbox(bad)

    def test_aircraft_api_parser_and_cache(self):
        now=int(time.time())
        raw={"time":now,"states":[
            ["abc123","TEST321","India",now,now,77.3,28.6,9000,False,100,270],
            ["xxxxxx","OLD","India",now-400,now-400,77,28,7000,False,100,30],
            ["yyyyyy","GND","India",now,now,77,28,0,True,0,30],
        ]}
        with patch.object(m,"_fetch",return_value=json.dumps(raw).encode()) as fetch:
            first=m.get_aircraft((28,77,29,78))
            second=m.get_aircraft((28,77,29,78))
            self.assertEqual(len(first["items"]),1)
            self.assertEqual(first["items"][0]["label"],"TEST321")
            self.assertEqual(second,first)
            self.assertEqual(fetch.call_count,1)

    def test_local_http_dashboard_and_cross_site_protection(self):
        url=m.start_map()
        self.assertTrue(url.startswith("http://127.0.0.1:"))
        with urlopen(url,timeout=3) as response:
            html=response.read().decode()
            self.assertIn("JARVIS",html)
            self.assertIn("world_map.js",html)
        with urlopen(url.replace("/world-map","/api/status"),timeout=3) as response:
            payload=json.loads(response.read())
            self.assertTrue(payload["ok"])
            self.assertFalse("tomtom_api_key" in str(payload))
        req=Request(url,headers={"Sec-Fetch-Site":"cross-site"})
        with self.assertRaises(HTTPError) as err:
            urlopen(req,timeout=3)
        self.assertEqual(err.exception.code,403)

    def test_empty_opensky_uses_regional_adsb(self):
        now = int(time.time())
        regional={"ok": True, "items": [{"lat":28.6,"lon":77.3,"label":"REGIONAL"}],
                  "source":"regional ADS-B", "updated":now}
        with patch.object(m, "_fetch", return_value=json.dumps({"time":now,"states":[]}).encode()):
            with patch.object(m, "_regional_aircraft", return_value=regional):
                result=m.get_aircraft((28,77,29,78))
        self.assertEqual(result["items"][0]["label"], "REGIONAL")

    def test_gesture_opt_in_and_health_explanations(self):
        page=(m._STATIC / "world_map.html").read_text(encoding="utf-8")
        code=(m._STATIC / "world_map_gestures.js").read_text(encoding="utf-8")
        self.assertIn('id="find-flights"',page)
        self.assertIn('id="gesture-toggle"',page)
        self.assertIn('world_map_gestures.js',page)
        self.assertIn("getUserMedia",code)
        self.assertIn("cameraStop()",code)
        self.assertIn("HandLandmarker",code)
        self.assertNotIn("getUserMedia",(m._STATIC / "world_map.js").read_text(encoding="utf-8"))

    def test_ais_incoming_position_reports(self):
        ais=m.AISCollector()
        ais._accept({"MessageType":"PositionReport",
                     "MetaData":{"MMSI":123456789,"Latitude":20.5,"Longitude":72.8,"ShipName":"TEST SHIP"},
                     "Message":{"PositionReport":{"Sog":12.5,"Cog":90}}})
        a=ais.snapshot((20,72,21,73))
        self.assertEqual(len(a["items"]),1)
        self.assertEqual(a["items"][0]["label"],"TEST SHIP")
        self.assertEqual(a["items"][0]["speed_kn"],12.5)
        self.assertFalse(ais.snapshot((22,72,23,73))["items"])

    def test_satellites_fail_cleanly_without_dependency(self):
        response=m.get_satellites()
        self.assertIn("items",response)
        self.assertIn("ok",response)

    def test_frontend_avoids_static_import_deadlock_and_reports_errors(self):
        root = m._STATIC
        html = (root / "world_map.html").read_text(encoding="utf-8")
        js = (root / "world_map.js").read_text(encoding="utf-8")
        self.assertNotIn('type="importmap"', html)
        self.assertNotIn('type="module" src="/world_map.js"', html)
        self.assertIn('defer src="/world_map.js"', html)
        self.assertIn('await loadRenderer()', js)
        self.assertIn('Map startup problem:', js)
        self.assertIn('cdn.jsdelivr.net', js)
        self.assertNotIn('tile.openstreetmap.org', js)

    def test_plugin_metadata_and_status(self):
        from plugins.world_map import PLUGIN,PLUGIN_SETTINGS,run
        self.assertEqual(PLUGIN["name"],"world_map")
        self.assertIn("fields",PLUGIN_SETTINGS)
        self.assertIn("World Map",run({"action":"status"}))


if __name__=="__main__": unittest.main()
