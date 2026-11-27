"""Analyze the latest clean dataset and save portfolio-ready charts.

Outputs (in outputs/figures/):
    1_map.png                 where earthquakes happened, colored by depth
    2_by_region.png           number of earthquakes per island region
    3_magnitude_vs_depth.png  magnitude against depth
    4_daily.png               earthquakes per day
plus outputs/summary.txt with the key numbers.

Usage:
    python src/analyze.py
"""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
COUNTRIES_FILE = ROOT / "data" / "external" / "ne_50m_admin_0_countries.zip"
FIG_DIR = ROOT / "outputs" / "figures"

# --- Style ---------------------------------------------------------------
# Colors from a validated, colorblind-checked palette.
TEXT = "#191919"
TEXT_2 = "#666666"
GRID = "#e6e6e6"
LAND = "#efefef"
SERIES = "#257de0"  # single-series blue

# Depth is an ordered category, so it uses one hue from light to dark
# (shallow = lightest, deep = darkest) instead of unrelated colors.
DEPTH_ORDER = ["Shallow (<70 km)", "Intermediate (70-300 km)", "Deep (>300 km)"]
DEPTH_COLORS = {
    "Shallow (<70 km)": "#84b9f3",
    "Intermediate (70-300 km)": "#257de0",
    "Deep (>300 km)": "#0f4a96",
}

plt.rcParams.update({
    "font.family": "Segoe UI",
    "font.size": 10,
    "text.color": TEXT,
    "axes.labelcolor": TEXT_2,
    "axes.edgecolor": GRID,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "xtick.color": TEXT_2,
    "ytick.color": TEXT_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


def latest_clean_file() -> Path:
    files = sorted(PROCESSED_DIR.glob("earthquakes_clean_*.csv"))
    if not files:
        raise FileNotFoundError("No clean data found. Run src/clean.py first.")
    return files[-1]


def add_source(fig, period: str) -> None:
    fig.text(0.01, 0.01, f"Source: USGS Earthquake Catalog, M4.0+, {period}",
             fontsize=8, color=TEXT_2)


COUNTRIES_URL = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"


def load_countries() -> gpd.GeoDataFrame:
    """Load country borders (Natural Earth, public domain); download once if missing."""
    if not COUNTRIES_FILE.exists():
        COUNTRIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(COUNTRIES_URL, timeout=120)
        response.raise_for_status()
        COUNTRIES_FILE.write_bytes(response.content)
    return gpd.read_file(COUNTRIES_FILE)


def plot_map(df: pd.DataFrame, period: str) -> Path:
    countries = load_countries()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    countries.plot(ax=ax, color=LAND, edgecolor="#cfcfcf", linewidth=0.5)

    for depth in DEPTH_ORDER:
        part = df[df["depth_class"] == depth]
        ax.scatter(
            part["longitude"], part["latitude"],
            s=(part["magnitude"] - 3) ** 2.5 * 12,   # bigger magnitude, bigger dot
            color=DEPTH_COLORS[depth], edgecolor="white", linewidth=1,
            alpha=0.9, label=f"{depth} ({len(part)})", zorder=3,
        )

    # Label the largest event directly
    top = df.loc[df["magnitude"].idxmax()]
    ax.annotate(f"M{top['magnitude']:.1f}\n{top['place']}",
                (top["longitude"], top["latitude"]), xytext=(30, -45),
                textcoords="offset points", fontsize=8, color=TEXT,
                arrowprops=dict(arrowstyle="-", color=TEXT_2, linewidth=0.8))

    ax.set_xlim(94, 142)
    ax.set_ylim(-12, 7)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(color=GRID, linewidth=0.5)
    ax.set_title(f"Earthquakes in Indonesia, {period} ({len(df)} events, M4.0+)")
    ax.legend(title="Depth (dot size = magnitude)", loc="lower left",
              frameon=True, facecolor="white", edgecolor=GRID, fontsize=8, title_fontsize=8)
    add_source(fig, period)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return save(fig, "1_map.png")


def plot_by_region(df: pd.DataFrame, period: str) -> Path:
    counts = df["region"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.barh(counts.index, counts.values, color=SERIES, height=0.6)
    ax.bar_label(bars, padding=4, color=TEXT, fontsize=9)
    ax.set_xlabel("Number of earthquakes")
    ax.grid(axis="x", color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    leader = counts.index[-1]
    share = counts.iloc[-1] / counts.sum()
    ax.set_title(f"{leader} had {share:.0%} of all earthquakes")
    add_source(fig, period)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return save(fig, "2_by_region.png")


def plot_magnitude_vs_depth(df: pd.DataFrame, period: str) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for depth in DEPTH_ORDER:
        part = df[df["depth_class"] == depth]
        ax.scatter(part["depth_km"], part["magnitude"], s=40,
                   color=DEPTH_COLORS[depth], edgecolor="white", linewidth=1,
                   label=depth, zorder=3)
    for boundary in (70, 300):
        ax.axvline(boundary, color=TEXT_2, linewidth=0.8, linestyle="--", zorder=1)
    ax.set_xlabel("Depth (km)")
    ax.set_ylabel("Magnitude")
    ax.grid(color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    shallow_share = (df["depth_km"] < 70).mean()
    ax.set_title(f"{shallow_share:.0%} of earthquakes were shallow (<70 km)")
    ax.legend(title="Depth class", frameon=False, fontsize=8, title_fontsize=8)
    add_source(fig, period)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return save(fig, "3_magnitude_vs_depth.png")


def plot_daily(df: pd.DataFrame, period: str) -> Path:
    days = pd.to_datetime(df["time_wib"].str[:10])
    full_range = pd.date_range(days.min(), days.max(), freq="D")
    daily = days.value_counts().reindex(full_range, fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(daily.index, daily.values, color=SERIES, width=0.7)
    ax.set_ylabel("Earthquakes per day")
    ax.grid(axis="y", color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    busiest = daily.idxmax()
    ax.set_title(f"Daily activity: busiest day was {busiest:%d %b} with {daily.max()} earthquakes")
    fig.autofmt_xdate()
    add_source(fig, period)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return save(fig, "4_daily.png")


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def write_summary(df: pd.DataFrame, period: str) -> Path:
    top = df.loc[df["magnitude"].idxmax()]
    lines = [
        f"Earthquake summary, Indonesia, {period}",
        f"Total events (M4.0+): {len(df)}",
        f"Largest: M{top['magnitude']:.1f}, {top['place']}, {top['time_wib'][:16]} WIB",
        f"Average magnitude: {df['magnitude'].mean():.2f}",
        f"Median depth: {df['depth_km'].median():.1f} km",
        "",
        "By region:",
        df["region"].value_counts().to_string(),
        "",
        "By depth class:",
        df["depth_class"].value_counts().reindex(DEPTH_ORDER).to_string(),
    ]
    path = ROOT / "outputs" / "summary.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run() -> list[Path]:
    """Build all charts and the summary from the latest clean file."""
    df = pd.read_csv(latest_clean_file())
    start, end = df["time_wib"].min()[:10], df["time_wib"].max()[:10]
    period = f"{start} to {end}"
    paths = [plot_map(df, period), plot_by_region(df, period),
             plot_magnitude_vs_depth(df, period), plot_daily(df, period),
             write_summary(df, period)]
    print(f"Saved {len(paths)} outputs to {ROOT / 'outputs'}")
    return paths


if __name__ == "__main__":
    run()
    print()
    print((ROOT / "outputs" / "summary.txt").read_text(encoding="utf-8"))
