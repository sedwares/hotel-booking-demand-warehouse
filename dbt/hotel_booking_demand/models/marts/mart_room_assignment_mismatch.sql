-- Operational signal unique to this dataset: reserved_room_type vs.
-- assigned_room_type. A mismatch usually means an upgrade, a downgrade,
-- or an operational reshuffle (overbooking recovery, maintenance issue,
-- group-block reallocation) - all things a revenue/ops manager tracks
-- because they affect both guest experience and realized ADR versus the
-- rate quoted at booking.

select
    hotel,
    reserved_room_type,
    assigned_room_type,
    (reserved_room_type = assigned_room_type) as is_match,
    count(*)                                                   as bookings,
    sum(case when is_canceled then 1 else 0 end)               as cancellations,
    round(avg(case when not is_adr_outlier then adr end), 2)   as avg_adr
from {{ ref('fact_bookings') }}
where is_stay_honored  -- mismatch is only operationally meaningful for stays that actually happened
group by 1, 2, 3, 4
order by hotel, bookings desc
