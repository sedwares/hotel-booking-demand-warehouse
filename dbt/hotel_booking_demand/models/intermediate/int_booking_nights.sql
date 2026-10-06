-- Grain: one row per hotel, per assigned room type, per night actually
-- stayed. Only honored stays (reservation_status = 'Check-Out') occupied a
-- room, so cancellations and no-shows are excluded here - same logic as
-- project 1's int_reservation_nights, applied to real PMS data this time.
--
-- Bookings with total_nights = 0 (715 rows - same-day/zero-night bookings)
-- are excluded from this model since there's no night to generate; they're
-- still present in stg_bookings / fact_bookings for booking-level analysis.

with honored_stays as (
    select *
    from {{ ref('stg_bookings') }}
    where is_stay_honored
      and total_nights > 0
),

nights as (
    select
        b.booking_row_id,
        b.hotel,
        b.assigned_room_type,
        b.market_segment,
        b.distribution_channel,
        b.adr,
        b.is_adr_outlier,
        gs.stay_date::date as stay_date
    from honored_stays b
    cross join lateral generate_series(
        b.arrival_date,
        b.departure_date - interval '1 day',
        interval '1 day'
    ) as gs(stay_date)
)

select
    booking_row_id,
    hotel,
    assigned_room_type,
    market_segment,
    distribution_channel,
    stay_date,
    case when is_adr_outlier then null else adr end as revenue_for_night
from nights
