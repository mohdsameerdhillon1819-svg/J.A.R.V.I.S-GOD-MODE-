"""Local bridge to the separately installed official 3D God's Eye View checkout."""
from __future__ import annotations
import shutil
import subprocess
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "external" / "gods-eye-view"
URL = "http://127.0.0.1:4173/"
_PROCESS = None
_LOCK = threading.Lock()


def installed() -> bool:
    return ((REPO / "package.json").is_file()
            and (REPO / "node_modules").is_dir()
            and (REPO / "public" / "jarvis_gesture_overlay.js").is_file()
            and 'jarvis_gesture_overlay.js' in (REPO / "index.html").read_text(encoding='utf-8'))


def _online() -> bool:
    try:
        with urllib.request.urlopen(URL, timeout=1.2) as response:
            return 200 <= response.status < 500
    except (OSError, ValueError):
        return False


def launch(*, open_browser: bool = True) -> tuple[bool, str]:
    global _PROCESS
    if not installed():
        return False, ("3D globe/gesture plugin not installed. Open VS Code terminal "
                       "and run: powershell -ExecutionPolicy Bypass -File .\\INSTALL_GODS_EYE_WINDOWS.ps1")
    executable = shutil.which("npm.cmd") or shutil.which("npm")
    if not executable:
        return False, "Node.js/npm missing. Install supported Node.js and reopen VS Code."
    with _LOCK:
        if not _online() and (_PROCESS is None or _PROCESS.poll() is not None):
            try:
                _PROCESS = subprocess.Popen(
                    [executable, "run", "dev", "--", "--host", "127.0.0.1", "--port", "4173", "--strictPort"],
                    cwd=REPO, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
            except OSError as exc:
                return False, f"Cannot start official 3D app: {type(exc).__name__}"
    if open_browser:
        def open_when_ready():
            for _ in range(60):
                if _online():
                    webbrowser.open(URL, new=2)
                    return
                if _PROCESS is not None and _PROCESS.poll() is not None:
                    break
                time.sleep(1)
            print("[GodsEye] Could not open app; check npm errors in the terminal.")
        threading.Thread(target=open_when_ready, daemon=True, name="gods-eye-browser").start()
    return True, (f"Official 3D God's Eye View starting at {URL}. "
                  "In the globe click the JARVIS HANDS button and allow webcam access. "
                  "Use POWER UP / Provider Settings for your live feeds.")
