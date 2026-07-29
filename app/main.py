from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "plant_name": "Kleines Kraftwerk",
            "capacity_w": 800,
            "tilt_deg": 17,
            "azimuth_deg": 203,
        },
    )