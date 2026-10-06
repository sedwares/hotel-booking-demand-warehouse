"""
Full-refresh load: raw CSV -> raw.bookings.

Unlike a live PMS feed, this dataset is a static historical extract (one
fixed file, published once in 2019 covering 2015-2017 arrivals). There's
no "new data landing daily" to incrementally append, so the honest
orchestration pattern here is idempotent full-refresh, not incremental
append - this is intentionally different from Project 1's daily-batch DAG,
and the README explains why.

Usage:
    python scripts/load_raw_data.py
"""
import pathlib
import sys

import pandas as pd
from sqlalchemy import text

sys.path.append(".")
from scripts.db import get_engine

CSV_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw" / "hotel_bookings.csv"

# raw.bookings columns, in load order (booking_row_id is a SERIAL, so it's
# omitted and auto-assigned on insert).
COLUMNS = [
    "hotel", "is_canceled", "lead_time", "arrival_date_year", "arrival_date_month",
    "arrival_date_week_number", "arrival_date_day_of_month", "stays_in_weekend_nights",
    "stays_in_week_nights", "adults", "children", "babies", "meal", "country",
    "market_segment", "distribution_channel", "is_repeated_guest", "previous_cancellations",
    "previous_bookings_not_canceled", "reserved_room_type", "assigned_room_type",
    "booking_changes", "deposit_type", "agent", "company", "days_in_waiting_list",
    "customer_type", "adr", "required_car_parking_spaces", "total_of_special_requests",
    "reservation_status", "reservation_status_date",
]


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"{CSV_PATH} not found. Run `python scripts/download_data.py` first, "
            "or confirm the checked-in copy under data/raw/ is present."
        )

    print(f"Reading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    df = df[COLUMNS]

    engine = get_engine()

    print("Truncating raw.bookings (full-refresh load) ...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE raw.bookings RESTART IDENTITY"))

    print(f"Loading {len(df):,} rows into raw.bookings ...")
    df.to_sql(
        "bookings",
        engine,
        schema="raw",
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )
    print("Done. Raw load complete.")


if __name__ == "__main__":
    main()
