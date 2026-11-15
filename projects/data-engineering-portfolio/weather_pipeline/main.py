"""command line entry point

Examples:
        uv run python -m weather_pipeline.main                                      # yesterday (UTC)
        uv run python -m weather_pipeline.main --date 2026-11-01                    # one specific day
        uv run python -m weather_pipeline.main --start 2026-10-01 --end 2026-10-31  #backfill
"""

import argparse
import logging
from datetime import UTC, date, datetime, timedelta

import requests
from pydantic import ValidationError

from weather_pipeline.client import fetch_raw_weather
from weather_pipeline.config import CITIES
from weather_pipeline.logging_config import setup_logging
from weather_pipeline.models import WeatherReading, WeatherResponse
from weather_pipeline.storage import save_readings_csv
from weather_pipeline.transform import to_readings

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch hourly weather data from Open-Meteo")
    parser.add_argument("--date", type=date.fromisoformat, help="One day, YYYY-MM-DD")
    parser.add_argument("--start", type=date.fromisoformat, help="Backfill start, YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, help="Backfill end, YYYY-MM-DD")
    return parser.parse_args(argv)


def dates_to_process(args: argparse.Namespace) -> list[date]:
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("--start and --end must be use together")
        if args.start > args.end:
            raise SystemExit("--start must be on or before --end")
        days = (args.end - args.start).days + 1
        return [args.start + timedelta(days=i) for i in range(days)]
    if args.date:
        return [args.date]
    return [datetime.now(UTC).date() - timedelta(days=1)]


def extract_day(target_date: date) -> tuple[list[WeatherReading], list[str]]:
    """fetch, save raw, validate, and flatten every city. Returns (readings, failed_cities)"""
    readings: list[WeatherReading] = []
    failed: list[str] = []
    for city in CITIES:
        try:
            raw = fetch_raw_weather(city, target_date)  # keep the evidence before validating
            parsed = WeatherResponse.model_validate(raw)
            readings.extend(to_readings(city, parsed))

        except (requests.RequestException, ValidationError):
            logger.exception("Skipping %s on %s", city.name, target_date)
            failed.append(city.name)

    return readings, failed


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = parse_args(argv)
    total_failures = 0
    for target_date in dates_to_process(args):
        readings, failed = extract_day(target_date)
        if readings:
            path = save_readings_csv(readings, target_date)
            logger.info("Saved %d readings to %s", len(readings), path)

        if failed:
            logger.error("%s: failed cities -> %s", target_date, ", ".join(failed))
        total_failures += len(failed)
    return 1 if total_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
