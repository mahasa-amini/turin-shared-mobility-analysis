from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PARKING_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "parking"
)

ZONE_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "zoning"
    / "torino_statistical_zones.gpkg"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_4"
    / "parking_by_zone"
)

GIS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "gis"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_4"
    / "parking"
)

for directory in [
    TABLE_DIR,
    GIS_DIR,
    AUDIT_DIR,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


OUTPUT_GPKG = (
    GIS_DIR
    / "exercise4_parking_layers.gpkg"
)

OPERATORS = [
    "bird",
    "lime",
    "voi",
]


# =============================================================================
# LOAD
# =============================================================================

def load_zones():

    zones = gpd.read_file(
        ZONE_GPKG,
        layer="zones",
    )

    assert len(zones) == 94
    assert zones.crs.to_epsg() == 3003

    zones["zone_id"] = (
        zones["zone_id"]
        .astype("string")
    )

    assert zones["zone_id"].is_unique

    return zones


def load_parking(operator):

    path = (
        PARKING_DIR
        / f"{operator}_parking_events_2024.parquet"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_parquet(
        path,
        columns=[
            "operator",
            "parking_event_uid",
            "destination_zone_id",
            "parking_duration_min",
            "parking_duration_h",
            "relocation_distance_m",
            "parking_start_time_local",
            "conventional_period",
        ],
    )

    df["destination_zone_id"] = (
        df["destination_zone_id"]
        .astype("string")
    )

    assert df["parking_event_uid"].is_unique
    assert df["parking_duration_min"].gt(0).all()
    assert df["parking_duration_min"].le(10080).all()
    assert df["relocation_distance_m"].le(100).all()

    return df


# =============================================================================
# ZONE AGGREGATION
# =============================================================================

def aggregate_zone_statistics(
    df,
    scope,
):

    grouped = (
        df.groupby(
            "destination_zone_id",
            observed=True,
        )
    )

    result = grouped.agg(
        parking_events=(
            "parking_event_uid",
            "count",
        ),

        mean_parking_min=(
            "parking_duration_min",
            "mean",
        ),

        median_parking_min=(
            "parking_duration_min",
            "median",
        ),

        std_parking_min=(
            "parking_duration_min",
            "std",
        ),

        p25_parking_min=(
            "parking_duration_min",
            lambda x:
                x.quantile(0.25),
        ),

        p75_parking_min=(
            "parking_duration_min",
            lambda x:
                x.quantile(0.75),
        ),

        p90_parking_min=(
            "parking_duration_min",
            lambda x:
                x.quantile(0.90),
        ),

        p95_parking_min=(
            "parking_duration_min",
            lambda x:
                x.quantile(0.95),
        ),

        max_parking_min=(
            "parking_duration_min",
            "max",
        ),
    ).reset_index()

    result = result.rename(
        columns={
            "destination_zone_id":
                "zone_id",
        }
    )

    result[
        "mean_parking_h"
    ] = (
        result[
            "mean_parking_min"
        ]
        / 60
    )

    result[
        "median_parking_h"
    ] = (
        result[
            "median_parking_min"
        ]
        / 60
    )

    result[
        "p90_parking_h"
    ] = (
        result[
            "p90_parking_min"
        ]
        / 60
    )

    result[
        "coefficient_of_variation"
    ] = (
        result[
            "std_parking_min"
        ]
        /
        result[
            "mean_parking_min"
        ]
    )

    # ---------------------------------------------------------
    # Long-parking shares
    # ---------------------------------------------------------

    thresholds = {
        "over_6h": 360,
        "over_12h": 720,
        "over_24h": 1440,
        "over_48h": 2880,
    }

    for label, threshold in thresholds.items():

        share = (
            df.assign(
                flag=(
                    df[
                        "parking_duration_min"
                    ]
                    > threshold
                )
            )
            .groupby(
                "destination_zone_id",
                observed=True,
            )[
                "flag"
            ]
            .mean()
            .mul(100)
            .rename(
                f"share_{label}_pct"
            )
            .reset_index()
            .rename(
                columns={
                    "destination_zone_id":
                        "zone_id",
                }
            )
        )

        result = result.merge(
            share,
            on="zone_id",
            how="left",
            validate="one_to_one",
        )

    result[
        "analysis_scope"
    ] = scope

    return result


# =============================================================================
# OPERATOR CONTRIBUTION TO POOLED SYSTEM
# =============================================================================

def build_operator_composition(
    combined,
):

    counts = (
        combined.groupby(
            [
                "destination_zone_id",
                "operator",
            ],
            observed=True,
        )
        .size()
        .rename(
            "parking_events"
        )
        .reset_index()
    )

    pivot = (
        counts.pivot(
            index="destination_zone_id",
            columns="operator",
            values="parking_events",
        )
        .fillna(0)
        .reset_index()
    )

    pivot.columns.name = None

    for operator in OPERATORS:

        if operator not in pivot.columns:
            pivot[operator] = 0

    pivot = pivot.rename(
        columns={
            "destination_zone_id":
                "zone_id",

            "bird":
                "bird_parking_events",

            "lime":
                "lime_parking_events",

            "voi":
                "voi_parking_events",
        }
    )

    event_cols = [
        "bird_parking_events",
        "lime_parking_events",
        "voi_parking_events",
    ]

    for col in event_cols:
        pivot[col] = (
            pivot[col]
            .astype("int64")
        )

    pivot[
        "system_parking_events"
    ] = (
        pivot[
            event_cols
        ]
        .sum(axis=1)
    )

    for operator in OPERATORS:

        pivot[
            f"{operator}_event_share_pct"
        ] = np.where(
            pivot[
                "system_parking_events"
            ] > 0,

            pivot[
                f"{operator}_parking_events"
            ]
            /
            pivot[
                "system_parking_events"
            ]
            * 100,

            np.nan,
        )

    pivot[
        "operators_present"
    ] = (
        (
            pivot[
                event_cols
            ]
            > 0
        )
        .sum(axis=1)
    )

    return pivot


# =============================================================================
# SAMPLE-SIZE DIAGNOSTICS
# =============================================================================

def sample_size_summary(
    table,
    scope,
):

    counts = (
        table[
            "parking_events"
        ]
    )

    return {
        "analysis_scope":
            scope,

        "zones_with_events":
            len(table),

        "min_events_per_zone":
            int(counts.min()),

        "p10_events_per_zone":
            counts.quantile(0.10),

        "p25_events_per_zone":
            counts.quantile(0.25),

        "median_events_per_zone":
            counts.median(),

        "p75_events_per_zone":
            counts.quantile(0.75),

        "p90_events_per_zone":
            counts.quantile(0.90),

        "max_events_per_zone":
            int(counts.max()),

        "zones_lt_10_events":
            int((counts < 10).sum()),

        "zones_lt_30_events":
            int((counts < 30).sum()),

        "zones_lt_100_events":
            int((counts < 100).sum()),
    }


# =============================================================================
# TOP / BOTTOM ZONES
# =============================================================================

def rank_zone_means(
    table,
    scope,
    n=10,
):

    eligible = table.loc[
        table[
            "parking_events"
        ]
        >= 30
    ].copy()

    highest = (
        eligible.sort_values(
            [
                "mean_parking_min",
                "parking_events",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(n)
        .copy()
    )

    highest[
        "ranking_type"
    ] = "highest_mean"

    lowest = (
        eligible.sort_values(
            [
                "mean_parking_min",
                "parking_events",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .head(n)
        .copy()
    )

    lowest[
        "ranking_type"
    ] = "lowest_mean"

    result = pd.concat(
        [
            highest,
            lowest,
        ],
        ignore_index=True,
    )

    result[
        "analysis_scope"
    ] = scope

    return result


# =============================================================================
# GIS LAYER
# =============================================================================

def attach_to_zones(
    zones,
    stats,
):

    layer = zones.merge(
        stats,
        on="zone_id",
        how="left",
        validate="one_to_one",
    )

    layer[
        "has_parking_data"
    ] = (
        layer[
            "parking_events"
        ]
        .notna()
    )

    layer[
        "parking_events"
    ] = (
        layer[
            "parking_events"
        ]
        .fillna(0)
        .astype("int64")
    )

    return layer


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
        f"Saved GIS layer: "
        f"{layer_name}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 115
    )

    print(
        "EXERCISE 4 — PARKING DURATION BY OFFICIAL TORINO ZONE"
    )

    print(
        "=" * 115
    )

    zones = load_zones()

    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()

    operator_data = {}
    operator_stats = {}

    sample_rows = []
    ranking_tables = []

    # =========================================================================
    # OPERATOR-SPECIFIC
    # =========================================================================

    for operator in OPERATORS:

        print(
            f"\nProcessing "
            f"{operator.upper()}..."
        )

        data = load_parking(
            operator
        )

        stats = aggregate_zone_statistics(
            data,
            scope=operator,
        )

        operator_data[
            operator
        ] = data

        operator_stats[
            operator
        ] = stats

        stats.to_csv(
            TABLE_DIR
            / f"parking_by_zone_{operator}_2024.csv",
            index=False,
        )

        sample_rows.append(
            sample_size_summary(
                stats,
                operator,
            )
        )

        ranking_tables.append(
            rank_zone_means(
                stats,
                operator,
                n=10,
            )
        )

        layer = attach_to_zones(
            zones,
            stats,
        )

        save_layer(
            layer,
            f"parking_{operator}",
        )

    # =========================================================================
    # SYSTEM POOLED
    #
    # Event-weighted pooled mean.
    # Lime contributes substantially more observations.
    # =========================================================================

    combined = pd.concat(
        operator_data.values(),
        ignore_index=True,
    )

    system_stats = (
        aggregate_zone_statistics(
            combined,
            scope="system_pooled",
        )
    )

    composition = (
        build_operator_composition(
            combined
        )
    )

    system_stats = system_stats.merge(
        composition,
        on="zone_id",
        how="left",
        validate="one_to_one",
    )

    system_stats.to_csv(
        TABLE_DIR
        / "parking_by_zone_system_pooled_2024.csv",
        index=False,
    )

    sample_rows.append(
        sample_size_summary(
            system_stats,
            "system_pooled",
        )
    )

    ranking_tables.append(
        rank_zone_means(
            system_stats,
            "system_pooled",
            n=10,
        )
    )

    system_layer = attach_to_zones(
        zones,
        system_stats,
    )

    save_layer(
        system_layer,
        "parking_system_pooled",
    )

    # =========================================================================
    # CROSS-OPERATOR COMPARISON BY ZONE
    # =========================================================================

    comparison = (
        zones[
            [
                "zone_id",
                "zone_name",
                "area_km2",
            ]
        ]
        .copy()
    )

    for operator in OPERATORS:

        subset = (
            operator_stats[
                operator
            ][
                [
                    "zone_id",
                    "parking_events",
                    "mean_parking_h",
                    "median_parking_h",
                ]
            ]
            .rename(
                columns={
                    "parking_events":
                        f"{operator}_events",

                    "mean_parking_h":
                        f"{operator}_mean_h",

                    "median_parking_h":
                        f"{operator}_median_h",
                }
            )
        )

        comparison = comparison.merge(
            subset,
            on="zone_id",
            how="left",
            validate="one_to_one",
        )

    comparison[
        "operators_with_parking"
    ] = (
        comparison[
            [
                "bird_events",
                "lime_events",
                "voi_events",
            ]
        ]
        .notna()
        .sum(axis=1)
    )

    comparison.to_csv(
        TABLE_DIR
        / "parking_zone_cross_operator_comparison_2024.csv",
        index=False,
    )

    # =========================================================================
    # SAVE SUMMARIES
    # =========================================================================

    sample_summary = pd.DataFrame(
        sample_rows
    )

    rankings = pd.concat(
        ranking_tables,
        ignore_index=True,
    )

    sample_summary.to_csv(
        AUDIT_DIR
        / "parking_zone_sample_size_summary_2024.csv",
        index=False,
    )

    rankings.to_csv(
        TABLE_DIR
        / "parking_zone_high_low_rankings_2024.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL
    # =========================================================================

    pd.set_option(
        "display.max_columns",
        None
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "ZONE SAMPLE-SIZE DIAGNOSTICS"
    )

    print(
        "=" * 115
    )

    print(
        sample_summary.round(1)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP 10 HIGHEST-MEAN PARKING ZONES"
    )

    print(
        "=" * 115
    )

    highest = rankings.loc[
        rankings[
            "ranking_type"
        ]
        == "highest_mean"
    ].copy()

    highest = highest.merge(
        zones[
            [
                "zone_id",
                "zone_name",
            ]
        ],
        on="zone_id",
        how="left",
        validate="many_to_one",
    )

    print(
        highest[
            [
                "analysis_scope",
                "zone_id",
                "zone_name",
                "parking_events",
                "mean_parking_h",
                "median_parking_h",
                "p90_parking_h",
            ]
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP 10 LOWEST-MEAN PARKING ZONES"
    )

    print(
        "=" * 115
    )

    lowest = rankings.loc[
        rankings[
            "ranking_type"
        ]
        == "lowest_mean"
    ].copy()

    lowest = lowest.merge(
        zones[
            [
                "zone_id",
                "zone_name",
            ]
        ],
        on="zone_id",
        how="left",
        validate="many_to_one",
    )

    print(
        lowest[
            [
                "analysis_scope",
                "zone_id",
                "zone_name",
                "parking_events",
                "mean_parking_h",
                "median_parking_h",
                "p90_parking_h",
            ]
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
        "\n- Parking is assigned to the destination zone of the preceding trip."
        "\n- Arithmetic mean is retained because Exercise 4 explicitly asks for average parking duration."
        "\n- Median and upper quantiles are retained because parking duration is strongly right-skewed."
        "\n- Operator-specific statistics are primary."
        "\n- System pooled means are event-weighted and therefore influenced strongly by Lime."
        "\n- Zones with fewer than 30 events are excluded only from ranking tables, not from GIS layers."
        "\n- No zone is silently removed from the official 94-zone GIS layer."
        "\n- GIS layers are stored in EPSG:3003."
    )

    print(
        f"\nGeoPackage -> "
        f"{OUTPUT_GPKG}"
    )


if __name__ == "__main__":
    main()