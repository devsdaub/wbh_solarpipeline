from fastapi import APIRouter

from app.pipeline.ingestion import ingest_weather

router = APIRouter(prefix="/api", tags=["Pipeline"])


@router.post("/ingest/weather")
def trigger_weather_ingestion() -> dict:
    """Stößt den Abruf der Wetterdaten an."""
    return ingest_weather()