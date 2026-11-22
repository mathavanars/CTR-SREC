"""Read public app details from the same config file used by the browser."""

import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "frontend" / "app-config.json"
with CONFIG_PATH.open(encoding="utf-8") as config_file:
    APP_CONFIG = json.load(config_file)

# Keep the developer credit and version in one shared config file.
APP_CREDIT = str(APP_CONFIG["APP_CREDIT"])
APP_VERSION = str(APP_CONFIG["APP_VERSION"])
