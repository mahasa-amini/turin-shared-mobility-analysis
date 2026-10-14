# -*- coding: utf-8 -*-
"""
EXERCISE 2
Figure E2.6 — Origin Production-Density Choropleth

System-wide all-day e-scooter trip production, Turin, 2024.

Mapping variable:
    production_density_trips_per_km2

The map uses official Torino statistical zones (94 zones).
Density is used instead of raw origin counts because statistical zones
have unequal areas.

Input:
    data/processed/exercise_2/gis/exercise2_od_layers.gpkg
    layer: zones_all_day

Outputs:
    outputs/figures/exercise_2/figure_e2_6_origin_production_density.png
    outputs/figures/exercise_2/figure_e2_6_origin_production_density.pdf
"""

from pathlib import Path
import math

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.patheffects as pe


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(
    "/Users/mahasaamini/Documents/transport_exercise"
)

GPKG_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "gis"
    / "exercise2_od_layers.gpkg"
)

LAYER_NAME = "zones_all_day"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_2"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PNG = (
    OUTPUT_DIR
    / "figure_e2_6_origin_production_density.png"
)

OUTPUT_PDF = (
    OUTPUT_DIR
    / "figure_e2_6_origin_production_density.pdf"
)


# =============================================================================
# CANONICAL FIELDS
# =============================================================================

ZONE_ID_COL = "zone_id"
ZONE_NAME_COL = "zone_name"

PRODUCTION_COL = "production_trips"
DENSITY_COL = "production_density_trips_per_km2"
AREA_COL = "area_km2"


# =============================================================================
# MAP STYLE
# =============================================================================

FIGSIZE = (11.5, 10.5)
DPI = 300

# Sequential orange palette:
# intentionally different from the blue OD-flow maps
CLASS_COLORS = [
    "#fff5eb",
    "#fdd0a2",
    "#fdae6b",
    "#f16913",
    "#a63603",
]

MISSING_COLOR = "#f2f2f2"

ZONE_EDGE_COLOR = "#9a9a9a"
ZONE_EDGE_WIDTH = 0.55

TITLE_SIZE = 20
SUBTITLE_SIZE = 12
LEGEND_SIZE = 10.5
FOOTNOTE_SIZE = 9.3

TOP_N_TABLE = 6
TOP_N_MAP_LABELS = 3

SCALEBAR_KM = 2

TITLE = (
    "Origin Production Density of E-scooter Trips — Turin, 2024"
)

SUBTITLE = (
    "System-wide all-day activity | "
    "Official Torino statistical zoning (94 zones)"
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_number(value):
    """
    Formatting used in legend labels and text boxes.
    """
    if pd.isna(value):
        return "NA"

    if abs(value) >= 100000:
        return f"{value / 1000:,.0f}k"

    if abs(value) >= 10000:
        return f"{value / 1000:,.1f}k"

    if abs(value) >= 1000:
        return f"{value:,.0f}"

    if abs(value) >= 100:
        return f"{value:.0f}"

    return f"{value:.1f}"


def make_quantile_bins(series, number_classes=5):
    """
    Create quantile class breaks.

    Duplicate breaks are removed automatically.
    Falls back to equal-width classification if required.
    """
    clean = (
        pd.to_numeric(series, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )

    if clean.empty:
        raise ValueError(
            "No valid production-density values are available."
        )

    probabilities = np.linspace(
        0,
        1,
        number_classes + 1
    )

    bins = np.quantile(
        clean.to_numpy(),
        probabilities
    )

    bins = np.unique(bins)

    # If many tied values collapse quantile breaks,
    # use equal-width classification as fallback.
    if len(bins) < 3:
        minimum = float(clean.min())
        maximum = float(clean.max())

        if math.isclose(minimum, maximum):
            raise ValueError(
                "All zones have the same production density."
            )

        bins = np.linspace(
            minimum,
            maximum,
            number_classes + 1
        )

    return bins


def classify_values(values, bins):
    """
    Convert continuous density values into class IDs.
    """
    values = np.asarray(values, dtype=float)

    return np.digitize(
        values,
        bins[1:-1],
        right=True
    )


def add_north_arrow(
    ax,
    x=0.925,
    y=0.88,
    arrow_length=0.075
):
    """
    Add one simple north arrow.
    """
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - arrow_length),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        arrowprops=dict(
            facecolor="black",
            edgecolor="black",
            width=2.8,
            headwidth=11,
            headlength=11,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=30,
    )


def add_scale_bar(
    ax,
    length_km=2,
    x_fraction=0.075,
    y_fraction=0.075
):
    """
    Add a metric scale bar.

    EPSG:3003 uses metre units.
    """
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    map_width = xmax - xmin
    map_height = ymax - ymin

    x0 = xmin + x_fraction * map_width
    y0 = ymin + y_fraction * map_height

    length_m = length_km * 1000
    x1 = x0 + length_m

    tick_height = map_height * 0.006

    ax.plot(
        [x0, x1],
        [y0, y0],
        color="black",
        linewidth=2.0,
        solid_capstyle="butt",
        zorder=30,
    )

    ax.plot(
        [x0, x0],
        [y0 - tick_height, y0 + tick_height],
        color="black",
        linewidth=1.5,
        zorder=30,
    )

    ax.plot(
        [x1, x1],
        [y0 - tick_height, y0 + tick_height],
        color="black",
        linewidth=1.5,
        zorder=30,
    )

    ax.text(
        (x0 + x1) / 2,
        y0 + map_height * 0.015,
        f"{length_km} km",
        ha="center",
        va="bottom",
        fontsize=10,
        zorder=30,
    )


# =============================================================================
# LOAD DATA
# =============================================================================

print("=" * 100)
print("FIGURE E2.6 — ORIGIN PRODUCTION-DENSITY CHOROPLETH")
print("=" * 100)

if not GPKG_PATH.exists():
    raise FileNotFoundError(
        f"GeoPackage not found:\n{GPKG_PATH}"
    )

zones = gpd.read_file(
    GPKG_PATH,
    layer=LAYER_NAME
)

print(f"Loaded layer: {LAYER_NAME}")
print(f"Rows: {len(zones)}")
print(f"CRS: {zones.crs}")
print(f"Columns: {list(zones.columns)}")


# =============================================================================
# BASIC VALIDATION
# =============================================================================

if len(zones) != 94:
    raise ValueError(
        f"Expected 94 official Torino statistical zones, "
        f"but found {len(zones)}."
    )

if zones.crs is None:
    raise ValueError(
        "The zones_all_day layer has no CRS."
    )

if zones.crs.to_epsg() != 3003:
    print(
        f"Reprojecting from {zones.crs} to EPSG:3003..."
    )

    zones = zones.to_crs(
        epsg=3003
    )


required_columns = [
    ZONE_ID_COL,
    ZONE_NAME_COL,
    PRODUCTION_COL,
    DENSITY_COL,
    AREA_COL,
]

missing_columns = [
    column
    for column in required_columns
    if column not in zones.columns
]

if missing_columns:
    raise KeyError(
        "Missing required columns in zones_all_day: "
        f"{missing_columns}"
    )


print()
print("Canonical mapping fields:")
print(f"  Zone ID     -> {ZONE_ID_COL}")
print(f"  Zone name   -> {ZONE_NAME_COL}")
print(f"  Production  -> {PRODUCTION_COL}")
print(f"  Area        -> {AREA_COL}")
print(f"  Density     -> {DENSITY_COL}")


# =============================================================================
# PREPARE VARIABLES
# =============================================================================

zones = zones.copy()

zones[ZONE_ID_COL] = (
    zones[ZONE_ID_COL]
    .astype(str)
)

zones[ZONE_NAME_COL] = (
    zones[ZONE_NAME_COL]
    .astype(str)
)

zones["production_trips_plot"] = pd.to_numeric(
    zones[PRODUCTION_COL],
    errors="coerce"
)

zones["area_km2_plot"] = pd.to_numeric(
    zones[AREA_COL],
    errors="coerce"
)

zones["origin_density_km2"] = pd.to_numeric(
    zones[DENSITY_COL],
    errors="coerce"
)


# =============================================================================
# SCIENTIFIC VALIDATION OF DENSITY FIELD
# =============================================================================

if (zones["area_km2_plot"] <= 0).any():
    bad_area_zones = zones.loc[
        zones["area_km2_plot"] <= 0,
        ZONE_ID_COL
    ].tolist()

    raise ValueError(
        f"Non-positive zone areas detected: {bad_area_zones}"
    )


zones["density_recomputed"] = (
    zones["production_trips_plot"]
    / zones["area_km2_plot"]
)

zones["density_absolute_difference"] = (
    zones["origin_density_km2"]
    - zones["density_recomputed"]
).abs()

max_density_difference = float(
    zones["density_absolute_difference"].max()
)

print()
print(
    "Maximum stored-vs-recomputed density difference: "
    f"{max_density_difference:.6f} trips/km²"
)

# Stored values may have been rounded slightly,
# therefore use a small numerical tolerance.
if max_density_difference > 1.0:
    raise ValueError(
        "Stored production density does not reconcile with "
        "production_trips / area_km2."
    )

print("Production-density validation: PASSED")


# =============================================================================
# MISSING / ZERO ACTIVITY CHECK
# =============================================================================

missing_density_count = int(
    zones["origin_density_km2"].isna().sum()
)

zero_density_count = int(
    (zones["origin_density_km2"] == 0).sum()
)

print()
print(f"Missing density zones: {missing_density_count}")
print(f"Zero-density zones: {zero_density_count}")


# =============================================================================
# CLASSIFICATION
# =============================================================================

bins = make_quantile_bins(
    zones["origin_density_km2"],
    number_classes=5
)

number_classes = len(bins) - 1

if number_classes > len(CLASS_COLORS):
    raise ValueError(
        "More classes were generated than available colors."
    )

palette = CLASS_COLORS[:number_classes]

zones["density_class"] = pd.Series(
    pd.NA,
    index=zones.index,
    dtype="Int64"
)

valid_mask = (
    zones["origin_density_km2"]
    .notna()
)

zones.loc[
    valid_mask,
    "density_class"
] = classify_values(
    zones.loc[
        valid_mask,
        "origin_density_km2"
    ].to_numpy(),
    bins
)


print()
print("Classification breaks [trips/km²]:")

for i in range(number_classes):
    print(
        f"  Class {i + 1}: "
        f"{bins[i]:,.1f} – {bins[i + 1]:,.1f}"
    )


# =============================================================================
# LEGEND HANDLES
# =============================================================================

legend_handles = []

for class_id in range(number_classes):

    lower = bins[class_id]
    upper = bins[class_id + 1]

    if class_id == 0:
        label = (
            f"{format_number(lower)} – "
            f"{format_number(upper)}"
        )
    else:
        label = (
            f"> {format_number(lower)} – "
            f"{format_number(upper)}"
        )

    handle = Patch(
        facecolor=palette[class_id],
        edgecolor=ZONE_EDGE_COLOR,
        linewidth=0.5,
        label=label
    )

    legend_handles.append(handle)


if missing_density_count > 0:
    legend_handles.append(
        Patch(
            facecolor=MISSING_COLOR,
            edgecolor=ZONE_EDGE_COLOR,
            linewidth=0.5,
            label="No valid density"
        )
    )


# =============================================================================
# TOP PRODUCTION-DENSITY ZONES
# =============================================================================

top_zones = (
    zones[
        [
            ZONE_ID_COL,
            ZONE_NAME_COL,
            "production_trips_plot",
            "origin_density_km2",
        ]
    ]
    .sort_values(
        "origin_density_km2",
        ascending=False
    )
    .head(TOP_N_TABLE)
    .copy()
)

print()
print("Top origin-production-density zones:")
print(
    top_zones.to_string(
        index=False
    )
)


# =============================================================================
# REPRESENTATIVE POINTS FOR MAP LABELS
# =============================================================================

zones["label_point"] = (
    zones.geometry
    .representative_point()
)


# =============================================================================
# BUILD TOP-ZONE TEXT BOX
# =============================================================================

top_text_lines = [
    "Highest origin-density zones"
]

for rank, (_, row) in enumerate(
    top_zones.iterrows(),
    start=1
):

    top_text_lines.append(
        f"{rank}. "
        f"{row[ZONE_ID_COL]} "
        f"{row[ZONE_NAME_COL]}  |  "
        f"{row['origin_density_km2']:,.0f} trips/km²"
    )

top_text = "\n".join(
    top_text_lines
)


# =============================================================================
# DRAW FIGURE
# =============================================================================

fig, ax = plt.subplots(
    figsize=FIGSIZE
)


# -----------------------------------------------------------------------------
# Missing/no-data background
# -----------------------------------------------------------------------------

zones.plot(
    ax=ax,
    color=MISSING_COLOR,
    edgecolor=ZONE_EDGE_COLOR,
    linewidth=ZONE_EDGE_WIDTH,
    zorder=1,
)


# -----------------------------------------------------------------------------
# Choropleth classes
# -----------------------------------------------------------------------------

for class_id in range(number_classes):

    class_subset = zones[
        zones["density_class"] == class_id
    ]

    if class_subset.empty:
        continue

    class_subset.plot(
        ax=ax,
        color=palette[class_id],
        edgecolor=ZONE_EDGE_COLOR,
        linewidth=ZONE_EDGE_WIDTH,
        zorder=2,
    )


# -----------------------------------------------------------------------------
# Municipal / zone boundaries
# -----------------------------------------------------------------------------

zones.boundary.plot(
    ax=ax,
    color="#8c8c8c",
    linewidth=0.50,
    zorder=3,
)


# =============================================================================
# MAP EXTENT
# =============================================================================

minx, miny, maxx, maxy = (
    zones.total_bounds
)

map_width = maxx - minx
map_height = maxy - miny

x_padding = map_width * 0.04
y_padding = map_height * 0.04

ax.set_xlim(
    minx - x_padding,
    maxx + x_padding
)

ax.set_ylim(
    miny - y_padding,
    maxy + y_padding
)

ax.set_aspect(
    "equal"
)

ax.set_axis_off()


# =============================================================================
# LABEL TOP 3 DENSITY ZONES
# =============================================================================

top_label_zone_ids = (
    top_zones
    .head(TOP_N_MAP_LABELS)[ZONE_ID_COL]
    .astype(str)
    .tolist()
)

for zone_id in top_label_zone_ids:

    row = zones.loc[
        zones[ZONE_ID_COL] == zone_id
    ].iloc[0]

    point = row["label_point"]

    ax.text(
        point.x,
        point.y,
        zone_id,
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="center",
        color="black",
        zorder=20,
        path_effects=[
            pe.withStroke(
                linewidth=3.2,
                foreground="white"
            )
        ],
    )


# =============================================================================
# MAP DECORATIONS
# =============================================================================

add_north_arrow(
    ax,
    x=0.925,
    y=0.885,
    arrow_length=0.075
)

add_scale_bar(
    ax,
    length_km=SCALEBAR_KM,
    x_fraction=0.075,
    y_fraction=0.075
)


# =============================================================================
# LEGEND
# =============================================================================

legend = ax.legend(
    handles=legend_handles,
    title=(
        "Origin production density\n"
        "(trips per km²)"
    ),
    loc="lower right",
    bbox_to_anchor=(0.985, 0.13),
    frameon=True,
    framealpha=0.96,
    facecolor="white",
    edgecolor="#aaaaaa",
    fontsize=LEGEND_SIZE,
    title_fontsize=LEGEND_SIZE + 0.7,
)

legend.get_frame().set_linewidth(
    0.8
)


# =============================================================================
# TOP-ZONE INFORMATION BOX
# =============================================================================

ax.text(
    0.035,
    0.025,
    top_text,
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=9.3,
    linespacing=1.35,
    bbox=dict(
        boxstyle="round,pad=0.45",
        facecolor="white",
        edgecolor="#aaaaaa",
        linewidth=0.8,
        alpha=0.96,
    ),
    zorder=30,
)


# =============================================================================
# TITLES
# =============================================================================

fig.suptitle(
    TITLE,
    fontsize=TITLE_SIZE,
    fontweight="bold",
    y=0.976,
)

fig.text(
    0.5,
    0.942,
    SUBTITLE,
    ha="center",
    va="center",
    fontsize=SUBTITLE_SIZE,
)


# =============================================================================
# FOOTNOTE / SCIENTIFIC CAPTION
# =============================================================================

fig.text(
    0.5,
    0.038,
    (
        "Fill color represents all-day origin-trip production density "
        "(trip origins per km²) rather than raw production counts, "
        "thereby controlling for unequal statistical-zone areas."
    ),
    ha="center",
    va="center",
    fontsize=FOOTNOTE_SIZE,
)

fig.text(
    0.5,
    0.019,
    (
        "Official Torino statistical zoning (94 zones), EPSG:3003. "
        "Production includes valid 2024 system-wide zoned OD trips."
    ),
    ha="center",
    va="center",
    fontsize=FOOTNOTE_SIZE,
)


# =============================================================================
# LAYOUT
# =============================================================================

plt.subplots_adjust(
    left=0.035,
    right=0.975,
    top=0.905,
    bottom=0.075,
)


# =============================================================================
# SAVE
# =============================================================================

fig.savefig(
    OUTPUT_PNG,
    dpi=DPI,
    bbox_inches="tight",
    facecolor="white",
)

fig.savefig(
    OUTPUT_PDF,
    dpi=DPI,
    bbox_inches="tight",
    facecolor="white",
)

plt.close(fig)


# =============================================================================
# FINAL TERMINAL OUTPUT
# =============================================================================

print()
print("=" * 100)
print("FIGURE E2.6 COMPLETED")
print("=" * 100)

print(f"PNG saved -> {OUTPUT_PNG}")
print(f"PDF saved -> {OUTPUT_PDF}")

print()
print("Scientific mapping variable:")
print("  production_density_trips_per_km2")
print()
print("Definition:")
print("  production_trips / area_km2")
print()
print("Classification:")
print("  5-class quantile choropleth")
print()
print("DONE.")