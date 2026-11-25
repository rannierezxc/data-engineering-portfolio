"""save data to local disk. Same date -> same fil name, so re-running overwrites. (idempotent)"""

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from weather_pipeline.config import PROCESSED_DIR, RAW_DIR, City
from weather_pipeline.models import WeatherReading


def save_raw_json(
    payload: dict[str, Any], city: City, target_date: date, base_dir: Path = RAW_DIR
) -> Path:
    path = base_dir / f"date={target_date.isoformat()}" / f"{city.name.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def save_readings_csv(
    readings: list[WeatherReading], target_date: date, base_dir: Path = PROCESSED_DIR
) -> Path:
    path = base_dir / f"weather_{target_date.isoformat()}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(WeatherReading.model_fields)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for reading in readings:
            writer.writerow(reading.model_dump(mode="json"))
    return path


def read_readings_csv(target_date: date, base_dir: Path = PROCESSED_DIR) -> list[WeatherReading]:
    """read a processed csv back into validated readings. empty cells become none"""
    path = base_dir / f"weather_{target_date.isoformat()}.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [
            WeatherReading.model_validate({k: (v if v != "" else None) for k, v in row.items()})
            for row in csv.DictReader(f)
        ]
