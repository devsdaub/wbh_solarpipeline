# SolarPipeline

Datenpipeline für mein 800-W-Balkonkraftwerk. Führt Produktionsdaten
(Hoymiles) mit Wetter- und Luftqualitätsdaten in einer PostgreSQL-Datenbank
zusammen und stellt sie in einem Dashboard dar.

## Schnellstart

Voraussetzung: Docker Desktop.

```bash
cp .env.example .env
docker compose up --build