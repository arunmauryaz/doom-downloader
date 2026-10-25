import os
import json
import pathlib

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")

def get_default_download_dir():
    music_dir = os.path.join(os.path.expanduser("~"), "Music", "YouTube Music")
    if not os.path.exists(music_dir):
        try:
            os.makedirs(music_dir, exist_ok=True)
        except Exception:
            music_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    return music_dir

DEFAULT_SETTINGS = {
    "download_dir": get_default_download_dir(),
    "default_format": "MP3 (320 kbps)",
    "embed_thumbnail": True,
    "crop_square": True,
    "skip_existing": True,
    "add_metadata": True,
    "max_concurrent_downloads": 2,
    "theme": "Light",
    "color_accent": "blue"
}

class ConfigManager:
    def __init__(self, config_file: str = DEFAULT_CONFIG_PATH):
        self.config_file = config_file
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"[Config] Error loading settings: {e}")

        # Ensure download directory exists
        download_dir = self.settings.get("download_dir", "")
        if not download_dir or not os.path.exists(download_dir):
            default_dir = get_default_download_dir()
            self.settings["download_dir"] = default_dir
            try:
                os.makedirs(default_dir, exist_ok=True)
            except Exception:
                pass

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

# Global singleton
config = ConfigManager()
