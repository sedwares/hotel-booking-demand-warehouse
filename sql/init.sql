-- Raw landing schema for the Antonio, Almeida & Nunes (2019) Hotel Booking
-- Demand dataset. Schema mirrors the published CSV columns as closely as
-- possible; all cleaning/typing/derivation happens downstream in dbt
-- staging models, not here.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS raw.bookings (
    booking_row_id                  SERIAL PRIMARY KEY,  -- surrogate; dataset ships with no natural PK
    hotel                           TEXT,
    is_canceled                     INTEGER,
    lead_time                       INTEGER,
    arrival_date_year               INTEGER,
    arrival_date_month              TEXT,
    arrival_date_week_number        INTEGER,
    arrival_date_day_of_month       INTEGER,
    stays_in_weekend_nights         INTEGER,
    stays_in_week_nights            INTEGER,
    adults                          INTEGER,
    children                        NUMERIC,
    babies                          INTEGER,
    meal                            TEXT,
    country                         TEXT,
    market_segment                  TEXT,
    distribution_channel            TEXT,
    is_repeated_guest               INTEGER,
    previous_cancellations          INTEGER,
    previous_bookings_not_canceled  INTEGER,
    reserved_room_type              TEXT,
    assigned_room_type              TEXT,
    booking_changes                 INTEGER,
    deposit_type                    TEXT,
    agent                           TEXT,
    company                         TEXT,
    days_in_waiting_list            INTEGER,
    customer_type                   TEXT,
    adr                             NUMERIC,
    required_car_parking_spaces     INTEGER,
    total_of_special_requests       INTEGER,
    reservation_status              TEXT,
    reservation_status_date         DATE
);
