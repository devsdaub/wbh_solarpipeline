from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text

from app.config import load_plant_config
from app.database import Base, SessionLocal, engine
from app.models import PlantConfig

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    _seed_plant_config()
    yield


def _seed_plant_config() -> None:
    settings = load_plant_config()
    with SessionLocal() as session:
        existing = session.execute(
            select(PlantConfig).where(PlantConfig.name == settings.name)
        ).scalar_one_or_none()

        if existing is None:
            session.add(PlantConfig(
                name=settings.name,
                latitude=settings.location.latitude,
                longitude=settings.location.longitude,
                tilt_deg=settings.panel.tilt_deg,
                azimuth_deg=settings.panel.azimuth_deg,
                capacity_w=settings.panel.capacity_w,
                installation_date=settings.installation_date,
                acquisition_cost_eur=settings.economics.acquisition_cost_eur,
                subsidy_eur=settings.economics.subsidy_eur,
            ))
            session.commit()


app = FastAPI(
    title="SolarPipeline",
    description="Datenpipeline für ein Balkonkraftwerk in Stuttgart",
    version="0.1.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as error:
        database_status = f"nicht erreichbar: {type(error).__name__}"

    return {"status": "ok", "database": database_status}


from app.config import load_plant_config

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    settings = load_plant_config()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "plant_name": settings.name,
            "capacity_w": settings.panel.capacity_w,
            "tilt_deg": settings.panel.tilt_deg,
            "azimuth_deg": settings.panel.azimuth_deg,
        },
    )