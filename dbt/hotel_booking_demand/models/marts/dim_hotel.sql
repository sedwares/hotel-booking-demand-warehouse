select
    hotel,
    assumed_capacity,
    p99_occupied,
    avg_occupied
from {{ ref('int_hotel_capacity') }}
