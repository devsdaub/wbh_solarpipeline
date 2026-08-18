import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.config import load_scheduler_config
from app.database import engine
from app.pipeline.ingestion import run_pipeline

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")

JOB_ID = "pipeline"

# frei gewählte, projektweit eindeutige Kennung der Advisory Lock
LOCK_KEY = 4711

_lock_connection = None


def _sperre_erhalten() -> bool:
    """Versucht, die projektweite Scheduler-Sperre zu belegen."""
    global _lock_connection

    verbindung = engine.connect()
    erhalten = verbindung.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}
    ).scalar_one()

    if erhalten:
        _lock_connection = verbindung
    else:
        verbindung.close()
    return erhalten


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

    if not _sperre_erhalten():
        logger.info("Scheduler läuft bereits in einem anderen Prozess")
        return

    scheduler.add_job(
        _pipeline_job,
        trigger="interval",
        minutes=job.interval_minutes,
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("Scheduler gestartet, Intervall %s Minuten", job.interval_minutes)


def stop_scheduler() -> None:
    global _lock_connection

    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler gestoppt")

    if _lock_connection is not None:
        _lock_connection.close()
        _lock_connection = None


def reschedule(interval_minutes: int) -> None:
    """Ändert das Intervall des laufenden Auftrags."""
    if scheduler.running and scheduler.get_job(JOB_ID):
        scheduler.reschedule_job(JOB_ID, trigger="interval", minutes=interval_minutes)
        logger.info("Intervall geändert auf %s Minuten", interval_minutes)


def scheduler_status() -> dict:
    """Liefert den aktuellen Zustand für die Anzeige."""
    job = scheduler.get_job(JOB_ID) if scheduler.running else None
    return {
        "laeuft": scheduler.running,
        "hat_sperre": _lock_connection is not None,
        "naechster_lauf": job.next_run_time.isoformat() if job else None,
    }