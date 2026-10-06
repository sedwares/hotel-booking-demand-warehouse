select
    hotel,
    date_day,
    assumed_capacity,
    rooms_occupied,
    round(room_revenue, 2)                                             as room_revenue,
    round(rooms_occupied::numeric / nullif(assumed_capacity, 0), 4)    as occupancy_rate,
    round(room_revenue / nullif(rooms_occupied, 0), 2)                 as adr,
    round(room_revenue / nullif(assumed_capacity, 0), 2)               as revpar
from {{ ref('fact_room_nights') }}
order by hotel, date_day
