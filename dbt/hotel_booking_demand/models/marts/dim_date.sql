-- Hand-written in place of dbt_utils.date_spine: this project intentionally
-- has zero external dbt package dependencies (dbt_utils requires reaching
-- hub.getdbt.com, which isn't reachable in every environment - this is
-- what happened while building it). generate_series does the same job for
-- a single day-grain spine.
with spine as (
    select generate_series(
        cast('2015-07-01' as date),
        cast('2017-09-30' as date),
        interval '1 day'
    )::date as date_day
)

select
    date_day::date                          as date_day,
    extract(year from date_day)::int        as year,
    extract(month from date_day)::int       as month,
    to_char(date_day, 'Month')              as month_name,
    extract(day from date_day)::int         as day_of_month,
    to_char(date_day, 'Day')                as day_name,
    extract(dow from date_day)::int         as day_of_week,
    (extract(dow from date_day) in (0, 6))  as is_weekend,
    extract(quarter from date_day)::int     as quarter
from spine
