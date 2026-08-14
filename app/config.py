import os
from pathlib import Path

import yaml

CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/app/config"))


def load_plant_config() -> dict:
    path = CONFIG_DIR / "plant.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw["plant"]