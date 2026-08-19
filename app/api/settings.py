from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from app.config import load_scheduler_config, save_scheduler_config
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