from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HARMONIZED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "harmonized"
)

HARMONIZATION_SUMMARY = (
    PROJECT_ROOT
    / "audit"
    / "harmonization"
    / "harmonization_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "vehicles"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "vehicles"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


FILES = {
    ("bird", 2024):
        HARMONIZED_DIR
        / "bird_2024_harmonized.parquet",

    ("bird", 2025):
        HARMONIZED_DIR
        / "bird_2025_harmonized.parquet",

    ("lime", 2024):
        HARMONIZED_DIR
        / "lime_2024_harmonized.parquet",

    ("lime", 2025):
        HARMONIZED_DIR
        / "lime_2025_harmonized.parquet",

    ("voi", 2024):
        HARMONIZED_DIR
        / "voi_2024_harmonized.parquet",

    ("voi", 2025):
        HARMONIZED_DIR
        / "voi_2025_harmonized.parquet",
}


# ============================================================
# LOAD
# ============================================================

def load_data():

    if not HARMONIZATION_SUMMARY.exists():
        raise FileNotFoundError(
            HARMONIZATION_SUMMARY
        )

    audit = pd.read_csv(
        HARMONIZATION_SUMMARY
    )

    columns = [
        "operator",
        "year",
        "vehicle_type",
        "vehicle_id",
        "vehicle_uid",
        "trip_uid",
        "source_period",
        "start_time_local",
        "valid_trip_record",
        "valid_temporal_detail",
    ]

    frames = {}

    for (
        operator,
        year
    ), path in FILES.items():

        if not path.exists():

            raise FileNotFoundError(
                path
            )

        df = pd.read_parquet(
            path,
            columns=columns,
        )

        df[
            "start_time_local"
        ] = pd.to_datetime(
            df[
                "start_time_local"
            ],
            errors="coerce",
        )

        # ----------------------------------------------------
        # Only canonical trip records participate in vehicle
        # activity analysis.
        # ----------------------------------------------------

        df = df.loc[
            df[
                "valid_trip_record"
            ]
            &
            df[
                "vehicle_uid"
            ].notna()
        ].copy()

        assert (
            df[
                "trip_uid"
            ].is_unique
        )

        assert (
            df[
                "operator"
            ] == operator
        ).all()

        assert (
            df[
                "year"
            ] == year
        ).all()

        frames[
            (
                operator,
                year,
            )
        ] = df

    return frames, audit


# ============================================================
# ANNUAL / OBSERVED VEHICLE-LEVEL DATA
#
# Uses ALL valid trip records.
#
# active_months is available for all operators because
# source_period remains valid even for VOI January 2024.
#
# We intentionally do NOT calculate annual active_days here
# because VOI January 2024 lacks detailed timestamps.
# ============================================================

def build_vehicle_year_data(
    frames
):

    parts = []

    for (
        operator,
        year
    ), df in frames.items():

        vehicle = (
            df.groupby(
                [
                    "operator",
                    "year",
                    "vehicle_type",
                    "vehicle_uid",
                    "vehicle_id",
                ],
                as_index=False,
                dropna=False,
            )
            .agg(
                trips=(
                    "trip_uid",
                    "count",
                ),
                active_months=(
                    "source_period",
                    "nunique",
                ),
                first_source_period=(
                    "source_period",
                    "min",
                ),
                last_source_period=(
                    "source_period",
                    "max",
                ),
            )
        )

        vehicle[
            "trips_per_active_month"
        ] = (
            vehicle[
                "trips"
            ]
            /
            vehicle[
                "active_months"
            ]
        )

        parts.append(
            vehicle
        )

    result = pd.concat(
        parts,
        ignore_index=True,
    )

    return result


# ============================================================
# DISTRIBUTION HELPER
# ============================================================

def distribution_stats(series):

    s = (
        pd.to_numeric(
            series,
            errors="coerce",
        )
        .dropna()
    )

    return {
        "mean":
            s.mean(),

        "median":
            s.median(),

        "std":
            s.std(),

        "min":
            s.min(),

        "p25":
            s.quantile(0.25),

        "p75":
            s.quantile(0.75),

        "p90":
            s.quantile(0.90),

        "p95":
            s.quantile(0.95),

        "p99":
            s.quantile(0.99),

        "max":
            s.max(),
    }


# ============================================================
# ANNUAL VEHICLE SUMMARY
#
# 2024 = complete annual comparison
# 2025 = observed partial coverage only
# ============================================================

def build_vehicle_year_summary(
    vehicle_year,
    audit
):

    records = []

    for (
        operator,
        year,
        vehicle_type
    ), group in vehicle_year.groupby(
        [
            "operator",
            "year",
            "vehicle_type",
        ],
        dropna=False,
    ):

        trip_stats = (
            distribution_stats(
                group[
                    "trips"
                ]
            )
        )

        month_stats = (
            distribution_stats(
                group[
                    "active_months"
                ]
            )
        )

        total_trips = int(
            group[
                "trips"
            ].sum()
        )

        unique_vehicles = int(
            group[
                "vehicle_uid"
            ].nunique()
        )

        records.append(
            {
                "operator":
                    operator,

                "year":
                    int(year),

                "vehicle_type":
                    vehicle_type,

                "unique_observed_vehicles":
                    unique_vehicles,

                "total_trips":
                    total_trips,

                "trips_per_observed_vehicle":
                    (
                        total_trips
                        / unique_vehicles
                    ),

                "mean_vehicle_trips":
                    trip_stats[
                        "mean"
                    ],

                "median_vehicle_trips":
                    trip_stats[
                        "median"
                    ],

                "std_vehicle_trips":
                    trip_stats[
                        "std"
                    ],

                "min_vehicle_trips":
                    trip_stats[
                        "min"
                    ],

                "p25_vehicle_trips":
                    trip_stats[
                        "p25"
                    ],

                "p75_vehicle_trips":
                    trip_stats[
                        "p75"
                    ],

                "p90_vehicle_trips":
                    trip_stats[
                        "p90"
                    ],

                "p95_vehicle_trips":
                    trip_stats[
                        "p95"
                    ],

                "p99_vehicle_trips":
                    trip_stats[
                        "p99"
                    ],

                "max_vehicle_trips":
                    trip_stats[
                        "max"
                    ],

                "mean_active_months":
                    month_stats[
                        "mean"
                    ],

                "median_active_months":
                    month_stats[
                        "median"
                    ],

                "annual_comparison_valid":
                    (
                        int(year)
                        == 2024
                    ),

                "coverage_label":
                    (
                        "complete_2024"
                        if int(year) == 2024
                        else "partial_2025_observed"
                    ),
            }
        )

    summary = pd.DataFrame(
        records
    )

    # --------------------------------------------------------
    # Reconcile against harmonization audit
    # --------------------------------------------------------

    expected = audit[
        [
            "operator",
            "year",
            "rows",
            "unique_vehicles",
        ]
    ].copy()

    check = summary.merge(
        expected,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="one_to_one",
    )

    assert (
        check[
            "total_trips"
        ]
        ==
        check[
            "rows"
        ]
    ).all(), (
        "Vehicle trip totals do not reconcile "
        "with harmonized rows."
    )

    assert (
        check[
            "unique_observed_vehicles"
        ]
        ==
        check[
            "unique_vehicles"
        ]
    ).all(), (
        "Unique vehicle counts do not reconcile "
        "with harmonization summary."
    )

    return summary


# ============================================================
# MATCHED DAILY YOY DATA
#
# 2024: Feb 1-Apr 29, excluding Feb 29
# 2025: Feb 1-Apr 29
#
# Exactly 88 calendar days.
#
# Only detailed timestamps are used because active-day
# utilization requires exact trip dates.
# ============================================================

def build_matched_yoy_trips(
    frames
):

    parts = []

    windows = {
        2024: (
            pd.Timestamp(
                "2024-02-01"
            ),
            pd.Timestamp(
                "2024-04-29"
            ),
        ),
        2025: (
            pd.Timestamp(
                "2025-02-01"
            ),
            pd.Timestamp(
                "2025-04-29"
            ),
        ),
    }

    for (
        operator,
        year
    ), df in frames.items():

        start_date, end_date = (
            windows[
                year
            ]
        )

        subset = df.loc[
            df[
                "valid_temporal_detail"
            ]
            &
            df[
                "start_time_local"
            ].notna()
        ].copy()

        subset[
            "date"
        ] = (
            subset[
                "start_time_local"
            ]
            .dt.normalize()
        )

        subset = subset.loc[
            subset[
                "date"
            ].between(
                start_date,
                end_date,
                inclusive="both",
            )
        ].copy()

        # ----------------------------------------------------
        # Leap day removed ONLY from matched YoY analysis.
        # ----------------------------------------------------

        if year == 2024:

            subset = subset.loc[
                subset[
                    "date"
                ]
                != pd.Timestamp(
                    "2024-02-29"
                )
            ].copy()

        subset[
            "matched_day_index"
        ] = (
            subset[
                "date"
            ]
            .map(
                {
                    date: i + 1
                    for i, date
                    in enumerate(
                        pd.date_range(
                            start_date,
                            end_date,
                            freq="D",
                        ).difference(
                            pd.DatetimeIndex(
                                [
                                    pd.Timestamp(
                                        "2024-02-29"
                                    )
                                ]
                                if year == 2024
                                else []
                            )
                        )
                    )
                }
            )
        )

        assert (
            subset[
                "matched_day_index"
            ].notna()
            .all()
        )

        parts.append(
            subset
        )

    matched = pd.concat(
        parts,
        ignore_index=True,
    )

    return matched


# ============================================================
# MATCHED VEHICLE-LEVEL UTILIZATION
# ============================================================

def build_matched_vehicle_level(
    matched
):

    vehicle = (
        matched.groupby(
            [
                "operator",
                "year",
                "vehicle_type",
                "vehicle_uid",
                "vehicle_id",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            ),
            active_days=(
                "date",
                "nunique",
            ),
            first_active_date=(
                "date",
                "min",
            ),
            last_active_date=(
                "date",
                "max",
            ),
        )
    )

    vehicle[
        "trips_per_active_day"
    ] = (
        vehicle[
            "trips"
        ]
        /
        vehicle[
            "active_days"
        ]
    )

    vehicle[
        "active_day_share_pct"
    ] = (
        vehicle[
            "active_days"
        ]
        / 88
        * 100
    )

    return vehicle


# ============================================================
# DAILY ACTIVE VEHICLE SERIES
#
# Active vehicle:
# vehicle with at least one recorded trip on that calendar day.
# ============================================================

def build_daily_active_vehicles(
    matched
):

    observed = (
        matched.groupby(
            [
                "operator",
                "year",
                "date",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            ),
            active_vehicles=(
                "vehicle_uid",
                "nunique",
            ),
        )
    )

    parts = []

    for (
        operator,
        year
    ), group in observed.groupby(
        [
            "operator",
            "year",
        ]
    ):

        if year == 2024:

            calendar = (
                pd.date_range(
                    "2024-02-01",
                    "2024-04-29",
                    freq="D",
                )
                .difference(
                    pd.DatetimeIndex(
                        [
                            pd.Timestamp(
                                "2024-02-29"
                            )
                        ]
                    )
                )
            )

        else:

            calendar = pd.date_range(
                "2025-02-01",
                "2025-04-29",
                freq="D",
            )

        assert len(calendar) == 88

        full = pd.DataFrame(
            {
                "date":
                    calendar
            }
        )

        full = full.merge(
            group[
                [
                    "date",
                    "trips",
                    "active_vehicles",
                ]
            ],
            on="date",
            how="left",
        )

        full[
            "trips"
        ] = (
            full[
                "trips"
            ]
            .fillna(0)
            .astype("int64")
        )

        full[
            "active_vehicles"
        ] = (
            full[
                "active_vehicles"
            ]
            .fillna(0)
            .astype("int64")
        )

        full[
            "operator"
        ] = operator

        full[
            "year"
        ] = year

        full[
            "trips_per_active_vehicle"
        ] = np.where(
            full[
                "active_vehicles"
            ] > 0,
            full[
                "trips"
            ]
            /
            full[
                "active_vehicles"
            ],
            np.nan,
        )

        full[
            "matched_day_index"
        ] = np.arange(
            1,
            89,
        )

        parts.append(
            full
        )

    result = pd.concat(
        parts,
        ignore_index=True,
    )

    check = (
        result.groupby(
            [
                "operator",
                "year",
            ]
        )[
            "date"
        ]
        .nunique()
    )

    assert (
        check == 88
    ).all()

    return result


# ============================================================
# MATCHED UTILIZATION SUMMARY
# ============================================================

def build_matched_summary(
    vehicle_level,
    daily_active,
):

    records = []

    for (
        operator,
        year
    ), vehicles in vehicle_level.groupby(
        [
            "operator",
            "year",
        ]
    ):

        daily = daily_active.loc[
            (
                daily_active[
                    "operator"
                ] == operator
            )
            &
            (
                daily_active[
                    "year"
                ] == year
            )
        ].copy()

        trip_stats = distribution_stats(
            vehicles[
                "trips"
            ]
        )

        active_day_stats = distribution_stats(
            vehicles[
                "active_days"
            ]
        )

        trip_per_active_day_stats = (
            distribution_stats(
                vehicles[
                    "trips_per_active_day"
                ]
            )
        )

        total_trips = int(
            vehicles[
                "trips"
            ].sum()
        )

        unique_vehicles = int(
            vehicles[
                "vehicle_uid"
            ].nunique()
        )

        vehicle_active_days = int(
            vehicles[
                "active_days"
            ].sum()
        )

        # ----------------------------------------------------
        # Cross-check:
        # sum of daily active vehicles must equal sum of
        # per-vehicle active days.
        # ----------------------------------------------------

        assert (
            int(
                daily[
                    "active_vehicles"
                ].sum()
            )
            ==
            vehicle_active_days
        )

        assert (
            int(
                daily[
                    "trips"
                ].sum()
            )
            ==
            total_trips
        )

        records.append(
            {
                "operator":
                    operator,

                "year":
                    int(year),

                "days":
                    88,

                "total_trips":
                    total_trips,

                "unique_observed_vehicles":
                    unique_vehicles,

                "trips_per_observed_vehicle":
                    (
                        total_trips
                        / unique_vehicles
                    ),

                "vehicle_active_days":
                    vehicle_active_days,

                "mean_daily_active_vehicles":
                    daily[
                        "active_vehicles"
                    ].mean(),

                "median_daily_active_vehicles":
                    daily[
                        "active_vehicles"
                    ].median(),

                "min_daily_active_vehicles":
                    daily[
                        "active_vehicles"
                    ].min(),

                "max_daily_active_vehicles":
                    daily[
                        "active_vehicles"
                    ].max(),

                "trips_per_active_vehicle_day":
                    (
                        total_trips
                        / vehicle_active_days
                    ),

                "mean_vehicle_trips":
                    trip_stats[
                        "mean"
                    ],

                "median_vehicle_trips":
                    trip_stats[
                        "median"
                    ],

                "p25_vehicle_trips":
                    trip_stats[
                        "p25"
                    ],

                "p75_vehicle_trips":
                    trip_stats[
                        "p75"
                    ],

                "p90_vehicle_trips":
                    trip_stats[
                        "p90"
                    ],

                "p95_vehicle_trips":
                    trip_stats[
                        "p95"
                    ],

                "p99_vehicle_trips":
                    trip_stats[
                        "p99"
                    ],

                "max_vehicle_trips":
                    trip_stats[
                        "max"
                    ],

                "mean_active_days_per_vehicle":
                    active_day_stats[
                        "mean"
                    ],

                "median_active_days_per_vehicle":
                    active_day_stats[
                        "median"
                    ],

                "p90_active_days_per_vehicle":
                    active_day_stats[
                        "p90"
                    ],

                "mean_trips_per_active_day_per_vehicle":
                    trip_per_active_day_stats[
                        "mean"
                    ],

                "median_trips_per_active_day_per_vehicle":
                    trip_per_active_day_stats[
                        "median"
                    ],
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# MATCHED YOY COMPARISON
#
# Helps distinguish:
# - more trips
# - more observed vehicles
# - more vehicles active each day
# - more trips generated per active vehicle-day
# ============================================================

def build_matched_yoy_comparison(
    summary
):

    metrics = [
        "total_trips",
        "unique_observed_vehicles",
        "trips_per_observed_vehicle",
        "mean_daily_active_vehicles",
        "trips_per_active_vehicle_day",
        "median_vehicle_trips",
        "median_active_days_per_vehicle",
    ]

    pivot = summary.pivot(
        index="operator",
        columns="year",
        values=metrics,
    )

    pivot.columns = [
        f"{metric}_{year}"
        for metric, year
        in pivot.columns
    ]

    pivot = pivot.reset_index()

    for metric in metrics:

        pivot[
            f"{metric}_pct_change_2025_vs_2024"
        ] = (
            (
                pivot[
                    f"{metric}_2025"
                ]
                /
                pivot[
                    f"{metric}_2024"
                ]
            )
            - 1
        ) * 100

    return pivot


# ============================================================
# FULL-YEAR 2024 SYSTEM SUMMARY
# ============================================================

def build_2024_system_summary(
    vehicle_year
):

    data = vehicle_year.loc[
        vehicle_year[
            "year"
        ] == 2024
    ].copy()

    assert (
        data[
            "vehicle_uid"
        ].nunique()
        ==
        len(data)
    )

    total_trips = int(
        data[
            "trips"
        ].sum()
    )

    unique_vehicles = int(
        data[
            "vehicle_uid"
        ].nunique()
    )

    result = pd.DataFrame(
        [
            {
                "year":
                    2024,

                "vehicle_type":
                    "e_scooter",

                "system_unique_observed_vehicles":
                    unique_vehicles,

                "system_total_trips":
                    total_trips,

                "system_trips_per_observed_vehicle":
                    (
                        total_trips
                        / unique_vehicles
                    ),
            }
        ]
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 115
    )

    print(
        "EXERCISE 1 — UNIQUE VEHICLES AND VEHICLE UTILIZATION"
    )

    print(
        "=" * 115
    )

    frames, audit = (
        load_data()
    )

    # ========================================================
    # ANNUAL / OBSERVED
    # ========================================================

    vehicle_year = (
        build_vehicle_year_data(
            frames
        )
    )

    year_summary = (
        build_vehicle_year_summary(
            vehicle_year,
            audit,
        )
    )

    system_2024 = (
        build_2024_system_summary(
            vehicle_year
        )
    )

    # ========================================================
    # MATCHED UTILIZATION
    # ========================================================

    matched_trips = (
        build_matched_yoy_trips(
            frames
        )
    )

    matched_vehicle = (
        build_matched_vehicle_level(
            matched_trips
        )
    )

    daily_active = (
        build_daily_active_vehicles(
            matched_trips
        )
    )

    matched_summary = (
        build_matched_summary(
            matched_vehicle,
            daily_active,
        )
    )

    yoy_comparison = (
        build_matched_yoy_comparison(
            matched_summary
        )
    )

    # ========================================================
    # SAVE DATASETS
    # ========================================================

    vehicle_year.to_parquet(
        OUTPUT_DIR
        / "vehicle_level_annual_observed.parquet",
        index=False,
    )

    matched_vehicle.to_parquet(
        OUTPUT_DIR
        / "vehicle_level_matched_feb_apr_yoy.parquet",
        index=False,
    )

    daily_active.to_parquet(
        OUTPUT_DIR
        / "daily_active_vehicle_intensity.parquet",
        index=False,
    )

    # ========================================================
    # SAVE TABLES
    # ========================================================

    year_summary.to_csv(
        TABLE_DIR
        / "vehicle_year_summary.csv",
        index=False,
    )

    year_summary.loc[
        year_summary[
            "year"
        ] == 2024
    ].to_csv(
        TABLE_DIR
        / "vehicle_2024_full_year_summary.csv",
        index=False,
    )

    year_summary.loc[
        year_summary[
            "year"
        ] == 2025
    ].to_csv(
        TABLE_DIR
        / "vehicle_2025_observed_summary.csv",
        index=False,
    )

    system_2024.to_csv(
        TABLE_DIR
        / "vehicle_system_2024_summary.csv",
        index=False,
    )

    matched_summary.to_csv(
        TABLE_DIR
        / "vehicle_matched_yoy_summary.csv",
        index=False,
    )

    yoy_comparison.to_csv(
        TABLE_DIR
        / "vehicle_matched_yoy_comparison.csv",
        index=False,
    )

    daily_active.to_csv(
        TABLE_DIR
        / "daily_active_vehicle_intensity.csv",
        index=False,
    )

    # ========================================================
    # TERMINAL DISPLAY
    # ========================================================

    pd.set_option(
        "display.max_columns",
        None
    )

    print(
        "\nObserved unique vehicles and "
        "trips-per-vehicle distribution:"
    )

    display_year = (
        year_summary.copy()
    )

    round_cols = [
        "trips_per_observed_vehicle",
        "mean_vehicle_trips",
        "median_vehicle_trips",
        "std_vehicle_trips",
        "p25_vehicle_trips",
        "p75_vehicle_trips",
        "p90_vehicle_trips",
        "p95_vehicle_trips",
        "p99_vehicle_trips",
        "mean_active_months",
        "median_active_months",
    ]

    for col in round_cols:

        display_year[col] = (
            display_year[col]
            .round(2)
        )

    print(
        display_year.to_string(
            index=False
        )
    )

    print(
        "\n2024 system vehicle summary:"
    )

    system_display = (
        system_2024.copy()
    )

    system_display[
        "system_trips_per_observed_vehicle"
    ] = (
        system_display[
            "system_trips_per_observed_vehicle"
        ]
        .round(2)
    )

    print(
        system_display.to_string(
            index=False
        )
    )

    print(
        "\nMatched utilization window:"
        "\n2024: Feb 1-Apr 29, excluding Feb 29"
        "\n2025: Feb 1-Apr 29"
        "\n88 calendar days per operator-year"
    )

    print(
        "\nMatched-period vehicle utilization:"
    )

    matched_display = (
        matched_summary.copy()
    )

    matched_round_cols = [
        "trips_per_observed_vehicle",
        "mean_daily_active_vehicles",
        "median_daily_active_vehicles",
        "trips_per_active_vehicle_day",
        "mean_vehicle_trips",
        "median_vehicle_trips",
        "p25_vehicle_trips",
        "p75_vehicle_trips",
        "p90_vehicle_trips",
        "p95_vehicle_trips",
        "p99_vehicle_trips",
        "mean_active_days_per_vehicle",
        "median_active_days_per_vehicle",
        "p90_active_days_per_vehicle",
        "mean_trips_per_active_day_per_vehicle",
        "median_trips_per_active_day_per_vehicle",
    ]

    for col in matched_round_cols:

        matched_display[col] = (
            matched_display[col]
            .round(2)
        )

    print(
        matched_display.to_string(
            index=False
        )
    )

    print(
        "\nMatched 2025 vs 2024 utilization changes:"
    )

    yoy_display = (
        yoy_comparison.copy()
    )

    for col in yoy_display.columns:

        if (
            col != "operator"
        ):

            yoy_display[col] = (
                pd.to_numeric(
                    yoy_display[col],
                    errors="coerce",
                )
                .round(2)
            )

    print(
        yoy_display.to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
        "\n- 'Unique vehicles' means observed vehicle IDs with >=1 trip, "
        "not official fleet size."
        "\n- vehicle_uid is used, so operator ID namespaces cannot collide."
        "\n- 2024 is the only complete annual cross-operator comparison."
        "\n- 2025 annual vehicle totals are descriptive only because coverage differs."
        "\n- Annual active-month metrics use source_period and remain valid for "
        "VOI January 2024."
        "\n- Active-day utilization is evaluated only in the matched detailed-time window."
        "\n- Matched YoY comparison contains exactly 88 calendar days per year."
        "\n- Trips per active vehicle-day separates utilization intensity from "
        "the number of vehicles observed."
        "\n- Vehicle-level Parquet outputs are histogram-ready."
    )


if __name__ == "__main__":
    main()