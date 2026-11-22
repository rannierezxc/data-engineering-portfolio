# 🌦️ Weather Data Platform

An end-to-end data engineering portfolio project, built in phases.

## Phase 1: Resilient Python Ingestion
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
![alt text](download.svg)

![alt text](download-1.svg)