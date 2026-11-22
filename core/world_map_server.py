"""Local-only, read-only map server for the world_map plugin.

No remotely reachable bind, no arbitrary URL proxy, no account keys returned to the
browser. Upstream failures are reported as unavailable rather than fabricated data.
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

_ROOT = Path(__file__).resolve().parent.parent
_STATIC = _ROOT / "dashboard" / "static"
_UA = "Mark-JARVIS-WorldMap/1.0 (local personal map viewer)"
_LOCK = threading.RLock()
_SERVER = None
_THREAD = None
_CACHES: dict[str, tuple[float, object]] = {}
_RATE: dict[str, float] = {}
_TILE_CACHE: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
_AIS = None


def _settings() -> dict:
    try:
        from memory.config_manager import get_plugin_config
        return get_plugin_config("world_map")
    except (ImportError, OSError, ValueError):
        return {}


def _key(which: str) -> str:
    config = _settings()
    env_name = {"tomtom": "TOMTOM_API_KEY", "ais": "AISSTREAM_API_KEY", "maptiler": "MAPTILER_API_KEY"}[which]
    return str(os.getenv(env_name) or config.get({"tomtom":"tomtom_api_key","ais":"aisstream_api_key","maptiler":"maptiler_api_key"}[which]) or "").strip()


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _fetch(url: str, *, timeout: float = 9, headers=None, max_bytes: int = 2_000_000) -> bytes:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json, text/plain, */*", **(headers or {})})
    with urlopen(req, timeout=timeout) as res:
        if res.status != 200:
            raise ValueError("Provider returned a non-success status")
        blob = res.read(max_bytes + 1)
        if len(blob) > max_bytes:
            raise ValueError("Provider response too large")
        return blob


def _clean_error(exc: Exception, service: str) -> str:
    if isinstance(exc, HTTPError):
        if exc.code in (401, 403):
            return f"{service} authorization is required or access was denied (HTTP {exc.code})."
        if exc.code == 429:
            return f"{service} rate limit exceeded; try again later."
        return f"{service} returned HTTP {exc.code}."
    if isinstance(exc, (TimeoutError, URLError)):
        return f"{service} network request timed out or failed."
    return f"{service} unavailable: {type(exc).__name__}."


def _bbox(query: dict) -> tuple[float, float, float, float]:
    try:
        south = float(query.get("south", [""])[0]); west = float(query.get("west", [""])[0])
        north = float(query.get("north", [""])[0]); east = float(query.get("east", [""])[0])
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("Provide south, west, north and east map bounds.") from exc
    if not all(map(math.isfinite, (south, west, north, east))):
        raise ValueError("Map bounds must be finite.")
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("Map bounds are outside the supported range or cross the dateline.")
    if north - south > 25 or east - west > 40:
        raise ValueError("Zoom closer to view live aircraft or vessels (max 25° latitude and 40° longitude).")
    return south, west, north, east


def _cache_get(key: str):
    with _LOCK:
        item = _CACHES.get(key)
        if item and item[0] > time.monotonic():
            return item[1]
    return None


def _cache_set(key: str, ttl: float, value):
    with _LOCK:
        _CACHES[key] = (time.monotonic() + ttl, value)
        if len(_CACHES) > 50:
            for old in list(_CACHES):
                if _CACHES[old][0] < time.monotonic() or len(_CACHES) > 40:
                    del _CACHES[old]


def get_aircraft(bounds: tuple[float, float, float, float]) -> dict:
    # One provider request at most per 90 seconds per desktop, even on rapid pans.
    # This respects anonymous OpenSky's per-day credits and avoids huge requests.
    cache_key = "aircraft:" + ":".join(f"{v:.1f}" for v in bounds)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    with _LOCK:
        last = _RATE.get("opensky", 0)
        remaining = 90 - (time.monotonic() - last)
        if remaining > 0:
            alternative = _regional_aircraft(bounds)
            if alternative is not None:
                _cache_set(cache_key, 30, alternative)
                return alternative
            return {"ok": False, "items": [], "error": f"OpenSky refresh is limited to once every 90 seconds; retry in {math.ceil(remaining)} s.", "source": "OpenSky"}
    # Community ADS-B feed is the primary regional data source; OpenSky is fallback.
    regional = _regional_aircraft(bounds)
    if regional is not None and regional.get("items"):
        _cache_set(cache_key, 60, regional)
        return regional
    with _LOCK:
        _RATE["opensky"] = time.monotonic()
    s, w, n, e = bounds
    url = "https://opensky-network.org/api/states/all?" + urlencode({
        "lamin": f"{s:.4f}", "lomin": f"{w:.4f}", "lamax": f"{n:.4f}", "lomax": f"{e:.4f}"
    })
    try:
        token = os.getenv("OPENSKY_ACCESS_TOKEN", "").strip()
        headers = {"Authorization": "Bearer " + token} if token else {}
        data = json.loads(_fetch(url, headers=headers))
        now = time.time()
        result = []
        for state in data.get("states") or []:
            if len(state) < 11 or state[5] is None or state[6] is None or state[8]:
                continue
            if state[3] is None or now - float(state[3]) > 180:
                continue
            lat, lon = float(state[6]), float(state[5])
            if not (s <= lat <= n and w <= lon <= e):
                continue
            result.append({"lat": round(lat, 3), "lon": round(lon, 3),
                           "label": str(state[1] or "Aircraft").strip()[:24],
                           "country": str(state[2] or "")[:48],
                           "altitude_m": round(state[7]) if state[7] is not None else None,
                           "heading": round(float(state[10])) if state[10] is not None else None,
                           "age_s": max(0, round(now-float(state[3])))})
            if len(result) >= 400:
                break
        payload = {"ok": True, "source": "OpenSky (near-real-time, incomplete coverage)",
                   "items": result, "updated": data.get("time")}
        # Anonymous OpenSky sometimes reports no states while regional volunteer
        # receivers have data. An empty response is not evidence of empty airspace.
        if not result:
            alternative = _regional_aircraft(bounds)
            if alternative is not None and alternative["items"]:
                _cache_set(cache_key, 90, alternative)
                return alternative
        _cache_set(cache_key, 90, payload)
        return payload
    except (HTTPError, URLError, OSError, ValueError, KeyError, TypeError, TimeoutError) as exc:
        alternative = _regional_aircraft(bounds)
        if alternative is not None:
            _cache_set(cache_key, 90, alternative)
            return alternative
        payload = {"ok": False, "source": "OpenSky", "items": [], "error": _clean_error(exc, "OpenSky")}
        _cache_set(cache_key, 60, payload)
        return payload


def _regional_aircraft(bounds: tuple[float, float, float, float]) -> dict | None:
    """Use the project's existing key-free regional ADS-B adapters when available.

    This is a bounded regional view, not a global aircraft scrape. There is no
    fallback to invented positions, and flight privacy/coverage gaps remain.
    """
    try:
        from plugins import aircraft_report as fallback
        south, west, north, east = bounds
        center_lat = (south + north)/2
        center_lon = (west + east)/2
        half_lat = (north-south)*55_600
        half_lon = (east-west)*55_600*abs(math.cos(math.radians(center_lat)))
        radius_m = min(250*1852, max(5_000, math.hypot(half_lat, half_lon)))
        flights, feed, problem = fallback._fetch(center_lat, center_lon, radius_m)
        if flights is None:
            return None
        items = []
        for flight in flights:
            lat, lon = flight.get("lat"), flight.get("lon")
            if flight.get("on_ground") or lat is None or lon is None:
                continue
            if not (south <= lat <= north and west <= lon <= east):
                continue
            items.append({"lat": round(lat,3), "lon": round(lon,3),
                          "label": str(flight.get("callsign") or "Aircraft")[:24],
                          "country": "", "altitude_m": round(flight["alt_m"]) if flight.get("alt_m") is not None else None,
                          "heading": round(flight["track"]) if flight.get("track") is not None else None,
                          "age_s": None})
            if len(items) >= 400: break
        return {"ok": True, "source": f"{feed} regional ADS-B (coverage varies)",
                "items": items, "updated": int(time.time())}
    except Exception as exc:
        print(f"[WorldMap] regional ADS-B feed unavailable: {type(exc).__name__}")
        return None


def _sidereal_angle(jd: float) -> float:
    t = (jd-2451545.0)/36525.0
    seconds = 67310.54841 + (876600*3600 + 8640184.812866)*t + 0.093104*t*t - 6.2e-6*t**3
    return (seconds % 86400.0)*2*math.pi/86400.0


def _groundtrack(sat, jd, fr) -> tuple[float,float] | None:
    err, (x, y, z), _ = sat.sgp4(jd, fr)
    if err or not all(math.isfinite(v) for v in (x,y,z)):
        return None
    theta = _sidereal_angle(jd+fr)
    X = math.cos(theta)*x + math.sin(theta)*y
    Y = -math.sin(theta)*x + math.cos(theta)*y
    a = 6378.137; b = 6356.752314245
    e2 = 1 - b*b/(a*a)
    r = math.hypot(X,Y)
    lat = math.atan2(z, r*(1-e2))
    for _ in range(5):
        N = a/math.sqrt(1-e2*math.sin(lat)**2)
        alt = r/max(math.cos(lat),1e-8)-N
        lat = math.atan2(z, r*(1-e2*N/(N+alt)))
    return round(math.degrees(lat), 3), round(math.degrees(math.atan2(Y,X)), 3)


def get_satellites() -> dict:
    """CelesTrak TLEs → SGP4 *estimated* satellite ground tracks, never live telemetry."""
    try:
        from sgp4.api import Satrec, jday
    except ImportError:
        return {"ok": False, "items": [], "source": "CelesTrak", "error": "Install sgp4 with: pip install sgp4"}
    cached = _cache_get("tle:stations+weather")
    if cached is None:
        try:
            tles = []
            for group in ("stations", "weather"):
                try:
                    blob = _fetch("https://celestrak.org/NORAD/elements/gp.php?" + urlencode({"GROUP": group, "FORMAT": "tle"}),
                                  max_bytes=600_000, timeout=12)
                except (HTTPError, URLError, OSError, ValueError, TimeoutError):
                    if group == "stations": raise
                    continue  # stations can still be displayed if weather is offline
                lines = blob.decode("utf-8", "replace").splitlines()
                for i in range(0, len(lines)-2, 3):
                    if lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
                        tles.append((lines[i][:60], lines[i+1], lines[i+2]))
            if not tles:
                raise ValueError("No orbital elements were provided")
            cached = tles[:220]
            _cache_set("tle:stations+weather", 4*3600, cached)
        except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
            return {"ok": False, "items": [], "source": "CelesTrak", "error": _clean_error(exc, "CelesTrak")}
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
    points = []
    for name, a, b in cached:
        try:
            loc = _groundtrack(Satrec.twoline2rv(a,b), jd,fr)
            if loc:
                points.append({"lat": loc[0], "lon": loc[1], "label": name.strip()[:52]})
        except (ValueError, OverflowError):
            continue
    return {"ok": True, "items": points, "source": "CelesTrak orbit estimates (SGP4; not live telemetry)",
            "updated": now.isoformat()}


class AISCollector:
    """One persistent regional AIS subscription, memory bounded and auto-expiring."""
    def __init__(self):
        self.lock = threading.RLock()
        self.bounds: tuple | None = None
        self.last_change = 0.0
        self.items: dict[int, dict] = {}
        self.trails: dict[int, deque] = {}
        self.state = "off"
        self.worker = None

    def ensure(self, bounds):
        with self.lock:
            if self.bounds != bounds:
                # Avoid churn caused by tiny map movements: new viewport is a
                # subscription only if current selection no longer covers it.
                if self.bounds is None or not (self.bounds[0] <= bounds[0] <= bounds[2] <= self.bounds[2] and
                                                self.bounds[1] <= bounds[1] <= bounds[3] <= self.bounds[3]):
                    self.bounds = bounds
                    self.last_change = time.monotonic()
                    self.items.clear(); self.trails.clear()
            if self.worker is None or not self.worker.is_alive():
                self.worker = threading.Thread(target=self._runner, daemon=True, name="jarvis-ais-collector")
                self.worker.start()

    def _runner(self):
        try:
            asyncio.run(self._listen())
        except Exception:
            with self.lock: self.state = "AIS collector stopped; connection failed"

    async def _listen(self):
        try:
            from websockets.asyncio.client import connect
        except ImportError:
            try:
                from websockets import connect
            except ImportError:
                with self.lock: self.state = "Install websockets: pip install websockets"
                return
        retry = 3
        while _key("ais"):
            with self.lock:
                bounds = self.bounds
                if bounds is None: return
                self.state = "connecting"
            try:
                # AISstream accepts lat/lon corner pairs; position reports alone.
                # Regional bounds prevent accidentally subscribing to whole Earth.
                async with connect("wss://stream.aisstream.io/v0/stream", open_timeout=9, max_size=800_000,
                                   compression="deflate") as ws:
                    s,w,n,e = bounds
                    await ws.send(json.dumps({"APIKey": _key("ais"),
                                              "BoundingBoxes": [[[s,w],[n,e]]],
                                              "FilterMessageTypes": ["PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"]}))
                    with self.lock: self.state = "connected; awaiting reports"
                    retry = 3
                    while True:
                        with self.lock:
                            if bounds != self.bounds: break
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=12)
                        except asyncio.TimeoutError:
                            continue
                        obj = json.loads(raw)
                        self._accept(obj)
            except Exception as exc:
                with self.lock: self.state = _clean_error(exc, "AISstream")
                await asyncio.sleep(retry)
                retry = min(60, retry*2)

    def _accept(self, message: dict) -> None:
        mtype = str(message.get("MessageType") or "")
        if mtype not in ("PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"):
            return
        meta = message.get("MetaData") or {}
        part = (message.get("Message") or {}).get(mtype) or {}
        try:
            ident = int(meta["MMSI"])
            lat = float(meta["Latitude"]); lon = float(meta["Longitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180): return
        except (TypeError, KeyError, ValueError):
            return
        now = time.monotonic()
        point = {"lat": round(lat,3), "lon": round(lon,3),
                 "label": str(meta.get("ShipName") or "Vessel")[:48].strip(),
                 "speed_kn": part.get("Sog"), "heading": part.get("Cog"), "seen": now}
        with self.lock:
            self.items[ident] = point
            track = self.trails.setdefault(ident, deque(maxlen=20))
            if not track or track[-1] != [point["lat"], point["lon"]]:
                track.append([point["lat"], point["lon"]])
            if len(self.items) > 600:
                old = min(self.items, key=lambda k: self.items[k]["seen"])
                self.items.pop(old, None); self.trails.pop(old, None)
            self.state = "receiving AIS updates"

    def snapshot(self, bounds):
        now = time.monotonic()
        s,w,n,e = bounds
        with self.lock:
            for k, v in list(self.items.items()):
                if now - v["seen"] > 900:
                    self.items.pop(k, None); self.trails.pop(k, None)
            items = []
            for k, v in self.items.items():
                if s <= v["lat"] <= n and w <= v["lon"] <= e:
                    d = {a:b for a,b in v.items() if a != "seen"}
                    d["age_s"] = round(now-v["seen"])
                    d["trail"] = list(self.trails.get(k) or [])
                    items.append(d)
            return {"ok": True, "items": items[:400], "source": "AISstream (receiver coverage varies)", "status": self.state}


def get_ships(bounds):
    if not _key("ais"):
        return {"ok": False, "items": [], "source": "AISstream", "error": "Set the AISstream API key in JARVIS → Plugin Settings → World Map."}
    global _AIS
    with _LOCK:
        if _AIS is None: _AIS = AISCollector()
    _AIS.ensure(bounds)
    return _AIS.snapshot(bounds)


def _traffic_tile(z: int, x: int, y: int) -> bytes:
    key = _key("tomtom")
    if not key: raise ValueError("Traffic requires a TomTom API key")
    if not (0 <= z <= 19 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise ValueError("Invalid tile coordinates")
    ck = f"{z}/{x}/{y}"
    with _LOCK:
        item = _TILE_CACHE.get(ck)
        if item and item[0] > time.monotonic():
            _TILE_CACHE.move_to_end(ck)
            return item[1]
    url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0-dark/{z}/{x}/{y}.png?" + urlencode({"key": key})
    blob = _fetch(url, timeout=6, max_bytes=800_000)
    if not blob.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Traffic provider did not return a PNG tile")
    with _LOCK:
        _TILE_CACHE[ck] = (time.monotonic() + 120, blob)
        while len(_TILE_CACHE) > 128:
            _TILE_CACHE.popitem(last=False)
    return blob


class _MapHandler(BaseHTTPRequestHandler):
    server_version = "JARVISMap/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code: int, data: bytes, kind: str = "application/json; charset=utf-8", cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        if kind.startswith("text/html"):
            self.send_header("Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'wasm-unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
                "connect-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://tiles.openfreemap.org https://storage.googleapis.com https://api.maptiler.com; "
                "img-src 'self' data: blob: https://tiles.openfreemap.org https://api.maptiler.com https://tiles.openseamap.org "
                "https://unpkg.com https://cdn.jsdelivr.net; "
                "worker-src 'self' blob:; font-src 'self' data: https://tiles.openfreemap.org https://api.maptiler.com "
                "https://unpkg.com https://cdn.jsdelivr.net")
        self.end_headers()
        try: self.wfile.write(data)
        except (ConnectionResetError, BrokenPipeError): pass

    def _result(self, obj, code=200): self._send(code, _json_bytes(obj))

    def do_GET(self):
        # Reject DNS-rebinding Host headers and cross-site browser requests,
        # especially important for private, metered traffic API credentials.
        host = self.headers.get("Host", "")
        try:
            host_parts = urlsplit("http://" + host)
            host_ok = (host_parts.hostname in ("127.0.0.1", "localhost")
                       and host_parts.port == self.server.server_port)
        except ValueError:
            host_ok = False
        if not host_ok:
            return self._result({"ok": False, "error": "Localhost access only"}, 403)
        site = self.headers.get("Sec-Fetch-Site", "")
        if site and site not in ("same-origin", "none"):
            return self._result({"ok": False, "error": "Cross-site access denied"}, 403)
        origin = self.headers.get("Origin", "")
        if origin and origin not in (f"http://127.0.0.1:{self.server.server_port}",
                                     f"http://localhost:{self.server.server_port}"):
            return self._result({"ok": False, "error": "Foreign origin denied"}, 403)
        parsed = urlsplit(self.path)
        path = parsed.path
        try:
            if path in ("/", "/world-map"):
                data = (_STATIC / "world_map.html").read_bytes()
                return self._send(200, data, "text/html; charset=utf-8")
            if path in ("/world_map.js", "/world_map.css", "/world_map_gestures.js"):
                data = (_STATIC / path.lstrip("/")).read_bytes()
                kind = "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
                return self._send(200, data, kind, "no-store")
            if path == "/api/start-3d":
                # Read-only GET starts a local subprocess: do NOT expose this
                # mutation to arbitrary browser requests. Operated separately.
                return self._result({"ok": False, "error": "Launch through the local Python bridge or batch file."}, 405)
            if path == "/api/maptiler-style":
                key = _key("maptiler")
                if not key:
                    return self._result({"ok": False, "error": "Configure a MapTiler browser key locally first."}, 400)
                # MapTiler API keys are client-visible by design. Browser usage
                # should be scoped to localhost origin in the MapTiler console.
                # Never send AISstream or TomTom secrets to the browser.
                return self._result({"ok": True, "style": "https://api.maptiler.com/maps/streets-v2/style.json?" + urlencode({"key": key})})
            if path == "/api/diagnostics":
                # Never send credential strings, errors containing secrets, or private paths.
                configured = {"maptiler": bool(_key("maptiler")), "aisstream": bool(_key("ais")),
                              "tomtom": bool(_key("tomtom"))}
                from core.gods_eye_bridge import installed
                return self._result({"ok": True, "keys_configured": configured,
                                     "upstream_3d_installed": installed(),
                                     "aircraft": "Public regional ADS-B + OpenSky, checked when zoomed in",
                                     "satellites": "CelesTrak orbital estimates, requires internet and sgp4",
                                     "note": "Configured does not mean provider connection is working."})
            if path == "/api/status":
                return self._result({"ok": True, "aircraft": True, "satellites": True,
                                     "ships": bool(_key("ais")), "traffic": bool(_key("tomtom")),
                                     "message": "Live feeds depend on third-party coverage and rate limits."})
            if path == "/api/satellites": return self._result(get_satellites())
            if path == "/api/aircraft": return self._result(get_aircraft(_bbox(parse_qs(parsed.query))))
            if path == "/api/ships": return self._result(get_ships(_bbox(parse_qs(parsed.query))))
            match = re.fullmatch(r"/api/traffic/(\d{1,2})/(\d{1,8})/(\d{1,8})\.png", path)
            if match:
                z,x,y = map(int,match.groups())
                return self._send(200, _traffic_tile(z,x,y), "image/png", "public, max-age=60")
            return self._result({"ok": False, "error": "Not found"},404)
        except ValueError as exc:
            return self._result({"ok": False, "items": [], "error": str(exc)[:160]},400)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            return self._result({"ok": False, "items": [], "error": _clean_error(exc,"Map provider")},502)
        except Exception as exc:
            # Do not leak credentials, request paths or tracebacks to browser.
            print(f"[WorldMap] Request failed: {type(exc).__name__}")
            return self._result({"ok": False, "items": [], "error": "Map request failed."},500)


def start_map() -> str:
    global _SERVER, _THREAD
    with _LOCK:
        if _SERVER is None:
            _SERVER = ThreadingHTTPServer(("127.0.0.1", 0), _MapHandler)
            _SERVER.daemon_threads = True
            _THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True, name="jarvis-world-map")
            _THREAD.start()
        return f"http://127.0.0.1:{_SERVER.server_port}/world-map"


def shutdown_map() -> None:
    global _SERVER, _THREAD
    with _LOCK:
        server, _SERVER = _SERVER, None
        _THREAD = None
    if server:
        server.shutdown(); server.server_close()
