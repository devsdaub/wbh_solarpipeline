from fastapi import FastAPI

app = FastAPI(
    title="SolarPipeline",
    description="Datenpipeline für ein Balkonkraftwerk",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}