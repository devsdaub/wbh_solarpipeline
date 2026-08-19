import logging
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text

from app.api.routes import router as api_router
from app.api.upload import router as upload_router
from app.api.data import router as data_router
from app.api.settings import router as settings_router
from app.config import load_plant_config, load_scheduler_config, load_sources_config
from app.pipeline.scheduler import scheduler_status, start_scheduler, stop_scheduler
from app.database import Base, SessionLocal, engine
from app.models import DailyFact, HourlyWeather, PipelineRun, PlantConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    _seed_plant_config()
    start_scheduler()
    yield
    stop_scheduler()


def _seed_plant_config() -> None:
    settings = load_plant_config()
    with SessionLocal() as session:
        plant = session.execute(
            select(PlantConfig).where(PlantConfig.name == settings.name)
        ).scalar_one_or_none()

        if plant is None:
            plant = PlantConfig(name=settings.name)
            session.add(plant)

        plant.latitude = settings.location.latitude
        plant.longitude = settings.location.longitude
        plant.tilt_deg = settings.panel.tilt_deg
        plant.azimuth_deg = settings.panel.azimuth_deg
        plant.capacity_w = settings.panel.capacity_w
        plant.installation_date = settings.installation_date
        plant.acquisition_cost_eur = settings.economics.acquisition_cost_eur
        plant.subsidy_eur = settings.economics.subsidy_eur
        session.commit()


app = FastAPI(
    title="SolarPipeline",
    description="Datenpipeline für ein Balkonkraftwerk in Stuttgart",
    version="0.1.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(api_router)
app.include_router(upload_router)
app.include_router(data_router)
app.include_router(settings_router)

@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as error:
        database_status = f"nicht erreichbar: {type(error).__name__}"

    return {"status": "ok", "database": database_status}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, upload: str | None = None, zeilen: int | None = None):
    settings = load_plant_config()

    with SessionLocal() as session:
        plant = session.execute(
            select(PlantConfig).where(PlantConfig.name == settings.name)
        ).scalar_one()

        tage = session.execute(
            select(DailyFact)
            .where(DailyFact.plant_id == plant.id)
            .order_by(DailyFact.date.desc())
            .limit(21)
        ).scalars().all()

        stunden, tage_gesamt, summe_kwh, eq_mittel = session.execute(
            select(
                select(func.count(HourlyWeather.id))
                .where(HourlyWeather.plant_id == plant.id)
                .scalar_subquery(),
                func.count(DailyFact.id),
                func.sum(DailyFact.production_kwh),
                func.avg(DailyFact.eq),
            ).where(DailyFact.plant_id == plant.id)
        ).one()

        letzter_lauf = session.execute(
            select(PipelineRun).order_by(PipelineRun.id.desc()).limit(1)
        ).scalar_one_or_none()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "plant_name": settings.name,
            "capacity_w": settings.panel.capacity_w,
            "tilt_deg": settings.panel.tilt_deg,
            "azimuth_deg": settings.panel.azimuth_deg,
            "tage": tage,
            "stunden": stunden,
            "tage_gesamt": tage_gesamt,
            "summe_kwh": summe_kwh,
            "eq_mittel": eq_mittel,
            "letzter_lauf": letzter_lauf,
            "upload": upload,
            "zeilen": zeilen,
        },
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, gespeichert: str | None = None):
    status = scheduler_status()

    with SessionLocal() as session:
        laeufe = session.execute(
            select(PipelineRun).order_by(PipelineRun.id.desc()).limit(25)
        ).scalars().all()

    naechster = None
    if status["naechster_lauf"]:
        naechster = datetime.fromisoformat(status["naechster_lauf"])

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "status": status,
            "scheduler": load_scheduler_config(),
            "quellen": load_sources_config(),
            "laeufe": laeufe,
            "naechster": naechster,
            "gespeichert": gespeichert,
        },
    )