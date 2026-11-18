-- 01_schema.sql: create the raw landing table and the star svhema. Safe to run many times as long as there is IF NOT EXISTS anywhere

CREATE SCHEMA IF NOT EXISTS raw; -- data exactly as it arrived
CREATE SCHEMA IF NOT EXISTS warehouse; -- modeled data for analysis


-----------------------------
-- RAW: one raw per city per hour, as produced by Python pipeline
-----------------------------

CREATE TABLE IF NOT EXISTS raw.weather_readings (
	city text not null,
	latitude double precision not null,
	longitude double precision not null,
	reading_time timestamptz not null,
	temperature_c numeric(5,2),
	humidity_pct numeric(5,2),
	precipitation_mm numeric(6,2),
	wind_speed_kmh numeric(6,2),
	loaded_at timestamptz not null default now(),
	primary key (city, reading_time)
);


-----------------------------
-- DIMENSION: calendar. One row per day. Key looks like 20261109
-----------------------------

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
	date_key integer primary key,
	full_date date not null unique,
	year smallint not null,
	quarter smallint not null,
	month smallint not null,
	month_name text not null,
	day_of_month smallint not null,
	day_of_week smallint not null,     --ISO: 1 = MONDAY ... 7 = SUNDAY
	day_name text not null,
	is_weekend boolean not null
);

---------------------------
-- DIMENSION: Location, tracked as slowly changing dimension type 2
-- Every change creates a new row; old rows are closed, never deleted
---------------------------


create table if not exists warehouse.dim_location (
	location_sk bigint generated always as identity primary key,   -- surrogate key
	city text not null,
	country text not null,
	region text not null,
	latitude double precision not null,
	longitude double precision not null,
	timezone text not null,
	valid_from timestamptz not null,
	valid_to timestamptz not null default '9999-12-31 00:00:00+00',
	is_current boolean not null default true

);


-- At most ONE current row per city
create unique index if not exists uq_dim_location_current
	on warehouse.dim_location (city) where is_current;


--------------------------
-- FACT: One row per location per hour (Grain)
--------------------------

create table if not exists warehouse.fact_weather_readings (
	location_sk bigint not null references warehouse.dim_location (location_sk),
	date_key integer not null references warehouse.dim_date (date_key),
	reading_time timestamptz not null,
	hour_of_day smallint not null, -- 0-23, UTC
	temperature_c numeric(5,2),
	humidity_pct numeric(5,2),
	precipitation_mm numeric(6,2),
	wind_speed_kmh numeric(6,2),
	primary key (location_sk, reading_time)
);

CREATE index if not exists ix_fact_weather_date_key
	on warehouse.fact_weather_readings(date_key);


