-- The angle almost no public analysis of this dataset takes: instead of
-- training a classifier to predict is_canceled, this treats cancellation
-- as a revenue-management reporting problem - the kind of table a
-- revenue manager would actually ask for. Segmented by the four levers
-- that most directly reflect booking risk in practice: how far ahead the
-- guest booked, what deposit they put down, which channel/segment sold
-- the booking, and what kind of guest they are.

select
    hotel,
    lead_time_bucket,
    deposit_type,
    market_segment,
    customer_type,
    count(*)                                                   as bookings,
    sum(case when is_canceled then 1 else 0 end)               as cancellations,
    round(
        sum(case when is_canceled then 1 else 0 end)::numeric
        / nullif(count(*), 0), 4
    )                                                            as cancellation_rate,
    round(avg(lead_time), 1)                                    as avg_lead_time,
    round(
        avg(case when not is_adr_outlier then adr end), 2
    )                                                            as avg_adr
from {{ ref('fact_bookings') }}
group by 1, 2, 3, 4, 5
having count(*) >= 5   -- drop near-empty segment combinations that would report a noisy 0%/100% rate
order by cancellation_rate desc
