from __future__ import annotations

from pathlib import Path

import pandas as pd
import geopandas as gpd


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PT_REFERENCE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "pt_reference"
    / "gtt_reference_network.gpkg"
)

PROXIMITY_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "proximity"
    / "exercise3_proximity_layers.gpkg"
)

ROUTE_FREQUENCY_CSV = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "route_overlap"
    / "direct_route_frequency_100m.csv"
)

FEEDER_HOTSPOTS_CSV = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "temporal_adduction"
    / "feeder_stop_bidirectional_hotspots_100m.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "gis"
)

OUTPUT_GPKG = (
    OUTPUT_DIR
    / "exercise3_final_gis.gpkg"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TARGET_CRS = "EPSG:3003"


# =============================================================================
# HELPERS
# =============================================================================

def clean_string(series):

    return (
        series
        .astype("string")
        .str.strip()
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 110)
    print("EXERCISE 3 — FINAL GIS PREPARATION")
    print("=" * 110)

    # -------------------------------------------------------------------------
    # Boundary + canonical stops
    # -------------------------------------------------------------------------

    boundary = gpd.read_file(
        PROXIMITY_GPKG,
        layer="torino_boundary",
    ).to_crs(TARGET_CRS)

    stops = gpd.read_file(
        PROXIMITY_GPKG,
        layer="pt_stops_canonical",
    ).to_crs(TARGET_CRS)

    stops["stop_id"] = clean_string(
        stops["stop_id"]
    )

    # -------------------------------------------------------------------------
    # PT route shapes
    # -------------------------------------------------------------------------

    route_shapes = gpd.read_file(
        PT_REFERENCE,
        layer="pt_route_shapes_urban",
    ).to_crs(TARGET_CRS)

    route_shapes["route_id"] = clean_string(
        route_shapes["route_id"]
    )

    print(
        f"Canonical stops: {len(stops):,}"
    )

    print(
        f"Urban PT route-shape records: "
        f"{len(route_shapes):,}"
    )

    # =========================================================================
    # DIRECT-OVERLAP ROUTE INTENSITY
    # =========================================================================

    route_frequency = pd.read_csv(
        ROUTE_FREQUENCY_CSV,
        dtype={
            "operator": "string",
            "season": "string",
            "route_id": "string",
            "route_short_name": "string",
        },
    )

    route_frequency["route_id"] = clean_string(
        route_frequency["route_id"]
    )

    route_system = (
        route_frequency.loc[
            route_frequency["operator"]
            == "system"
        ]
        .copy()
    )

    # One statistic row per route × season
    if route_system.duplicated(
        ["season", "route_id"]
    ).any():

        raise RuntimeError(
            "Duplicate system route statistics."
        )

    route_layers = {}

    for season in [
        "winter_february",
        "summer_july",
    ]:

        stats = (
            route_system.loc[
                route_system["season"]
                == season
            ]
            .copy()
        )

        layer = route_shapes.merge(
            stats[
                [
                    "route_id",
                    "candidate_trip_mentions",
                    "share_of_direct_candidate_trips_pct",
                ]
            ],
            on="route_id",
            how="left",
            validate="many_to_one",
        )

        layer[
            "candidate_trip_mentions"
        ] = (
            layer[
                "candidate_trip_mentions"
            ]
            .fillna(0)
            .astype(int)
        )

        layer[
            "share_of_direct_candidate_trips_pct"
        ] = (
            layer[
                "share_of_direct_candidate_trips_pct"
            ]
            .fillna(0.0)
        )

        layer["season"] = season

        route_layers[season] = layer

    # =========================================================================
    # FEEDER HOTSPOTS
    # =========================================================================

    hotspots = pd.read_csv(
        FEEDER_HOTSPOTS_CSV,
        dtype={
            "operator": "string",
            "season": "string",
            "transport_period": "string",
            "pt_stop_id": "string",
            "pt_stop_name": "string",
            "pt_stop_modes": "string",
        },
    )

    hotspots["pt_stop_id"] = clean_string(
        hotspots["pt_stop_id"]
    )

    system_hotspots = (
        hotspots.loc[
            hotspots["operator"]
            == "system"
        ]
        .copy()
    )

    stop_geometry = (
        stops[
            [
                "stop_id",
                "geometry",
            ]
        ]
        .drop_duplicates(
            "stop_id"
        )
    )

    hotspot_gdf = (
        system_hotspots.merge(
            stop_geometry,
            left_on="pt_stop_id",
            right_on="stop_id",
            how="left",
            validate="many_to_one",
        )
    )

    if hotspot_gdf["geometry"].isna().any():

        missing = (
            hotspot_gdf.loc[
                hotspot_gdf["geometry"].isna(),
                "pt_stop_id",
            ]
            .unique()
        )

        raise RuntimeError(
            "Missing hotspot geometries for "
            f"{len(missing)} stops."
        )

    hotspot_gdf = gpd.GeoDataFrame(
        hotspot_gdf,
        geometry="geometry",
        crs=TARGET_CRS,
    )

    # -------------------------------------------------------------------------
    # Useful cartographic variables
    # -------------------------------------------------------------------------

    hotspot_gdf[
        "sqrt_feeder_trips"
    ] = (
        hotspot_gdf[
            "total_feeder_trips"
        ]
        .astype(float)
        .pow(0.5)
    )

    hotspot_gdf[
        "direction_label"
    ] = "balanced"

    hotspot_gdf.loc[
        hotspot_gdf[
            "direction_balance_index"
        ] >= 0.20,
        "direction_label",
    ] = "access-oriented"

    hotspot_gdf.loc[
        hotspot_gdf[
            "direction_balance_index"
        ] <= -0.20,
        "direction_label",
    ] = "egress-oriented"

    # =========================================================================
    # SELECT MAP-READY SUBSETS
    # =========================================================================

    all_day_hotspots = (
        hotspot_gdf.loc[
            hotspot_gdf[
                "transport_period"
            ]
            == "All day"
        ]
        .copy()
    )

    am_hotspots = (
        hotspot_gdf.loc[
            hotspot_gdf[
                "transport_period"
            ]
            == "AM peak"
        ]
        .copy()
    )

    pm_hotspots = (
        hotspot_gdf.loc[
            hotspot_gdf[
                "transport_period"
            ]
            == "PM peak"
        ]
        .copy()
    )

    # =========================================================================
    # SAVE GPKG
    # =========================================================================

    if OUTPUT_GPKG.exists():

        OUTPUT_GPKG.unlink()

    boundary.to_file(
        OUTPUT_GPKG,
        layer="torino_boundary",
        driver="GPKG",
    )

    stops.to_file(
        OUTPUT_GPKG,
        layer="pt_stops_canonical",
        driver="GPKG",
    )

    route_layers[
        "winter_february"
    ].to_file(
        OUTPUT_GPKG,
        layer="routes_direct_overlap_winter",
        driver="GPKG",
    )

    route_layers[
        "summer_july"
    ].to_file(
        OUTPUT_GPKG,
        layer="routes_direct_overlap_summer",
        driver="GPKG",
    )

    all_day_hotspots.to_file(
        OUTPUT_GPKG,
        layer="feeder_hotspots_all_day",
        driver="GPKG",
    )

    am_hotspots.to_file(
        OUTPUT_GPKG,
        layer="feeder_hotspots_am_peak",
        driver="GPKG",
    )

    pm_hotspots.to_file(
        OUTPUT_GPKG,
        layer="feeder_hotspots_pm_peak",
        driver="GPKG",
    )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    layers = gpd.list_layers(
        OUTPUT_GPKG
    )

    print(
        "\nSaved layers:"
    )

    print(
        layers.to_string(
            index=False
        )
    )

    expected_layers = {
        "torino_boundary",
        "pt_stops_canonical",
        "routes_direct_overlap_winter",
        "routes_direct_overlap_summer",
        "feeder_hotspots_all_day",
        "feeder_hotspots_am_peak",
        "feeder_hotspots_pm_peak",
    }

    observed = set(
        layers["name"]
    )

    missing = (
        expected_layers
        - observed
    )

    if missing:

        raise RuntimeError(
            f"Missing GIS layers: {missing}"
        )

    print(
        "\nGIS validation: PASSED"
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "MAP-READY FEATURE COUNTS"
    )

    print(
        "=" * 110
    )

    print(
        f"Canonical PT stops: "
        f"{len(stops):,}"
    )

    print(
        f"All-day hotspot records: "
        f"{len(all_day_hotspots):,}"
    )

    print(
        f"AM hotspot records: "
        f"{len(am_hotspots):,}"
    )

    print(
        f"PM hotspot records: "
        f"{len(pm_hotspots):,}"
    )

    print(
        "\nHotspot seasons:"
    )

    print(
        hotspot_gdf[
            "season"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nFinal GIS package ->"
    )

    print(
        OUTPUT_GPKG
    )


if __name__ == "__main__":

    main()