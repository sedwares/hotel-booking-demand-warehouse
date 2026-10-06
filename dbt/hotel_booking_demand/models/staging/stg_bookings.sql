with source as (
    select * from {{ source('raw', 'bookings') }}
),

cleaned as (
    select
        booking_row_id,
        hotel,
        is_canceled::boolean                as is_canceled,
        lead_time,
        arrival_date_year,
        arrival_date_month,
        arrival_date_week_number,
        arrival_date_day_of_month,

        -- Postgres to_date is lenient about month-name capitalization/padding
        to_date(
            arrival_date_year || '-' || arrival_date_month || '-' || arrival_date_day_of_month,
            'YYYY-FMMonth-DD'
        )                                    as arrival_date,

        coalesce(stays_in_weekend_nights, 0) as stays_in_weekend_nights,
        coalesce(stays_in_week_nights, 0)    as stays_in_week_nights,
        coalesce(stays_in_weekend_nights, 0) + coalesce(stays_in_week_nights, 0) as total_nights,

        adults,
        coalesce(children, 0)::int          as children,
        coalesce(babies, 0)                 as babies,
        meal,
        country,
        market_segment,
        distribution_channel,
        is_repeated_guest::boolean          as is_repeated_guest,
        previous_cancellations,
        previous_bookings_not_canceled,
        reserved_room_type,
        assigned_room_type,
        (reserved_room_type <> assigned_room_type) as is_room_type_mismatch,
        booking_changes,
        deposit_type,
        agent,
        company,
        days_in_waiting_list,
        customer_type,
        adr,
        -- Known data-quality issue in this dataset: a single row has an
        -- ADR of 5400 (~50x the next-highest fare) and one row has a
        -- negative ADR. Both look like PMS data-entry errors rather than
        -- real rates, not something to silently average into revenue
        -- metrics. Flagged here; excluded from revenue sums downstream,
        -- kept in the row set for completeness/auditability.
        (adr < 0 or adr > 1000)             as is_adr_outlier,
        required_car_parking_spaces,
        total_of_special_requests,
        reservation_status,
        reservation_status_date,
        (reservation_status = 'Check-Out')  as is_stay_honored
    from source
),

with_departure as (
    select
        *,
        arrival_date + (total_nights || ' days')::interval as departure_date
    from cleaned
)

select * from with_departure
