from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select

from app.adapters.open_meteo_weather import OpenMeteoWeatherAdapter
from app.config import load_plant_config, load_sources_config
from app.database import SessionLocal
from app.models import HourlyWeather, PlantConfig


def _to_records(frame: pd.DataFrame) -> list[dict]:
    records = frame.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
    return records


def ingest_weather(start: date | None = None, end: date | None = None) -> dict:
    """Holt Wetterdaten und schreibt sie in die Tabelle hourly_weather."""
    plant_settings = load_plant_config()
    source = load_sources_config().open_meteo_weather

    if not source.enabled:
        return {"status": "uebersprungen", "grund": "Quelle ist deaktiviert"}

    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=source.default_days_back)

    with SessionLocal() as session:
        plant = session.execute(
            select(PlantConfig).where(PlantConfig.name == plant_settings.name)
        ).scalar_one()

        adapter = OpenMeteoWeatherAdapter(plant_settings, source, plant.id)
        frame = adapter.fetch(start, end)
        records = _to_records(frame)

        session.add_all([HourlyWeather(**record) for record in records])
        session.commit()

    return {
        "status": "ok",
        "quelle": adapter.name,
        "zeitraum": f"{start} bis {end}",
        "datensaetze": len(records),
    }