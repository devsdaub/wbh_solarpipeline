from datetime import date

from fastapi import APIRouter

from app.pipeline.ingestion import ingest_all, ingest_source
from app.pipeline.transformation import aggregate_daily, find_production_gaps
from app.database import SessionLocal
from app.pipeline.ingestion import _current_plant_id

router = APIRouter(prefix="/api", tags=["Pipeline"])


@router.post("/ingest/weather")
def trigger_weather_ingestion(
    start: date | None = None, end: date | None = None
) -> dict:
    """Stößt den Abruf der Wetterdaten an.

    Ohne Angabe wird der in sources.yaml hinterlegte Zeitraum verwendet.
    """
    return ingest_source("open_meteo_weather", start, end)


@router.post("/ingest/air")
def trigger_air_ingestion(
    start: date | None = None, end: date | None = None
) -> dict:
    """Stößt den Abruf der Luftqualitätsdaten an."""
    return ingest_source("open_meteo_air", start, end)


@router.post("/ingest/all")
def trigger_full_ingestion(
    start: date | None = None, end: date | None = None
) -> list[dict]:
    """Ruft alle aktiven Quellen für denselben Zeitraum ab."""
    return ingest_all(start, end)


@router.post("/transform/daily")
def trigger_daily_aggregation() -> dict:
    """Verdichtet die Stundenwerte zu Tageswerten."""
    with SessionLocal() as session:
        plant_id = _current_plant_id(session)
    return aggregate_daily(plant_id)


@router.get("/quality/gaps")
def report_production_gaps() -> dict:
    """Meldet Lücken in den Produktionsdaten innerhalb des Messzeitraums."""
    with SessionLocal() as session:
        plant_id = _current_plant_id(session)
    return find_production_gaps(plant_id)