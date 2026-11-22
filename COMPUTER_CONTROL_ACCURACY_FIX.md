# JARVIS computer-control accuracy update

The existing `actions/computer_control.py` is updated in-place. No new plugin is required.

## Changes

- Windows scroll values now use ordinary PyAutoGUI scroll units instead of multiplying each scroll by 120.
- Screen clicks, moves, and drags reject out-of-bounds, missing, and invalid coordinates before moving the cursor.
- AI screenshot element detection requests JSON-only screenshot-pixel coordinates, rejects missing/off-screen targets and converts between screenshot and cursor sizes for DPI scaling.
- `focus_window` reports failure if Windows AppActivate returns false; untrusted titles aren't inserted into executable PowerShell source.
- Unicode typing uses clipboard paste where installed and reports missing dependencies instead of typing corrupt characters.
- Computer-control tool logs no longer echo typed text / clipboard inputs.
- Unknown personal memory fields are not silently replaced by fabricated random identities.
- Negative wait duration is bounded at zero.

## Windows VS Code instructions

1. Back up the old JARVIS project. Extract this ZIP into a new folder and open the `Mark-LVII` folder in VS Code.
2. Open **Terminal > New Terminal**.
3. Use the existing virtual environment, or create one:
   `py -3.12 -m venv .venv`
4. Install the original requirements:
   `.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt`
5. Run all offline tests:
   `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v`
6. Start JARVIS:
   `.\\.venv\\Scripts\\python.exe main.py`
7. Test in a disposable text editor window: "type hello", "scroll down three", "focus Notepad", "find the Save button" (use a visible harmless UI target).

The existing 3D God's Eye View plugin and local-media-pipe gesture installer remain included. To repair/install gestures separately, use `FIX_GESTURES_WINDOWS.ps1` from this folder. Its webcam integration and live provider data have NOT been verified on this host.

## Accuracy limitations

Screen-location predictions are heuristic, not guaranteed. Use normal Windows display scaling and avoid changing monitors/resolution mid-command. Test low-risk clicks before using any UI automation on important files. The module refuses invalid coordinates but cannot guarantee an in-bounds click hits the intended control.

Keep all API keys in local configuration. Credentials previously pasted in chat should be rotated.
