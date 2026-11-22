""" integration tests: they need the postgreSQL container running, otherwise they are skipped."""

import dataclasses
from datetime import UTC, date, datetime

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from pydantic import ValidationError

from weather_pipeline.config import CITIES
from weather_pipeline.load_postgres import (
	apply_schema,
	load_fact_for_date,
	load_raw_readings,
	sync_dim_location,
)
from weather_pipeline.models import WeatherReading
from weather_pipeline.settings import get_settings

TEST_DB = "weather_test" # a separate database, so tests never touch your real data
DAY = date(2026,11, 9)

@pytest.fixture
def conn():
	try:
		main_conninfo = get_settings().postgres_conninfo
		admin = psycopg.connect(main_conninfo, autocommit=True, connect_timeout=3)
	except (ValidationError, psycopg.OperationalError):
		pytest.skip("PostgreSQL is nto configured or not running")

	with admin:
		if not admin.execute("select 1 from pg_database where datname = %s", (TEST_DB,)).fetchone():
			admin.execute(f"CREATE DATABASE {TEST_DB}")
	with psycopg.connect(make_conninfo(main_conninfo, dbname=TEST_DB), autocommit=True) as c:
		c.execute("DROP SCHEMA IF EXISTS raw CASCADE; DROP SCHEMA IF EXISTS warehouse CASCADE;")
		apply_schema(c)
		yield c

def make_readings(day: date) -> list[WeatherReading]:
	return [
		WeatherReading(
			city=c.name,
			latitude=c.latitude,
			longitude=c.longitude,
			reading_time=datetime(day.year, day.month, day.day, hour, tzinfo=UTC),
			temperature_c=25 + hour/2,
			humidity_pct=70,
			precipitation_mm=0.1 * hour,
			wind_speed_kmh=5,
		)
		for c in CITIES
		for hour in range(24)
	]

def scalar(conn, sql):
	return conn.execute(sql).fetchone()[0]

def manila_moved():
	return [dataclasses.replace(c, region="NCR") if c.name == "Manila" else c for c in CITIES]

def test_dim_date_is_populated(conn):
	row = conn.execute(
		"SELECT day_name, is_weekend FROM warehouse.dim_date WHERE date_key = 20261108"
	).fetchone()
	assert row == ("Sunday", True)


def test_scd2_only_adds_rows_when_something_changes(conn):
	sync_dim_location(conn, CITIES)
	sync_dim_location(conn, CITIES) # nothing changes -> nothing new
	assert scalar(conn, "SELECT count(*) FROM warehouse.dim_location") == 5

	sync_dim_location(conn, manila_moved())
	
	rows = conn.execute(
		"SELECT region, is_current FROM warehouse.dim_location "
		"WHERE city = 'Manila' ORDER BY valid_from"
	).fetchall()
	assert rows == [("Metro Manila", False), ("NCR", True)]
	assert scalar(conn, "SELECT count(*) FROM warehouse.dim_location WHERE is_current") == 5

def test_fact_load_is_idempotent(conn):
	sync_dim_location(conn, CITIES)
	for _ in range(2): #load the same day twice
		load_raw_readings(conn, make_readings(DAY))
		assert load_fact_for_date(conn, DAY) == 120
	assert scalar(conn, "SELECT count(*) FROM warehouse.fact_weather_readings") == 120

def test_fact_points_to_version_valid_at_reading_time(conn):
	sync_dim_location(conn, CITIES)
	load_raw_readings(conn, make_readings(DAY))
	sync_dim_location(conn, manila_moved()) #the change happens now, after the readings
	
	load_fact_for_date(conn, DAY)
	regions = conn.execute(
		"SELECT DISTINCT l.region FROM warehouse.fact_weather_readings as f "
		"JOIN warehouse.dim_location as l using (location_sk) where l.city = 'Manila'"
	).fetchall()
	assert regions == [("Metro Manila",)]


