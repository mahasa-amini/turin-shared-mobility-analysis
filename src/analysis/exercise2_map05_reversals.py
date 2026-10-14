# -*- coding: utf-8 -*-
"""
exercise2_map05_reversals.py

Standalone analytical map for Exercise 2.

Shows the five strongest AM <-> PM directional reversals among
inter-zonal e-scooter OD flows in Turin, 2024.

Selection:
    reversal_rank <= 5

Symbology:
    Blue   = AM-specialized direction
    Orange = PM-specialized direction
    Line width = temporal specialization strength (percentage points)

The selected_temporal_reversals layer already contains one directed
geometry for the AM-specialized direction and one for the PM-specialized
direction for each ranked zone pair.
"""

from pathlib import Path
import math

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


# =============================================================================
# PATHS
# =============================================================================

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
    / "map05_selected_am_pm_direction_reversals.png"
)

PDF_OUT = (
    OUTPUT_DIR
    / "map05_selected_am_pm_direction_reversals.pdf"
)


# =============================================================================
# SETTINGS
# =============================================================================

TARGET_EPSG = 3003
TOP_N = 5

# Base map
ZONE_FACE = "#f3f3f3"
ZONE_EDGE = "#a6a6a6"
FOCUS_ZONE_FACE = "#e5e5e5"
FOCUS_ZONE_EDGE = "#777777"

# Temporal directions
AM_COLOR = "#2166ac"
PM_COLOR = "#d95f02"

# Figure
FIGSIZE = (12.0, 9.0)
DPI = 350

TITLE = (
    "Selected AM↔PM Direction Reversals in "
    "Inter-zonal E-scooter OD Flows — Turin, 2024"
)

SUBTITLE = (
    "Top 5 zone pairs ranked by combined temporal specialization"
)

# Directional line rendering
MIN_LINEWIDTH = 1.6
MAX_LINEWIDTH = 4.6

# Offset between opposite directional arrows.
# CRS is metric (EPSG:3003).
DIRECTION_OFFSET_M = 42

# Main-map contextual buffer around the selected reversals
ZOOM_BUFFER_M = 1700

# Pair-number label offset
PAIR_LABEL_OFFSET_M = 115


# =============================================================================
# LOAD
# =============================================================================

def load_data():

    zones = gpd.read_file(
        GPKG,
        layer="zones",
    )

    reversals = gpd.read_file(
        GPKG,
        layer="selected_temporal_reversals",
    )

    if zones.crs is None:
        raise ValueError("Zones layer has no CRS.")

    if reversals.crs is None:
        raise ValueError(
            "selected_temporal_reversals layer has no CRS."
        )

    if zones.crs.to_epsg() != TARGET_EPSG:
        zones = zones.to_crs(
            epsg=TARGET_EPSG
        )

    if reversals.crs.to_epsg() != TARGET_EPSG:
        reversals = reversals.to_crs(
            epsg=TARGET_EPSG
        )

    required_columns = [
        "reversal_rank",
        "zone_pair",
        "direction_type",
        "origin_zone_id",
        "destination_zone_id",
        "specialization_pp",
        "reversal_score",
        "origin_zone_name",
        "destination_zone_name",
        "geometry",
    ]

    missing = [
        col
        for col in required_columns
        if col not in reversals.columns
    ]

    if missing:
        raise KeyError(
            "Missing required columns in "
            f"'selected_temporal_reversals': {missing}"
        )

    selected = reversals.loc[
        reversals["reversal_rank"] <= TOP_N
    ].copy()

    selected = selected.sort_values(
        [
            "reversal_rank",
            "direction_type",
        ]
    )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    expected_rows = TOP_N * 2

    if len(selected) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} directional records "
            f"for Top {TOP_N} pairs, found {len(selected)}."
        )

    rank_counts = (
        selected
        .groupby("reversal_rank")
        .size()
    )

    if not (
        rank_counts == 2
    ).all():
        raise ValueError(
            "Every selected reversal rank must contain "
            "exactly two directional records."
        )

    expected_types = {
        "AM-specialized direction",
        "PM-specialized direction",
    }

    for rank, group in selected.groupby(
        "reversal_rank"
    ):
        observed = set(
            group["direction_type"]
        )

        if observed != expected_types:
            raise ValueError(
                f"Rank {rank} does not contain exactly "
                "one AM-specialized and one "
                "PM-specialized direction."
            )

    print(
        "=" * 100
    )

    print(
        "EXERCISE 2 — AM↔PM DIRECTION REVERSAL MAP"
    )

    print(
        "=" * 100
    )

    print(
        f"Selected zone pairs: {TOP_N}"
    )

    print(
        f"Directional records: {len(selected)}"
    )

    print(
        "\nSelected pairs:"
    )

    pair_summary = (
        selected[
            [
                "reversal_rank",
                "zone_pair",
                "reversal_score",
            ]
        ]
        .drop_duplicates(
            subset=[
                "reversal_rank",
                "zone_pair",
            ]
        )
        .sort_values(
            "reversal_rank"
        )
    )

    print(
        pair_summary.to_string(
            index=False
        )
    )

    return zones, selected


# =============================================================================
# WIDTH SCALE
# =============================================================================

def scale_widths(
    values,
    global_min,
    global_max,
):

    values = np.asarray(
        values,
        dtype=float,
    )

    # sqrt transform maintains differences while preventing
    # the strongest AM direction from dominating too much
    transformed = np.sqrt(
        values
    )

    low = math.sqrt(
        global_min
    )

    high = math.sqrt(
        global_max
    )

    if math.isclose(
        low,
        high,
    ):
        return np.full(
            len(values),
            (
                MIN_LINEWIDTH
                +
                MAX_LINEWIDTH
            )
            / 2,
        )

    return (
        MIN_LINEWIDTH
        +
        (
            transformed
            -
            low
        )
        /
        (
            high
            -
            low
        )
        *
        (
            MAX_LINEWIDTH
            -
            MIN_LINEWIDTH
        )
    )


# =============================================================================
# GEOMETRIC OFFSET
# =============================================================================

def offset_segment(
    start,
    end,
    offset_m,
):
    """
    Offset a straight origin-destination segment perpendicular
    to its direction.

    start/end:
        (x, y)

    offset_m:
        signed perpendicular offset in metres.
    """

    x1, y1 = start
    x2, y2 = end

    dx = x2 - x1
    dy = y2 - y1

    length = math.hypot(
        dx,
        dy,
    )

    if length == 0:
        return start, end

    # Unit perpendicular vector
    px = -dy / length
    py = dx / length

    shifted_start = (
        x1 + px * offset_m,
        y1 + py * offset_m,
    )

    shifted_end = (
        x2 + px * offset_m,
        y2 + py * offset_m,
    )

    return (
        shifted_start,
        shifted_end,
    )


# =============================================================================
# DRAW DIRECTIONAL ARROW
# =============================================================================

def draw_direction(
    ax,
    row,
    linewidth,
):

    geom = row.geometry

    if geom.geom_type != "LineString":
        raise ValueError(
            "Reversal geometry must be LineString."
        )

    coords = list(
        geom.coords
    )

    start = coords[0]
    end = coords[-1]

    if (
        row.direction_type
        ==
        "AM-specialized direction"
    ):

        color = AM_COLOR
        offset = +DIRECTION_OFFSET_M

    elif (
        row.direction_type
        ==
        "PM-specialized direction"
    ):

        color = PM_COLOR
        offset = -DIRECTION_OFFSET_M

    else:

        raise ValueError(
            "Unexpected direction_type: "
            f"{row.direction_type}"
        )

    start_shifted, end_shifted = (
        offset_segment(
            start,
            end,
            offset,
        )
    )

    arrow = FancyArrowPatch(
        posA=start_shifted,
        posB=end_shifted,

        arrowstyle="-|>",

        mutation_scale=(
            10
            +
            linewidth
            * 1.7
        ),

        linewidth=linewidth,

        color=color,

        alpha=0.90,

        shrinkA=3,
        shrinkB=3,

        zorder=8,

        capstyle="round",
        joinstyle="round",
    )

    ax.add_patch(
        arrow
    )


# =============================================================================
# PAIR LABELS
# =============================================================================

def add_pair_rank_labels(
    ax,
    selected,
):

    for rank, group in selected.groupby(
        "reversal_rank"
    ):

        # Both directional geometries represent the same pair.
        row = group.iloc[0]

        geom = row.geometry

        coords = list(
            geom.coords
        )

        x1, y1 = coords[0]
        x2, y2 = coords[-1]

        mx = (
            x1 + x2
        ) / 2

        my = (
            y1 + y2
        ) / 2

        dx = x2 - x1
        dy = y2 - y1

        length = math.hypot(
            dx,
            dy,
        )

        if length == 0:
            continue

        px = -dy / length
        py = dx / length

        # Alternate sides slightly to reduce collisions
        sign = (
            1
            if int(rank) % 2
            else -1
        )

        label_x = (
            mx
            +
            px
            *
            PAIR_LABEL_OFFSET_M
            *
            sign
        )

        label_y = (
            my
            +
            py
            *
            PAIR_LABEL_OFFSET_M
            *
            sign
        )

        ax.text(
            label_x,
            label_y,

            str(
                int(rank)
            ),

            ha="center",
            va="center",

            fontsize=9.3,

            fontweight="bold",

            color="black",

            bbox=dict(
                boxstyle="circle,pad=0.22",
                facecolor="white",
                edgecolor="#555555",
                linewidth=0.8,
                alpha=0.95,
            ),

            zorder=20,
        )


# =============================================================================
# PAIR DESCRIPTION BOX
# =============================================================================

def build_pair_description(
    selected,
):

    lines = [
        "Ranked reversal pairs"
    ]

    for rank in sorted(
        selected["reversal_rank"].unique()
    ):

        group = selected.loc[
            selected["reversal_rank"]
            == rank
        ]

        am = group.loc[
            group["direction_type"]
            ==
            "AM-specialized direction"
        ].iloc[0]

        pm = group.loc[
            group["direction_type"]
            ==
            "PM-specialized direction"
        ].iloc[0]

        lines.append(
            (
                f"{int(rank)}. "
                f"{am.origin_zone_id} {am.origin_zone_name}"
                f" → "
                f"{am.destination_zone_id} {am.destination_zone_name}"
                f"  [AM]"
            )
        )

        lines.append(
            (
                "   "
                f"{pm.origin_zone_id} {pm.origin_zone_name}"
                f" → "
                f"{pm.destination_zone_id} {pm.destination_zone_name}"
                f"  [PM]"
            )
        )

    return "\n".join(
        lines
    )


# =============================================================================
# SCALE BAR
# =============================================================================

def add_scale_bar(
    ax,
    length_km=1,
):

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    width = (
        xmax - xmin
    )

    height = (
        ymax - ymin
    )

    x0 = (
        xmin
        +
        0.06
        *
        width
    )

    y0 = (
        ymin
        +
        0.055
        *
        height
    )

    length_m = (
        length_km
        *
        1000
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

        linewidth=2,

        zorder=30,
    )

    ax.plot(
        [
            x0,
            x0,
        ],
        [
            y0 - 45,
            y0 + 45,
        ],

        color="black",

        linewidth=1.3,

        zorder=30,
    )

    ax.plot(
        [
            x0 + length_m,
            x0 + length_m,
        ],
        [
            y0 - 45,
            y0 + 45,
        ],

        color="black",

        linewidth=1.3,

        zorder=30,
    )

    ax.text(
        x0
        +
        length_m
        /
        2,

        y0
        +
        90,

        f"{length_km} km",

        ha="center",
        va="bottom",

        fontsize=9,

        zorder=30,
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
            0.93,
            0.91,
        ),

        xytext=(
            0.93,
            0.82,
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
            width=2.3,
            headwidth=8,
            headlength=8,
        ),

        zorder=40,
    )


# =============================================================================
# INSET LOCATOR MAP
# =============================================================================

def add_locator_inset(
    ax,
    zones,
    zoom_bounds,
):

    inset = inset_axes(
        ax,
        width="25%",
        height="25%",
        loc="upper left",
        borderpad=1.4,
    )

    zones.plot(
        ax=inset,

        facecolor="#f2f2f2",

        edgecolor="#aaaaaa",

        linewidth=0.3,
    )

    xmin, ymin, xmax, ymax = (
        zones.total_bounds
    )

    inset.set_xlim(
        xmin,
        xmax,
    )

    inset.set_ylim(
        ymin,
        ymax,
    )

    zxmin, zymin, zxmax, zymax = (
        zoom_bounds
    )

    rectangle = Rectangle(
        (
            zxmin,
            zymin,
        ),

        zxmax - zxmin,
        zymax - zymin,

        fill=False,

        edgecolor="#444444",

        linewidth=1.25,

        zorder=10,
    )

    inset.add_patch(
        rectangle
    )

    inset.set_aspect(
        "equal"
    )

    inset.set_axis_off()

    inset.set_title(
        "Location within Turin",
        fontsize=7.7,
        pad=3,
    )


# =============================================================================
# LEGENDS
# =============================================================================

def add_legends(
    ax,
    min_strength,
    max_strength,
):

    # ---------------------------------------------------------
    # Direction legend
    # ---------------------------------------------------------

    direction_handles = [
        Line2D(
            [0],
            [0],
            color=AM_COLOR,
            linewidth=2.8,
            label="AM-specialized direction",
        ),

        Line2D(
            [0],
            [0],
            color=PM_COLOR,
            linewidth=2.8,
            label="PM-specialized direction",
        ),
    ]

    legend_direction = ax.legend(
        handles=direction_handles,

        title="Temporal direction",

        loc="lower right",

        bbox_to_anchor=(
            0.99,
            0.19,
        ),

        frameon=True,

        framealpha=0.97,

        fontsize=9,

        title_fontsize=9.5,
    )

    legend_direction.get_frame().set_edgecolor(
        "#aaaaaa"
    )

    ax.add_artist(
        legend_direction
    )

    # ---------------------------------------------------------
    # Width legend
    # ---------------------------------------------------------

    strength_values = np.array(
        [
            min_strength,

            (
                min_strength
                +
                max_strength
            )
            /
            2,

            max_strength,
        ]
    )

    widths = scale_widths(
        strength_values,

        min_strength,

        max_strength,
    )

    width_handles = []

    for value, width in zip(
        strength_values,
        widths,
    ):

        width_handles.append(
            Line2D(
                [0],
                [0],

                color="#555555",

                linewidth=width,

                label=f"{value:.2f} pp",
            )
        )

    legend_width = ax.legend(
        handles=width_handles,

        title="Temporal specialization",

        loc="lower right",

        bbox_to_anchor=(
            0.99,
            0.02,
        ),

        frameon=True,

        framealpha=0.97,

        fontsize=9,

        title_fontsize=9.5,
    )

    legend_width.get_frame().set_edgecolor(
        "#aaaaaa"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    zones, selected = (
        load_data()
    )

    # ---------------------------------------------------------
    # Strength scale
    # ---------------------------------------------------------

    strengths = (
        selected[
            "specialization_pp"
        ]
        .astype(float)
        .to_numpy()
    )

    min_strength = float(
        strengths.min()
    )

    max_strength = float(
        strengths.max()
    )

    selected[
        "plot_linewidth"
    ] = scale_widths(
        strengths,

        min_strength,

        max_strength,
    )

    print(
        "\nTemporal specialization range:"
    )

    print(
        f"{min_strength:.4f} pp "
        f"to {max_strength:.4f} pp"
    )

    # ---------------------------------------------------------
    # Zones involved in selected reversal pairs
    # ---------------------------------------------------------

    involved_ids = set(
        selected[
            "origin_zone_id"
        ].astype(str)
    ).union(
        set(
            selected[
                "destination_zone_id"
            ].astype(str)
        )
    )

    zone_id_field = (
        "zone_id"
        if "zone_id" in zones.columns
        else "ZONASTAT"
    )

    focus_zones = zones.loc[
        zones[
            zone_id_field
        ]
        .astype(str)
        .isin(
            involved_ids
        )
    ].copy()

    # ---------------------------------------------------------
    # Zoom extent based directly on selected OD geometries
    # ---------------------------------------------------------

    sxmin, symin, sxmax, symax = (
        selected.total_bounds
    )

    zoom_bounds = (
        sxmin - ZOOM_BUFFER_M,
        symin - ZOOM_BUFFER_M,
        sxmax + ZOOM_BUFFER_M,
        symax + ZOOM_BUFFER_M,
    )

    # ---------------------------------------------------------
    # FIGURE
    # ---------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=FIGSIZE
    )

    # Base zones
    zones.plot(
        ax=ax,

        facecolor=ZONE_FACE,

        edgecolor=ZONE_EDGE,

        linewidth=0.45,

        zorder=1,
    )

    # Subtle emphasis of involved zones
    focus_zones.plot(
        ax=ax,

        facecolor=FOCUS_ZONE_FACE,

        edgecolor=FOCUS_ZONE_EDGE,

        linewidth=0.8,

        zorder=2,
    )

    # ---------------------------------------------------------
    # Draw directions
    # ---------------------------------------------------------

    for row in selected.itertuples():

        draw_direction(
            ax,

            row,

            float(
                row.plot_linewidth
            ),
        )

    # Pair numbers
    add_pair_rank_labels(
        ax,
        selected,
    )

    # ---------------------------------------------------------
    # Zoom
    # ---------------------------------------------------------

    ax.set_xlim(
        zoom_bounds[0],
        zoom_bounds[2],
    )

    ax.set_ylim(
        zoom_bounds[1],
        zoom_bounds[3],
    )

    ax.set_aspect(
        "equal"
    )

    ax.set_axis_off()

    # ---------------------------------------------------------
    # Map furniture
    # ---------------------------------------------------------

    add_scale_bar(
        ax,
        length_km=1,
    )

    add_north_arrow(
        ax
    )

    add_locator_inset(
        ax,
        zones,
        zoom_bounds,
    )

    add_legends(
        ax,

        min_strength,

        max_strength,
    )

    # ---------------------------------------------------------
    # Ranked pair description
    # ---------------------------------------------------------

    pair_description = (
        build_pair_description(
            selected
        )
    )

    ax.text(
        0.025,
        0.305,

        pair_description,

        transform=ax.transAxes,

        ha="left",
        va="top",

        fontsize=8.25,

        linespacing=1.35,

        bbox=dict(
            boxstyle="round,pad=0.55",
            facecolor="white",
            edgecolor="#aaaaaa",
            linewidth=0.8,
            alpha=0.96,
        ),

        zorder=50,
    )

    # ---------------------------------------------------------
    # TITLES
    # ---------------------------------------------------------

    fig.suptitle(
        TITLE,

        fontsize=17.5,

        fontweight="semibold",

        y=0.975,
    )

    fig.text(
        0.5,
        0.935,

        SUBTITLE,

        ha="center",

        fontsize=11,
    )

    # ---------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------

    fig.text(
        0.5,
        0.040,

        (
            "Blue and orange arrows identify the AM- and PM-specialized directions "
            "within each selected zone pair. Line width represents the difference "
            "between AM and PM period shares (percentage points)."
        ),

        ha="center",

        fontsize=8.8,
    )

    fig.text(
        0.5,
        0.020,

        (
            "Common detailed-time window: 1 February–31 December 2024. "
            "Links connect official statistical-zone centroids and represent "
            "directional OD relationships; they are not travelled routes."
        ),

        ha="center",

        fontsize=8.8,
    )

    plt.tight_layout(
        rect=[
            0.02,
            0.075,
            0.98,
            0.91,
        ]
    )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    fig.savefig(
        PNG_OUT,

        dpi=DPI,

        bbox_inches="tight",

        facecolor="white",
    )

    fig.savefig(
        PDF_OUT,

        bbox_inches="tight",

        facecolor="white",
    )

    plt.close(
        fig
    )

    print(
        f"\nPNG saved -> {PNG_OUT}"
    )

    print(
        f"PDF saved -> {PDF_OUT}"
    )


if __name__ == "__main__":
    main()