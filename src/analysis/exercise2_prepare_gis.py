from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ZONE_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "zoning"
    / "torino_statistical_zones.gpkg"
)

OD_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "od"
)

TEMPORAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "temporal_od"
)

CONTRAST_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "temporal_contrasts"
)

OD_TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "od"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "gis"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "gis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_GPKG = (
    OUTPUT_DIR
    / "exercise2_od_layers.gpkg"
)


ALL_DAY_FILE = (
    OD_DIR
    / "od_system_2024_long.parquet"
)

CONVENTIONAL_FILE = (
    TEMPORAL_DIR
    / "system_conventional_period_od_2024.parquet"
)

EMPIRICAL_FILE = (
    TEMPORAL_DIR
    / "system_empirical_period_od_2024.parquet"
)

CONTRAST_FILE = (
    CONTRAST_DIR
    / "system_temporal_od_contrasts_2024.parquet"
)

ALL_DAY_INTENSITY_FILE = (
    OD_TABLE_DIR
    / "zone_production_attraction_system_2024.csv"
)


# ============================================================
# LOAD ZONES
# ============================================================

def load_zones():

    zones = gpd.read_file(
        ZONE_GPKG,
        layer="zones",
    )

    assert len(zones) == 94

    assert (
        zones.crs.to_epsg()
        == 3003
    )

    zones["zone_id"] = (
        zones["zone_id"]
        .astype("string")
    )

    return zones


# ============================================================
# CENTROID LOOKUP
# ============================================================

def build_centroid_lookup(
    zones,
):

    lookup = (
        zones[
            [
                "zone_id",
                "zone_name",
                "centroid_x",
                "centroid_y",
            ]
        ]
        .copy()
    )

    return lookup


# ============================================================
# ADD FLOW GEOMETRY
# ============================================================

def build_flow_lines(
    df,
    zones,
    value_col,
):

    data = df.copy()

    data["origin_zone_id"] = (
        data["origin_zone_id"]
        .astype("string")
    )

    data["destination_zone_id"] = (
        data["destination_zone_id"]
        .astype("string")
    )

    # --------------------------------------------------------
    # Inter-zonal only.
    #
    # Intra-zonal trips are represented by polygon-based
    # intensity layers, not zero-length flow lines.
    # --------------------------------------------------------

    data = data.loc[
        data["origin_zone_id"]
        != data["destination_zone_id"]
    ].copy()

    data = data.loc[
        data[value_col] > 0
    ].copy()

    lookup = (
        build_centroid_lookup(
            zones
        )
    )

    origin_lookup = (
        lookup.rename(
            columns={
                "zone_id":
                    "origin_zone_id",

                "zone_name":
                    "origin_zone_name_lookup",

                "centroid_x":
                    "origin_x",

                "centroid_y":
                    "origin_y",
            }
        )
    )

    destination_lookup = (
        lookup.rename(
            columns={
                "zone_id":
                    "destination_zone_id",

                "zone_name":
                    "destination_zone_name_lookup",

                "centroid_x":
                    "destination_x",

                "centroid_y":
                    "destination_y",
            }
        )
    )

    data = (
        data.merge(
            origin_lookup,
            on="origin_zone_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            destination_lookup,
            on="destination_zone_id",
            how="left",
            validate="many_to_one",
        )
    )

    assert (
        data[
            [
                "origin_x",
                "origin_y",
                "destination_x",
                "destination_y",
            ]
        ]
        .notna()
        .all()
        .all()
    )

    # Prefer existing names where available.
    if "origin_zone_name" not in data.columns:

        data["origin_zone_name"] = (
            data[
                "origin_zone_name_lookup"
            ]
        )

    if "destination_zone_name" not in data.columns:

        data["destination_zone_name"] = (
            data[
                "destination_zone_name_lookup"
            ]
        )

    geometry = [
        LineString(
            [
                (
                    origin_x,
                    origin_y,
                ),
                (
                    destination_x,
                    destination_y,
                ),
            ]
        )
        for (
            origin_x,
            origin_y,
            destination_x,
            destination_y,
        )
        in zip(
            data["origin_x"],
            data["origin_y"],
            data["destination_x"],
            data["destination_y"],
        )
    ]

    gdf = gpd.GeoDataFrame(
        data,
        geometry=geometry,
        crs=zones.crs,
    )

    gdf[
        "centroid_distance_km"
    ] = (
        gdf.geometry.length
        /
        1000
    )

    gdf = gdf.drop(
        columns=[
            "origin_zone_name_lookup",
            "destination_zone_name_lookup",
        ],
        errors="ignore",
    )

    return gdf


# ============================================================
# RANKING / MAP FILTER FIELDS
# ============================================================

def first_rank_reaching_share(
    cumulative_share,
    target,
):

    reached = np.flatnonzero(
        cumulative_share.to_numpy()
        >= target
    )

    if len(reached) == 0:

        return len(
            cumulative_share
        )

    return int(
        reached[0]
        + 1
    )


def rank_flow_group(
    group,
    value_col,
):

    data = (
        group.sort_values(
            value_col,
            ascending=False,
        )
        .copy()
        .reset_index(
            drop=True
        )
    )

    data[
        "flow_rank"
    ] = np.arange(
        1,
        len(data) + 1,
    )

    total = (
        data[
            value_col
        ]
        .sum()
    )

    data[
        "flow_share_pct"
    ] = (
        data[
            value_col
        ]
        /
        total
        * 100
    )

    data[
        "cumulative_flow_share_pct"
    ] = (
        data[
            "flow_share_pct"
        ]
        .cumsum()
    )

    data[
        "pair_rank_percentile_pct"
    ] = (
        data[
            "flow_rank"
        ]
        /
        len(data)
        * 100
    )

    # --------------------------------------------------------
    # Pair-count thresholds
    # --------------------------------------------------------

    data[
        "top_1pct_pairs"
    ] = (
        data[
            "pair_rank_percentile_pct"
        ]
        <= 1
    )

    data[
        "top_2pct_pairs"
    ] = (
        data[
            "pair_rank_percentile_pct"
        ]
        <= 2
    )

    data[
        "top_5pct_pairs"
    ] = (
        data[
            "pair_rank_percentile_pct"
        ]
        <= 5
    )

    # --------------------------------------------------------
    # Demand-coverage thresholds
    #
    # Include the first flow that crosses each target,
    # so selected flows cover AT LEAST the target share.
    # --------------------------------------------------------

    for target in [
        10,
        25,
        50,
    ]:

        cutoff_rank = (
            first_rank_reaching_share(
                data[
                    "cumulative_flow_share_pct"
                ],
                target,
            )
        )

        data[
            f"demand_core_{target}pct"
        ] = (
            data[
                "flow_rank"
            ]
            <= cutoff_rank
        )

    return data


def add_flow_rankings(
    gdf,
    value_col,
    group_col=None,
):

    if group_col is None:

        ranked = rank_flow_group(
            gdf,
            value_col,
        )

        return gpd.GeoDataFrame(
            ranked,
            geometry="geometry",
            crs=gdf.crs,
        )

    outputs = []

    for period, group in (
        gdf.groupby(
            group_col,
            sort=False,
        )
    ):

        ranked = rank_flow_group(
            group,
            value_col,
        )

        outputs.append(
            ranked
        )

    result = pd.concat(
        outputs,
        ignore_index=True,
    )

    return gpd.GeoDataFrame(
        result,
        geometry="geometry",
        crs=gdf.crs,
    )


# ============================================================
# PERIOD-SPECIFIC ZONE PRODUCTION / ATTRACTION
# ============================================================

def build_zone_period_layer(
    zones,
    od,
    period_col,
    period,
    value_col,
):

    subset = od.loc[
        od[
            period_col
        ]
        == period
    ].copy()

    production = (
        subset.groupby(
            "origin_zone_id"
        )[
            value_col
        ]
        .sum()
        .rename(
            "production_trips"
        )
    )

    attraction = (
        subset.groupby(
            "destination_zone_id"
        )[
            value_col
        ]
        .sum()
        .rename(
            "attraction_trips"
        )
    )

    result = zones.copy()

    result = result.merge(
        production,
        left_on="zone_id",
        right_index=True,
        how="left",
    )

    result = result.merge(
        attraction,
        left_on="zone_id",
        right_index=True,
        how="left",
    )

    result[
        "production_trips"
    ] = (
        result[
            "production_trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    result[
        "attraction_trips"
    ] = (
        result[
            "attraction_trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    result[
        "net_attraction_trips"
    ] = (
        result[
            "attraction_trips"
        ]
        -
        result[
            "production_trips"
        ]
    )

    result[
        "production_density_per_km2"
    ] = (
        result[
            "production_trips"
        ]
        /
        result[
            "area_km2"
        ]
    )

    result[
        "attraction_density_per_km2"
    ] = (
        result[
            "attraction_trips"
        ]
        /
        result[
            "area_km2"
        ]
    )

    total = (
        result[
            "production_trips"
        ]
        .sum()
    )

    result[
        "production_share_pct"
    ] = (
        result[
            "production_trips"
        ]
        /
        total
        * 100
    )

    result[
        "attraction_share_pct"
    ] = (
        result[
            "attraction_trips"
        ]
        /
        total
        * 100
    )

    result[
        "period"
    ] = period

    return result


# ============================================================
# TEMPORAL REVERSAL PAIRS
#
# Find unordered zone pairs where:
#
# direction A → B is AM-specialized
# and
# reverse B → A is PM-specialized.
# ============================================================

def find_temporal_reversal_pairs(
    contrasts,
    n=10,
):

    data = contrasts.copy()

    data[
        "origin_zone_id"
    ] = (
        data[
            "origin_zone_id"
        ]
        .astype("string")
    )

    data[
        "destination_zone_id"
    ] = (
        data[
            "destination_zone_id"
        ]
        .astype("string")
    )

    lookup = (
        data.set_index(
            [
                "origin_zone_id",
                "destination_zone_id",
            ]
        )
    )

    candidates = []

    seen = set()

    for row in (
        data.itertuples(
            index=False
        )
    ):

        origin = (
            row.origin_zone_id
        )

        destination = (
            row.destination_zone_id
        )

        pair_key = tuple(
            sorted(
                [
                    origin,
                    destination,
                ]
            )
        )

        if pair_key in seen:

            continue

        reverse_key = (
            destination,
            origin,
        )

        if (
            reverse_key
            not in lookup.index
        ):

            continue

        reverse = (
            lookup.loc[
                reverse_key
            ]
        )

        # ----------------------------------------------------
        # Direction row is AM-specialized,
        # reverse is PM-specialized.
        # ----------------------------------------------------

        if (
            row.am_minus_pm_share_pp > 0
            and
            reverse[
                "pm_minus_am_share_pp"
            ] > 0
        ):

            am_origin = origin
            am_destination = destination

            pm_origin = destination
            pm_destination = origin

            am_specialization = (
                row.am_minus_pm_share_pp
            )

            pm_specialization = (
                reverse[
                    "pm_minus_am_share_pp"
                ]
            )

            am_direction_trips = (
                row.total_common_window_trips
            )

            pm_direction_trips = (
                reverse[
                    "total_common_window_trips"
                ]
            )

        # ----------------------------------------------------
        # Reverse orientation
        # ----------------------------------------------------

        elif (
            row.pm_minus_am_share_pp > 0
            and
            reverse[
                "am_minus_pm_share_pp"
            ] > 0
        ):

            am_origin = destination
            am_destination = origin

            pm_origin = origin
            pm_destination = destination

            am_specialization = (
                reverse[
                    "am_minus_pm_share_pp"
                ]
            )

            pm_specialization = (
                row.pm_minus_am_share_pp
            )

            am_direction_trips = (
                reverse[
                    "total_common_window_trips"
                ]
            )

            pm_direction_trips = (
                row.total_common_window_trips
            )

        else:

            continue

        candidates.append(
            {
                "zone_pair":
                    (
                        f"{pair_key[0]}"
                        f"↔"
                        f"{pair_key[1]}"
                    ),

                "am_origin_zone_id":
                    am_origin,

                "am_destination_zone_id":
                    am_destination,

                "pm_origin_zone_id":
                    pm_origin,

                "pm_destination_zone_id":
                    pm_destination,

                "am_specialization_pp":
                    am_specialization,

                "pm_specialization_pp":
                    pm_specialization,

                "reversal_score":
                    (
                        am_specialization
                        +
                        pm_specialization
                    ),

                "am_direction_total_trips":
                    am_direction_trips,

                "pm_direction_total_trips":
                    pm_direction_trips,
            }
        )

        seen.add(
            pair_key
        )

    result = (
        pd.DataFrame(
            candidates
        )
        .sort_values(
            [
                "reversal_score",
                "am_direction_total_trips",
                "pm_direction_total_trips",
            ],
            ascending=[
                False,
                False,
                False,
            ],
        )
        .head(n)
        .reset_index(
            drop=True
        )
    )

    result.insert(
        0,
        "reversal_rank",
        np.arange(
            1,
            len(result) + 1,
        )
    )

    return result


# ============================================================
# REVERSAL FLOW GEOMETRY
# ============================================================

def build_reversal_flow_layer(
    reversal_pairs,
    contrasts,
    zones,
):

    contrast_lookup = (
        contrasts.set_index(
            [
                "origin_zone_id",
                "destination_zone_id",
            ]
        )
    )

    rows = []

    for pair in (
        reversal_pairs.itertuples(
            index=False
        )
    ):

        directions = [
            (
                "AM-specialized direction",
                pair.am_origin_zone_id,
                pair.am_destination_zone_id,
                pair.am_specialization_pp,
            ),
            (
                "PM-specialized direction",
                pair.pm_origin_zone_id,
                pair.pm_destination_zone_id,
                pair.pm_specialization_pp,
            ),
        ]

        for (
            direction_type,
            origin,
            destination,
            specialization,
        ) in directions:

            source = contrast_lookup.loc[
                (
                    origin,
                    destination,
                )
            ]

            rows.append(
                {
                    "reversal_rank":
                        pair.reversal_rank,

                    "zone_pair":
                        pair.zone_pair,

                    "direction_type":
                        direction_type,

                    "origin_zone_id":
                        origin,

                    "destination_zone_id":
                        destination,

                    "specialization_pp":
                        specialization,

                    "reversal_score":
                        pair.reversal_score,

                    "am_trips":
                        source[
                            "am_trips"
                        ],

                    "pm_trips":
                        source[
                            "pm_trips"
                        ],

                    "offpeak_trips":
                        source[
                            "offpeak_trips"
                        ],

                    "am_share_pct":
                        source[
                            "am_share_pct"
                        ],

                    "pm_share_pct":
                        source[
                            "pm_share_pct"
                        ],

                    "offpeak_share_pct":
                        source[
                            "offpeak_share_pct"
                        ],
                }
            )

    df = pd.DataFrame(
        rows
    )

    return build_flow_lines(
        df,
        zones,
        value_col="specialization_pp",
    )


# ============================================================
# SAVE LAYER
# ============================================================

def save_layer(
    gdf,
    layer_name,
):

    gdf.to_file(
        OUTPUT_GPKG,
        layer=layer_name,
        driver="GPKG",
    )

    print(
        f"Saved layer: {layer_name}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 2 — GIS PREPARATION"
    )

    print(
        "=" * 110
    )

    zones = load_zones()

    all_day = pd.read_parquet(
        ALL_DAY_FILE
    )

    conventional = pd.read_parquet(
        CONVENTIONAL_FILE
    )

    empirical = pd.read_parquet(
        EMPIRICAL_FILE
    )

    contrasts = pd.read_parquet(
        CONTRAST_FILE
    )

    # ========================================================
    # REMOVE OLD PACKAGE
    # ========================================================

    if OUTPUT_GPKG.exists():

        OUTPUT_GPKG.unlink()

    # ========================================================
    # BASE ZONES
    # ========================================================

    save_layer(
        zones,
        "zones",
    )

    # ========================================================
    # ALL-DAY ZONE INTENSITY
    # ========================================================

    all_day_intensity = pd.read_csv(
        ALL_DAY_INTENSITY_FILE,
        dtype={
            "zone_id":
                "string",
        },
    )

    zones_all_day = zones.merge(
        all_day_intensity[
            [
                "zone_id",
                "production_trips",
                "attraction_trips",
                "production_share_pct",
                "attraction_share_pct",
                "net_attraction_trips",
                "production_density_trips_per_km2",
                "attraction_density_trips_per_km2",
            ]
        ],
        on="zone_id",
        how="left",
        validate="one_to_one",
    )

    save_layer(
        zones_all_day,
        "zones_all_day",
    )

    # ========================================================
    # ALL-DAY FLOWS
    # ========================================================

    all_day_flows = (
        build_flow_lines(
            all_day,
            zones,
            value_col="system_trips",
        )
    )

    all_day_flows = (
        add_flow_rankings(
            all_day_flows,
            value_col="system_trips",
        )
    )

    all_day_flows[
        "period"
    ] = "All day"

    save_layer(
        all_day_flows,
        "flows_all_day",
    )

    # ========================================================
    # CONVENTIONAL TEMPORAL FLOWS + ZONES
    # ========================================================

    conventional_flows = (
        build_flow_lines(
            conventional,
            zones,
            value_col="system_trips",
        )
    )

    conventional_flows = (
        add_flow_rankings(
            conventional_flows,
            value_col="system_trips",
            group_col="conventional_period",
        )
    )

    conventional_layers = {
        "AM peak":
            "am_peak",

        "PM peak":
            "pm_peak",

        "Off-peak":
            "offpeak",
    }

    for period, suffix in (
        conventional_layers.items()
    ):

        flow_subset = (
            conventional_flows.loc[
                conventional_flows[
                    "conventional_period"
                ]
                == period
            ]
            .copy()
        )

        save_layer(
            flow_subset,
            f"flows_{suffix}",
        )

        zone_period = (
            build_zone_period_layer(
                zones,
                conventional,
                period_col="conventional_period",
                period=period,
                value_col="system_trips",
            )
        )

        save_layer(
            zone_period,
            f"zones_{suffix}",
        )

    # ========================================================
    # EMPIRICAL TEMPORAL FLOWS + ZONES
    # ========================================================

    empirical_flows = (
        build_flow_lines(
            empirical,
            zones,
            value_col="system_trips",
        )
    )

    empirical_flows = (
        add_flow_rankings(
            empirical_flows,
            value_col="system_trips",
            group_col="empirical_period",
        )
    )

    empirical_layers = {
        "Empirical peak":
            "empirical_peak",

        "Empirical off-peak":
            "empirical_offpeak",
    }

    for period, suffix in (
        empirical_layers.items()
    ):

        flow_subset = (
            empirical_flows.loc[
                empirical_flows[
                    "empirical_period"
                ]
                == period
            ]
            .copy()
        )

        save_layer(
            flow_subset,
            f"flows_{suffix}",
        )

        zone_period = (
            build_zone_period_layer(
                zones,
                empirical,
                period_col="empirical_period",
                period=period,
                value_col="system_trips",
            )
        )

        save_layer(
            zone_period,
            f"zones_{suffix}",
        )

    # ========================================================
    # TEMPORAL DIRECTION-REVERSAL PAIRS
    # ========================================================

    reversal_pairs = (
        find_temporal_reversal_pairs(
            contrasts,
            n=10,
        )
    )

    reversal_pairs.to_csv(
        TABLE_DIR
        / "top_temporal_direction_reversal_pairs_2024.csv",
        index=False,
    )

    reversal_flows = (
        build_reversal_flow_layer(
            reversal_pairs,
            contrasts,
            zones,
        )
    )

    save_layer(
        reversal_flows,
        "selected_temporal_reversals",
    )

    # ========================================================
    # MAP FILTER SUMMARY
    # ========================================================

    summary_rows = []

    map_layers = [
        (
            "All day",
            all_day_flows,
            "system_trips",
        ),
    ]

    for period, suffix in (
        conventional_layers.items()
    ):

        subset = (
            conventional_flows.loc[
                conventional_flows[
                    "conventional_period"
                ]
                == period
            ]
        )

        map_layers.append(
            (
                period,
                subset,
                "system_trips",
            )
        )

    for label, data, value_col in (
        map_layers
    ):

        summary_rows.append(
            {
                "period":
                    label,

                "interzonal_flows":
                    len(data),

                "total_interzonal_trips":
                    int(
                        data[
                            value_col
                        ].sum()
                    ),

                "top_1pct_pair_count":
                    int(
                        data[
                            "top_1pct_pairs"
                        ].sum()
                    ),

                "top_2pct_pair_count":
                    int(
                        data[
                            "top_2pct_pairs"
                        ].sum()
                    ),

                "top_5pct_pair_count":
                    int(
                        data[
                            "top_5pct_pairs"
                        ].sum()
                    ),

                "demand_core_10pct_count":
                    int(
                        data[
                            "demand_core_10pct"
                        ].sum()
                    ),

                "demand_core_25pct_count":
                    int(
                        data[
                            "demand_core_25pct"
                        ].sum()
                    ),

                "demand_core_50pct_count":
                    int(
                        data[
                            "demand_core_50pct"
                        ].sum()
                    ),
            }
        )

    summary = pd.DataFrame(
        summary_rows
    )

    summary.to_csv(
        TABLE_DIR
        / "gis_flow_filter_summary.csv",
        index=False,
    )

    # ========================================================
    # READ-BACK
    # ========================================================

    readback = gpd.read_file(
        OUTPUT_GPKG,
        layer="flows_all_day",
    )

    assert (
        len(readback)
        ==
        len(all_day_flows)
    )

    assert (
        readback.crs.to_epsg()
        == 3003
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "GIS FLOW FILTER SUMMARY"
    )

    print(
        "=" * 110
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "TOP TEMPORAL DIRECTION-REVERSAL PAIRS"
    )

    print(
        "=" * 110
    )

    print(
        reversal_pairs.round(
            {
                "am_specialization_pp":
                    4,

                "pm_specialization_pp":
                    4,

                "reversal_score":
                    4,
            }
        ).to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION:"
        "\n- All GIS geometries use EPSG:3003."
        "\n- Inter-zonal flows are represented by centroid-to-centroid lines."
        "\n- Intra-zonal trips are not converted to zero-length lines."
        "\n- All flow layers retain the complete inter-zonal network."
        "\n- Rank, cumulative demand share, and percentile filters are stored as attributes."
        "\n- demand_core_25pct is the recommended initial QGIS filter."
        "\n- Conventional and empirical temporal layers are both retained."
        "\n- Production/attraction polygon layers are included."
        "\n- Selected temporal reversals are derived from AM/PM specialization, not chosen manually."
        "\n- GeoPackage read-back validation passed."
    )

    print(
        f"\nGeoPackage saved -> "
        f"{OUTPUT_GPKG}"
    )


if __name__ == "__main__":
    main()