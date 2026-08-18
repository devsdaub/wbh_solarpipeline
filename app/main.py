from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text

from app.api.routes import router as api_router
from app.api.upload import router as upload_router
from app.config import load_plant_config
from app.database import Base, SessionLocal, engine
from app.models import HourlyWeather, PlantConfig


BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    _seed_plant_config()
    yield


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
def dashboard(request: Request):
    settings = load_plant_config()

    with SessionLocal() as session:
        plant = session.execute(
            select(PlantConfig).where(PlantConfig.name == settings.name)
        ).scalar_one()

        rows = session.execute(
            select(HourlyWeather)
            .where(HourlyWeather.plant_id == plant.id)
            .order_by(HourlyWeather.timestamp.desc())
            .limit(24)
        ).scalars().all()

        total, first, last, max_dust = session.execute(
            select(
                func.count(HourlyWeather.id),
                func.min(HourlyWeather.timestamp),
                func.max(HourlyWeather.timestamp),
                func.max(HourlyWeather.dust),
            ).where(HourlyWeather.plant_id == plant.id)
        ).one()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "plant_name": settings.name,
            "capacity_w": settings.panel.capacity_w,
            "tilt_deg": settings.panel.tilt_deg,
            "azimuth_deg": settings.panel.azimuth_deg,
            "rows": rows,
            "total": total,
            "first": first,
            "last": last,
            "max_dust": max_dust,
        },
    )