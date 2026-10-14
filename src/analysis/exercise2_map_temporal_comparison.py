# -*- coding: utf-8 -*-

"""
exercise2_map_temporal_comparison.py

Exercise 2
Three-panel comparison of conventional temporal OD demand cores:

A. AM peak      07:00–09:59
B. PM peak      16:00–19:59
C. Off-peak     remaining 17 hours/day

IMPORTANT:
Only demand_core_25pct flows are displayed.

Expected counts:
AM peak   = 73 flows
PM peak   = 100 flows
Off-peak  = 110 flows

All panels use the same flow-share linewidth scale.
"""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(
    "/Users/mahasaamini/Documents/transport_exercise"
)

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
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PNG_OUT = (
    OUTPUT_DIR
    / "figure_E2_temporal_comparison_3panel.png"
)

PDF_OUT = (
    OUTPUT_DIR
    / "figure_E2_temporal_comparison_3panel.pdf"
)


# =============================================================================
# CARTOGRAPHIC SETTINGS
# =============================================================================

FIGSIZE = (18, 8.8)
DPI = 350

ZONE_FACE = "#f2f2f2"
ZONE_EDGE = "#a6a6a6"

FLOW_COLOR = "#2b74b9"

MIN_LINE_WIDTH = 0.35
MAX_LINE_WIDTH = 2.45

MAIN_TITLE = (
    "Temporal Comparison of Inter-zonal E-scooter OD Flows — Turin, 2024"
)

SUBTITLE = (
    "Common detailed-time window: 1 February–31 December 2024"
)


# =============================================================================
# DATA LOADING
# =============================================================================

def load_zones():

    zones = gpd.read_file(
        GPKG,
        layer="zones",
    )

    if zones.crs is None:
        raise ValueError(
            "Zones layer has no CRS."
        )

    if zones.crs.to_epsg() != 3003:
        zones = zones.to_crs(
            epsg=3003
        )

    return zones


def load_demand_core(
    layer_name,
    expected_count,
):

    flows = gpd.read_file(
        GPKG,
        layer=layer_name,
    )

    if flows.crs is None:
        raise ValueError(
            f"{layer_name}: CRS missing."
        )

    if flows.crs.to_epsg() != 3003:
        flows = flows.to_crs(
            epsg=3003
        )

    # -------------------------------------------------------------------------
    # Required fields
    # -------------------------------------------------------------------------

    required_columns = [
        "demand_core_25pct",
        "flow_share_pct",
        "origin_zone_id",
        "destination_zone_id",
        "geometry",
    ]

    missing = [
        col
        for col in required_columns
        if col not in flows.columns
    ]

    if missing:
        raise KeyError(
            f"{layer_name}: missing required columns: {missing}\n"
            f"Available columns:\n{flows.columns.tolist()}"
        )

    # -------------------------------------------------------------------------
    # STRICT 25% DEMAND-CORE FILTER
    # -------------------------------------------------------------------------

    flag = flows[
        "demand_core_25pct"
    ]

    if flag.dtype == bool:

        mask = flag.fillna(
            False
        )

    else:

        mask = (
            flag
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                    "yes",
                    "t",
                ]
            )
        )

    core = flows.loc[
        mask
    ].copy()

    # -------------------------------------------------------------------------
    # Critical validation
    # -------------------------------------------------------------------------

    if len(core) != expected_count:

        raise ValueError(
            "\n"
            f"{layer_name}: WRONG demand-core flow count.\n"
            f"Expected: {expected_count}\n"
            f"Found:    {len(core)}\n"
            "\n"
            "STOPPING because the map would not represent the 25% demand core."
        )

    core[
        "flow_share_pct"
    ] = core[
        "flow_share_pct"
    ].astype(float)

    if core[
        "flow_share_pct"
    ].isna().any():

        raise ValueError(
            f"{layer_name}: missing flow_share_pct values."
        )

    return core


# =============================================================================
# LINE-WIDTH SCALE
# =============================================================================

def scale_line_width(
    value,
    global_min,
    global_max,
):

    """
    Square-root scaling improves visibility while preserving
    a single common scale across AM, PM and off-peak.
    """

    value = float(value)

    if global_max <= global_min:

        return (
            MIN_LINE_WIDTH
            +
            MAX_LINE_WIDTH
        ) / 2

    transformed_value = np.sqrt(
        value
    )

    transformed_min = np.sqrt(
        global_min
    )

    transformed_max = np.sqrt(
        global_max
    )

    normalized = (
        transformed_value
        -
        transformed_min
    ) / (
        transformed_max
        -
        transformed_min
    )

    normalized = np.clip(
        normalized,
        0,
        1,
    )

    return (
        MIN_LINE_WIDTH
        +
        normalized
        *
        (
            MAX_LINE_WIDTH
            -
            MIN_LINE_WIDTH
        )
    )


# =============================================================================
# DRAW BASE MAP
# =============================================================================

def draw_zones(
    ax,
    zones,
):

    zones.plot(
        ax=ax,
        facecolor=ZONE_FACE,
        edgecolor=ZONE_EDGE,
        linewidth=0.38,
        zorder=1,
    )


# =============================================================================
# DRAW DIRECTIONAL OD FLOWS
# =============================================================================

def draw_flows(
    ax,
    flows,
    global_min,
    global_max,
):

    for row in flows.itertuples():

        geom = row.geometry

        if geom is None:
            continue

        if geom.is_empty:
            continue

        if geom.geom_type == "LineString":

            coords = list(
                geom.coords
            )

        elif geom.geom_type == "MultiLineString":

            longest = max(
                geom.geoms,
                key=lambda g: g.length,
            )

            coords = list(
                longest.coords
            )

        else:
            continue

        if len(coords) < 2:
            continue

        start = coords[0]
        end = coords[-1]

        share = float(
            row.flow_share_pct
        )

        width = scale_line_width(
            share,
            global_min,
            global_max,
        )

        # ---------------------------------------------------------------------
        # Slight curvature separates opposite directional flows
        # ---------------------------------------------------------------------

        origin = str(
            row.origin_zone_id
        )

        destination = str(
            row.destination_zone_id
        )

        if origin < destination:
            curvature = 0.055
        else:
            curvature = -0.055

        # ---------------------------------------------------------------------
        # Stronger flows slightly more opaque
        # ---------------------------------------------------------------------

        strength = (
            share
            -
            global_min
        ) / (
            global_max
            -
            global_min
        )

        strength = np.clip(
            strength,
            0,
            1,
        )

        alpha = (
            0.28
            +
            0.62
            *
            np.sqrt(
                strength
            )
        )

        arrow = FancyArrowPatch(
            posA=start,
            posB=end,

            arrowstyle="-|>",

            mutation_scale=(
                5.5
                +
                width
                *
                2.2
            ),

            linewidth=width,

            color=FLOW_COLOR,

            alpha=alpha,

            connectionstyle=(
                f"arc3,rad={curvature}"
            ),

            shrinkA=2,
            shrinkB=2,

            zorder=4,
        )

        ax.add_patch(
            arrow
        )


# =============================================================================
# COMMON EXTENT
# =============================================================================

def apply_common_extent(
    ax,
    zones,
):

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    width = maxx - minx
    height = maxy - miny

    x_pad = width * 0.025
    y_pad = height * 0.025

    ax.set_xlim(
        minx - x_pad,
        maxx + x_pad,
    )

    ax.set_ylim(
        miny - y_pad,
        maxy + y_pad,
    )

    ax.set_aspect(
        "equal"
    )

    ax.set_axis_off()


# =============================================================================
# SCALE BAR
# =============================================================================

def add_scale_bar(
    ax,
    zones,
    length_km=2,
):

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    width = maxx - minx
    height = maxy - miny

    length_m = (
        length_km
        *
        1000
    )

    x0 = (
        minx
        +
        width
        *
        0.055
    )

    y0 = (
        miny
        +
        height
        *
        0.045
    )

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
        linewidth=1.6,
        zorder=20,
    )

    # left tick
    ax.plot(
        [
            x0,
            x0,
        ],
        [
            y0 - 70,
            y0 + 70,
        ],
        color="black",
        linewidth=1.2,
        zorder=20,
    )

    # right tick
    ax.plot(
        [
            x0 + length_m,
            x0 + length_m,
        ],
        [
            y0 - 70,
            y0 + 70,
        ],
        color="black",
        linewidth=1.2,
        zorder=20,
    )

    ax.text(
        x0 + length_m / 2,
        y0 + height * 0.015,

        f"{length_km} km",

        ha="center",
        va="bottom",

        fontsize=9,

        zorder=20,
    )


# =============================================================================
# NORTH ARROW
# =============================================================================

def add_north_arrow(
    ax,
):

    ax.annotate(
        "N",

        xy=(
            0.90,
            0.90,
        ),

        xytext=(
            0.90,
            0.81,
        ),

        xycoords="axes fraction",
        textcoords="axes fraction",

        ha="center",
        va="center",

        fontsize=12,
        fontweight="bold",

        arrowprops=dict(
            facecolor="black",
            edgecolor="black",

            width=2,
            headwidth=7,
            headlength=8,
        ),

        zorder=30,
    )


# =============================================================================
# DRAW PANEL
# =============================================================================

def draw_panel(
    ax,
    zones,
    flows,
    title,
    global_min,
    global_max,
):

    draw_zones(
        ax,
        zones,
    )

    draw_flows(
        ax,
        flows,
        global_min,
        global_max,
    )

    apply_common_extent(
        ax,
        zones,
    )

    ax.set_title(
        title,

        fontsize=12.5,

        fontweight="semibold",

        pad=8,
    )


# =============================================================================
# SHARED LEGEND
# =============================================================================

def add_shared_legend(
    fig,
    global_min,
    global_max,
):

    middle = (
        global_min
        +
        global_max
    ) / 2

    legend_values = [
        global_min,
        middle,
        global_max,
    ]

    handles = []

    for value in legend_values:

        width = scale_line_width(
            value,
            global_min,
            global_max,
        )

        handle = Line2D(
            [0],
            [0],

            color=FLOW_COLOR,

            linewidth=width,

            alpha=0.82,

            label=f"{value:.2f}%",
        )

        handles.append(
            handle
        )

    legend = fig.legend(
        handles=handles,

        title=(
            "Share of period inter-zonal demand"
        ),

        loc="lower center",

        bbox_to_anchor=(
            0.5,
            0.083,
        ),

        ncol=3,

        frameon=True,

        fancybox=False,

        edgecolor="#aaaaaa",

        fontsize=9.5,

        title_fontsize=10,

        handlelength=3.1,

        columnspacing=1.7,
    )

    legend.get_frame().set_facecolor(
        "white"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 100
    )

    print(
        "EXERCISE 2 — TEMPORAL OD DEMAND-CORE COMPARISON"
    )

    print(
        "=" * 100
    )

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    zones = load_zones()

    am = load_demand_core(
        layer_name="flows_am_peak",
        expected_count=73,
    )

    pm = load_demand_core(
        layer_name="flows_pm_peak",
        expected_count=100,
    )

    offpeak = load_demand_core(
        layer_name="flows_offpeak",
        expected_count=110,
    )

    # -------------------------------------------------------------------------
    # Validate counts
    # -------------------------------------------------------------------------

    assert len(am) == 73
    assert len(pm) == 100
    assert len(offpeak) == 110

    print()
    print(
        f"AM demand-core flows       : {len(am):,}"
    )

    print(
        f"PM demand-core flows       : {len(pm):,}"
    )

    print(
        f"Off-peak demand-core flows : {len(offpeak):,}"
    )

    # -------------------------------------------------------------------------
    # One common share scale across all three panels
    # -------------------------------------------------------------------------

    all_shares = np.concatenate(
        [
            am[
                "flow_share_pct"
            ].to_numpy(
                dtype=float
            ),

            pm[
                "flow_share_pct"
            ].to_numpy(
                dtype=float
            ),

            offpeak[
                "flow_share_pct"
            ].to_numpy(
                dtype=float
            ),
        ]
    )

    global_min = float(
        np.min(
            all_shares
        )
    )

    global_max = float(
        np.max(
            all_shares
        )
    )

    print()
    print(
        "Common flow-share scale:"
    )

    print(
        f"Minimum: {global_min:.4f}%"
    )

    print(
        f"Maximum: {global_max:.4f}%"
    )

    # -------------------------------------------------------------------------
    # Safety check
    #
    # Previous incorrect version produced values around 0.00–0.05%.
    # The actual demand-core map should be substantially larger.
    # -------------------------------------------------------------------------

    if global_max < 0.10:

        raise ValueError(
            "\nUnexpectedly small flow-share scale.\n"
            "This indicates that the full OD network may have been loaded "
            "instead of the 25% demand core.\n"
            "STOPPING."
        )

    # -------------------------------------------------------------------------
    # Create figure
    # -------------------------------------------------------------------------

    fig, axes = plt.subplots(
        1,
        3,

        figsize=FIGSIZE,
    )

    fig.patch.set_facecolor(
        "white"
    )

    # -------------------------------------------------------------------------
    # Panel A
    # -------------------------------------------------------------------------

    draw_panel(
        ax=axes[0],

        zones=zones,

        flows=am,

        title=(
            "A. AM peak\n"
            "07:00–09:59"
        ),

        global_min=global_min,

        global_max=global_max,
    )

    add_scale_bar(
        axes[0],
        zones,
        length_km=2,
    )

    # -------------------------------------------------------------------------
    # Panel B
    # -------------------------------------------------------------------------

    draw_panel(
        ax=axes[1],

        zones=zones,

        flows=pm,

        title=(
            "B. PM peak\n"
            "16:00–19:59"
        ),

        global_min=global_min,

        global_max=global_max,
    )

    # -------------------------------------------------------------------------
    # Panel C
    # -------------------------------------------------------------------------

    draw_panel(
        ax=axes[2],

        zones=zones,

        flows=offpeak,

        title=(
            "C. Off-peak\n"
            "17 remaining hours/day"
        ),

        global_min=global_min,

        global_max=global_max,
    )

    add_north_arrow(
        axes[2]
    )

    # -------------------------------------------------------------------------
    # Main title
    # -------------------------------------------------------------------------

    fig.suptitle(
        MAIN_TITLE,

        fontsize=19,

        fontweight="bold",

        y=0.975,
    )

    # -------------------------------------------------------------------------
    # Subtitle
    # -------------------------------------------------------------------------

    fig.text(
        0.5,
        0.930,

        SUBTITLE,

        ha="center",
        va="center",

        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # Shared legend
    # -------------------------------------------------------------------------

    add_shared_legend(
        fig,
        global_min,
        global_max,
    )

    # -------------------------------------------------------------------------
    # Footer line 1
    # -------------------------------------------------------------------------

    fig.text(
        0.5,
        0.038,

        (
            "Each panel shows the smallest ranked set covering at least 25% of "
            "inter-zonal demand: AM = 73 flows, PM = 100 flows, "
            "off-peak = 110 flows."
        ),

        ha="center",
        va="center",

        fontsize=9.2,
    )

    # -------------------------------------------------------------------------
    # Footer line 2
    # -------------------------------------------------------------------------

    fig.text(
        0.5,
        0.018,

        (
            "One common flow-share scale is used across all panels. "
            "Centroid links represent directional OD connections, not travelled "
            "routes; intra-zonal trips are excluded."
        ),

        ha="center",
        va="center",

        fontsize=9.2,
    )

    # -------------------------------------------------------------------------
    # Layout
    # -------------------------------------------------------------------------

    plt.subplots_adjust(
        left=0.025,
        right=0.985,

        top=0.81,
        bottom=0.19,

        wspace=0.06,
    )

    # -------------------------------------------------------------------------
    # Save PNG
    # -------------------------------------------------------------------------

    fig.savefig(
        PNG_OUT,

        dpi=DPI,

        bbox_inches="tight",

        facecolor="white",
    )

    # -------------------------------------------------------------------------
    # Save PDF
    # -------------------------------------------------------------------------

    fig.savefig(
        PDF_OUT,

        bbox_inches="tight",

        facecolor="white",
    )

    plt.close(
        fig
    )

    print()
    print(
        f"PNG saved -> {PNG_OUT}"
    )

    print(
        f"PDF saved -> {PDF_OUT}"
    )

    print()
    print(
        "VALIDATION PASSED:"
    )

    print(
        "- Only demand_core_25pct flows were mapped."
    )

    print(
        "- AM = 73 flows."
    )

    print(
        "- PM = 100 flows."
    )

    print(
        "- Off-peak = 110 flows."
    )

    print(
        "- One common flow-share scale was used."
    )


if __name__ == "__main__":
    main()