"""Replace the legacy 2D world_map plugin with the official 3D God's Eye View.

The plugin keeps its original name to preserve JARVIS voice-tool discovery and
existing enable/disable settings. Upstream source is downloaded separately.
"""
from __future__ import annotations

from core.gods_eye_bridge import launch, installed

PLUGIN = {
    "name": "world_map",
    "description": (
        "Open the official 3D God's Eye View globe with public aircraft positions, "
        "satellite orbit estimates, AIS vessels and traffic layers. The globe also "
        "has opt-in webcam hand gesture navigation. Use for open world map, "
        "God's Eye View, 3D map, flights, satellites, ships and traffic requests."
    ),
    "parameters": {"type": "OBJECT", "properties": {
        "action": {"type": "STRING", "enum": ["open", "status"],
                   "description": "open launches the official 3D globe; status checks installation"}},
                   "required": []},
    "behavior": "NON_BLOCKING",
    "tier": "core",
    "brief": "Launch official 3D God's Eye View with opt-in webcam gestures.",
}

# Existing namespace retained so plugin controls and existing keys are not lost.
# Upstream's Provider Settings are separate and need their own credentials.
PLUGIN_SETTINGS = {
    "namespace": "world_map",
    "title": "🌍 GOD'S EYE 3D GLOBE",
    "fields": [],
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = str((parameters or {}).get("action") or "open").strip().lower()
    if action == "status":
        return ("Official 3D God's Eye View and webcam gesture overlay are installed. "
                if installed() else
                "World Map 3D globe not installed yet. Run INSTALL_GODS_EYE_WINDOWS.ps1 once "
                "from the project's VS Code terminal; then ask JARVIS to open world map.")
    try:
        ok, message = launch(open_browser=True)
        if player:
            player.write_log("SYS: " + message)
        return message
    except Exception as exc:
        return f"God's Eye View couldn't start ({type(exc).__name__}): {exc}"
