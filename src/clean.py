"""Clean the latest raw USGS download into an analysis-ready dataset.

Steps:
1. Keep only earthquakes in Indonesia (including Indonesian seas).
2. Keep the useful columns and give them clear names.
3. Convert time from UTC to WIB (UTC+7).
4. Classify depth (shallow / intermediate / deep).
5. Assign an approximate island region from coordinates.

Usage:
    python src/clean.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# USGS writes "..., Indonesia" for most events, but sea regions inside
# Indonesia have no country name, so we list them explicitly.
INDONESIAN_SEAS = {
    "Banda Sea", "Molucca Sea", "Ceram Sea", "Flores Sea", "Java Sea",
    "Savu Sea", "Halmahera Sea", "Bali Sea", "Seram Sea",
}


def latest_raw_file() -> Path:
    files = sorted(RAW_DIR.glob("earthquakes_*.csv"))
    if not files:
        raise FileNotFoundError("No raw data found. Run src/fetch.py first.")
    return files[-1]


def is_indonesia(place: str) -> bool:
    region = str(place).split(", ")[-1]
    return region == "Indonesia" or region in INDONESIAN_SEAS


def depth_class(depth_km: float) -> str:
    # Standard seismology classes
    if depth_km < 70:
        return "Shallow (<70 km)"
    if depth_km <= 300:
        return "Intermediate (70-300 km)"
    return "Deep (>300 km)"


def island_region(lat: float, lon: float) -> str:
    """Approximate island group from coordinates (simple boxes, checked in order)."""
    if lon >= 134.5 or (lon >= 131 and lat > -4.5):
        return "Papua"
    if lon < 105.8 and lat > -6.5:
        return "Sumatra"
    if lat < -7.8 and 114.4 <= lon < 127:
        return "Bali & Nusa Tenggara"
    if lon < 114.4 and lat < -5:
        return "Java"
    if 108 <= lon < 118.5 and lat >= -4.5:
        return "Kalimantan"
    if 118.5 <= lon < 125.5 and -6.5 <= lat <= 4:
        return "Sulawesi"
    return "Maluku"


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw["place"].apply(is_indonesia)].copy()

    df = df[["id", "time", "latitude", "longitude", "depth", "mag", "magType", "place"]]
    df = df.rename(columns={
        "time": "time_utc",
        "depth": "depth_km",
        "mag": "magnitude",
        "magType": "magnitude_type",
    })

    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    df["time_wib"] = df["time_utc"].dt.tz_convert("Asia/Jakarta")

    df["depth_class"] = df["depth_km"].apply(depth_class)
    df["region"] = [island_region(lat, lon) for lat, lon in zip(df["latitude"], df["longitude"])]

    df = df.drop_duplicates(subset="id").sort_values("time_utc").reset_index(drop=True)
    return df


def run() -> Path:
    """Clean the latest raw file. Returns the path of the clean file."""
    raw_path = latest_raw_file()
    raw = pd.read_csv(raw_path)
    df = clean(raw)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / raw_path.name.replace("earthquakes_", "earthquakes_clean_")
    df.to_csv(out_path, index=False)
    print(f"Kept {len(df)} of {len(raw)} earthquakes (inside Indonesia)")
    return out_path


if __name__ == "__main__":
    out_path = run()
    df = pd.read_csv(out_path)
    print(f"Saved : {out_path}\n")
    print("By region:")
    print(df["region"].value_counts().to_string(), "\n")
    print("By depth class:")
    print(df["depth_class"].value_counts().to_string(), "\n")
    print("Sample rows:")
    print(df[["time_wib", "magnitude", "depth_km", "region", "place"]].tail(5).to_string(index=False))
