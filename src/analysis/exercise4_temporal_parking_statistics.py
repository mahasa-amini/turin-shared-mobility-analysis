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

OUTPUT_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "gis"
    / "exercise4_temporal_parking_layers.gpkg"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_4"
    / "temporal_parking"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_4"
    / "parking"
)

TABLE_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_GPKG.parent.mkdir(parents=True, exist_ok=True)


OPERATORS = [
    "bird",
    "lime",
    "voi",
]

PERIODS = [
    "AM peak",
    "PM peak",
    "Off-peak",
]


# =============================================================================
# LOAD
# =============================================================================

def load_zones():

    zones = gpd.read_file(
        ZONE_GPKG,
        layer="zones",
    )

    zones["zone_id"] = (
        zones["zone_id"]
        .astype("string")
    )

    assert len(zones) == 94
    assert zones.crs.to_epsg() == 3003

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
            "parking_start_time_local",
            "parking_start_hour",
            "conventional_period",
        ],
    )

    df[
        "destination_zone_id"
    ] = (
        df[
            "destination_zone_id"
        ]
        .astype("string")
    )

    df[
        "conventional_period"
    ] = (
        df[
            "conventional_period"
        ]
        .astype("string")
    )

    assert df[
        "parking_event_uid"
    ].is_unique

    return df


# =============================================================================
# VALIDATE PERIOD ASSIGNMENT
# =============================================================================

def validate_periods(df):

    hour = df[
        "parking_start_hour"
    ]

    expected = pd.Series(
        "Off-peak",
        index=df.index,
        dtype="string",
    )

    expected.loc[
        hour.isin([7, 8, 9])
    ] = "AM peak"

    expected.loc[
        hour.isin([16, 17, 18, 19])
    ] = "PM peak"

    assert (
        expected
        ==
        df[
            "conventional_period"
        ]
    ).all()


# =============================================================================
# AGGREGATION
# =============================================================================

def aggregate_zone_period(
    df,
    scope,
):

    grouped = (
        df.groupby(
            [
                "conventional_period",
                "destination_zone_id",
            ],
            observed=True,
        )
    )

    stats = grouped.agg(
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

        std_parking_min=(
            "parking_duration_min",
            "std",
        ),
    ).reset_index()

    stats = stats.rename(
        columns={
            "destination_zone_id":
                "zone_id",
        }
    )

    stats[
        "mean_parking_h"
    ] = (
        stats[
            "mean_parking_min"
        ]
        / 60
    )

    stats[
        "median_parking_h"
    ] = (
        stats[
            "median_parking_min"
        ]
        / 60
    )

    stats[
        "p90_parking_h"
    ] = (
        stats[
            "p90_parking_min"
        ]
        / 60
    )

    stats[
        "analysis_scope"
    ] = scope

    return stats


# =============================================================================
# PERIOD SUMMARY
# =============================================================================

def period_summary(
    df,
    scope,
):

    rows = []

    for period in PERIODS:

        subset = df.loc[
            df[
                "conventional_period"
            ]
            == period
        ]

        gap = subset[
            "parking_duration_min"
        ]

        rows.append(
            {
                "analysis_scope":
                    scope,

                "period":
                    period,

                "parking_events":
                    len(subset),

                "zones_with_events":
                    subset[
                        "destination_zone_id"
                    ]
                    .nunique(),

                "mean_parking_h":
                    gap.mean() / 60,

                "median_parking_h":
                    gap.median() / 60,

                "p75_parking_h":
                    gap.quantile(0.75) / 60,

                "p90_parking_h":
                    gap.quantile(0.90) / 60,

                "p95_parking_h":
                    gap.quantile(0.95) / 60,
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# SAMPLE SIZE BY PERIOD
# =============================================================================

def sample_size_diagnostics(
    stats,
    scope,
):

    rows = []

    for period in PERIODS:

        subset = stats.loc[
            stats[
                "conventional_period"
            ]
            == period
        ].copy()

        counts = subset[
            "parking_events"
        ]

        rows.append(
            {
                "analysis_scope":
                    scope,

                "period":
                    period,

                "zones_with_events":
                    len(subset),

                "min_events":
                    int(
                        counts.min()
                    ),

                "p10_events":
                    counts.quantile(
                        0.10
                    ),

                "p25_events":
                    counts.quantile(
                        0.25
                    ),

                "median_events":
                    counts.median(),

                "p75_events":
                    counts.quantile(
                        0.75
                    ),

                "max_events":
                    int(
                        counts.max()
                    ),

                "zones_lt_10":
                    int(
                        (
                            counts < 10
                        ).sum()
                    ),

                "zones_lt_30":
                    int(
                        (
                            counts < 30
                        ).sum()
                    ),

                "zones_lt_100":
                    int(
                        (
                            counts < 100
                        ).sum()
                    ),
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# PERIOD CHANGE TABLE
# =============================================================================

def build_period_comparison(
    stats,
):

    mean_pivot = (
        stats.pivot(
            index="zone_id",
            columns="conventional_period",
            values="mean_parking_h",
        )
        .reset_index()
    )

    count_pivot = (
        stats.pivot(
            index="zone_id",
            columns="conventional_period",
            values="parking_events",
        )
        .reset_index()
    )

    mean_pivot.columns.name = None
    count_pivot.columns.name = None

    mean_pivot = mean_pivot.rename(
        columns={
            "AM peak":
                "am_mean_parking_h",

            "PM peak":
                "pm_mean_parking_h",

            "Off-peak":
                "offpeak_mean_parking_h",
        }
    )

    count_pivot = count_pivot.rename(
        columns={
            "AM peak":
                "am_events",

            "PM peak":
                "pm_events",

            "Off-peak":
                "offpeak_events",
        }
    )

    comparison = mean_pivot.merge(
        count_pivot,
        on="zone_id",
        how="outer",
        validate="one_to_one",
    )

    comparison[
        "pm_minus_am_h"
    ] = (
        comparison[
            "pm_mean_parking_h"
        ]
        -
        comparison[
            "am_mean_parking_h"
        ]
    )

    comparison[
        "am_minus_offpeak_h"
    ] = (
        comparison[
            "am_mean_parking_h"
        ]
        -
        comparison[
            "offpeak_mean_parking_h"
        ]
    )

    comparison[
        "pm_minus_offpeak_h"
    ] = (
        comparison[
            "pm_mean_parking_h"
        ]
        -
        comparison[
            "offpeak_mean_parking_h"
        ]
    )

    return comparison


# =============================================================================
# GIS
# =============================================================================

def save_period_layers(
    zones,
    stats,
    prefix,
):

    for period in PERIODS:

        period_stats = stats.loc[
            stats[
                "conventional_period"
            ]
            == period
        ].copy()

        layer = zones.merge(
            period_stats,
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

        layer_suffix = {
            "AM peak":
                "am_peak",

            "PM peak":
                "pm_peak",

            "Off-peak":
                "offpeak",
        }[
            period
        ]

        layer_name = (
            f"{prefix}_"
            f"{layer_suffix}"
        )

        layer.to_file(
            OUTPUT_GPKG,
            layer=layer_name,
            driver="GPKG",
        )

        print(
            f"Saved layer: "
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
        "EXERCISE 4 — TEMPORAL PARKING STATISTICS"
    )

    print(
        "=" * 115
    )

    zones = load_zones()

    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()

    all_data = []

    period_summaries = []
    sample_summaries = []

    operator_stats = {}

    # =========================================================================
    # OPERATOR-SPECIFIC
    # =========================================================================

    for operator in OPERATORS:

        print(
            f"\nProcessing "
            f"{operator.upper()}..."
        )

        df = load_parking(
            operator
        )

        validate_periods(
            df
        )

        stats = aggregate_zone_period(
            df,
            operator,
        )

        operator_stats[
            operator
        ] = stats

        all_data.append(
            df
        )

        period_summaries.append(
            period_summary(
                df,
                operator,
            )
        )

        sample_summaries.append(
            sample_size_diagnostics(
                stats,
                operator,
            )
        )

        stats.to_csv(
            TABLE_DIR
            / (
                f"parking_by_zone_period_"
                f"{operator}_2024.csv"
            ),
            index=False,
        )

        save_period_layers(
            zones,
            stats,
            f"parking_{operator}",
        )

    # =========================================================================
    # SYSTEM POOLED
    # =========================================================================

    combined = pd.concat(
        all_data,
        ignore_index=True,
    )

    system_stats = aggregate_zone_period(
        combined,
        "system_pooled",
    )

    period_summaries.append(
        period_summary(
            combined,
            "system_pooled",
        )
    )

    sample_summaries.append(
        sample_size_diagnostics(
            system_stats,
            "system_pooled",
        )
    )

    system_stats.to_csv(
        TABLE_DIR
        / "parking_by_zone_period_system_pooled_2024.csv",
        index=False,
    )

    save_period_layers(
        zones,
        system_stats,
        "parking_system",
    )

    # =========================================================================
    # PERIOD DIFFERENCES
    # =========================================================================

    system_comparison = (
        build_period_comparison(
            system_stats
        )
    )

    system_comparison = (
        zones[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .merge(
            system_comparison,
            on="zone_id",
            how="left",
            validate="one_to_one",
        )
    )

    system_comparison.to_csv(
        TABLE_DIR
        / "system_parking_period_comparison_by_zone_2024.csv",
        index=False,
    )

    # =========================================================================
    # SAVE AUDIT TABLES
    # =========================================================================

    period_summary_df = (
        pd.concat(
            period_summaries,
            ignore_index=True,
        )
    )

    sample_summary_df = (
        pd.concat(
            sample_summaries,
            ignore_index=True,
        )
    )

    period_summary_df.to_csv(
        AUDIT_DIR
        / "temporal_parking_period_summary_2024.csv",
        index=False,
    )

    sample_summary_df.to_csv(
        AUDIT_DIR
        / "temporal_parking_sample_size_summary_2024.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL OUTPUT
    # =========================================================================

    print(
        "\n"
        + "=" * 115
    )

    print(
        "PARKING DURATION BY PERIOD"
    )

    print(
        "=" * 115
    )

    print(
        period_summary_df
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
        "ZONE SAMPLE-SIZE BY PERIOD"
    )

    print(
        "=" * 115
    )

    print(
        sample_summary_df
        .round(1)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "SYSTEM ZONES WITH LARGEST PM - AM DIFFERENCES"
    )

    print(
        "=" * 115
    )

    eligible = (
        system_comparison.loc[
            (
                system_comparison[
                    "am_events"
                ]
                >= 30
            )
            &
            (
                system_comparison[
                    "pm_events"
                ]
                >= 30
            )
        ]
        .copy()
    )

    print(
        eligible.sort_values(
            "pm_minus_am_h",
            ascending=False,
        )[
            [
                "zone_id",
                "zone_name",
                "am_events",
                "pm_events",
                "am_mean_parking_h",
                "pm_mean_parking_h",
                "pm_minus_am_h",
            ]
        ]
        .head(15)
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
        "SYSTEM ZONES WITH LARGEST AM - PM DIFFERENCES"
    )

    print(
        "=" * 115
    )

    print(
        eligible.sort_values(
            "pm_minus_am_h",
            ascending=True,
        )[
            [
                "zone_id",
                "zone_name",
                "am_events",
                "pm_events",
                "am_mean_parking_h",
                "pm_mean_parking_h",
                "pm_minus_am_h",
            ]
        ]
        .head(15)
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION:"
        "\n- Parking period is defined by the START of parking."
        "\n- Parking start = end time of the preceding trip."
        "\n- AM = 07:00–09:59."
        "\n- PM = 16:00–19:59."
        "\n- Off-peak = all remaining hours."
        "\n- Period definitions exactly match Exercise 2."
        "\n- System pooled statistics are event-weighted."
        "\n- No OD flows have been plotted yet."
    )

    print(
        f"\nGeoPackage -> "
        f"{OUTPUT_GPKG}"
    )


if __name__ == "__main__":
    main()