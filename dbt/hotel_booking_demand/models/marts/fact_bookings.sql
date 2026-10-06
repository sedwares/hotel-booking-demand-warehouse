select
    booking_row_id,
    hotel,
    is_canceled,
    is_stay_honored,
    reservation_status,
    reservation_status_date,
    lead_time,
    case
        when lead_time = 0                    then '0 (same day)'
        when lead_time between 1 and 7        then '1-7 days'
        when lead_time between 8 and 30       then '8-30 days'
        when lead_time between 31 and 90      then '31-90 days'
        when lead_time between 91 and 180     then '91-180 days'
        else '180+ days'
    end                                       as lead_time_bucket,
    arrival_date,
    departure_date,
    total_nights,
    stays_in_weekend_nights,
    stays_in_week_nights,
    adults,
    children,
    babies,
    meal,
    country,
    market_segment,
    distribution_channel,
    is_repeated_guest,
    previous_cancellations,
    previous_bookings_not_canceled,
    reserved_room_type,
    assigned_room_type,
    is_room_type_mismatch,
    booking_changes,
    deposit_type,
    agent,
    company,
    days_in_waiting_list,
    customer_type,
    adr,
    is_adr_outlier,
    case when is_adr_outlier then null else adr * total_nights end as booking_value,
    required_car_parking_spaces,
    total_of_special_requests
from {{ ref('stg_bookings') }}
