"""lake tests use the local filesystem in a temp folder: same code path, no minio needed"""

from datetime import date

import duckdb
import pyarrow as pa
from pyarrow import fs

from weather_pipeline.lake import (
    LAKE_SCHEMA,
    read_curated_day,
    readings_to_table,
    write_curated_parquet,
    write_raw_json,
)
from weather_pipeline.lake_query import DAILY_SUMMARY_SQL, run_query
from weather_pipeline.models import WeatherResponse
from weather_pipeline.pipeline import build_parser
from weather_pipeline.transform import to_readings

DAY = date(2026, 11, 10)
LOCAL = fs.LocalFileSystem()


def bucket_in(tmp_path) -> str:
    return tmp_path.as_posix()  # a temp folder plays the role of a bucket


def make_table(manila, sample_payload) -> pa.Table:
    readings = to_readings(manila, WeatherResponse.model_validate(sample_payload))
    return readings_to_table(readings, DAY)


def test_table_matches_lake_schema(manila, sample_payload):
    table = make_table(manila, sample_payload)
    assert table.schema == LAKE_SCHEMA
    assert table.num_rows == 3


def test_parquet_is_partitioned_by_date_and_city(tmp_path, manila, sample_payload):
    write_curated_parquet(
        make_table(manila, sample_payload), filesystem=LOCAL, bucket=bucket_in(tmp_path)
    )

    files = [p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.parquet")]
    assert files == ["curated/weather_readings/reading_date=2026-11-10/city=Manila/part-0.parquet"]


def test_rewriting_a_day_does_not_duplicate(tmp_path, manila, sample_payload):
    bucket = bucket_in(tmp_path)
    table = make_table(manila, sample_payload)
    write_curated_parquet(table, filesystem=LOCAL, bucket=bucket)
    write_curated_parquet(table, filesystem=LOCAL, bucket=bucket)  # same day again

    readings = read_curated_day(DAY, filesystem=LOCAL, bucket=bucket)
    assert len(readings) == 3
    assert {r.city for r in readings} == {"Manila"}


def test_reading_a_missing_day_returns_empty(tmp_path):
    assert read_curated_day(DAY, filesystem=LOCAL, bucket=bucket_in(tmp_path)) == []


def test_raw_json_goes_to_bronze_path(tmp_path, manila, sample_payload):
    path = write_raw_json(sample_payload, manila, DAY, filesystem=LOCAL, bucket=bucket_in(tmp_path))
    assert path.endswith("raw/weather/date=2026-11-10/manila.json")


def test_duckdb_summary_reads_partitions(tmp_path, manila, sample_payload):
    bucket = bucket_in(tmp_path)
    write_curated_parquet(make_table(manila, sample_payload), filesystem=LOCAL, bucket=bucket)

    glob = f"{bucket}/curated/weather_readings/**/*.parquet"
    rows = run_query(duckdb.connect(), DAILY_SUMMARY_SQL, glob)

    assert len(rows) == 1
    reading_date, city, count, avg_temp, max_temp, rain = rows[0]
    assert (reading_date, city, count) == (DAY, "Manila", 3)
    assert max_temp == 27.1
    assert rain == 1.6


def test_pipelime_cli_parses_subcommands():
    args = build_parser().parse_args(["load-postgres", "--date", "2026-11-10"])
    assert args.command == "load-postgres"
    assert args.date == DAY
