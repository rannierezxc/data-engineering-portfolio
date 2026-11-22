# 🌦️ Weather Data Platform

An end-to-end data engineering portfolio project, built in phases.

## Phase 1: Resilient Python Ingestion
"I built a modular ingestion pipeline for a weather API. I separated the API's response contract from my internal row model using Pydantic, so schema changes upstream fail loudly at the boundary instead of corrupting downstream tables. The client retries only transient errors (429 and 5xx) using exponential backoff with jitter, and fails fast on 4xx. Storage is date-partitioned and idempotent, so backfills are safe. Everything's covered by unit tests that mock HTTP, including the retry behavior."

- Fetches hourly weather for 5 Asian cities from the Open-Meteo API
- Retries temporary failures with exponential backoff + jitter (tenacity)
- Validates every payload and row with Pydantic data contracts
- Idempotent, date-partitioned raw (JSON) and processed (CSV) storage
- Rotating log files; CLI for daily runs and backfills
- 17 unit tests (pytest + mocked HTTP), Ruff, strict mypy

## Run it
```bash
uv sync
uv run python -m weather_pipeline.main --date 2026-11-09
uv run pytest
```
## Phase 2: SQL Modeling
"I modeled hourly weather data as a Kimball star schema with a grain of one city per hour. The location dimension is SCD Type 2 with surrogate keys, valid-from/valid-to ranges and a partial unique index guaranteeing one current row per city. Facts are loaded with a point-in-time join, so each reading links to the dimension version that was valid when it was observed. Loads are idempotent: raw data is upserted, and facts are delete-and-insert per day inside a single transaction. I verified both SCD2 behavior and idempotency with integration tests against a real PostgreSQL instance. I also know which measures are additive: precipitation is summed, temperature is averaged."


![alt text](download.svg)

![alt text](download-1.svg)