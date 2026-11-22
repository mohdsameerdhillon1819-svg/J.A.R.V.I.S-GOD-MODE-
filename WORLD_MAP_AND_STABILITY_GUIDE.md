# Mark-LVII: stability + World Map integration

This is the original Mark-LVII project with targeted repairs and a new read-only
world-map plugin. No original plugins or core features were deliberately removed.

## On Windows: install and run

1. Back up your old Mark-LVII folder. Extract the updated ZIP into a *new* folder.
2. In that new folder, run `py -3.12 setup.py` (or `python setup.py` if you
   already have Python 3.11–3.13 installed). This installs dependencies,
   including the small `sgp4` satellite-orbit package.
3. Run `py -3.12 main.py` (or `python main.py`). Complete JARVIS's initial setup
   with your Gemini key or chosen local engine. You can copy **your own**
   `config/api_keys.json` from your original installation **locally** if you
   want to preserve settings and API keys. To keep existing memories and
   routines, also copy your **own** `memory/long_term.json` and
   `memory/routines.json` from the backup to the corresponding new folder.
   Never commit or upload these private files.
4. Say or type **“Open the world map”** or **“Show me satellites and airplanes
   on the map”**. The `world_map` plugin launches a localhost browser dashboard.
5. To try the map without voice recognition, run
   `py -3.12 start_world_map.py`. It shows a localhost URL and runs until you
   press Enter in that console.

## Map layers and which sources they use

| Layer | Source | Availability |
|---|---|---|
| Base map | OpenStreetMap/Leaflet | Internet; no key |
| Airplanes | OpenSky state vectors; fallback to the bundled `aircraft_report` plugin's ADS-B feeds | Regional view (zoom ≥6); feed may have gaps/rate limits |
| Satellites | CelesTrak orbital element sets + Python SGP4 | No account; *predicted ground positions*, not live telemetry |
| Ships | AISstream WebSocket data | Optional **AISstream API key**, regional view; receiver coverage varies |
| Vessel trails | Recent AIS observations collected while the map is running | **Observed paths only**; not scheduled/planned shipping routes |
| Nautical marks | OpenSeaMap overlay | No account; nautical symbols, **not** commercial shipping lanes |
| Road traffic | TomTom raster flow tiles | Optional **TomTom API key**; based on provider coverage/plan |

The app intentionally does not claim that OpenStreetMap itself broadcasts live
planes, ship locations, satellite positions, or traffic. The other data providers
are necessary. Fully global real-time ship positions and planned sea routes
cannot be promised from these free/optional sources.

### Optional provider keys

Inside JARVIS: **⚙ → PLUGIN SETTINGS → WORLD MAP & LIVE LAYERS**.
Enter your AISstream or TomTom keys in the masked fields and select Save. The
plugin reads its values on each request, so restart is normally unnecessary.
You may alternatively set environment variables `AISSTREAM_API_KEY` and
`TOMTOM_API_KEY`; `OPENSKY_ACCESS_TOKEN` supports an existing OpenSky bearer
access token. Never paste keys into an issue or a shared project ZIP.

### Map details

- The map server only binds to `127.0.0.1` and uses a random free port.
- API credentials stay in Python, not in the browser's traffic URLs; traffic
  tiles are fetched through a bounded local proxy.
- The browser can pan and zoom; turn individual layers on/off. Aircraft and
  ships load only for reasonable regional bounds (max 25° × 40°).
- Aircraft data is cached and provider requests are throttled to ~90 seconds.
  AIS updates are collected in a single regional WebSocket subscription, retained
  for at most 15 minutes in memory, and re-rendered every ~12 seconds.
- CelesTrak orbital elements are cached for ~4 hours; satellite ground positions
  are recomputed via SGP4. These are calculations, not live satellite GPS fixes.
- The server does not store map history or ship trails across restarts.

## Stability/memory changes

- Recent typed and spoken user/assistant turns are written to
  `memory/conversation_history.jsonl` (max 40 turns, up to 4,000 characters each).
- On a **fresh** connection, the most recent 16 turns provide fallback context.
  When a Gemini Live session-resumption handle is valid, JARVIS relies on that
  instead of duplicating history.
- Typed commands are queued through a disconnect and sent serially when the
  next session becomes active. The in-memory pending queue holds at most 20
  commands; if full, its oldest unsent entry is discarded with a visible notice.
  Queued-but-unsent commands do **not** persist across application restarts.
- Remote web-dashboard text commands use the same queue instead of being
  discarded after a short offline wait.
- Tool dispatch deadlines prevent indefinite wait on normal actions/plugins
  (45 s); long-running file/coding tasks allow 120 s.
  **Important:** cancelling a Python executor wait does not terminate the
  underlying worker thread. Check the status of an operation that timed out
  before running it again.
- The existing 30-second no-response reconnect watcher, long-term memory store,
  and session-resumption support remain present.
- The journal is local and separate from the existing long-term fact memory.
  You can delete the journal when JARVIS is **fully shut down** to reset recent
  chat context. Avoid clearing the long-term memory unless you mean to.

## Tests

Run `python -m unittest discover -s tests -v` from the project root.
The unit tests do **not** contact real map services or require API keys.
They verify offline map endpoints, bounds, AIS parsing, airplane state vectors,
cache behavior, local-only access, journal persistence and reconnect queues.

### Limits of testing

These checks confirm syntax and targeted logic. The full voice/UI startup could
not be run in the build environment because PyQt6, sounddevice and Google's
live API/client hardware and credentials are unavailable. Run a full microphone,
Windows UI, provider and map test on your computer. Provider quotas, satellite
coverage and network availability are outside JARVIS's control.

## Private files intentionally not included

The uploaded archive contained `config/api_keys.json`, `memory/long_term.json`
and other runtime artifacts. These, cached location information, generated
reports, bytecode and local secrets are deliberately excluded from the delivered
ZIP. The updated project creates its own local runtime files.

## Basemap 403 fix (November 2026)

The OpenStreetMap Foundation's standard raster tile service can return a `403 Access blocked` placeholder when its tile policy is not satisfied. This version uses OpenFreeMap's published `liberty` vector map style (OSM-derived data), loaded by MapLibre through the Leaflet adapter. It is free to use without a basemap API key. The map needs internet access to `unpkg.com` and `tiles.openfreemap.org`. Keep the OpenFreeMap, OpenMapTiles and OpenStreetMap attributions visible. Provider availability is not guaranteed. The aircraft, satellite, vessel and traffic layers are otherwise unchanged.

## 22 November 2026: Blank map / "Starting map…" repair

The initial OpenFreeMap/Leaflet-bridge dashboard had static CDN imports. If an import
was blocked, the dashboard script never ran and remained on “Starting map…”.
The new dashboard uses MapLibre GL directly, dynamically loads the renderer from
unpkg with a jsDelivr fallback, and shows a visible startup error if neither can
load. It continues to use OpenFreeMap's permitted vector basemap, not the OSMF
volunteer raster tile service that returned HTTP 403.

**VS Code:** close the old map terminal (Ctrl+C); extract this ZIP to a NEW folder;
File → Open Folder → the NEW `Mark-LVII` folder; Terminal → New Terminal;
`py -3.12 start_world_map.py`. Open the printed localhost URL (do not reuse an old
bookmark/port); press Ctrl+Shift+R in the browser. Use current Chrome or Edge with
WebGL enabled. Keep the terminal open while using the map.

**If the map is still dark:** read the status text in the panel; open F12 → Console
and Network. Errors reaching `unpkg.com` or `cdn.jsdelivr.net` mean renderer CDN
access is unavailable; errors reaching `tiles.openfreemap.org` indicate map style
or tile-service access failed. Check ad-blocking / network policy without bypassing
provider limits. Internet access is required to load the map and real data.

**You DO NOT need to provide keys to fix the empty basemap.** Keep keys private.
Optional: set AISstream and TomTom keys in JARVIS's local Plugin Settings →
World Map, or in your Windows process environment as `AISSTREAM_API_KEY` and
`TOMTOM_API_KEY`; do not upload keys in chat or include them in screenshots.
OpenSky aircraft can still be unavailable or rate limited and needs zoom 6+;
satellite positions are calculated estimates. Not all layers provide global
real-time coverage.
