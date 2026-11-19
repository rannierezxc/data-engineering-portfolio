---------------------------------
-- 03_scd2_dim_location.sql : slowly changing dimension type2 merge
--
-- expects a temporary table 'stg_location' holding the current truth
-- (one row per city). run both statements in one transaction
-- so now() returns the same timestamp in both: old.valid_to = new.valid_from
---------------------------------


-- step1: close the current row of every city whose attributes changed
update warehouse.dim_location as d
set valid_to = now(), is_current = false
from stg_location as s
where d.city = s.city
	and d.is_current
	and (d.country, d.region, d.latitude, d.longitude, d.timezone)
	is distinct from 
	(s.country, s.region, s.latitude, s.longitude, s.timezone);


-- step2: insert a new current row for
-- (a) brand-new cities, and
-- (b) cities whose row was just closed in step 1.
-- a city's very first version is valid "since forever" (1900-01-01),
-- so historical backfills can still find a matching dimension row.

insert into warehouse.dim_location (city, country, region, latitude, longitude, timezone, valid_from)
select s.city, s.country, s.region, s.latitude, s.longitude, s.timezone,
	case when exists (select 1 from warehouse.dim_location as h where h.city = s.city)
	then now()
	else timestamptz '1900-01-01 00:00:00+00'
	end
from stg_location as s
where not exists ( select 1 from warehouse.dim_location as d where d.city = s.city and d.is_current);
