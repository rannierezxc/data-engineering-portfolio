-----------------------------------
-- 02_dim_date.sql: fill the calendar dimension for 2020-2030
-- ON CONFLICT DO NOTHING makes it safe to re-run
-----------------------------------


INSERT INTO warehouse.dim_date (
	date_key, full_date, year, quarter, month, month_name,
	day_of_month, day_of_week, day_name, is_weekend
)

SELECT
	TO_CHAR(d, 'YYYYMMDD')::INTEGER as date_key,
	d::date as full_date,
	extract(year from d) as year,
	extract(quarter from d) as quarter,
	extract(month from d) as month,
	to_char(d, 'FMMonth') as month_name,
	extract(day from d) as day_of_month,
	extract(isodow from d) as day_of_week,
	to_char(d, 'FMDay') as day_name,
	extract(isodow from d) in (6,7) as is_weekend

FROM
	generate_series(date '2020-01-01', date '2030-12-31', interval '1 day') as g(d)
ON CONFLICT (date_key) DO NOTHING;
