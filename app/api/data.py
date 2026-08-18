from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import DailyFact
from app.pipeline.ingestion import _current_plant_id

router = APIRouter(prefix="/api/data", tags=["Daten"])


@router.get("/daily")
def daily_series(days: int = 90) -> dict:
    """Liefert Tageswerte als Zeitreihe für die Diagramme."""
    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

        letzter = session.execute(
            select(func.max(DailyFact.date)).where(DailyFact.plant_id == plant_id)
        ).scalar_one()

        if letzter is None:
            return {"labels": [], "produktion": [], "einstrahlung": [], "eq": []}

        von = letzter - timedelta(days=days - 1)

        zeilen = session.execute(
            select(DailyFact)
            .where(DailyFact.plant_id == plant_id)
            .where(DailyFact.date.between(von, letzter))
            .order_by(DailyFact.date)
        ).scalars().all()

    return {
        "labels": [zeile.date.isoformat() for zeile in zeilen],
        "produktion": [zeile.production_kwh for zeile in zeilen],
        "einstrahlung": [zeile.gti_kwh for zeile in zeilen],
        "eq": [zeile.eq for zeile in zeilen],
    }


@router.get("/scatter")
def scatter_series() -> dict:
    """Liefert Wertepaare aus Einstrahlung und Produktion."""
    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

        zeilen = session.execute(
            select(DailyFact)
            .where(DailyFact.plant_id == plant_id)
            .where(DailyFact.production_kwh.is_not(None))
            .where(DailyFact.gti_kwh.is_not(None))
            .order_by(DailyFact.date)
        ).scalars().all()

    return {
        "punkte": [
            {"x": zeile.gti_kwh, "y": zeile.production_kwh,
             "datum": zeile.date.isoformat()}
            for zeile in zeilen
        ]
    }