""" phase2: load the processed CSV files into the postgreSQL star schema.

Ex:
	uv run python -m weather_pipeline.load_postgres --date 2026-11-09
	uv run python -m weather_pipeline.load_postgres --start 2026-10-01 --end 2026-10-31
"""

import logging
from datetime import date
from pathlib import Path

import psycopg

from weather_pipeline.config import CITIES, City
from weather_pipeline.logging_config import setup_logging
from weather_pipeline.main import dates_to_process, parse_args
from weather_pipeline.models import WeatherReading
from weather_pipeline.settings import get_settings
from weather_pipeline.storage import read_readings_csv

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

UPSERT_RAW_SQL = """
INSERT INTO raw.weather_readings (
	city, latitude, longitude, reading_time,
	temperature_c, humidity_pct, precipitation_mm, wind_speed_kmh 
) values (
	%(city)s, %(latitude)s, %(longitude)s, %(reading_time)s, 
	%(temperature_c)s, %(humidity_pct)s, %(precipitation_mm)s, %(wind_speed_kmh)s
)
on conflict (city, reading_time) do update set
	temperature_c = excluded.temperature_c,
	humidity_pct = excluded.humidity_pct,
	precipitation_mm = excluded.precipitation_mm,
	wind_speed_kmh = excluded.wind_speed_kmh,
	loaded_at = now()
"""

DELETE_FACT_DAY_SQL = "delete from warehouse.fact_weather_readings where date_key = %(date_key)s"

INSERT_FACT_DAY_SQL = """
insert into warehouse.fact_weather_readings (
	location_sk, date_key, reading_time, hour_of_day,
	temperature_c, humidity_pct, precipitation_mm, wind_speed_kmh
)

select
	l.location_sk,
	to_char(r.reading_time at time zone 'utc', 'yyyymmdd')::integer,
	r.reading_time,
	extract(hour from r.reading_time at time zone 'utc')::smallint,
	r.temperature_c, r.humidity_pct, r.precipitation_mm, r.wind_speed_kmh
from raw.weather_readings as r
join warehouse.dim_location as l
on l.city = r.city
and r.reading_time >= l.valid_from --point-in-time join: pick the version
and r.reading_time < l.valid_to --that was valid when the reading happened
where (r.reading_time at time zone 'utc')::date = %(target_date)s
"""


def run_sql_file(conn: psycopg.Connection, filename: str) -> None:
	"""run every statement in a .sql file (allowed because we pass no parameters)"""
	conn.execute((SQL_DIR / filename).read_text(encoding="utf-8"))

def apply_schema(conn: psycopg.Connection) -> None:
	with conn.transaction():
		run_sql_file(conn, "01_schema.sql")
		run_sql_file(conn, "02_dim_date.sql")

def sync_dim_location(conn: psycopg.Connection, cities: list[City]) -> None:
	"""copy today's city list into a temp table, then apply the SCD type2 merge"""
	with conn.transaction():
		conn.execute(
			"""
			CREATE temp table stg_location (
				city TEXT, country TEXT, region text, latitude double precision, longitude double precision,
				timezone TEXT ) on commit drop """
		)
		with conn.cursor() as cur:
			cur.executemany(
			"insert into stg_location values (%s, %s, %s, %s, %s, %s)",
			[ (c.name, c.country, c.region, c.latitude, c.longitude, c.timezone)
				for c in cities
			],
		)
		run_sql_file(conn, "03_scd2_dim_location.sql")


def load_raw_readings(conn: psycopg.Connection, readings: list[WeatherReading]) -> int:
	with conn.transaction(), conn.cursor() as cur:
		cur.executemany(UPSERT_RAW_SQL, [r.model_dump() for r in readings])
	return len(readings)


def load_fact_for_date(conn: psycopg.Connection, target_date: date) -> int:
	""" delete-then-insert one day of facts inside one transaction (idempotent)"""
	date_key = int(target_date.strftime("%Y%m%d"))
	with conn.transaction():
		conn.execute(DELETE_FACT_DAY_SQL, {"date_key": date_key})
		cur = conn.execute(INSERT_FACT_DAY_SQL, {"target_date": target_date})
		return cur.rowcount

def main(argv: list[str] | None = None) -> int:
	setup_logging()
	args = parse_args(argv)
	settings = get_settings()
	with psycopg.connect(settings.postgres_conninfo, autocommit=True) as conn:
		apply_schema(conn)
		sync_dim_location(conn, CITIES)
		for target_date in dates_to_process(args):
			readings = read_readings_csv(target_date)
			if not readings:
				logger.warning("%s: no processed CSV found, skipping", target_date)
				continue
			load_raw_readings(conn, readings)
			fact_rows = load_fact_for_date(conn, target_date)
			logger.info("%s: %d raw rows -> %d fact rows", target_date, len(readings), fact_rows)
			if fact_rows != len(readings):
				logger.warning("%s: row counts differ! check dim_location", target_date)
	return 0

if __name__ == "__main__":
	raise SystemExit(main())

