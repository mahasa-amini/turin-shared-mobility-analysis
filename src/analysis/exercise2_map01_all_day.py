from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch


# ============================================================
# EXERCISE 2 — MAP 01
# SYSTEM-WIDE ALL-DAY INTER-ZONAL OD DEMAND CORE
# ============================================================


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GPKG = (
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
    / "exercise_2"
    / "maps"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PNG_OUT = (
    OUTPUT_DIR
    / "map01_all_day_od_demand_core.png"
)

PDF_OUT = (
    OUTPUT_DIR
    / "map01_all_day_od_demand_core.pdf"
)


# ============================================================
# CARTOGRAPHIC SETTINGS
# ============================================================

ZONE_FACE = "#f2f2f2"
ZONE_EDGE = "#9a9a9a"

FLOW_COLOR = "#2166ac"

MIN_FLOW_WIDTH = 0.45
MAX_FLOW_WIDTH = 3.20

TITLE = (
    "System-wide Inter-zonal E-scooter OD Flows — Turin, 2024"
)

SUBTITLE = (
    "Strongest flows covering 25% of observed inter-zonal demand"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_layers():

    print("\n" + "=" * 90)
    print("EXERCISE 2 — MAP 01: ALL-DAY OD DEMAND CORE")
    print("=" * 90)

    zones = gpd.read_file(
        GPKG,
        layer="zones",
    )

    flows = gpd.read_file(
        GPKG,
        layer="flows_all_day",
    )

    # --------------------------------------------------------
    # CRS validation
    # --------------------------------------------------------

    if zones.crs is None:
        raise ValueError(
            "Zones layer has no CRS."
        )

    if flows.crs is None:
        raise ValueError(
            "Flows layer has no CRS."
        )

    if zones.crs.to_epsg() != 3003:
        raise ValueError(
            f"Unexpected zones CRS: {zones.crs}"
        )

    if flows.crs.to_epsg() != 3003:
        raise ValueError(
            f"Unexpected flows CRS: {flows.crs}"
        )

    # --------------------------------------------------------
    # Demand-core filter
    # --------------------------------------------------------

    flows = flows.loc[
        flows["demand_core_25pct"].fillna(False)
    ].copy()

    if flows.empty:
        raise ValueError(
            "No flows found after demand_core_25pct filtering."
        )

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    required_columns = [
        "origin_zone_id",
        "destination_zone_id",
        "system_trips",
        "geometry",
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in flows.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if flows["system_trips"].isna().any():
        raise ValueError(
            "system_trips contains missing values."
        )

    if (flows["system_trips"] <= 0).any():
        raise ValueError(
            "All displayed system_trips must be positive."
        )

    # --------------------------------------------------------
    # Terminal summary
    # --------------------------------------------------------

    print(
        f"Official zones: {len(zones):,}"
    )

    print(
        f"Selected demand-core flows: {len(flows):,}"
    )

    print(
        "Trips represented by selected flows: "
        f"{flows['system_trips'].sum():,.0f}"
    )

    print(
        "Minimum displayed OD flow: "
        f"{flows['system_trips'].min():,.0f} trips"
    )

    print(
        "Maximum displayed OD flow: "
        f"{flows['system_trips'].max():,.0f} trips"
    )

    return zones, flows


# ============================================================
# LINE-WIDTH SCALING
#
# IMPORTANT:
# A square-root transformation is used because OD-flow
# magnitudes are right-skewed.
#
# global_min and global_max are passed explicitly so that
# legend line widths use EXACTLY the same scale as map lines.
# ============================================================

def scale_line_width(
    values,
    global_min,
    global_max,
    min_width=MIN_FLOW_WIDTH,
    max_width=MAX_FLOW_WIDTH,
):

    values = np.asarray(
        values,
        dtype=float,
    )

    transformed = np.sqrt(
        values
    )

    low = np.sqrt(
        float(global_min)
    )

    high = np.sqrt(
        float(global_max)
    )

    if high == low:

        return np.full(
            len(values),
            (
                min_width
                + max_width
            )
            / 2.0,
        )

    widths = (
        min_width
        +
        (
            transformed - low
        )
        /
        (
            high - low
        )
        *
        (
            max_width
            - min_width
        )
    )

    return widths


# ============================================================
# DRAW DIRECTIONAL OD FLOWS
#
# OD flows connect zone centroids.
#
# Opposite directions are slightly curved to opposite sides
# so A→B and B→A remain visually distinguishable.
#
# These lines are schematic OD connectors, NOT street routes.
# ============================================================

def draw_flows(
    ax,
    flows,
):

    global_min = (
        flows["system_trips"]
        .min()
    )

    global_max = (
        flows["system_trips"]
        .max()
    )

    widths = scale_line_width(
        flows["system_trips"].values,
        global_min=global_min,
        global_max=global_max,
    )

    for row, width in zip(
        flows.itertuples(),
        widths,
    ):

        geom = row.geometry

        if geom is None:
            continue

        if geom.is_empty:
            continue

        coords = list(
            geom.coords
        )

        if len(coords) < 2:
            continue

        start = coords[0]
        end = coords[-1]

        # ----------------------------------------------------
        # Opposite OD directions bend to opposite sides
        # ----------------------------------------------------

        if (
            str(row.origin_zone_id)
            <
            str(row.destination_zone_id)
        ):

            curvature = 0.055

        else:

            curvature = -0.055

        # ----------------------------------------------------
        # Visual hierarchy through opacity
        # ----------------------------------------------------

        strength = (
            float(row.system_trips)
            /
            float(global_max)
        )

        alpha = (
            0.28
            +
            0.62
            * np.sqrt(
                strength
            )
        )

        alpha = np.clip(
            alpha,
            0.28,
            0.90,
        )

        # ----------------------------------------------------
        # Directional flow
        # ----------------------------------------------------

        arrow = FancyArrowPatch(
            posA=start,
            posB=end,

            arrowstyle="-|>",

            mutation_scale=(
                7.0
                +
                width
                * 2.6
            ),

            linewidth=width,

            color=FLOW_COLOR,

            alpha=alpha,

            connectionstyle=(
                f"arc3,rad={curvature}"
            ),

            shrinkA=1.5,
            shrinkB=1.5,

            capstyle="round",
            joinstyle="round",

            zorder=4,
        )

        ax.add_patch(
            arrow
        )


# ============================================================
# SCALE BAR
#
# EPSG:3003 uses metres.
# ============================================================

def add_scale_bar(
    ax,
    zones,
    length_km=2,
):

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    map_width = (
        maxx - minx
    )

    map_height = (
        maxy - miny
    )

    x0 = (
        minx
        +
        map_width
        * 0.065
    )

    y0 = (
        miny
        +
        map_height
        * 0.055
    )

    length_m = (
        length_km
        * 1000
    )

    # Main bar
    ax.plot(
        [
            x0,
            x0 + length_m,
        ],
        [
            y0,
            y0,
        ],
        color="black",
        linewidth=2.0,
        zorder=20,
    )

    # Left tick
    ax.plot(
        [
            x0,
            x0,
        ],
        [
            y0 - 80,
            y0 + 80,
        ],
        color="black",
        linewidth=1.4,
        zorder=20,
    )

    # Right tick
    ax.plot(
        [
            x0 + length_m,
            x0 + length_m,
        ],
        [
            y0 - 80,
            y0 + 80,
        ],
        color="black",
        linewidth=1.4,
        zorder=20,
    )

    # Scale label
    ax.text(
        x0 + length_m / 2,
        y0 + map_height * 0.018,
        f"{length_km} km",
        ha="center",
        va="bottom",
        fontsize=9,
        color="black",
        zorder=20,
    )


# ============================================================
# NORTH ARROW
# ============================================================

def add_north_arrow(
    ax,
):

    ax.annotate(
        "N",

        xy=(
            0.935,
            0.945,
        ),

        xytext=(
            0.935,
            0.855,
        ),

        xycoords="axes fraction",
        textcoords="axes fraction",

        ha="center",
        va="center",

        fontsize=13,
        fontweight="bold",

        arrowprops=dict(
            facecolor="black",
            edgecolor="black",
            width=3.0,
            headwidth=10,
            headlength=10,
            shrink=0,
        ),

        zorder=30,
    )


# ============================================================
# FLOW LEGEND
#
# Uses 10th, 50th and 90th percentiles of displayed flows.
#
# IMPORTANT:
# The SAME global map scale is used for legend widths.
# ============================================================

def add_flow_legend(
    ax,
    flows,
):

    global_min = (
        flows["system_trips"]
        .min()
    )

    global_max = (
        flows["system_trips"]
        .max()
    )

    quantiles = (
        flows["system_trips"]
        .quantile(
            [
                0.10,
                0.50,
                0.90,
            ]
        )
        .round()
        .astype(int)
        .to_numpy()
    )

    widths = scale_line_width(
        quantiles,
        global_min=global_min,
        global_max=global_max,
    )

    handles = []
    labels = []

    for value, width in zip(
        quantiles,
        widths,
    ):

        handle = Line2D(
            [0],
            [0],

            color=FLOW_COLOR,

            linewidth=width,

            alpha=0.85,

            solid_capstyle="round",
        )

        handles.append(
            handle
        )

        labels.append(
            f"{value:,} trips"
        )

    legend = ax.legend(
        handles,
        labels,

        title="OD flow magnitude",

        loc="lower right",

        frameon=True,
        framealpha=0.96,

        fontsize=9,
        title_fontsize=9.5,

        borderpad=0.8,
        labelspacing=0.65,
        handlelength=2.2,
        handletextpad=0.9,
    )

    legend.get_frame().set_edgecolor(
        "#aaaaaa"
    )

    legend.get_frame().set_linewidth(
        0.8
    )


# ============================================================
# MAP EXTENT
# ============================================================

def set_map_extent(
    ax,
    zones,
):

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    map_width = (
        maxx - minx
    )

    map_height = (
        maxy - miny
    )

    x_pad = (
        map_width
        * 0.025
    )

    y_pad = (
        map_height
        * 0.025
    )

    ax.set_xlim(
        minx - x_pad,
        maxx + x_pad,
    )

    ax.set_ylim(
        miny - y_pad,
        maxy + y_pad,
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )


# ============================================================
# MAIN
# ============================================================

def main():

    zones, flows = (
        load_layers()
    )

    # --------------------------------------------------------
    # A4 landscape
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            11.69,
            8.27,
        ),
        facecolor="white",
    )

    ax.set_facecolor(
        "white"
    )

    # --------------------------------------------------------
    # Official statistical zoning
    # --------------------------------------------------------

    zones.plot(
        ax=ax,

        facecolor=ZONE_FACE,

        edgecolor=ZONE_EDGE,

        linewidth=0.45,

        zorder=1,
    )

    # --------------------------------------------------------
    # Directional OD flows
    # --------------------------------------------------------

    draw_flows(
        ax,
        flows,
    )

    # --------------------------------------------------------
    # Map extent
    # --------------------------------------------------------

    set_map_extent(
        ax,
        zones,
    )

    # --------------------------------------------------------
    # Cartographic elements
    # --------------------------------------------------------

    add_scale_bar(
        ax,
        zones,
        length_km=2,
    )

    add_north_arrow(
        ax
    )

    add_flow_legend(
        ax,
        flows,
    )

    # --------------------------------------------------------
    # Main title
    # --------------------------------------------------------

    fig.suptitle(
        TITLE,

        fontsize=16,

        fontweight="semibold",

        y=0.955,
    )

    # --------------------------------------------------------
    # Subtitle
    # --------------------------------------------------------

    ax.set_title(
        SUBTITLE,

        fontsize=11,

        fontweight="normal",

        pad=8,
    )

    # --------------------------------------------------------
    # Methodological notes
    # --------------------------------------------------------

    fig.text(
        0.5,
        0.035,

        (
            "Official Torino statistical zoning (94 zones). "
            "Lines connect zone centroids and represent directional OD flows; "
            "they are not travelled routes. "
            "Intra-zonal trips are excluded from the flow map."
        ),

        ha="center",
        va="center",

        fontsize=8.3,
    )

    fig.text(
        0.5,
        0.017,

        (
            "Displayed corridors form the smallest ranked set covering "
            "at least 25% of system-wide inter-zonal trips."
        ),

        ha="center",
        va="center",

        fontsize=8.3,
    )

    # --------------------------------------------------------
    # Remove axes / coordinates
    # --------------------------------------------------------

    ax.set_axis_off()

    # --------------------------------------------------------
    # Page composition
    # --------------------------------------------------------

    plt.tight_layout(
        rect=[
            0.015,
            0.055,
            0.985,
            0.945,
        ]
    )

    # --------------------------------------------------------
    # Export PNG
    # --------------------------------------------------------

    fig.savefig(
        PNG_OUT,

        dpi=350,

        bbox_inches="tight",

        facecolor="white",
    )

    # --------------------------------------------------------
    # Export vector PDF
    # --------------------------------------------------------

    fig.savefig(
        PDF_OUT,

        bbox_inches="tight",

        facecolor="white",
    )

    plt.close(
        fig
    )

    print("\n" + "-" * 90)

    print(
        f"PNG saved -> {PNG_OUT}"
    )

    print(
        f"PDF saved -> {PDF_OUT}"
    )

    print("-" * 90)

    print(
        "\nMAP 01 COMPLETED."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()