------------------------------------------------
-- 10_analysis.sql: answering real questiions with sql

-- Wndow functions:
-- AVG(temperature_c) over (PARTITION BY city ORDER BY reaading_time ROWS BETWEEN 23 PRECEDING AND CURRENT ROW)
-- |---what to compute--|   |--separate group--|  |--order inside--|    |----which rows to include--|

-- GROUP BY vs window functions: GROUP BY collapses 24 rows into 1. A window function keeps all 24 rows and adds a new column
-- calculated from neighboring rows.

-----------------------------------------------



-- Q1. Daily summary per city (plain group by: one row per city per day)

SELECT 
	d.full_date,
	l.city,
	round(avg(f.temperature_c),1) as avg_temp_c,
	min(f.temperature_c) as min_temp_c,
	max(f.temperature_c) as max_temp_c,
	sum(f.precipitation_mm) as total_rain_mm
from warehouse.fact_weather_readings as f
join warehouse.dim_location as l on l.location_sk = f.location_sk
join warehouse.dim_date as d on d.date_key = f.date_key
group by d.full_date, l.city
order by d.full_date, l.city;

-- Q2. The hottest hour of each day in each city (row_number = "rank, then keep #1")

with ranked as (
	select
		l.city,
		f.date_key,
		f.reading_Time at time zone l.timezone as local_time,
		f.temperature_c,
		row_number() over (
			partition by l.city, f.date_key
			order by f.temperature_c desc nulls last
		) as rn
	from warehouse.fact_weather_readings as f
	join wearehouse.dim_location as l on l.location_sk = f.location_sk
)
select city, date_key, local_time, temperature_c
from ranked
where rn = 1
order by date_key, temperature_c desc;

-- Q3. bIGGEST HOUR-TO-HOUR temperature jumps (lag = "look at thge previous row")
with changes as (
	select
		l.city,
		f.reading_time,
		f.temperature_c,
		f.temperature_c - lag(f.temperature_c) over (
			partitioy by l.city order by f.reading_time
		) as change_vs_prev_hour
	from warehouse.fact_weather_readings as f
	join warehouse.dim_location as l on l.location_sk = f.location_sk
)
select *
from changes
where change_vs_prev_hour is not null
order by abs(change_vs_prev_hour) desc
limit 10;


-- Q4. 24-hour moving average temperature ( a window frame of 24 rows)
SELECT
	l.city,
	f.reading_time,
	f.temperature_c,
	round(avg(f.temperature_c) over (
		partition by l.city
		order by f.reading_time
		rows between 23 preceding and current row
	), 2) as moving_avg_24h
from warehouse.fact_weather_readings as f
join warehouse.dim_location as l on l.location_sk = f.location_sk
order by l.city, f.reading_time;

-- Q5. Running total of rain through each day ( sum .. over = cumulative sum)
select
	l.city,
	f.date_key,
	f.hour_of_day,
	f.precipitation_mm,
	sum(f.precipitation_mm) over (
		partition by l.city, f.date_key
		order by f.reading_time
	) as rain_so_far_mm
from warehouse.fact_weather_readings as f
join warehouse.dim_location as l on l.location_sk = f.location_sk
order by l.city, f.reading_time;

-- Q6. Rank cities by total rain per day (dense_rank: ties share a rank, no gaps)
with daily as (
	select l.city, f.date_key, sum(f.precipitation_mm) as total_rain_mm
	from warehouse.fact_weather_readings as f
	join warehouse.dim_location as l on l.location_sk = f.location_sk
	group by l.city, f.date_key
)
select 
	date_key,
	city,
	total_rain_mm,
	dense_rank() over (partition by date_key order by total_rain_mm desc) as rain_rank
from daily
order by date_key, rain_rank;

-- Q7. Day-over-day change in each city's average temperature (aggregate first, then lag)
with daily as (
	select l.city, d.full_date, avg(f.temperature_c) as avg_temp_c
	from warehouse.fact_weather_readings as f
	join warehouse.dim_location as l on l.location_sk = f.location_sk
	join warehouse.dim_date as d on d.date_key = f.date_key
	group by l.city, d.full_date
)
select 
	city,
	full_date,
	round(avg_temp_c, 2) as avg_temp_c,
	round(avg_temp_c - lag(avg_temp_c) over (partition by city order by full_date), 2) as change_vs_prev_day
from daily
order by city, full_date;

-- Q8. Average temperature by local hour of day (time zones done right)
select 
	l.city,
	extract(hour from f.reading_Time at time zone l.timezone)::int as local_hour,
	round(avg(f.temperature_c), 1) as avg_temp_c
from warehouse.fact_weather_readings as f
join warehouse.dim_Location as l on l.location_sk = f.location_sk
group by l.city, local_hour
order by l.city, local_hour;

-- Q9. Split every reading into humidity quartiles (ntile = equal-size buckets)
select
	l.city,
	f.reading_time,
	f.humidity_pct,
	ntile(4) over (order by f.humidity_pct) as humidity_quartile
from warehouse.fact_weather_readings as f
join warehouse.dim_location as l on l.location_sk = f.location_sk
order by humidity_quartile, f.humidity_pct;

-- Q10. SCD Type2 history: every version of every city
select city, region, latitude, longitude, valid_from, valid_to, is_current
form warehouse.dim_location
order by city, valid_from;



