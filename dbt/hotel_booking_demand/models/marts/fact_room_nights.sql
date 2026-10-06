-- Grain: one row per hotel, per calendar night, across the date range the
-- data actually covers for that hotel (bounded by observed stay_date
-- min/max, not the full dim_date spine - there's no reservation data
-- before the first observed stay or after the last one).
--
-- This mirrors project 1's fact_room_nights (every night present whether
-- or not it sold), but at hotel grain rather than room grain, because the
-- inferred capacity (int_hotel_capacity) is a hotel-level estimate, not a
-- per-room-type one - decomposing it by room type isn't defensible from
-- this data (see int_hotel_capacity's documented limitation).

with date_bounds as (
    select
        hotel,
        min(stay_date) as min_stay_date,
        max(stay_date) as max_stay_date
    from {{ ref('int_booking_nights') }}
    group by 1
),

calendar as (
    select
        b.hotel,
        d.date_day
    from date_bounds b
    inner join {{ ref('dim_date') }} d
        on d.date_day between b.min_stay_date and b.max_stay_date
),

hotel_grid as (
    select
        c.hotel,
        c.date_day,
        h.assumed_capacity
    from calendar c
    inner join {{ ref('dim_hotel') }} h on c.hotel = h.hotel
),

nightly_actuals as (
    select
        hotel,
        stay_date,
        count(distinct booking_row_id)             as rooms_occupied,
        sum(coalesce(revenue_for_night, 0))         as room_revenue
    from {{ ref('int_booking_nights') }}
    group by 1, 2
)

select
    g.hotel,
    g.date_day,
    g.assumed_capacity,
    coalesce(a.rooms_occupied, 0)  as rooms_occupied,
    coalesce(a.room_revenue, 0)    as room_revenue
from hotel_grid g
left join nightly_actuals a
    on g.hotel = a.hotel
    and g.date_day = a.stay_date
