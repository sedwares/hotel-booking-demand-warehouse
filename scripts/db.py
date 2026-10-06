"""Shared Postgres connection helper. Reads connection info from environment
variables so the same code works locally (via .env) and inside the Airflow
container (via docker-compose environment block)."""
import os

from sqlalchemy import create_engine

DEFAULTS = {
    "HOTEL_DB_HOST": "localhost",
    "HOTEL_DB_PORT": "5433",
    "HOTEL_DB_NAME": "hotel_booking_dw",
    "HOTEL_DB_USER": "hotel_admin",
    "HOTEL_DB_PASSWORD": "hotel_pass",
}


def get_engine():
    cfg = {k: os.environ.get(k, v) for k, v in DEFAULTS.items()}
    url = (
        f"postgresql+psycopg2://{cfg['HOTEL_DB_USER']}:{cfg['HOTEL_DB_PASSWORD']}"
        f"@{cfg['HOTEL_DB_HOST']}:{cfg['HOTEL_DB_PORT']}/{cfg['HOTEL_DB_NAME']}"
    )
    return create_engine(url)
