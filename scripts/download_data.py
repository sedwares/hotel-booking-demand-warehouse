"""
Fetches the Antonio, Almeida & Nunes (2019) Hotel Booking Demand dataset.

Source: Antonio, N., de Almeida, A., & Nunes, L. (2019). "Hotel booking
demand datasets." Data in Brief, 22, 41-49. Two real (anonymized) European
hotels - H1 a resort, H2 a city hotel - covering arrivals July 2015 through
August 2017. Published as open data specifically because real hotel PMS
extracts are scarce for research and education.

A copy is already checked into data/raw/hotel_bookings.csv for
reproducibility (it's a static, ~17MB historical extract - not something
that changes upstream), but this script lets you re-fetch it from a public
mirror if needed.

Usage:
    python scripts/download_data.py
"""
import pathlib
import urllib.request

# TidyTuesday mirror of the original Data in Brief supplementary file.
SOURCE_URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "master/data/2020/2020-02-11/hotels.csv"
)
DEST = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw" / "hotel_bookings.csv"


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading dataset from {SOURCE_URL} ...")
    urllib.request.urlretrieve(SOURCE_URL, DEST)
    size_mb = DEST.stat().st_size / 1_000_000
    print(f"Saved to {DEST} ({size_mb:.1f} MB).")


if __name__ == "__main__":
    main()
