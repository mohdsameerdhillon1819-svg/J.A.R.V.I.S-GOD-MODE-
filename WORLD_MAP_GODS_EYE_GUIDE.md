# JARVIS Mark-LVII — God’s Eye-style public data map

## What has changed

- Default dark vector map (OpenFreeMap), with a toggle to the classic Liberty style.
- **Explore flights** zooms to a regional demonstration view around Delhi. You can pan and zoom to any other supported area. The map fetches regional public ADS-B observations at zoom level 6 or higher (max 25 degrees latitude by 40 degrees longitude). OpenSky is primary, the existing `aircraft_report` community receiver adapters are used if OpenSky returns no aircraft or errors. If all public sources are empty or unavailable, no imaginary positions are shown. Requests are rate-limited and refresh every 90 seconds.
- Predicted satellite ground positions from CelesTrak TLEs via SGP4. This is *not* satellite camera footage, satellite sensor telemetry, or a live video feed.
- AIS ship positions from AISstream after you set a key; coverage depends on receivers and AIS broadcasts. Trail lines are only observations obtained while your map collector runs; they are not ship route plans.
- TomTom traffic overlay after you set a key. Review TomTom's free monthly allowance and current terms before enabling the layer.
- **Enable gestures** opt-in webcam control using the same MediaPipe HandLandmarker model approach as the JARVIS 3D lab. Camera data stays in browser memory; project code never uploads your frames to the map server. The MediaPipe JavaScript, WebAssembly and model are downloaded from CDNs.

## In VS Code / Windows

1. Extract the ZIP into a **new** folder and select that folder in VS Code: File → Open Folder.
2. In Terminal → New Terminal run:

   ```powershell
   py -3.12 -m pip install -r requirements.txt
   ```

   If your previous JARVIS setup uses a virtual environment, activate it first. For minimal map-only dependencies run `py -3.12 -m pip install sgp4 websockets`.
3. Start the local dashboard: `py -3.12 start_world_map.py`.
4. Open the URL printed in the terminal, use `Ctrl+Shift+R` to hard refresh the page.
5. Click **Explore flights** to use a small geographic area; the map initially shows the whole world and therefore does not request flights. Click **Refresh** to update available feeds (provider limits apply).
6. Click **Enable gestures** and allow webcam access if you want gesture navigation. Open palm + hand movement pans. Pinch and move up or down zooms. Two open hands move apart or together to zoom. Close your hand to pause. Click **Stop gestures** to release the webcam.
7. If you see zero flights, test a different well-covered region, inspect the status panel, then try the diagnostics below. Public ADS-B coverage can be empty/blocked by the upstream service; no API can guarantee every flight.

## Optional free keys — create these YOURSELF, keep private

### AISstream (ships)

1. Open https://aisstream.io/ and click **API keys**.
2. Sign in with GitHub and create an API key under Account.
3. In the JARVIS desktop application, open **Plugin Settings → World Map & Live Layers**, paste the key into **AISstream API key** and save. Alternatively, in your own local PowerShell session before starting JARVIS: `$env:AISSTREAM_API_KEY='YOUR_KEY'`.
4. Restart the map process and enable **AIS vessels** on a zoomed-in coastal area. New AIS messages may take time to arrive; not all vessels transmit or are covered.

### TomTom (road traffic)

1. Open https://my.tomtom.com/ and create a developer account.
2. Go to **API & SDK Keys**. A new account may already include **My first API key**. Confirm current eligible free quota, supported Traffic Flow tile API and billing terms.
3. In **Plugin Settings → World Map & Live Layers**, set **TomTom Traffic API key** and save. Or in your own local PowerShell session: `$env:TOMTOM_API_KEY='YOUR_KEY'`.
4. Restart the map and enable **Traffic flow**. Zoom toward roads. If tiles error, check provider endpoint eligibility, credits and the F12 Console.

Do **not** post your API keys into ChatGPT, screenshots, or public repositories. Keep old private `config/api_keys.json` and `memory/` files only on your own machine. They are excluded from this package.

## Quick diagnostics

- Check `http://127.0.0.1:PORT/api/status` using the same port printed at startup. It returns feature configuration booleans and no keys.
- Satellite failure: `py -3.12 -m pip install sgp4` then press Refresh; check network access to CelesTrak.
- Flight failure: zoom to 6+, click Explore flights; check status message and provider network availability. No ADS-B API key is necessary for the existing public regional fallback, subject to provider limits.
- Ship failure: verify AISstream key is configured and `py -3.12 -m pip install websockets` completed; allow time for new messages.
- Gesture failure: use Chrome/Edge on localhost, check camera permission, and test connectivity to `cdn.jsdelivr.net` and `storage.googleapis.com`. The webcam is off until you explicitly enable gestures.
- F12 → Console shows renderer/provider errors. Send screenshots **without any API keys** if you need debugging help.

## Limits and ethics

This is a public-data visualization dashboard, not an actual all-seeing live Earth camera or a means to locate private individuals. Position accuracy and availability depend on separate providers, their data rights and their update cadence. No live data is fabricated. Any provider may impose rate limits or change availability.
