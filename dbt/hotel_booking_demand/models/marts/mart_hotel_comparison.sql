-- Side-by-side Resort vs. City hotel performance summary - different
-- demand curves, channel mixes, and cancellation behavior, one row per
-- hotel so they're trivially comparable in the dashboard.

with booking_stats as (
    select
        hotel,
        count(*)                                                       as total_bookings,
        sum(case when is_canceled then 1 else 0 end)                   as total_cancellations,
        round(
            sum(case when is_canceled then 1 else 0 end)::numeric
            / nullif(count(*), 0), 4
        )                                                                as cancellation_rate,
        round(avg(lead_time), 1)                                        as avg_lead_time,
        round(avg(case when not is_adr_outlier then adr end), 2)        as avg_adr,
        round(avg(total_nights), 2)                                     as avg_length_of_stay,
        mode() within group (order by market_segment)                   as top_market_segment,
        mode() within group (order by distribution_channel)             as top_distribution_channel
    from {{ ref('fact_bookings') }}
    group by 1
),

occupancy_stats as (
    select
        hotel,
        round(avg(occupancy_rate), 4)  as avg_occupancy_rate,
        round(avg(revpar), 2)          as avg_revpar
    from {{ ref('mart_daily_metrics') }}
    group by 1
)

select
    b.hotel,
    b.total_bookings,
    b.total_cancellations,
    b.cancellation_rate,
    b.avg_lead_time,
    b.avg_adr,
    b.avg_length_of_stay,
    b.top_market_segment,
    b.top_distribution_channel,
    o.avg_occupancy_rate,
    o.avg_revpar
from booking_stats b
left join occupancy_stats o on b.hotel = o.hotel
