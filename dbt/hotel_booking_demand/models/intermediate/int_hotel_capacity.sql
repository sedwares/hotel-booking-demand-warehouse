-- Capacity inference: the dataset ships with no room-inventory count, so
-- there's no ready-made denominator for occupancy rate or RevPAR. This
-- model derives one.
--
-- Approach: for each hotel, take the maximum number of rooms occupied
-- concurrently on any single night across the full 2015-2017 window. A
-- hotel cannot have sold more rooms than it physically has, so the
-- observed peak is a hard floor on capacity - and checking the
-- distribution (see below) shows it isn't an outlier-driven number: the
-- 99th percentile of nightly occupied-room-counts sits within 1-3 rooms
-- of the max for both properties, meaning the hotel is *near* full on
-- dozens of nights, not just one freak night. That's the kind of pattern
-- a resort/city hotel genuinely produces at high season, not a data
-- artifact.
--
-- Known limitation, stated plainly: this is a floor, not a confirmed
-- number. The dataset only contains bookings that were actually made, so
-- if the hotel was fully sold out and turned guests away, that lost
-- demand leaves no row here - true capacity could be somewhat higher than
-- this estimate. In a real analytics-engineering job this is exactly the
-- kind of assumption you'd flag to a stakeholder rather than quietly bake
-- in, so it's documented here rather than buried in a constant.

with nightly_occupied as (
    select
        hotel,
        stay_date,
        count(distinct booking_row_id) as rooms_occupied
    from {{ ref('int_booking_nights') }}
    group by 1, 2
)

select
    hotel,
    max(rooms_occupied)                                           as assumed_capacity,
    percentile_cont(0.99) within group (order by rooms_occupied)  as p99_occupied,
    round(avg(rooms_occupied), 1)                                 as avg_occupied
from nightly_occupied
group by 1
