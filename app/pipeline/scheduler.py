import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import load_scheduler_config
from app.pipeline.ingestion import run_pipeline

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")

JOB_ID = "pipeline"


def _pipeline_job() -> None:
    try:
        run_pipeline(trigger="scheduler")
    except Exception:
        logger.exception("Geplanter Pipeline-Lauf fehlgeschlagen")


def start_scheduler() -> None:
    """Startet den Hintergrund-Scheduler gemäss scheduler.yaml."""
    settings = load_scheduler_config()

    if not settings.enabled:
        logger.info("Scheduler ist deaktiviert")
        return

    job = settings.jobs["pipeline"]
    if not job.enabled:
        logger.info("Pipeline-Auftrag ist deaktiviert")
        return

    scheduler.add_job(
        _pipeline_job,
        trigger="interval",
        minutes=job.interval_minutes,
        id=JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler gestartet, Intervall %s Minuten", job.interval_minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler gestoppt")