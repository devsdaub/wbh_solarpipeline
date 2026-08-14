from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.adapters.open_meteo_weather import OpenMeteoWeatherAdapter
from app.config import load_plant_config, load_sources_config
from app.database import SessionLocal
from app.models import HourlyWeather, PlantConfig

# Spalten, die bei einem erneuten Abruf überschrieben werden.
# plant_id und timestamp fehlen bewusst, über sie wird die Zeile identifiziert.
WEATHER_UPDATE_COLUMNS = (
    "gti",
    "temperature",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "visibility",
)


def _to_records(frame: pd.DataFrame) -> list[dict]:
    """Wandelt ein DataFrame in Datensätze für die Datenbank um.

    pandas nutzt NaN und NA als Fehlwerte. Beide sind keine Python-None-Werte
    und würden von PostgreSQL nicht als NULL, sondern als Zahlenwert NaN
    gespeichert. Deshalb werden sie hier ausdrücklich ersetzt.
    """
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

        statement = insert(HourlyWeather).values(records)
        statement = statement.on_conflict_do_update(
            index_elements=["plant_id", "timestamp"],
            set_={
                spalte: statement.excluded[spalte]
                for spalte in WEATHER_UPDATE_COLUMNS
            },
        )
        session.execute(statement)
        session.commit()

    return {
        "status": "ok",
        "quelle": adapter.name,
        "zeitraum": f"{start} bis {end}",
        "datensaetze": len(records),
    }