# JARVIS Mark-LVII — official God's Eye View as the `world_map` plugin

This release **replaces the `world_map` plugin's default action**. "Open world map" in JARVIS now starts the official **3D God's Eye View** in your browser, not JARVIS's former 2D dashboard. An opt-in webcam gesture overlay is automatically installed into the official app's *local checkout*.

## One-time install (VS Code / Windows)

1. Extract the ZIP and open `Mark-LVII` in VS Code via **File → Open Folder**.
2. Install [Git for Windows](https://git-scm.com/downloads/win) and supported [Node.js](https://nodejs.org/) (Node 24.14+ or supported 26). Restart VS Code.
3. In **Terminal → New Terminal**, run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\INSTALL_GODS_EYE_WINDOWS.ps1
   ```

   This downloads the official source from `https://github.com/bilawalsidhu/gods-eye-view`, installs npm dependencies, and adds the JARVIS gesture overlay. **The official app itself is downloaded on your PC and isn't in this ZIP.**
4. Open the app with **`OPEN_MAP_WINDOWS.bat`**, or from a terminal:

   ```powershell
   py -3.12 start_world_map.py
   ```

   It should open `http://127.0.0.1:4173/`.
5. In the official globe choose **POWER UP → Provider Settings** to configure your own provider credentials. Keys are *not* included in this ZIP. MapTiler isn't needed for the Cesium 3D globe. Public aircraft feeds are not always complete or reachable.
6. Click **✋ JARVIS HANDS** (bottom-right), allow webcam access and let MediaPipe load. It runs locally in your browser. Click **STOP HANDS** to release the webcam. MediaPipe JavaScript and WASM files are installed locally by the installer. The model is also downloaded locally when available.
7. If you also want the full JARVIS assistant:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe main.py
   ```

   Ask **"JARVIS, open world map"** — the existing plugin name `world_map` now launches the official 3D app.

## Gestures

- Open palm + movement: attempt to navigate the globe with simulated canvas dragging.
- Pinch and move up/down: attempt to zoom.
- Closed fist + movement: attempt to adjust the 3D camera.
- Two hands farther/closer: attempt to zoom.

**Gesture limitation:** Input is implemented by dispatching mouse/wheel events to the upstream WebGL canvas. Upstream's renderer changes frequently and may ignore synthetic events, so actual camera movement **must be tested in your browser**. Hand tracking itself is opt-in and does not transmit camera frames to JARVIS. This is a local companion modification, not an upstream-supported feature.

## Troubleshooting

- **Can't open app?** Confirm install script finished successfully; check Node and Git versions and VS Code terminal errors.
- **Hand button missing?** Rerun the installer. Confirm `external/gods-eye-view/index.html` contains `jarvis_gesture_overlay.js`, then press Ctrl+Shift+R.
- **Hand tracking loads but camera doesn't move?** Test mouse pan/zoom first, then inspect browser F12 → Console. The app's renderer may use input handling that rejects synthetic events.
- **Aircraft missing?** Use upstream provider settings and browser Network diagnostics; API keys for AISstream or TomTom do not provide ADS-B aircraft data.
- **Security:** Rotate AISstream, TomTom and MapTiler keys previously pasted into chat. Do not share credentials or upload your `.env`/`config/api_keys.json`.

## Verification status

JARVIS Python unit tests and the overlay's JS syntax have been checked offline. The official remote app, Windows startup, live providers and WebGL camera gestures **have not been tested** in this container. No promise of universal tracking is implied; aircraft and ship coverage varies and orbital positions are calculated estimates.

## Fix the 'Failed to fetch dynamically imported module' error

If the browser error mentions `cdn.jsdelivr.net` or `vision_bundle.mjs`, you do **not** need any API key. In VS Code, inside the extracted Mark-LVII project folder, stop the running map and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\FIX_GESTURES_WINDOWS.ps1
```

After it reports SUCCESS, restart the 3D app and press `Ctrl+Shift+R` in Chrome/Edge. Click **JARVIS HANDS** again. This copies the MediaPipe module and WASM assets under `external/gods-eye-view/public/jarvis_mediapipe/` and updates the overlay. A failing model download falls back to Google's official hosted model.

If the error persists: open `http://127.0.0.1:4173/jarvis_mediapipe/vision_bundle.mjs` in the browser. If it returns 404, you are running the wrong project folder or the repair did not complete. If the file loads, look at F12 → Console for the specific remaining error.


## Hand-gesture repair (pinch and two-hand zoom)

In your **existing installed JARVIS Mark-LVII folder**, copy the updated
`integrations/gods_eye_gestures.js`, `integrations/jarvis_gesture_engine.js`
and `FIX_GESTURES_WINDOWS.ps1` files from the patch ZIP. Then run in VS Code:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\FIX_GESTURES_WINDOWS.ps1
```

Stop and restart the God's Eye View server and force refresh (`Ctrl+Shift+R`).
Click **JARVIS HANDS**, grant camera access and wait for `Camera ready`.
If you see `No hands detected`, ensure the camera shows your full hand with
good lighting. **Pinch** thumb and index tip together and move the hand up,
down, left or right to drag the globe. **Two hands** moving apart zoom in,
together zoom out. Remove the pinch to stop moving the globe.

The repair copies local MediaPipe/WASM assets. It requires the official 3D
project to already exist in `external/gods-eye-view` and internet access
for installation if the MediaPipe package was not installed.
