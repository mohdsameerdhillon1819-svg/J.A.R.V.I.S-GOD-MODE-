"""Compatibility entry point: world_map now opens the official 3D globe."""
from core.gods_eye_bridge import launch
if __name__ == "__main__":
    success, message = launch(open_browser=True)
    print(message)
    if not success:
        raise SystemExit(1)
