"""Fetch recent earthquakes in the Indonesia region from the USGS FDSN Event API.

Usage:
    python src/fetch.py              # last 30 days, magnitude >= 4.0
    python src/fetch.py 7 3.5        # last 7 days, magnitude >= 3.5
"""
import sys
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Bounding box that covers Indonesia
INDONESIA_BOX = {
    "minlatitude": -11,
    "maxlatitude": 6,
    "minlongitude": 95,
    "maxlongitude": 141,
}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch_earthquakes(days: int = 30, min_magnitude: float = 4.0) -> pd.DataFrame:
    """Download earthquakes from the last `days` days as a DataFrame."""
    end = date.today()
    start = end - timedelta(days=days)

    params = {
        "format": "csv",
        "starttime": start.isoformat(),
        "endtime": (end + timedelta(days=1)).isoformat(),  # include today
        "minmagnitude": min_magnitude,
        "orderby": "time",
        **INDONESIA_BOX,
    }

    response = requests.get(USGS_URL, params=params, timeout=60)
    response.raise_for_status()  # stop with a clear error if the request failed

    return pd.read_csv(StringIO(response.text))


def save_raw(df: pd.DataFrame) -> Path:
    """Save the untouched download, named by today's date."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"earthquakes_{date.today():%Y%m%d}.csv"
    df.to_csv(path, index=False)
    return path


def run(days: int = 30, min_mag: float = 4.0) -> Path:
    """Fetch and save. Returns the path of the saved raw file."""
    df = fetch_earthquakes(days, min_mag)
    path = save_raw(df)
    print(f"Downloaded {len(df)} earthquakes (last {days} days, M >= {min_mag})")
    return path


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    min_mag = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0

    path = run(days, min_mag)
    df = pd.read_csv(path)
    print(f"Saved to: {path}")
    print(f"Columns: {list(df.columns)}")
    if not df.empty:
        biggest = df.loc[df["mag"].idxmax()]
        print(f"Largest: M{biggest['mag']} - {biggest['place']} - {biggest['time']}")
        print(f"Average depth: {df['depth'].mean():.1f} km")
