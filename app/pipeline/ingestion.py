import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.adapters.hoymiles_csv import HoymilesEnergyAdapter
from app.adapters.open_meteo_air import OpenMeteoAirAdapter
from app.adapters.open_meteo_weather import OpenMeteoWeatherAdapter
from app.config import load_plant_config, load_sources_config
from app.database import SessionLocal
from app.models import DailyFact, HourlyWeather, PlantConfig
from app.pipeline.util import to_records

logger = logging.getLogger(__name__)

ADAPTERS = {
    "open_meteo_weather": OpenMeteoWeatherAdapter,
    "open_meteo_air": OpenMeteoAirAdapter,
}

KEY_COLUMNS = ("plant_id", "timestamp")


def _current_plant_id(session) -> int:
    """Liefert die id der konfigurierten Anlage."""
    settings = load_plant_config()
    return session.execute(
        select(PlantConfig).where(PlantConfig.name == settings.name)
    ).scalar_one().id


def ingest_source(
    name: str, start: date | None = None, end: date | None = None
) -> dict:
    """Holt die Daten einer Quelle und schreibt sie nach hourly_weather."""
    if name not in ADAPTERS:
        return {"status": "fehler", "grund": f"Unbekannte Quelle: {name}"}

    plant_settings = load_plant_config()
    source = getattr(load_sources_config(), name)

    if not source.enabled:
        return {"status": "uebersprungen", "quelle": name,
                "grund": "Quelle ist deaktiviert"}

    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=source.default_days_back)

    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

        adapter = ADAPTERS[name](plant_settings, source, plant_id)
        frame = adapter.fetch(start, end)
        records = to_records(frame)

        update_columns = [
            spalte for spalte in frame.columns if spalte not in KEY_COLUMNS
        ]

        statement = insert(HourlyWeather).values(records)
        statement = statement.on_conflict_do_update(
            index_elements=list(KEY_COLUMNS),
            set_={
                spalte: statement.excluded[spalte] for spalte in update_columns
            },
        )
        session.execute(statement)
        session.commit()

    return {
        "status": "ok",
        "quelle": name,
        "zeitraum": f"{start} bis {end}",
        "datensaetze": len(records),
        "spalten": update_columns,
    }


def ingest_all(start: date | None = None, end: date | None = None) -> list[dict]:
    """Ruft alle konfigurierten Quellen für denselben Zeitraum ab."""
    return [ingest_source(name, start, end) for name in ADAPTERS]


def import_energy_report(path: Path) -> dict:
    """Liest einen Hoymiles-Energy-Report ein und schreibt ihn nach daily_facts."""
    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

        adapter = HoymilesEnergyAdapter()
        frame = adapter.parse(path, plant_id)
        records = to_records(frame)

        statement = insert(DailyFact).values(records)
        statement = statement.on_conflict_do_update(
            index_elements=["plant_id", "date"],
            set_={"production_kwh": statement.excluded.production_kwh},
        )
        session.execute(statement)
        session.commit()

    kalender = pd.date_range(frame["date"].min(), frame["date"].max(), freq="D")
    fehlend = kalender.difference(frame["date"])

    return {
        "status": "ok",
        "quelle": adapter.name,
        "datei": path.name,
        "datensaetze": len(records),
        "zeitraum": f"{frame['date'].min().date()} bis {frame['date'].max().date()}",
        "kalendertage": len(kalender),
        "fehlende_tage": len(fehlend),
    }


def run_pipeline(start: date | None = None, end: date | None = None) -> dict:
    """Ruft alle Quellen ab und verdichtet anschliessend auf Tageswerte."""
    # lokal importiert, sonst Zirkelbezug mit transformation.py
    from app.pipeline.transformation import aggregate_daily, find_production_gaps

    quellen = ingest_all(start, end)

    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

    aggregation = aggregate_daily(plant_id)
    luecken = find_production_gaps(plant_id)

    return {
        "status": "ok",
        "quellen": quellen,
        "aggregation": aggregation,
        "datenqualitaet": luecken,
    }