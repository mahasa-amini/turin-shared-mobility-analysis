from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch


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
    / "map04_offpeak_od_demand_core.png"
)

PDF_OUT = (
    OUTPUT_DIR
    / "map04_offpeak_od_demand_core.pdf"
)


# ============================================================
# CARTOGRAPHIC SETTINGS
# ============================================================

ZONE_FACE = "#f2f2f2"
ZONE_EDGE = "#9a9a9a"

FLOW_COLOR = "#2166ac"

TITLE = (
    "Off-peak Inter-zonal E-scooter OD Flows — Turin, 2024"
)

SUBTITLE = (
    "17 remaining hours/day | Strongest flows covering 25% "
    "of observed off-peak inter-zonal demand"
)


# ============================================================
# LOAD DATA
#
# Only off-peak is plotted.
#
# AM and PM are also loaded so Maps 2, 3 and 4 use exactly
# the same flow-share scale.
# ============================================================

def load_layers():

    zones = gpd.read_file(
        GPKG,
        layer="zones",
    )

    am = gpd.read_file(
        GPKG,
        layer="flows_am_peak",
    )

    pm = gpd.read_file(
        GPKG,
        layer="flows_pm_peak",
    )

    offpeak = gpd.read_file(
        GPKG,
        layer="flows_offpeak",
    )

    for layer in [
        zones,
        am,
        pm,
        offpeak,
    ]:

        assert (
            layer.crs.to_epsg()
            == 3003
        )

    # ========================================================
    # 25% DEMAND CORE
    # ========================================================

    am = am.loc[
        am["demand_core_25pct"]
        == True
    ].copy()

    pm = pm.loc[
        pm["demand_core_25pct"]
        == True
    ].copy()

    offpeak = offpeak.loc[
        offpeak["demand_core_25pct"]
        == True
    ].copy()

    assert len(am) == 73
    assert len(pm) == 100
    assert len(offpeak) == 110

    # ========================================================
    # COMMON TEMPORAL FLOW-SHARE SCALE
    #
    # IMPORTANT:
    # Must be identical to Maps 2 and 3.
    # ========================================================

    all_temporal_shares = np.concatenate(
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
        all_temporal_shares.min()
    )

    global_max = float(
        all_temporal_shares.max()
    )

    print(
        f"Selected off-peak flows: "
        f"{len(offpeak):,}"
    )

    print(
        f"Off-peak inter-zonal trips represented: "
        f"{offpeak['system_trips'].sum():,.0f}"
    )

    print(
        f"Off-peak demand share represented: "
        f"{offpeak['flow_share_pct'].sum():.2f}%"
    )

    print(
        "\nCommon temporal flow-share scale:"
    )

    print(
        f"Minimum = "
        f"{global_min:.4f}%"
    )

    print(
        f"Maximum = "
        f"{global_max:.4f}%"
    )

    return (
        zones,
        offpeak,
        global_min,
        global_max,
    )


# ============================================================
# LINE WIDTH SCALING
#
# Same function and same limits as AM and PM maps.
# ============================================================

def scale_line_width(
    values,
    global_min,
    global_max,
    min_width=0.45,
    max_width=3.2,
):

    values = np.asarray(
        values,
        dtype=float,
    )

    transformed = np.sqrt(
        values
    )

    low = np.sqrt(
        global_min
    )

    high = np.sqrt(
        global_max
    )

    if high == low:

        return np.full(
            len(values),
            (
                min_width
                +
                max_width
            )
            / 2,
        )

    return (
        min_width
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
            max_width
            -
            min_width
        )
    )


# ============================================================
# DRAW DIRECTIONAL OD FLOWS
# ============================================================

def draw_flows(
    ax,
    flows,
    global_min,
    global_max,
):

    widths = scale_line_width(
        flows[
            "flow_share_pct"
        ],
        global_min=global_min,
        global_max=global_max,
    )

    for (
        row,
        width,
    ) in zip(
        flows.itertuples(),
        widths,
    ):

        geom = row.geometry

        start = (
            geom.coords[0]
        )

        end = (
            geom.coords[-1]
        )

        # ----------------------------------------------------
        # Opposite OD directions curve to opposite sides.
        # ----------------------------------------------------

        if (
            str(
                row.origin_zone_id
            )
            <
            str(
                row.destination_zone_id
            )
        ):

            curvature = 0.055

        else:

            curvature = -0.055

        # ----------------------------------------------------
        # Common temporal alpha scaling
        # ----------------------------------------------------

        if (
            global_max
            >
            global_min
        ):

            strength = (
                (
                    row.flow_share_pct
                    -
                    global_min
                )
                /
                (
                    global_max
                    -
                    global_min
                )
            )

        else:

            strength = 1.0

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
                7.0
                +
                width
                *
                2.6
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


# ============================================================
# SCALE BAR
# ============================================================

def add_scale_bar(
    ax,
    zones,
    length_km=2,
):

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    width = (
        maxx
        -
        minx
    )

    height = (
        maxy
        -
        miny
    )

    x0 = (
        minx
        +
        width
        *
        0.065
    )

    y0 = (
        miny
        +
        height
        *
        0.055
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
        linewidth=2.0,
        zorder=10,
    )

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
        zorder=10,
    )

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
        zorder=10,
    )

    ax.text(
        x0
        +
        length_m
        /
        2,

        y0
        +
        height
        *
        0.018,

        f"{length_km} km",

        ha="center",
        va="bottom",

        fontsize=9,

        zorder=10,
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
            0.94,
            0.94,
        ),

        xytext=(
            0.94,
            0.84,
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
            width=3,
            headwidth=10,
            headlength=10,
        ),

        zorder=20,
    )


# ============================================================
# TEMPORAL FLOW LEGEND
#
# Same values as AM and PM maps.
# ============================================================

def add_flow_legend(
    ax,
    global_min,
    global_max,
):

    legend_values = np.array(
        [
            global_min,

            (
                global_min
                +
                global_max
            )
            /
            2,

            global_max,
        ],

        dtype=float,
    )

    widths = scale_line_width(
        legend_values,

        global_min=global_min,

        global_max=global_max,
    )

    handles = []

    labels = []

    for (
        value,
        width,
    ) in zip(
        legend_values,
        widths,
    ):

        handles.append(
            Line2D(
                [0],
                [0],

                color=FLOW_COLOR,

                linewidth=width,

                alpha=0.8,
            )
        )

        labels.append(
            f"{value:.2f}%"
        )

    legend = ax.legend(
        handles,
        labels,

        title=(
            "Share of period\n"
            "inter-zonal demand"
        ),

        loc="lower right",

        frameon=True,

        framealpha=0.95,

        fontsize=9,

        title_fontsize=9.5,

        borderpad=0.8,
    )

    legend.get_frame().set_edgecolor(
        "#b0b0b0"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    (
        zones,
        flows,
        global_min,
        global_max,
    ) = load_layers()

    # ========================================================
    # A4 LANDSCAPE
    # ========================================================

    fig, ax = plt.subplots(
        figsize=(
            11.69,
            8.27,
        )
    )

    # ========================================================
    # ZONE BACKGROUND
    # ========================================================

    zones.plot(
        ax=ax,

        facecolor=ZONE_FACE,

        edgecolor=ZONE_EDGE,

        linewidth=0.45,

        zorder=1,
    )

    # ========================================================
    # OFF-PEAK FLOWS
    # ========================================================

    draw_flows(
        ax,
        flows,
        global_min,
        global_max,
    )

    # ========================================================
    # SAME CITY EXTENT AS AM AND PM
    # ========================================================

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    x_pad = (
        maxx
        -
        minx
    ) * 0.035

    y_pad = (
        maxy
        -
        miny
    ) * 0.035

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

    # ========================================================
    # CARTOGRAPHIC ELEMENTS
    # ========================================================

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
        global_min,
        global_max,
    )

    # ========================================================
    # TITLES
    # ========================================================

    fig.suptitle(
        TITLE,

        fontsize=16,

        fontweight="semibold",

        y=0.955,
    )

    ax.set_title(
        SUBTITLE,

        fontsize=11,

        pad=11,
    )

    # ========================================================
    # NOTES
    # ========================================================

    fig.text(
        0.5,
        0.035,

        (
            "Common detailed-time window: "
            "1 February–31 December 2024. "
            "Official Torino statistical zoning (94 zones). "
            "Lines connect zone centroids and represent "
            "directional OD flows."
        ),

        ha="center",
        va="center",

        fontsize=8.3,
    )

    fig.text(
        0.5,
        0.016,

        (
            "Line width represents each corridor's share "
            "of off-peak inter-zonal demand. "
            "The same flow-share scale is used for AM, PM "
            "and off-peak maps. "
            "Intra-zonal trips are excluded."
        ),

        ha="center",
        va="center",

        fontsize=8.3,
    )

    ax.set_axis_off()

    plt.tight_layout(
        rect=[
            0.015,
            0.055,
            0.985,
            0.945,
        ]
    )

    # ========================================================
    # SAVE
    # ========================================================

    fig.savefig(
        PNG_OUT,

        dpi=350,

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
        f"\nPNG saved -> "
        f"{PNG_OUT}"
    )

    print(
        f"PDF saved -> "
        f"{PDF_OUT}"
    )


if __name__ == "__main__":
    main()