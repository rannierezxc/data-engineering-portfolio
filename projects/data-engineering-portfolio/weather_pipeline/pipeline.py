"""Phase 3+: the lake-based pipeline. Each sub-command can run on its own (Airflow will use this)

python -m weather_pipeline.pipeline ingest --date 2026-11-09 # api -> lake
python -m weather_pipeline.pipeline load-postgres --date 2026-11-09 #lake -> postgres
python -m weather_pipeline.pipeline run --start 2026-11-01 --end 2026-11-09 #both
"""

import argparse
import functools
import logging
from datetime import date

import psycopg
from pyarrow import fs

from weather_pipeline.config import CITIES
from weather_pipeline.lake import (
    ensure_bucket,
    make_s3_filesystem,
    read_curated_day,
    readings_to_table,
    write_curated_parquet,
    write_raw_json,
)
from weather_pipeline.load_postgres import (
    apply_schema,
    load_fact_for_date,
    load_raw_readings,
    sync_dim_location,
)
from weather_pipeline.logging_config import setup_logging
from weather_pipeline.main import dates_to_process, extract_day
from weather_pipeline.settings import Settings, get_settings

logger = logging.getLogger(__name__)

COMMANDS = {
    "ingest": "API -> raw JSON + curated Parquet in the lake",
    "load-postgres": "curated Parquet -> PostgreSQL star schema",
    "run": "ingest, then load-postgres",
}


def build_parser() -> argparse.ArgumentParser:
    date_args = argparse.ArgumentParser(add_help=False)
    date_args.add_argument("--date", type=date.fromisoformat, help="One day, YYYY-MM-DD")
    date_args.add_argument("--start", type=date.fromisoformat, help="Backfill start")
    date_args.add_argument("--end", type=date.fromisoformat, help="Backfill end")

    parser = argparse.ArgumentParser(description="Weather data platform pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in COMMANDS.items():
        sub.add_parser(name, parents=[date_args], help=help_text)
    return parser


def ingest(dates: list[date], filesystem: fs.FileSystem, bucket: str) -> int:
    """returns the number of city-days that failed."""
    save_raw = functools.partial(write_raw_json, filesystem=filesystem, bucket=bucket)
    failures = 0
    for target_date in dates:
        readings, failed = extract_day(target_date, save_raw=save_raw)
        if readings:
            write_curated_parquet(
                readings_to_table(readings, target_date), filesystem=filesystem, bucket=bucket
            )
            logger.info("%s: wrote %d readings to the lake", target_date, len(readings))
        if failed:
            logger.error("%s: failed cities -> %s", target_date, ", ".join(failed))
        failures += len(failed)
    return failures


def load_postgres(
    dates: list[date], filesystem: fs.FileSystem, bucket: str, settings: Settings
) -> int:
    """returns the number of days that had no date in the lake"""
    missing = 0
    with psycopg.connect(settings.postgres_conninfo, autocommit=True) as conn:
        apply_schema(conn)
        sync_dim_location(conn, CITIES)
        for target_date in dates:
            readings = read_curated_day(target_date, filesystem=filesystem, bucket=bucket)
            if not readings:
                logger.warning("%s: nothing in the lake for this date", target_date)
                missing += 1
                continue
            load_raw_readings(conn, readings)
            fact_rows = load_fact_for_date(conn, target_date)
            logger.info("%s: %d lake rows -> %d fact rows", target_date, len(readings), fact_rows)
        return missing


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    settings = get_settings()
    filesystem = make_s3_filesystem(settings)
    ensure_bucket(filesystem, settings.s3_bucket)
    dates = dates_to_process(args)

    problems = 0
    if args.command in ("ingest", "run"):
        problems += ingest(dates, filesystem, settings.s3_bucket)
    if args.command in ("load-postgres", "run"):
        problems += load_postgres(dates, filesystem, settings.s3_bucket, settings)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
