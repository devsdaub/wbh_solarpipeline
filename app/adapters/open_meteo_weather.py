from datetime import date

import httpx
import pandas as pd

from app.adapters.base import SourceAdapter
from app.config import PlantSettings, SourceSettings
from app.schemas import HOURLY_WEATHER_SCHEMA

COLUMN_MAP = {
    "time": "timestamp",
    "global_tilted_irradiance": "gti",
    "temperature_2m": "temperature",
}


def to_open_meteo_azimuth(azimuth_deg: float) -> float:
    """
    Anlagendaten sind Nord-basiert (0 = Nord, 180 = Süd, 270 = West).
    Open-Meteo erwartet Süd-basierte Werte zwischen -180 und 180
    """
    return (azimuth_deg % 360) - 180


class OpenMeteoWeatherAdapter(SourceAdapter):
    """Liest stündliche Wetterdaten aus dem Open-Meteo-Archiv."""

    name = "open_meteo_weather"

    def __init__(self, plant: PlantSettings, source: SourceSettings, plant_id: int):
        self.plant = plant
        self.source = source
        self.plant_id = plant_id

    def fetch(self, start: date, end: date) -> pd.DataFrame:
        params = {
            "latitude": self.plant.location.latitude,
            "longitude": self.plant.location.longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(self.source.variables),
            "tilt": self.plant.panel.tilt_deg,
            "azimuth": to_open_meteo_azimuth(self.plant.panel.azimuth_deg),
            "timezone": "UTC",
        }

        response = httpx.get(self.source.url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        frame = pd.DataFrame(payload["hourly"])
        frame["time"] = pd.to_datetime(frame["time"]).dt.tz_localize("UTC")
        frame = frame.rename(columns=COLUMN_MAP)
        frame["plant_id"] = self.plant_id
        return HOURLY_WEATHER_SCHEMA.validate(frame)