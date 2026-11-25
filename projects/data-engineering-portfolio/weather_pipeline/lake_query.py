"""query the parquet data lake with duckdb, straight from s3/minio, with no database server.

uv run python -m weather_pipeline.lake_query
"""

import duckdb

from weather_pipeline.lake import CURATED_PREFIX
from weather_pipeline.settings import Settings, get_settings

DAILY_SUMMARY_SQL = """
select
	reading_date,
	city,
	count(*) as readings,
	round(avg(temperature_c),1) as avg_temp_c,
	max(temperature_c) as max_temp_c,
	round(sum(precipitation_mm), 1) as total_rain_mm
from read_parquet($lake_glob, hive_partitioning = true)
group by reading_date, city
order by reading_date, city
"""

WETTEST_DAYS_SQL = """
select city, reading_date, round(sum(precipitation_mm), 1) as total_rain_mm
from read_parquet($lake_glob, hive_partitioning = true)
group by city, reading_date
qualify row_number() over (partition by city order by sum(precipitation_mm) desc) = 1
order by total_rain_mm desc
"""


def sql_literal(value: str) -> str:
    """quote a value for sql text. CREATE SECRET can't take ? parameters"""
    return "'" + value.replace("'", "''") + "'"


def connect(settings: Settings) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()  # in-memory: duckdb runs inside this python process
    con.execute("INSTALL httpfs; LOAD httpfs;")  # the extension that speaks s3/http
    con.execute(
        f"""
		CREATE OR REPLACE SECRET lake (
			TYPE s3,
			KEY_ID {sql_literal(settings.s3_access_key)},
			SECRET {sql_literal(settings.s3_secret_key.get_secret_value())},
			ENDPOINT {sql_literal(settings.s3_endpoint)},
			URL_STYLE 'path',
			USE_SSL {"true" if settings.s3_use_ssl else "false"}
		)
		"""
    )
    return con


def lake_glob(bucket: str) -> str:
    return f"s3://{bucket}/{CURATED_PREFIX}/**/*.parquet"


def run_query(con: duckdb.DuckDBPyConnection, sql: str, glob: str) -> list[tuple[object, ...]]:
    return con.execute(sql, {"lake_glob": glob}).fetchall()


def main() -> int:
    settings = get_settings()
    con = connect(settings)
    glob = lake_glob(settings.s3_bucket)
    for title, sql in [("Daily summary", DAILY_SUMMARY_SQL), ("Wettest day", WETTEST_DAYS_SQL)]:
        print(f"\n=== {title} ===")
        for row in run_query(con, sql, glob):
            print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
