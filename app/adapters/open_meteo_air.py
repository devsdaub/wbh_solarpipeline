from datetime import date

import httpx
import pandas as pd

from app.adapters.base import SourceAdapter
from app.config import PlantSettings, SourceSettings
from app.schemas import HOURLY_AIR_SCHEMA

COLUMN_MAP = {
    "time": "timestamp",
}


class OpenMeteoAirAdapter(SourceAdapter):
    """Liest stündliche Luftqualitätsdaten von Open-Meteo."""

    name = "open_meteo_air"

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
            "timezone": "UTC",
        }

        response = httpx.get(self.source.url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        frame = pd.DataFrame(payload["hourly"])
        frame["time"] = pd.to_datetime(frame["time"]).dt.tz_localize("UTC")
        frame = frame.rename(columns=COLUMN_MAP)
        frame["plant_id"] = self.plant_id
        return HOURLY_AIR_SCHEMA.validate(frame)