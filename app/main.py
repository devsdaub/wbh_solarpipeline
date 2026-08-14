from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text
from app.database import engine

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="SolarPipeline",
    description="Datenpipeline für ein Balkonkraftwerk in Stuttgart",
    version="0.1.0",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")

from fastapi.staticfiles import StaticFiles

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