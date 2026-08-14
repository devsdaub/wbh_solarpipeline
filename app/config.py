import os
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/app/config"))


class Location(BaseModel):
    latitude: float
    longitude: float
    city: str


class Panel(BaseModel):
    capacity_w: int
    tilt_deg: int
    azimuth_deg: int


class Economics(BaseModel):
    acquisition_cost_eur: float
    subsidy_eur: float
    electricity_price_eur_kwh: float


class PlantSettings(BaseModel):
    name: str
    installation_date: date
    location: Location
    panel: Panel
    economics: Economics


def load_plant_config() -> PlantSettings:
    path = CONFIG_DIR / "plant.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PlantSettings.model_validate(raw["plant"])


class SourceSettings(BaseModel):
    enabled: bool
    url: str
    default_days_back: int
    variables: list[str]


class SourcesSettings(BaseModel):
    open_meteo_weather: SourceSettings


def load_sources_config() -> SourcesSettings:
    path = CONFIG_DIR / "sources.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SourcesSettings.model_validate(raw["sources"])