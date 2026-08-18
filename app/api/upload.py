import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.pipeline.ingestion import import_energy_report

router = APIRouter(prefix="/api", tags=["Upload"])

UPLOAD_DIR = Path("/app/uploads")


@router.post("/upload/energy")
def upload_energy_report(file: UploadFile) -> dict:
    """Nimmt einen Hoymiles-Energy-Report entgegen und importiert ihn."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Es werden nur CSV-Dateien akzeptiert.")

    # .name verwirft Pfadanteile im Dateinamen (Path Traversal)
    target = UPLOAD_DIR / Path(file.filename).name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with target.open("wb") as ziel:
        shutil.copyfileobj(file.file, ziel)

    try:
        return import_energy_report(target)
    except ValueError as fehler:
        raise HTTPException(422, str(fehler))