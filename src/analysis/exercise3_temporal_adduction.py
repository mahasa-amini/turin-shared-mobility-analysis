from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PARQUET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "route_overlap"
    / "scooter_pt_route_overlap_february_july_2024.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "temporal_adduction"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "temporal_adduction"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BASELINE_THRESHOLD_M = 100

CLASS_COL = (
    f"route_interaction_class_"
    f"{BASELINE_THRESHOLD_M}m"
)

DIRECT_CLASS = (
    "Direct PT-route overlap candidate"
)

NETWORK_CLASS = (
    "PT-network overlap / no direct route"
)

ACCESS_CLASS = (
    "Potential access / first-mile"
)

EGRESS_CLASS = (
    "Potential egress / last-mile"
)

INDEPENDENT_CLASS = (
    "Potential independent / spatial-gap"
)

PERIOD_HOURS = {
    "AM peak": 3,
    "PM peak": 4,
    "Off-peak": 17,
}


# =============================================================================
# HELPERS
# =============================================================================

def assign_period(
    hour: pd.Series,
):

    return np.select(
        [
            hour.between(
                7,
                9,
                inclusive="both",
            ),
            hour.between(
                16,
                19,
                inclusive="both",
            ),
        ],
        [
            "AM peak",
            "PM peak",
        ],
        default="Off-peak",
    )


def add_system_scope(
    df,
):

    system = df.copy()

    system[
        "operator"
    ] = "system"

    return pd.concat(
        [
            df,
            system,
        ],
        ignore_index=True,
    )


# =============================================================================
# TEMPORAL SUMMARY
# =============================================================================

def summarize_temporal_interactions(
    df,
):

    working = add_system_scope(
        df
    )

    rows = []

    group_cols = [
        "operator",
        "season",
        "transport_period",
    ]

    for (
        operator,
        season,
        period,
    ), group in working.groupby(
        group_cols,
        sort=False,
    ):

        trips = len(
            group
        )

        dates = (
            group[
                "start_time"
            ]
            .dt.normalize()
            .nunique()
        )

        hours_per_day = (
            PERIOD_HOURS[
                period
            ]
        )

        available_clock_hours = (
            dates
            * hours_per_day
        )

        counts = (
            group[
                CLASS_COL
            ]
            .value_counts()
        )

        def count_class(
            class_name,
        ):

            return int(
                counts.get(
                    class_name,
                    0,
                )
            )

        direct = count_class(
            DIRECT_CLASS
        )

        network = count_class(
            NETWORK_CLASS
        )

        access = count_class(
            ACCESS_CLASS
        )

        egress = count_class(
            EGRESS_CLASS
        )

        independent = count_class(
            INDEPENDENT_CLASS
        )

        feeder_total = (
            access
            + egress
        )

        rows.append(
            {
                "operator":
                    operator,

                "season":
                    season,

                "transport_period":
                    period,

                "calendar_days":
                    dates,

                "hours_per_day":
                    hours_per_day,

                "available_clock_hours":
                    available_clock_hours,

                "trips":
                    trips,

                "mean_trips_per_day":
                    trips
                    / dates,

                "mean_trips_per_clock_hour":
                    trips
                    / available_clock_hours,

                "direct_overlap_trips":
                    direct,

                "direct_overlap_pct":
                    100
                    * direct
                    / trips,

                "network_no_direct_trips":
                    network,

                "network_no_direct_pct":
                    100
                    * network
                    / trips,

                "access_trips":
                    access,

                "access_pct":
                    100
                    * access
                    / trips,

                "egress_trips":
                    egress,

                "egress_pct":
                    100
                    * egress
                    / trips,

                "feeder_total_trips":
                    feeder_total,

                "feeder_total_pct":
                    100
                    * feeder_total
                    / trips,

                "independent_trips":
                    independent,

                "independent_pct":
                    100
                    * independent
                    / trips,

                "egress_minus_access_pp":
                    (
                        100
                        * egress
                        / trips
                    )
                    -
                    (
                        100
                        * access
                        / trips
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# ALL-DAY SUMMARY
# =============================================================================

def summarize_all_day(
    df,
):

    working = add_system_scope(
        df
    )

    rows = []

    for (
        operator,
        season,
    ), group in working.groupby(
        [
            "operator",
            "season",
        ],
        sort=False,
    ):

        trips = len(
            group
        )

        counts = (
            group[
                CLASS_COL
            ]
            .value_counts()
        )

        direct = int(
            counts.get(
                DIRECT_CLASS,
                0,
            )
        )

        network = int(
            counts.get(
                NETWORK_CLASS,
                0,
            )
        )

        access = int(
            counts.get(
                ACCESS_CLASS,
                0,
            )
        )

        egress = int(
            counts.get(
                EGRESS_CLASS,
                0,
            )
        )

        independent = int(
            counts.get(
                INDEPENDENT_CLASS,
                0,
            )
        )

        feeder_total = (
            access
            + egress
        )

        rows.append(
            {
                "operator":
                    operator,

                "season":
                    season,

                "transport_period":
                    "All day",

                "calendar_days":
                    group[
                        "start_time"
                    ]
                    .dt.normalize()
                    .nunique(),

                "hours_per_day":
                    24,

                "available_clock_hours":
                    group[
                        "start_time"
                    ]
                    .dt.normalize()
                    .nunique()
                    * 24,

                "trips":
                    trips,

                "mean_trips_per_day":
                    trips
                    /
                    group[
                        "start_time"
                    ]
                    .dt.normalize()
                    .nunique(),

                "mean_trips_per_clock_hour":
                    trips
                    /
                    (
                        group[
                            "start_time"
                        ]
                        .dt.normalize()
                        .nunique()
                        * 24
                    ),

                "direct_overlap_trips":
                    direct,

                "direct_overlap_pct":
                    100
                    * direct
                    / trips,

                "network_no_direct_trips":
                    network,

                "network_no_direct_pct":
                    100
                    * network
                    / trips,

                "access_trips":
                    access,

                "access_pct":
                    100
                    * access
                    / trips,

                "egress_trips":
                    egress,

                "egress_pct":
                    100
                    * egress
                    / trips,

                "feeder_total_trips":
                    feeder_total,

                "feeder_total_pct":
                    100
                    * feeder_total
                    / trips,

                "independent_trips":
                    independent,

                "independent_pct":
                    100
                    * independent
                    / trips,

                "egress_minus_access_pp":
                    (
                        100
                        * egress
                        / trips
                    )
                    -
                    (
                        100
                        * access
                        / trips
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# FEEDER EVENTS
# =============================================================================

def build_feeder_events(
    df,
):

    access = (
        df.loc[
            df[
                CLASS_COL
            ]
            == ACCESS_CLASS
        ]
        .copy()
    )

    access_events = pd.DataFrame(
        {
            "analysis_trip_id":
                access[
                    "analysis_trip_id"
                ],

            "operator":
                access[
                    "operator"
                ],

            "season":
                access[
                    "season"
                ],

            "transport_period":
                access[
                    "transport_period"
                ],

            "feeder_direction":
                "access_to_pt",

            "pt_stop_id":
                access[
                    "destination_nearest_stop_id"
                ],

            "pt_stop_name":
                access[
                    "destination_nearest_stop_name"
                ],

            "pt_stop_modes":
                access[
                    "destination_nearest_stop_modes"
                ],

            "distance_to_stop_m":
                access[
                    "destination_nearest_stop_distance_m"
                ],
        }
    )

    egress = (
        df.loc[
            df[
                CLASS_COL
            ]
            == EGRESS_CLASS
        ]
        .copy()
    )

    egress_events = pd.DataFrame(
        {
            "analysis_trip_id":
                egress[
                    "analysis_trip_id"
                ],

            "operator":
                egress[
                    "operator"
                ],

            "season":
                egress[
                    "season"
                ],

            "transport_period":
                egress[
                    "transport_period"
                ],

            "feeder_direction":
                "egress_from_pt",

            "pt_stop_id":
                egress[
                    "origin_nearest_stop_id"
                ],

            "pt_stop_name":
                egress[
                    "origin_nearest_stop_name"
                ],

            "pt_stop_modes":
                egress[
                    "origin_nearest_stop_modes"
                ],

            "distance_to_stop_m":
                egress[
                    "origin_nearest_stop_distance_m"
                ],
        }
    )

    events = pd.concat(
        [
            access_events,
            egress_events,
        ],
        ignore_index=True,
    )

    if events[
        "pt_stop_id"
    ].isna().any():

        raise RuntimeError(
            "Missing PT stop ID in "
            "feeder events."
        )

    return events


# =============================================================================
# FEEDER STOP HOTSPOTS
# =============================================================================

def build_hotspots(
    feeder_events,
):

    # -------------------------------------------------------------------------
    # Add system scope
    # -------------------------------------------------------------------------

    system = feeder_events.copy()

    system[
        "operator"
    ] = "system"

    working = pd.concat(
        [
            feeder_events,
            system,
        ],
        ignore_index=True,
    )

    # -------------------------------------------------------------------------
    # Add all-day copy
    # -------------------------------------------------------------------------

    all_day = working.copy()

    all_day[
        "transport_period"
    ] = "All day"

    working = pd.concat(
        [
            working,
            all_day,
        ],
        ignore_index=True,
    )

    # -------------------------------------------------------------------------
    # Direction-specific stop counts
    # -------------------------------------------------------------------------

    direction_counts = (
        working
        .groupby(
            [
                "operator",
                "season",
                "transport_period",
                "pt_stop_id",
                "pt_stop_name",
                "pt_stop_modes",
                "feeder_direction",
            ],
            dropna=False,
        )
        .agg(
            trips=(
                "analysis_trip_id",
                "nunique",
            ),
            median_distance_to_stop_m=(
                "distance_to_stop_m",
                "median",
            ),
        )
        .reset_index()
    )

    # -------------------------------------------------------------------------
    # Bidirectional feeder summary
    # -------------------------------------------------------------------------

    pivot = (
        direction_counts
        .pivot_table(
            index=[
                "operator",
                "season",
                "transport_period",
                "pt_stop_id",
                "pt_stop_name",
                "pt_stop_modes",
            ],
            columns="feeder_direction",
            values="trips",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    for col in [
        "access_to_pt",
        "egress_from_pt",
    ]:

        if col not in pivot.columns:

            pivot[
                col
            ] = 0

    pivot[
        "total_feeder_trips"
    ] = (
        pivot[
            "access_to_pt"
        ]
        +
        pivot[
            "egress_from_pt"
        ]
    )

    pivot[
        "net_access_minus_egress"
    ] = (
        pivot[
            "access_to_pt"
        ]
        -
        pivot[
            "egress_from_pt"
        ]
    )

    pivot[
        "direction_balance_index"
    ] = np.where(
        pivot[
            "total_feeder_trips"
        ]
        > 0,
        (
            pivot[
                "access_to_pt"
            ]
            -
            pivot[
                "egress_from_pt"
            ]
        )
        /
        pivot[
            "total_feeder_trips"
        ],
        np.nan,
    )

    pivot = (
        pivot
        .sort_values(
            [
                "operator",
                "season",
                "transport_period",
                "total_feeder_trips",
            ],
            ascending=[
                True,
                True,
                True,
                False,
            ],
        )
    )

    return (
        direction_counts,
        pivot,
    )


# =============================================================================
# SEASONAL DIFFERENCE
# =============================================================================

def build_system_seasonal_period_comparison(
    summary,
):

    system = (
        summary.loc[
            summary[
                "operator"
            ]
            == "system"
        ]
        .copy()
    )

    metrics = [
        "direct_overlap_pct",
        "network_no_direct_pct",
        "access_pct",
        "egress_pct",
        "feeder_total_pct",
        "independent_pct",
    ]

    rows = []

    for period in system[
        "transport_period"
    ].unique():

        period_df = (
            system.loc[
                system[
                    "transport_period"
                ]
                == period
            ]
            .set_index(
                "season"
            )
        )

        if not {
            "winter_february",
            "summer_july",
        }.issubset(
            period_df.index
        ):

            continue

        for metric in metrics:

            winter = float(
                period_df.loc[
                    "winter_february",
                    metric,
                ]
            )

            summer = float(
                period_df.loc[
                    "summer_july",
                    metric,
                ]
            )

            rows.append(
                {
                    "transport_period":
                        period,

                    "metric":
                        metric,

                    "winter_february_pct":
                        winter,

                    "summer_july_pct":
                        summer,

                    "summer_minus_winter_pp":
                        summer
                        - winter,
                }
            )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 110
    )

    print(
        "EXERCISE 3 — TEMPORAL ADDUCTION / PT INTERACTION"
    )

    print(
        "=" * 110
    )

    if not INPUT_PARQUET.exists():

        raise FileNotFoundError(
            f"Missing Stage 3 file:\n"
            f"{INPUT_PARQUET}"
        )

    df = pd.read_parquet(
        INPUT_PARQUET
    )

    print(
        f"\nTrips loaded: "
        f"{len(df):,}"
    )

    # =========================================================================
    # VALIDATE
    # =========================================================================

    required = [
        "analysis_trip_id",
        "operator",
        "season",
        "start_time",
        CLASS_COL,
        "origin_nearest_stop_id",
        "origin_nearest_stop_name",
        "origin_nearest_stop_modes",
        "origin_nearest_stop_distance_m",
        "destination_nearest_stop_id",
        "destination_nearest_stop_name",
        "destination_nearest_stop_modes",
        "destination_nearest_stop_distance_m",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Required columns missing:\n"
            f"{missing}"
        )

    if df[
        "analysis_trip_id"
    ].duplicated().any():

        raise RuntimeError(
            "analysis_trip_id is not unique."
        )

    df[
        "start_time"
    ] = pd.to_datetime(
        df[
            "start_time"
        ],
        errors="coerce",
    )

    if df[
        "start_time"
    ].isna().any():

        raise RuntimeError(
            "Missing start_time values."
        )

    # =========================================================================
    # ASSIGN PERIODS
    # =========================================================================

    df[
        "hour"
    ] = (
        df[
            "start_time"
        ].dt.hour
    )

    df[
        "transport_period"
    ] = assign_period(
        df[
            "hour"
        ]
    )

    print(
        "\nTransport period counts:"
    )

    print(
        df[
            "transport_period"
        ]
        .value_counts()
        .to_string()
    )

    # =========================================================================
    # SUMMARIES
    # =========================================================================

    temporal = (
        summarize_temporal_interactions(
            df
        )
    )

    all_day = (
        summarize_all_day(
            df
        )
    )

    summary = pd.concat(
        [
            all_day,
            temporal,
        ],
        ignore_index=True,
    )

    seasonal_comparison = (
        build_system_seasonal_period_comparison(
            summary
        )
    )

    # =========================================================================
    # FEEDER HOTSPOTS
    # =========================================================================

    feeder_events = (
        build_feeder_events(
            df
        )
    )

    (
        direction_hotspots,
        bidirectional_hotspots,
    ) = build_hotspots(
        feeder_events
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    summary.to_csv(
        AUDIT_DIR
        / "pt_interaction_by_transport_period_100m.csv",
        index=False,
    )

    seasonal_comparison.to_csv(
        AUDIT_DIR
        / "system_seasonal_period_comparison_100m.csv",
        index=False,
    )

    feeder_events.to_parquet(
        OUTPUT_DIR
        / "feeder_events_100m.parquet",
        index=False,
    )

    direction_hotspots.to_csv(
        AUDIT_DIR
        / "feeder_stop_direction_hotspots_100m.csv",
        index=False,
    )

    bidirectional_hotspots.to_csv(
        AUDIT_DIR
        / "feeder_stop_bidirectional_hotspots_100m.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL OUTPUT
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "SYSTEM PT INTERACTION BY TRANSPORT PERIOD — 100 m"
    )

    print(
        "=" * 110
    )

    system_summary = (
        summary.loc[
            summary[
                "operator"
            ]
            == "system"
        ]
        .copy()
    )

    period_order = {
        "All day": 0,
        "AM peak": 1,
        "PM peak": 2,
        "Off-peak": 3,
    }

    system_summary[
        "_period_order"
    ] = (
        system_summary[
            "transport_period"
        ].map(
            period_order
        )
    )

    system_summary = (
        system_summary
        .sort_values(
            [
                "season",
                "_period_order",
            ]
        )
    )

    print(
        system_summary[
            [
                "season",
                "transport_period",
                "trips",
                "mean_trips_per_clock_hour",
                "direct_overlap_pct",
                "network_no_direct_pct",
                "access_pct",
                "egress_pct",
                "feeder_total_pct",
                "independent_pct",
                "egress_minus_access_pp",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "SYSTEM SEASONAL DIFFERENCE BY PERIOD — 100 m"
    )

    print(
        "=" * 110
    )

    print(
        seasonal_comparison.to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "TOP SYSTEM FEEDER STOPS — ALL DAY / 100 m"
    )

    print(
        "=" * 110
    )

    top_system = (
        bidirectional_hotspots.loc[
            (
                bidirectional_hotspots[
                    "operator"
                ]
                == "system"
            )
            &
            (
                bidirectional_hotspots[
                    "transport_period"
                ]
                == "All day"
            )
        ]
        .groupby(
            "season",
            sort=False,
        )
        .head(15)
    )

    print(
        top_system[
            [
                "season",
                "pt_stop_id",
                "pt_stop_name",
                "pt_stop_modes",
                "access_to_pt",
                "egress_from_pt",
                "total_feeder_trips",
                "net_access_minus_egress",
                "direction_balance_index",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "OUTPUTS"
    )

    print(
        "=" * 110
    )

    print(
        f"Temporal audit tables -> "
        f"{AUDIT_DIR}"
    )

    print(
        "Feeder events -> "
        f"{OUTPUT_DIR / 'feeder_events_100m.parquet'}"
    )

    print(
        "\nINTERPRETATION:"
    )

    print(
        "- AM/PM timing comes from 2024 "
        "scooter timestamps."
    )

    print(
        "- PT topology remains a spatial "
        "reference network; no 2024 timetable "
        "availability is inferred."
    )

    print(
        "- Access/egress hotspot counts are "
        "potential feeder interactions, not "
        "observed transfers."
    )

    print(
        "- Stop-level results may split large "
        "interchanges across multiple nearby "
        "GTFS stop IDs."
    )


if __name__ == "__main__":

    main()