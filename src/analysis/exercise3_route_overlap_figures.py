from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
import geopandas as gpd


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GIS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "gis"
    / "exercise3_final_gis.gpkg"
)

ROUTE_OVERLAP_PARQUET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "route_overlap"
    / "scooter_pt_route_overlap_february_july_2024.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_3"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BOUNDARY_LAYER = "torino_boundary"

WINTER_LAYER = "routes_direct_overlap_winter"
SUMMER_LAYER = "routes_direct_overlap_summer"

RAW_METRIC = "candidate_trip_mentions"

NORMALIZED_METRIC = (
    "direct_overlap_mentions_per_1000_trips"
)

DIRECT_CLASS = (
    "Direct PT-route overlap candidate"
)

CLASS_COL = (
    "route_interaction_class_100m"
)

SEASON_CONFIG = {
    "winter_february": {
        "layer": WINTER_LAYER,
        "panel_title": "Winter — February 2024",
        "single_title": (
            "Potential Direct PT-Route Overlap — February 2024"
        ),
        "filename": "direct_route_overlap_winter.png",
    },
    "summer_july": {
        "layer": SUMMER_LAYER,
        "panel_title": "Summer — July 2024",
        "single_title": (
            "Potential Direct PT-Route Overlap — July 2024"
        ),
        "filename": "direct_route_overlap_summer.png",
    },
}


# =============================================================================
# ROUTE PREPARATION
# =============================================================================

def prepare_route_layer(
    gdf: gpd.GeoDataFrame,
    total_scooter_trips: int,
) -> gpd.GeoDataFrame:
    """
    Dissolve multiple GTFS shape variants into one geometry per route.

    candidate_trip_mentions is a route-level statistic. It is therefore
    preserved once per route rather than visually repeated because a route
    happens to have several GTFS shape variants.

    The raw number of candidate mentions is then normalized by total scooter
    trips in the corresponding season:

        candidate_trip_mentions
        / total analyzed scooter trips
        * 1000

    This makes winter and summer spatial patterns comparable despite the
    much larger absolute scooter volume in July.
    """

    required = [
        "route_id",
        "route_short_name",
        RAW_METRIC,
        "geometry",
    ]

    missing = [
        col
        for col in required
        if col not in gdf.columns
    ]

    if missing:
        raise RuntimeError(
            f"Missing required route columns: {missing}"
        )

    if total_scooter_trips <= 0:
        raise RuntimeError(
            "Total scooter-trip denominator must be positive."
        )

    gdf = gdf.copy()

    gdf[RAW_METRIC] = (
        pd.to_numeric(
            gdf[RAW_METRIC],
            errors="coerce",
        )
        .fillna(0)
        .astype(float)
    )

    # -------------------------------------------------------------------------
    # Validate that statistics really are route-level.
    # -------------------------------------------------------------------------

    consistency = (
        gdf
        .groupby("route_id")[RAW_METRIC]
        .nunique()
    )

    inconsistent = consistency.loc[
        consistency > 1
    ]

    if not inconsistent.empty:
        bad_routes = (
            inconsistent
            .index
            .astype(str)
            .tolist()
        )

        raise RuntimeError(
            "candidate_trip_mentions varies across GTFS shape "
            "records belonging to the same route.\n"
            f"Examples: {bad_routes[:10]}"
        )

    # -------------------------------------------------------------------------
    # One geometry per route.
    # -------------------------------------------------------------------------

    route_level = (
        gdf[
            [
                "route_id",
                "route_short_name",
                RAW_METRIC,
                "geometry",
            ]
        ]
        .dissolve(
            by="route_id",
            aggfunc={
                "route_short_name": "first",
                RAW_METRIC: "first",
            },
            as_index=False,
        )
    )

    route_level[NORMALIZED_METRIC] = (
        route_level[RAW_METRIC]
        / total_scooter_trips
        * 1000.0
    )

    return route_level


# =============================================================================
# SCOOTER DENOMINATORS / DIRECT-ROUTE RATES
# =============================================================================

def build_season_statistics(
    trip_df: pd.DataFrame,
) -> dict:
    """
    Derive denominators from the actual Stage-3 per-trip analysis rather than
    hard-coding February and July trip counts.

    Also calculates the percentage of scooter trips classified as direct
    PT-route overlap candidates at the 100 m baseline.
    """

    required = [
        "analysis_trip_id",
        "season",
        CLASS_COL,
    ]

    missing = [
        col
        for col in required
        if col not in trip_df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Required Stage-3 columns missing: {missing}"
        )

    if trip_df["analysis_trip_id"].duplicated().any():
        raise RuntimeError(
            "analysis_trip_id is not unique in Stage-3 dataset."
        )

    result = {}

    for season in SEASON_CONFIG:

        group = (
            trip_df.loc[
                trip_df["season"] == season
            ]
            .copy()
        )

        if group.empty:
            raise RuntimeError(
                f"No Stage-3 trips found for season: {season}"
            )

        total_trips = len(group)

        direct_trips = int(
            (
                group[CLASS_COL]
                == DIRECT_CLASS
            ).sum()
        )

        direct_pct = (
            100.0
            * direct_trips
            / total_trips
        )

        result[season] = {
            "total_trips": total_trips,
            "direct_trips": direct_trips,
            "direct_pct": direct_pct,
        }

    return result


# =============================================================================
# CARTOGRAPHIC SCALING
# =============================================================================

def width_from_value(
    value: float,
    global_max: float,
    min_width: float = 0.85,
    max_width: float = 2.30,
) -> float:
    """
    Use only a modest width variation.

    Colour is the primary quantitative encoding. Line width is secondary and
    deliberately constrained so dense central routes do not dominate the map.
    """

    if (
        value <= 0
        or global_max <= 0
    ):
        return min_width

    ratio = np.sqrt(
        value / global_max
    )

    return (
        min_width
        + ratio
        * (
            max_width
            - min_width
        )
    )


# =============================================================================
# MAP FUNCTION
# =============================================================================

def plot_single_map(
    ax,
    boundary: gpd.GeoDataFrame,
    routes: gpd.GeoDataFrame,
    global_max: float,
    norm,
    cmap,
    title: str,
    total_trips: int,
    direct_pct: float,
):
    """
    Draw one seasonal panel using a scale shared across both seasons.
    """

    # -------------------------------------------------------------------------
    # Torino municipal boundary
    # -------------------------------------------------------------------------

    boundary.plot(
        ax=ax,
        facecolor="none",
        edgecolor="0.30",
        linewidth=1.0,
        zorder=1,
    )

    # -------------------------------------------------------------------------
    # Entire reference PT network as subtle context
    # -------------------------------------------------------------------------

    routes.plot(
        ax=ax,
        color="0.84",
        linewidth=0.45,
        alpha=0.70,
        zorder=2,
    )

    # -------------------------------------------------------------------------
    # Routes with at least one direct-overlap candidate mention
    # -------------------------------------------------------------------------

    active = (
        routes.loc[
            routes[NORMALIZED_METRIC] > 0
        ]
        .copy()
    )

    active = active.sort_values(
        NORMALIZED_METRIC
    )

    for row in active.itertuples(
        index=False
    ):

        value = getattr(
            row,
            NORMALIZED_METRIC,
        )

        geometry = row.geometry

        color = cmap(
            norm(value)
        )

        linewidth = width_from_value(
            value=value,
            global_max=global_max,
        )

        gpd.GeoSeries(
            [geometry],
            crs=routes.crs,
        ).plot(
            ax=ax,
            color=color,
            linewidth=linewidth,
            alpha=0.92,
            zorder=3,
        )

    # -------------------------------------------------------------------------
    # Titles / analytical annotation
    # -------------------------------------------------------------------------

    ax.set_title(
        title,
        fontsize=14,
        pad=10,
    )

    annotation = (
        f"Analyzed trips: {total_trips:,}\n"
        f"Direct-route candidates: {direct_pct:.1f}%"
    )

    ax.text(
        0.025,
        0.025,
        annotation,
        transform=ax.transAxes,
        fontsize=9,
        va="bottom",
        ha="left",
        bbox={
            "facecolor": "white",
            "edgecolor": "0.75",
            "alpha": 0.88,
            "boxstyle": "round,pad=0.35",
        },
        zorder=5,
    )

    ax.set_axis_off()

    ax.set_aspect(
        "equal"
    )


# =============================================================================
# TERMINAL SUMMARY
# =============================================================================

def print_top_routes(
    season: str,
    routes: gpd.GeoDataFrame,
    n: int = 10,
):
    """
    Print the strongest normalized route-overlap corridors for audit and
    interpretation.
    """

    top = (
        routes[
            [
                "route_id",
                "route_short_name",
                RAW_METRIC,
                NORMALIZED_METRIC,
            ]
        ]
        .sort_values(
            NORMALIZED_METRIC,
            ascending=False,
        )
        .head(n)
    )

    print(
        f"\nTop {n} routes — {season}"
    )

    print(
        top.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 110
    )

    print(
        "EXERCISE 3 — NORMALIZED DIRECT-ROUTE OVERLAP FIGURES"
    )

    print(
        "=" * 110
    )

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    if not GIS_PATH.exists():
        raise FileNotFoundError(
            f"GIS package not found:\n{GIS_PATH}"
        )

    if not ROUTE_OVERLAP_PARQUET.exists():
        raise FileNotFoundError(
            "Stage-3 route-overlap dataset not found:\n"
            f"{ROUTE_OVERLAP_PARQUET}"
        )

    # =========================================================================
    # LOAD BOUNDARY
    # =========================================================================

    boundary = gpd.read_file(
        GIS_PATH,
        layer=BOUNDARY_LAYER,
    )

    # =========================================================================
    # LOAD STAGE-3 SCOOTER DATA
    # =========================================================================

    trip_df = pd.read_parquet(
        ROUTE_OVERLAP_PARQUET,
        columns=[
            "analysis_trip_id",
            "season",
            CLASS_COL,
        ],
    )

    season_stats = (
        build_season_statistics(
            trip_df
        )
    )

    print(
        "\nSeason denominators:"
    )

    for season, stats in season_stats.items():

        print(
            f"{season:20s} "
            f"trips={stats['total_trips']:,} | "
            f"direct candidates="
            f"{stats['direct_trips']:,} "
            f"({stats['direct_pct']:.2f}%)"
        )

    # =========================================================================
    # LOAD AND NORMALIZE ROUTE LAYERS
    # =========================================================================

    route_layers = {}

    for season, config in SEASON_CONFIG.items():

        raw = gpd.read_file(
            GIS_PATH,
            layer=config["layer"],
        )

        print(
            f"\n{season}: "
            f"{len(raw):,} raw GTFS route-shape records"
        )

        prepared = prepare_route_layer(
            gdf=raw,
            total_scooter_trips=(
                season_stats[
                    season
                ][
                    "total_trips"
                ]
            ),
        )

        route_layers[
            season
        ] = prepared

        print(
            f"{season}: "
            f"{len(prepared):,} route-level records"
        )

    winter = route_layers[
        "winter_february"
    ]

    summer = route_layers[
        "summer_july"
    ]

    # =========================================================================
    # SHARED NORMALIZATION ACROSS BOTH SEASONS
    # =========================================================================

    global_max = max(
        winter[
            NORMALIZED_METRIC
        ].max(),
        summer[
            NORMALIZED_METRIC
        ].max(),
    )

    if (
        pd.isna(global_max)
        or global_max <= 0
    ):
        raise RuntimeError(
            "No positive normalized overlap values found."
        )

    print(
        "\nShared normalized scale:"
    )

    print(
        "Maximum route-overlap intensity: "
        f"{global_max:.2f} mentions per 1,000 trips"
    )

    # -------------------------------------------------------------------------
    # Power normalization:
    #
    # More readable than a logarithmic scale while still compressing the
    # strongly skewed route-intensity distribution.
    # -------------------------------------------------------------------------

    norm = mpl.colors.PowerNorm(
        gamma=0.55,
        vmin=0,
        vmax=global_max,
    )

    cmap = plt.get_cmap(
        "viridis"
    )

    # =========================================================================
    # AUDIT / INTERPRETATION TABLES
    # =========================================================================

    print_top_routes(
        "winter_february",
        winter,
    )

    print_top_routes(
        "summer_july",
        summer,
    )

    # =========================================================================
    # COMBINED WINTER / SUMMER FIGURE
    # =========================================================================

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(15, 9),
        constrained_layout=True,
    )

    winter_stats = (
        season_stats[
            "winter_february"
        ]
    )

    summer_stats = (
        season_stats[
            "summer_july"
        ]
    )

    plot_single_map(
        ax=axes[0],
        boundary=boundary,
        routes=winter,
        global_max=global_max,
        norm=norm,
        cmap=cmap,
        title=(
            SEASON_CONFIG[
                "winter_february"
            ][
                "panel_title"
            ]
        ),
        total_trips=(
            winter_stats[
                "total_trips"
            ]
        ),
        direct_pct=(
            winter_stats[
                "direct_pct"
            ]
        ),
    )

    plot_single_map(
        ax=axes[1],
        boundary=boundary,
        routes=summer,
        global_max=global_max,
        norm=norm,
        cmap=cmap,
        title=(
            SEASON_CONFIG[
                "summer_july"
            ][
                "panel_title"
            ]
        ),
        total_trips=(
            summer_stats[
                "total_trips"
            ]
        ),
        direct_pct=(
            summer_stats[
                "direct_pct"
            ]
        ),
    )

    fig.suptitle(
        (
            "Potential Direct Public-Transport Route Overlap "
            "with Scooter O-Ds"
        ),
        fontsize=18,
    )

    # -------------------------------------------------------------------------
    # Shared colourbar
    # -------------------------------------------------------------------------

    sm = mpl.cm.ScalarMappable(
        norm=norm,
        cmap=cmap,
    )

    sm.set_array([])

    cbar = fig.colorbar(
        sm,
        ax=axes,
        fraction=0.026,
        pad=0.025,
    )

    cbar.set_label(
        (
            "Direct-route overlap mentions "
            "per 1,000 analyzed scooter trips"
        ),
        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # Short methodological footer
    # -------------------------------------------------------------------------

    fig.text(
        0.5,
        0.022,
        (
            "100 m endpoint-to-stop threshold; "
            "ordered direct PT-route compatibility. "
            "Winter and summer use the same normalized scale.\n"
            "Later GTFS reference: 12 Aug 2026–31 Jan 2027; "
            "spatial/topological compatibility, not historical service or observed transfers."
        ),
        ha="center",
        fontsize=10,
    )

    combined_path = (
        OUTPUT_DIR
        / "direct_route_overlap_winter_summer.png"
    )

    fig.savefig(
        combined_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        f"\nSaved -> {combined_path}"
    )

    # =========================================================================
    # SEPARATE SEASONAL FIGURES
    # =========================================================================

    for season, config in SEASON_CONFIG.items():

        routes = route_layers[
            season
        ]

        stats = season_stats[
            season
        ]

        fig, ax = plt.subplots(
            figsize=(9, 9)
        )

        plot_single_map(
            ax=ax,
            boundary=boundary,
            routes=routes,
            global_max=global_max,
            norm=norm,
            cmap=cmap,
            title=config[
                "single_title"
            ],
            total_trips=stats[
                "total_trips"
            ],
            direct_pct=stats[
                "direct_pct"
            ],
        )

        sm = mpl.cm.ScalarMappable(
            norm=norm,
            cmap=cmap,
        )

        sm.set_array([])

        cbar = fig.colorbar(
            sm,
            ax=ax,
            fraction=0.035,
            pad=0.02,
        )

        cbar.set_label(
            (
                "Direct-route overlap mentions "
                "per 1,000 analyzed scooter trips"
            )
        )

        fig.text(
            0.5,
            0.022,
            (
                "100 m endpoint-to-stop threshold; "
                "later GTFS reference: 12 Aug 2026–31 Jan 2027.\n"
                "Spatial/topological compatibility, not historical service or observed transfers."
            ),
            ha="center",
            fontsize=9,
        )

        out_path = (
            OUTPUT_DIR
            / config[
                "filename"
            ]
        )

        fig.savefig(
            out_path,
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(
            fig
        )

        print(
            f"Saved -> {out_path}"
        )

    # =========================================================================
    # FINAL NOTES
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "FIGURE VALIDATION"
    )

    print(
        "=" * 110
    )

    print(
        "- Route geometries were dissolved to "
        "one feature per route."
    )

    print(
        "- Raw February and July scooter volumes "
        "are NOT directly compared through colour."
    )

    print(
        "- Route intensity is normalized per "
        "1,000 analyzed scooter trips in each season."
    )

    print(
        "- Winter and summer use the same colour "
        "and line-width scale."
    )

    print(
        "- Colour is the primary intensity encoding; "
        "line-width variation is deliberately modest."
    )

    print(
        "- candidate_trip_mentions may count one "
        "scooter trip against multiple compatible "
        "PT routes."
    )

    print(
        "- Therefore the mapped measure is correctly "
        "labelled as route-overlap MENTIONS per "
        "1,000 scooter trips."
    )

    print(
        "- Direct-route compatibility represents "
        "potential competition, not observed "
        "mode substitution."
    )


if __name__ == "__main__":

    main()
