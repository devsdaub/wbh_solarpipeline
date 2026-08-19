from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import DailyFact
from app.pipeline.ingestion import _current_plant_id

router = APIRouter(prefix="/api/data", tags=["Daten"])

# Ein vollständiger Tag hat 24 Stundenwerte, an der Zeitumstellung 23 oder 25.
MIN_STUNDEN = 23


@router.get("/daily")
def daily_series(days: int = 90) -> dict:
    """Liefert Tageswerte als Zeitreihe für die Diagramme."""
    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

        letzter = session.execute(
            select(func.max(DailyFact.date))
            .where(DailyFact.plant_id == plant_id)
            .where(DailyFact.hours >= MIN_STUNDEN)
        ).scalar_one()

        if letzter is None:
            return {"labels": [], "produktion": [], "einstrahlung": [], "eq": []}

        von = letzter - timedelta(days=days - 1)

        zeilen = session.execute(
            select(DailyFact)
            .where(DailyFact.plant_id == plant_id)
            .where(DailyFact.date.between(von, letzter))
            .where(DailyFact.hours >= MIN_STUNDEN)
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
            .where(DailyFact.hours >= MIN_STUNDEN)
            .order_by(DailyFact.date)
        ).scalars().all()

    return {
        "punkte": [
            {"x": zeile.gti_kwh, "y": zeile.production_kwh,
             "datum": zeile.date.isoformat()}
            for zeile in zeilen
        ]
    }


@router.get("/monthly")
def monthly_series() -> dict:
    """Liefert Monatssummen je Jahr für den Jahresvergleich."""
    monat = func.extract("month", DailyFact.date)
    jahr = func.extract("year", DailyFact.date)

    with SessionLocal() as session:
        plant_id = _current_plant_id(session)

        zeilen = session.execute(
            select(
                jahr.label("jahr"),
                monat.label("monat"),
                func.sum(DailyFact.production_kwh).label("kwh"),
                func.count(DailyFact.production_kwh).label("tage"),
            )
            .where(DailyFact.plant_id == plant_id)
            .where(DailyFact.production_kwh.is_not(None))
            .group_by("jahr", "monat")
            .order_by("jahr", "monat")
        ).all()

    jahre = sorted({int(zeile.jahr) for zeile in zeilen})
    werte = {(int(z.jahr), int(z.monat)): round(z.kwh, 1) for z in zeilen}
    tage = {(int(z.jahr), int(z.monat)): z.tage for z in zeilen}

    return {
        "labels": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        "reihen": [
            {
                "jahr": j,
                "werte": [werte.get((j, m)) for m in range(1, 13)],
                "tage": [tage.get((j, m)) for m in range(1, 13)],
            }
            for j in jahre
        ],
    }