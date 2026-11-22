"""Enter AISstream and TomTom keys privately on your own machine.
Never paste credentials into screenshots, chat, or source code.
"""
from getpass import getpass
from memory.config_manager import save_plugin_config

if __name__ == "__main__":
    print("JARVIS World Map — local credentials setup")
    print("Press Enter to skip a field. Input is hidden.")
    changes = {}
    for option, label in (("aisstream_api_key", "AISstream key"), ("tomtom_api_key", "TomTom key"), ("maptiler_api_key", "MapTiler public browser key (optional; restrict to localhost)")):
        secret = getpass(f"{label}: ").strip()
        if secret:
            changes[option] = secret
    if changes:
        save_plugin_config("world_map", changes)
        print("Saved locally in config/api_keys.json. Do not upload or share this file.")
    else:
        print("No changes made.")
