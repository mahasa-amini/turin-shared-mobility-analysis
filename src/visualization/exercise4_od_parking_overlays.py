from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch, FancyArrowPatch
from matplotlib.lines import Line2D


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PARKING_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "gis"
    / "exercise4_temporal_parking_layers.gpkg"
)

OD_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "gis"
    / "exercise2_od_layers.gpkg"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_4"
    / "od_parking_overlays"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# PERIOD CONFIG
# =============================================================================

PERIODS = {
    "am_peak": {
        "parking_layer": "parking_system_am_peak",
        "flow_layer": "flows_am_peak",
        "title": "AM Peak (07:00–09:59)",
    },

    "pm_peak": {
        "parking_layer": "parking_system_pm_peak",
        "flow_layer": "flows_pm_peak",
        "title": "PM Peak (16:00–19:59)",
    },

    "offpeak": {
        "parking_layer": "parking_system_offpeak",
        "flow_layer": "flows_offpeak",
        "title": "Off-peak",
    },
}


# Same parking classes used in Q1
PARKING_BINS = [
    0,
    6,
    12,
    18,
    24,
    30,
    48,
]

PARKING_LABELS = [
    "0–6 h",
    "6–12 h",
    "12–18 h",
    "18–24 h",
    "24–30 h",
    ">30 h",
]

LOW_SAMPLE_THRESHOLD = 30

# Parallel offset for opposite-direction OD flows.
FLOW_OFFSET_M = 28.0

# Common line-width range across all three temporal maps.
MIN_FLOW_WIDTH = 0.55
MAX_FLOW_WIDTH = 4.2


# =============================================================================
# LOAD / VALIDATE
# =============================================================================

def load_parking(layer_name):

    gdf = gpd.read_file(
        PARKING_GPKG,
        layer=layer_name,
    )

    if gdf.crs.to_epsg() != 3003:
        gdf = gdf.to_crs(
            epsg=3003
        )

    required = {
        "zone_id",
        "parking_events",
        "mean_parking_h",
        "has_parking_data",
    }

    missing = (
        required
        -
        set(gdf.columns)
    )

    if missing:
        raise ValueError(
            f"{layer_name} missing columns: "
            f"{sorted(missing)}"
        )

    return gdf


def load_flows(layer_name):

    gdf = gpd.read_file(
        OD_GPKG,
        layer=layer_name,
    )

    if gdf.crs.to_epsg() != 3003:
        gdf = gdf.to_crs(
            epsg=3003
        )

    required = {
        "origin_zone_id",
        "destination_zone_id",
        "system_trips",
        "flow_share_pct",
        "demand_core_25pct",
    }

    missing = (
        required
        -
        set(gdf.columns)
    )

    if missing:
        raise ValueError(
            f"{layer_name} missing columns: "
            f"{sorted(missing)}"
        )

    # Only inter-zonal flows.
    gdf = gdf.loc[
        gdf[
            "origin_zone_id"
        ].astype("string")
        !=
        gdf[
            "destination_zone_id"
        ].astype("string")
    ].copy()

    # Use the already-established Exercise 2 demand core.
    gdf = gdf.loc[
        gdf[
            "demand_core_25pct"
        ]
        .fillna(False)
        .astype(bool)
    ].copy()

    gdf[
        "flow_share_pct"
    ] = (
        gdf[
            "flow_share_pct"
        ]
        .astype(float)
    )

    return gdf


# =============================================================================
# COMMON FLOW SCALE
# =============================================================================

def determine_global_flow_max():

    maxima = []

    for config in PERIODS.values():

        flows = load_flows(
            config[
                "flow_layer"
            ]
        )

        if len(flows):

            maxima.append(
                flows[
                    "flow_share_pct"
                ].max()
            )

    if not maxima:
        raise RuntimeError(
            "No demand-core OD flows found."
        )

    global_max = max(maxima)

    print(
        f"Global maximum flow share "
        f"for common width scaling: "
        f"{global_max:.4f}%"
    )

    return global_max


def flow_width(
    share,
    global_max,
):

    if global_max <= 0:
        return MIN_FLOW_WIDTH

    ratio = (
        max(0.0, share)
        /
        global_max
    )

    return (
        MIN_FLOW_WIDTH
        +
        (
            MAX_FLOW_WIDTH
            -
            MIN_FLOW_WIDTH
        )
        *
        ratio
    )


# =============================================================================
# OFFSET DIRECTIONAL FLOW
# =============================================================================

def shifted_endpoints(
    geometry,
    origin_zone,
    destination_zone,
    offset_m=FLOW_OFFSET_M,
):
    """
    OD geometries from Exercise 2 are centroid-to-centroid lines.

    Opposite directions are shifted to opposite sides of the
    original line so both can remain visible.
    """

    if geometry is None:
        return None

    coords = list(
        geometry.coords
    )

    if len(coords) < 2:
        return None

    x1, y1 = coords[0]
    x2, y2 = coords[-1]

    dx = x2 - x1
    dy = y2 - y1

    length = np.hypot(
        dx,
        dy,
    )

    if length == 0:
        return None

    # Unit normal vector.
    nx = -dy / length
    ny = dx / length

    # Same unordered OD pair receives opposite signs
    # depending on direction.
    origin = str(
        origin_zone
    )

    destination = str(
        destination_zone
    )

    sign = (
        1.0
        if origin < destination
        else -1.0
    )

    shift_x = (
        sign
        *
        offset_m
        *
        nx
    )

    shift_y = (
        sign
        *
        offset_m
        *
        ny
    )

    return (
        (
            x1 + shift_x,
            y1 + shift_y,
        ),
        (
            x2 + shift_x,
            y2 + shift_y,
        ),
    )


# =============================================================================
# MAP ELEMENTS
# =============================================================================

def add_north_arrow(ax):

    ax.annotate(
        "N",
        xy=(0.94, 0.91),
        xytext=(0.94, 0.80),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="-|>",
            linewidth=1.4,
        ),
        zorder=50,
    )


def add_scale_bar(
    ax,
    length_m=2000,
):

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    x_start = (
        xmax
        -
        0.07
        *
        (xmax - xmin)
        -
        length_m
    )

    y = (
        ymin
        +
        0.055
        *
        (ymax - ymin)
    )

    ax.plot(
        [
            x_start,
            x_start + length_m,
        ],
        [
            y,
            y,
        ],
        linewidth=2.0,
        color="black",
        zorder=50,
    )

    for x in [
        x_start,
        x_start + length_m,
    ]:

        ax.plot(
            [
                x,
                x,
            ],
            [
                y - 80,
                y + 80,
            ],
            linewidth=1.2,
            color="black",
            zorder=50,
        )

    ax.text(
        x_start + length_m / 2,
        y + 150,
        "2 km",
        ha="center",
        va="bottom",
        fontsize=8,
        zorder=50,
    )


# =============================================================================
# FLOW DRAWING
# =============================================================================

def draw_flows(
    ax,
    flows,
    global_flow_max,
):

    for _, row in flows.iterrows():

        endpoints = shifted_endpoints(
            row.geometry,
            row[
                "origin_zone_id"
            ],
            row[
                "destination_zone_id"
            ],
        )

        if endpoints is None:
            continue

        start, end = endpoints

        width = flow_width(
            row[
                "flow_share_pct"
            ],
            global_flow_max,
        )

        arrow = FancyArrowPatch(
            posA=start,
            posB=end,
            arrowstyle="-|>",
            mutation_scale=(
                5.5
                +
                1.5
                *
                width
            ),
            linewidth=width,
            color="#1f4e79",
            alpha=0.72,
            shrinkA=0,
            shrinkB=0,
            zorder=10,
        )

        ax.add_patch(
            arrow
        )


# =============================================================================
# MAKE MAP
# =============================================================================

def make_overlay_map(
    period_key,
    config,
    global_flow_max,
):

    print(
        f"\nBuilding "
        f"{period_key} overlay..."
    )

    parking = load_parking(
        config[
            "parking_layer"
        ]
    )

    flows = load_flows(
        config[
            "flow_layer"
        ]
    )

    has_data = (
        parking[
            "has_parking_data"
        ]
        .fillna(False)
        .astype(bool)
    )

    no_data = parking.loc[
        ~has_data
    ].copy()

    data = parking.loc[
        has_data
    ].copy()

    low_sample = data.loc[
        data[
            "parking_events"
        ]
        <
        LOW_SAMPLE_THRESHOLD
    ].copy()

    # ---------------------------------------------------------
    # Plot
    # ---------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(9, 9),
        facecolor="white",
    )

    ax.set_facecolor(
        "white"
    )

    cmap = plt.get_cmap(
        "YlOrRd",
        len(
            PARKING_LABELS
        ),
    )

    norm = BoundaryNorm(
        PARKING_BINS,
        ncolors=cmap.N,
        clip=True,
    )

    # No parking observations.
    if not no_data.empty:

        no_data.plot(
            ax=ax,
            facecolor="#dddddd",
            edgecolor="#777777",
            linewidth=0.5,
            zorder=1,
        )

    # Parking choropleth.
    data[
        "_display_mean_h"
    ] = (
        data[
            "mean_parking_h"
        ]
        .clip(
            lower=0,
            upper=47.999,
        )
    )

    data.plot(
        column="_display_mean_h",
        ax=ax,
        cmap=cmap,
        norm=norm,
        edgecolor="#8a8a8a",
        linewidth=0.35,
        zorder=2,
    )

    # Municipal/zone boundaries.
    parking.boundary.plot(
        ax=ax,
        color="#555555",
        linewidth=0.35,
        zorder=3,
    )

    # Low sample.
    if not low_sample.empty:

        low_sample.plot(
            ax=ax,
            facecolor="none",
            edgecolor="black",
            linewidth=0.8,
            hatch="///",
            zorder=4,
        )

    # OD arrows.
    draw_flows(
        ax,
        flows,
        global_flow_max,
    )

    # ---------------------------------------------------------
    # Legend
    # ---------------------------------------------------------

    handles = []

    for i, label in enumerate(
        PARKING_LABELS
    ):

        handles.append(
            Patch(
                facecolor=cmap(i),
                edgecolor="#666666",
                label=label,
            )
        )

    handles.append(
        Line2D(
            [0],
            [0],
            color="#1f4e79",
            linewidth=2.4,
            marker=">",
            markersize=6,
            label=(
                "OD demand core "
                "(width ∝ flow share)"
            ),
        )
    )

    if not low_sample.empty:

        handles.append(
            Patch(
                facecolor="white",
                edgecolor="black",
                hatch="///",
                label=(
                    "Low parking sample "
                    "(<30 events)"
                ),
            )
        )

    if not no_data.empty:

        handles.append(
            Patch(
                facecolor="#dddddd",
                edgecolor="#777777",
                label=(
                    "No valid parking "
                    "observations"
                ),
            )
        )

    legend = ax.legend(
        handles=handles,
        title=(
            "Mean parking duration "
            "+ OD flows"
        ),
        loc="lower left",
        fontsize=7.6,
        title_fontsize=8.5,
        frameon=True,
        framealpha=0.94,
        facecolor="white",
    )

    legend.set_zorder(
        100
    )

    # ---------------------------------------------------------
    # Map furniture
    # ---------------------------------------------------------

    add_north_arrow(
        ax
    )

    add_scale_bar(
        ax,
        2000,
    )

    # ---------------------------------------------------------
    # Title
    # ---------------------------------------------------------

    ax.set_title(
        (
            f"{config['title']} — "
            f"E-scooter OD Demand and Mean Parking Duration\n"
            f"Turin, Feb–Dec 2024"
        ),
        fontsize=12.5,
        fontweight="bold",
        pad=14,
    )

    # ---------------------------------------------------------
    # Footnote
    # ---------------------------------------------------------

    ax.text(
        0.5,
        -0.035,
        (
            "Parking is classified by parking start time "
            "(end of preceding trip); "
            "OD flows use the corresponding Exercise 2 period. "
            "Only the 25% cumulative demand core of inter-zonal OD flows is shown."
        ),
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=7.2,
    )

    ax.set_axis_off()

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / (
            f"od_parking_overlay_"
            f"{period_key}_2024.png"
        )
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(
        fig
    )

    print(
        f"Parking zones with data: "
        f"{len(data):,}"
    )

    print(
        f"Low-sample zones: "
        f"{len(low_sample):,}"
    )

    print(
        f"OD demand-core flows plotted: "
        f"{len(flows):,}"
    )

    print(
        f"Saved -> "
        f"{output_path}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 4 — OD × PARKING TEMPORAL OVERLAYS"
    )

    print(
        "=" * 110
    )

    global_flow_max = (
        determine_global_flow_max()
    )

    for (
        period_key,
        config,
    ) in PERIODS.items():

        make_overlay_map(
            period_key,
            config,
            global_flow_max,
        )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "OVERLAY MAPS COMPLETED"
    )

    print(
        "=" * 110
    )

    print(
        f"Outputs -> "
        f"{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()