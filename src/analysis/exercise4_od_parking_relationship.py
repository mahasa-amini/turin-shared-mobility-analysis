from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


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
    / "od_parking_relationship"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_4"
    / "parking"
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


PERIODS = {
    "AM peak": {
        "parking_layer":
            "parking_system_am_peak",

        "flow_layer":
            "flows_am_peak",
    },

    "PM peak": {
        "parking_layer":
            "parking_system_pm_peak",

        "flow_layer":
            "flows_pm_peak",
    },

    "Off-peak": {
        "parking_layer":
            "parking_system_offpeak",

        "flow_layer":
            "flows_offpeak",
    },
}


MIN_PARKING_EVENTS = 30


# =============================================================================
# LOAD ZONES
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

    return zones[
        [
            "zone_id",
            "zone_name",
        ]
    ].copy()


# =============================================================================
# PARKING
# =============================================================================

def load_parking(
    layer_name,
):

    gdf = gpd.read_file(
        PARKING_GPKG,
        layer=layer_name,
    )

    gdf["zone_id"] = (
        gdf["zone_id"]
        .astype("string")
    )

    return gdf[
        [
            "zone_id",
            "parking_events",
            "mean_parking_h",
            "median_parking_h",
            "p90_parking_h",
            "has_parking_data",
        ]
    ].copy()


# =============================================================================
# OD
# =============================================================================

def load_full_interzonal_flows(
    layer_name,
):

    flows = gpd.read_file(
        OD_GPKG,
        layer=layer_name,
    )

    flows[
        "origin_zone_id"
    ] = (
        flows[
            "origin_zone_id"
        ]
        .astype("string")
    )

    flows[
        "destination_zone_id"
    ] = (
        flows[
            "destination_zone_id"
        ]
        .astype("string")
    )

    flows[
        "system_trips"
    ] = (
        pd.to_numeric(
            flows[
                "system_trips"
            ],
            errors="coerce",
        )
    )

    # Explicitly keep inter-zonal flows only.
    flows = flows.loc[
        flows[
            "origin_zone_id"
        ]
        !=
        flows[
            "destination_zone_id"
        ]
    ].copy()

    assert (
        flows[
            "system_trips"
        ]
        >= 0
    ).all()

    return flows


def aggregate_od_by_zone(
    flows,
):

    departures = (
        flows.groupby(
            "origin_zone_id",
            observed=True,
        )[
            "system_trips"
        ]
        .sum()
        .rename(
            "interzonal_departures"
        )
        .reset_index()
        .rename(
            columns={
                "origin_zone_id":
                    "zone_id",
            }
        )
    )

    arrivals = (
        flows.groupby(
            "destination_zone_id",
            observed=True,
        )[
            "system_trips"
        ]
        .sum()
        .rename(
            "interzonal_arrivals"
        )
        .reset_index()
        .rename(
            columns={
                "destination_zone_id":
                    "zone_id",
            }
        )
    )

    od = departures.merge(
        arrivals,
        on="zone_id",
        how="outer",
        validate="one_to_one",
    )

    for col in [
        "interzonal_departures",
        "interzonal_arrivals",
    ]:

        od[col] = (
            od[col]
            .fillna(0)
        )

    od[
        "interzonal_endpoint_activity"
    ] = (
        od[
            "interzonal_departures"
        ]
        +
        od[
            "interzonal_arrivals"
        ]
    )

    od[
        "net_interzonal_inflow"
    ] = (
        od[
            "interzonal_arrivals"
        ]
        -
        od[
            "interzonal_departures"
        ]
    )

    total_endpoint_activity = (
        od[
            "interzonal_endpoint_activity"
        ]
        .sum()
    )

    od[
        "endpoint_activity_share_pct"
    ] = np.where(
        total_endpoint_activity > 0,

        od[
            "interzonal_endpoint_activity"
        ]
        /
        total_endpoint_activity
        * 100,

        np.nan,
    )

    return od


# =============================================================================
# CORRELATION
# =============================================================================

def correlation_row(
    df,
    period,
    demand_variable,
):

    subset = df[
        [
            demand_variable,
            "mean_parking_h",
        ]
    ].dropna()

    # Spearman: rank-based, primary.
    spearman = (
        subset[
            demand_variable
        ]
        .corr(
            subset[
                "mean_parking_h"
            ],
            method="spearman",
        )
    )

    # Supporting sensitivity:
    # Pearson using log-transformed demand.
    log_demand = np.log1p(
        subset[
            demand_variable
        ]
    )

    pearson_log = (
        log_demand.corr(
            subset[
                "mean_parking_h"
            ],
            method="pearson",
        )
    )

    return {
        "period":
            period,

        "demand_variable":
            demand_variable,

        "zones":
            len(subset),

        "spearman_rho":
            spearman,

        "pearson_log_demand_r":
            pearson_log,
    }


# =============================================================================
# DEMAND QUARTILES
# =============================================================================

def demand_quartile_summary(
    df,
    period,
):

    subset = df.loc[
        df[
            "eligible_for_primary_analysis"
        ]
    ].copy()

    # Ranking prevents qcut problems due to repeated demand values.
    ranked = (
        subset[
            "interzonal_endpoint_activity"
        ]
        .rank(
            method="first"
        )
    )

    subset[
        "demand_quartile"
    ] = pd.qcut(
        ranked,
        q=4,
        labels=[
            "Q1 lowest",
            "Q2",
            "Q3",
            "Q4 highest",
        ],
    )

    result = (
        subset.groupby(
            "demand_quartile",
            observed=True,
        )
        .agg(
            zones=(
                "zone_id",
                "count",
            ),

            mean_endpoint_activity=(
                "interzonal_endpoint_activity",
                "mean",
            ),

            mean_zone_parking_h=(
                "mean_parking_h",
                "mean",
            ),

            median_zone_parking_h=(
                "mean_parking_h",
                "median",
            ),

            median_event_parking_h=(
                "median_parking_h",
                "median",
            ),
        )
        .reset_index()
    )

    result.insert(
        0,
        "period",
        period,
    )

    return result


# =============================================================================
# EXTREME COMBINATIONS
# =============================================================================

def classify_zone_profiles(
    df,
    period,
):

    subset = df.loc[
        df[
            "eligible_for_primary_analysis"
        ]
    ].copy()

    demand_median = (
        subset[
            "interzonal_endpoint_activity"
        ]
        .median()
    )

    parking_median = (
        subset[
            "mean_parking_h"
        ]
        .median()
    )

    subset[
        "demand_level"
    ] = np.where(
        subset[
            "interzonal_endpoint_activity"
        ]
        >= demand_median,
        "High demand",
        "Low demand",
    )

    subset[
        "parking_level"
    ] = np.where(
        subset[
            "mean_parking_h"
        ]
        >= parking_median,
        "Long parking",
        "Short parking",
    )

    subset[
        "profile"
    ] = (
        subset[
            "demand_level"
        ]
        +
        " / "
        +
        subset[
            "parking_level"
        ]
    )

    

    return subset[
        [
            "period",
            "zone_id",
            "zone_name",
            "parking_events",
            "mean_parking_h",
            "median_parking_h",
            "interzonal_arrivals",
            "interzonal_departures",
            "interzonal_endpoint_activity",
            "net_interzonal_inflow",
            "profile",
        ]
    ]


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 115
    )

    print(
        "EXERCISE 4 — QUANTITATIVE OD × PARKING RELATIONSHIP"
    )

    print(
        "=" * 115
    )

    zones = load_zones()

    period_tables = []
    correlations = []
    quartile_tables = []
    profile_tables = []

    for period, config in (
        PERIODS.items()
    ):

        print(
            f"\nProcessing {period}..."
        )

        parking = load_parking(
            config[
                "parking_layer"
            ]
        )

        flows = (
            load_full_interzonal_flows(
                config[
                    "flow_layer"
                ]
            )
        )

        od = aggregate_od_by_zone(
            flows
        )

        table = (
            zones.merge(
                parking,
                on="zone_id",
                how="left",
                validate="one_to_one",
            )
            .merge(
                od,
                on="zone_id",
                how="left",
                validate="one_to_one",
            )
        )

        for col in [
            "interzonal_arrivals",
            "interzonal_departures",
            "interzonal_endpoint_activity",
            "net_interzonal_inflow",
        ]:

            table[col] = (
                table[col]
                .fillna(0)
            )

        table[
            "eligible_for_primary_analysis"
        ] = (
            table[
                "mean_parking_h"
            ]
            .notna()
            &
            (
                table[
                    "parking_events"
                ]
                >= MIN_PARKING_EVENTS
            )
            &
            (
                table[
                    "interzonal_endpoint_activity"
                ]
                > 0
            )
        )

        table.insert(
            0,
            "period",
            period,
        )

        period_tables.append(
            table
        )

        eligible = table.loc[
            table[
                "eligible_for_primary_analysis"
            ]
        ].copy()

        for demand_variable in [
            "interzonal_arrivals",
            "interzonal_departures",
            "interzonal_endpoint_activity",
        ]:

            correlations.append(
                correlation_row(
                    eligible,
                    period,
                    demand_variable,
                )
            )

        quartile_tables.append(
            demand_quartile_summary(
                table,
                period,
            )
        )

        profile_tables.append(
            classify_zone_profiles(
                table,
                period,
            )
        )

    # =========================================================================
    # SAVE
    # =========================================================================

    zone_table = pd.concat(
        period_tables,
        ignore_index=True,
    )

    correlation_table = pd.DataFrame(
        correlations
    )

    quartile_table = pd.concat(
        quartile_tables,
        ignore_index=True,
    )

    profile_table = pd.concat(
        profile_tables,
        ignore_index=True,
    )

    zone_table.to_csv(
        TABLE_DIR
        / "od_parking_zone_level_2024.csv",
        index=False,
    )

    correlation_table.to_csv(
        TABLE_DIR
        / "od_parking_correlations_2024.csv",
        index=False,
    )

    quartile_table.to_csv(
        TABLE_DIR
        / "od_parking_demand_quartiles_2024.csv",
        index=False,
    )

    profile_table.to_csv(
        TABLE_DIR
        / "od_parking_zone_profiles_2024.csv",
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
        "OD DEMAND × MEAN PARKING CORRELATIONS"
    )

    print(
        "=" * 115
    )

    print(
        correlation_table
        .round(3)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "PARKING DURATION BY OD DEMAND QUARTILE"
    )

    print(
        "=" * 115
    )

    print(
        quartile_table
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
        "HIGH-DEMAND / LONG-PARKING ZONES"
    )

    print(
        "=" * 115
    )

    selected = (
        profile_table.loc[
            profile_table[
                "profile"
            ]
            ==
            "High demand / Long parking"
        ]
        .copy()
    )

    for period in PERIODS:

        print(
            f"\n{period}:"
        )

        subset = (
            selected.loc[
                selected[
                    "period"
                ]
                == period
            ]
            .sort_values(
                "interzonal_endpoint_activity",
                ascending=False,
            )
            .head(10)
        )

        print(
            subset[
                [
                    "zone_id",
                    "zone_name",
                    "parking_events",
                    "mean_parking_h",
                    "interzonal_arrivals",
                    "interzonal_departures",
                    "interzonal_endpoint_activity",
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
        "HIGH-DEMAND / SHORT-PARKING ZONES"
    )

    print(
        "=" * 115
    )

    selected = (
        profile_table.loc[
            profile_table[
                "profile"
            ]
            ==
            "High demand / Short parking"
        ]
        .copy()
    )

    for period in PERIODS:

        print(
            f"\n{period}:"
        )

        subset = (
            selected.loc[
                selected[
                    "period"
                ]
                == period
            ]
            .sort_values(
                "interzonal_endpoint_activity",
                ascending=False,
            )
            .head(10)
        )

        print(
            subset[
                [
                    "zone_id",
                    "zone_name",
                    "parking_events",
                    "mean_parking_h",
                    "interzonal_arrivals",
                    "interzonal_departures",
                    "interzonal_endpoint_activity",
                ]
            ]
            .round(2)
            .to_string(
                index=False
            )
        )

    print(
        "\nINTERPRETATION RULES:"
        "\n- Primary statistic = Spearman rho."
        "\n- Negative rho: zones with greater inter-zonal OD activity tend to have shorter mean parking."
        "\n- Positive rho: zones with greater OD activity tend to have longer mean parking."
        "\n- Correlation is spatial association, not causation."
        "\n- Only zones with >=30 valid parking events enter the primary correlation."
        "\n- OD demand here refers to inter-zonal trips represented by the Exercise 2 OD matrices."
        "\n- Demand-core filtering is NOT used for correlations; all inter-zonal OD pairs are used."
    )


if __name__ == "__main__":
    main()