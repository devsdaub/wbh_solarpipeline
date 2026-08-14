# SolarPipeline

Datenpipeline für mein 800-W-Balkonkraftwerk. Führt Produktionsdaten
(Hoymiles) mit Wetter- und Luftqualitätsdaten in einer PostgreSQL-Datenbank
zusammen und stellt sie in einem Dashboard dar.

## Schnellstart

Voraussetzung: Docker Desktop.

```bash
cp .env.example .env
docker compose up --build
```

## Endpunkte

| Pfad | Zweck |
|---|---|
| `/` | Dashboard |
| `/health` | Betriebszustand von Anwendung und Datenbank |
| `/docs` | Automatisch erzeugte OpenAPI-Dokumentation |


## Konfiguration

Anlagendaten stehen in `config/plant.yaml` und werden beim Start automatisch
in die Tabelle `plant_config` übernommen.


## Datenmodell

Star-Schema mit vier Tabellen:

| Tabelle | Zweck |
|---|---|
| `plant_config` | Stammdaten der Anlage (Dimension) |
| `daily_facts` | Tageswerte, Produktion und Wetter zusammengeführt (Fakten) |
| `hourly_weather` | Stündliche Wetter- und Luftqualitätsdaten |
| `power_readings` | 20-Minuten-Leistungswerte aus dem Hoymiles-Inverter |

Tabellen und Anlagenzeile entstehen automatisch beim Start


## Datenquellen

| Quelle | Endpunkt | Status |
|---|---|---|
| Open-Meteo Wetterarchiv | `archive-api.open-meteo.com/v1/archive` | angebunden |
| Open-Meteo Luftqualität | `air-quality-api.open-meteo.com/v1/air-quality` | geplant |
| Hoymiles (CSV-Import) | manueller Upload | geplant |

Konfiguriert werden die Quellen in `config/sources.yaml`. Über das Feld
`enabled` lässt sich jede Quelle einzeln abschalten, ohne Code zu ändern.

### Datenabruf auslösen

```bash
curl -X POST http://localhost:8008/api/ingest/weather