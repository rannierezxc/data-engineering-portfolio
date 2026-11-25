"""data lake: raw json + partitioned parquet on s3-compatible object sotrage (minIO)"""

import json
from datetime import UTC, date, datetime
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import fs

from weather_pipeline.config import City
from weather_pipeline.models import WeatherReading
from weather_pipeline.settings import Settings

CURATED_PREFIX = "curated/weather_readings"

# An explicit schema = a data contract for the lake. Every file has exactly these types

LAKE_SCHEMA = pa.schema(
    [
        ("city", pa.string()),
        ("latitude", pa.float64()),
        ("longitude", pa.float64()),
        ("reading_time", pa.timestamp("us", tz="UTC")),
        ("temperature_c", pa.float64()),
        ("humidity_pct", pa.float64()),
        ("precipitation_mm", pa.float64()),
        ("wind_speed_kmh", pa.float64()),
        ("reading_date", pa.date32()),
        ("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def make_s3_filesystem(settings: Settings) -> fs.S3FileSystem:
    return fs.S3FileSystem(
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key.get_secret_value(),
        endpoint_override=settings.s3_endpoint,
        scheme="https" if settings.s3_use_ssl else "http",
        allow_bucket_creation=True,
    )


def ensure_bucket(filesystem: fs.FileSystem, bucket: str) -> None:
    if filesystem.get_file_info(bucket).type == fs.FileType.NotFound:
        filesystem.create_dir(bucket)


def readings_to_table(readings: list[WeatherReading], target_date: date) -> pa.Table:
    ingested_at = datetime.now(UTC)
    rows = [
        r.model_dump() | {"reading_date": target_date, "ingested_at": ingested_at} for r in readings
    ]
    return pa.Table.from_pylist(rows, schema=LAKE_SCHEMA)


def write_raw_json(
    payload: dict[str, Any],
    city: City,
    target_date: date,
    *,
    filesystem: fs.FileSystem,
    bucket: str,
) -> str:
    """Bronze layer: the untouched api response"""
    folder = f"{bucket}/raw/weather/date={target_date.isoformat()}"
    filesystem.create_dir(folder, recursive=True)  # needed on local disk, harmless on s3
    path = f"{folder}/{city.name.lower()}.json"
    with filesystem.open_output_stream(path) as stream:
        stream.write(json.dumps(payload).encode("utf-8"))
    return path


def write_curated_parquet(table: pa.Table, *, filesystem: fs.FileSystem, bucket: str) -> None:
    """silver layer: validated rows, partitioned by date and city"""
    pq.write_to_dataset(
        table,
        root_path=f"{bucket}/{CURATED_PREFIX}",
        partition_cols=["reading_date", "city"],
        filesystem=filesystem,
        existing_data_behavior="delete_matching",  # re-runs replace the partition = idempotent
        basename_template="part-{i}.parquet",
    )


def read_curated_day(
    target_date: date, *, filesystem: fs.FileSystem, bucket: str
) -> list[WeatherReading]:
    """Read one day back from the lake (all cities) as validated readings"""
    path = f"{bucket}/{CURATED_PREFIX}/reading_date={target_date.isoformat()}"
    if filesystem.get_file_info(path).type == fs.FileType.NotFound:
        return []
    table = pq.read_table(path, filesystem=filesystem, partitioning="hive")
    return [WeatherReading.model_validate(row) for row in table.to_pylist()]
