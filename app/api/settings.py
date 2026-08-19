from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from app.config import load_scheduler_config, load_sources_config, save_scheduler_config, save_sources_config
from app.pipeline.scheduler import apply_config

router = APIRouter(prefix="/settings", tags=["Einstellungen"])


@router.post("/scheduler")
def update_scheduler(
    interval_minutes: int = Form(...),
    enabled: bool = Form(False),
) -> RedirectResponse:
    """Speichert die Scheduler-Konfiguration und übernimmt sie sofort."""
    settings = load_scheduler_config()
    settings.enabled = enabled
    settings.jobs["pipeline"].interval_minutes = interval_minutes
    settings.jobs["pipeline"].enabled = enabled
    save_scheduler_config(settings)

    apply_config()

    return RedirectResponse("/settings?gespeichert=scheduler", status_code=303)


@router.post("/sources")
def update_sources(
    open_meteo_weather: bool = Form(False),
    open_meteo_air: bool = Form(False),
) -> RedirectResponse:
    """Schaltet einzelne Datenquellen an oder ab."""
    settings = load_sources_config()
    settings.open_meteo_weather.enabled = open_meteo_weather
    settings.open_meteo_air.enabled = open_meteo_air
    save_sources_config(settings)

    return RedirectResponse("/settings?gespeichert=quellen", status_code=303)