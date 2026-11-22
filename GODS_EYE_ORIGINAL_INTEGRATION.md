# Replaced world_map plugin with official 3D God's Eye View

The user-facing `world_map` plugin now launches the official open-source globe. The optional 2D server implementation remains in source for compatibility/testing but is **not launched** by the `world_map` plugin or `start_world_map.py`.

See [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) for installation and hand gesture limitations. The official repository is installed separately into `external/gods-eye-view` by the provided installer. The JavaScript in `integrations/gods_eye_gestures.js` is injected into that locally downloaded app's `index.html`.

Existing `world_map` plugin enablement persists. Upstream provider keys must be set in upstream provider settings; the old `world_map` configuration is not automatically transferred. Never share or bundle keys.
