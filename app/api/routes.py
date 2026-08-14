from fastapi import APIRouter

from app.pipeline.ingestion import ingest_all, ingest_source

router = APIRouter(prefix="/api", tags=["Pipeline"])


@router.post("/ingest/weather")
def trigger_weather_ingestion() -> dict:
    """Stößt den Abruf der Wetterdaten an."""
    return ingest_source("open_meteo_weather")


@router.post("/ingest/air")
def trigger_air_ingestion() -> dict:
    """Stößt den Abruf der Luftqualitätsdaten an."""
    return ingest_source("open_meteo_air")


@router.post("/ingest/all")
def trigger_full_ingestion() -> list[dict]:
    """Ruft alle aktiven Quellen nacheinander ab."""
    return ingest_all()