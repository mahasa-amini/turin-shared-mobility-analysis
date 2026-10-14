from pathlib import Path

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

HARMONIZATION_AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "harmonization"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "temporal"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "temporal"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


SUMMARY_FILE = (
    HARMONIZATION_AUDIT_DIR
    / "harmonization_summary.csv"
)

COVERAGE_FILE = (
    HARMONIZATION_AUDIT_DIR
    / "harmonization_coverage.csv"
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
# EXPLICIT COVERAGE REGISTRY
#
# IMPORTANT:
# These windows come from the actual source coverage and
# cleaning/harmonization audits.
#
# monthly_start/monthly_end:
#     valid month-level attribution from SOURCE_PERIOD
#
# detail_start/detail_end:
#     dates for which day/hour-level timestamps are available
#
# partial_month:
#     final source month is incomplete
# ============================================================

COVERAGE_REGISTRY = [
    {
        "operator": "bird",
        "year": 2024,
        "monthly_start": "2024-01",
        "monthly_end": "2024-12",
        "detail_start": "2024-01-01",
        "detail_end": "2024-12-31",
        "partial_month": None,
        "coverage_note":
            "Complete 2024 coverage.",
    },
    {
        "operator": "lime",
        "year": 2024,
        "monthly_start": "2024-01",
        "monthly_end": "2024-12",
        "detail_start": "2024-01-01",
        "detail_end": "2024-12-31",
        "partial_month": None,
        "coverage_note":
            "Complete 2024 coverage.",
    },
    {
        "operator": "voi",
        "year": 2024,
        "monthly_start": "2024-01",
        "monthly_end": "2024-12",
        "detail_start": "2024-02-01",
        "detail_end": "2024-12-31",
        "partial_month": None,
        "coverage_note":
            (
                "January 2024 is valid only at month level; "
                "day/hour timestamps are unavailable."
            ),
    },
    {
        "operator": "bird",
        "year": 2025,
        "monthly_start": "2025-01",
        "monthly_end": "2025-11",
        "detail_start": "2025-01-01",
        "detail_end": "2025-11-18",
        "partial_month": "2025-11",
        "coverage_note":
            "2025 data available through 18 November.",
    },
    {
        "operator": "lime",
        "year": 2025,
        "monthly_start": "2025-01",
        "monthly_end": "2025-04",
        "detail_start": "2025-01-01",
        "detail_end": "2025-04-29",
        "partial_month": "2025-04",
        "coverage_note":
            "2025 data available through 29 April.",
    },
    {
        "operator": "voi",
        "year": 2025,
        "monthly_start": "2025-01",
        "monthly_end": "2025-10",
        "detail_start": "2025-01-01",
        "detail_end": "2025-10-31",
        "partial_month": None,
        "coverage_note":
            "Complete monthly files through October 2025.",
    },
]


# ============================================================
# COMMON COMPARISON WINDOWS
# ============================================================

COMPARISON_WINDOWS = [
    {
        "window_name":
            "2024_monthly_full_year",
        "year": 2024,
        "temporal_level":
            "monthly_annual",
        "start_date":
            "2024-01-01",
        "end_date":
            "2024-12-31",
        "first_full_week":
            None,
        "last_full_week_end":
            None,
        "use_case":
            (
                "Full-year monthly and annual "
                "comparison across all three operators"
            ),
    },
    {
        "window_name":
            "2024_detailed_common",
        "year": 2024,
        "temporal_level":
            "daily_hourly",
        "start_date":
            "2024-02-01",
        "end_date":
            "2024-12-31",
        "first_full_week":
            None,
        "last_full_week_end":
            None,
        "use_case":
            (
                "Common day/hour-level comparison; "
                "VOI January excluded"
            ),
    },
    {
        "window_name":
            "2024_weekly_common_full_weeks",
        "year": 2024,
        "temporal_level":
            "weekly",
        "start_date":
            "2024-02-05",
        "end_date":
            "2024-12-29",
        "first_full_week":
            "2024-02-05",
        "last_full_week_end":
            "2024-12-29",
        "use_case":
            (
                "Monday-Sunday complete weeks available "
                "for all operators"
            ),
    },
    {
        "window_name":
            "2025_monthly_common_full_months",
        "year": 2025,
        "temporal_level":
            "monthly",
        "start_date":
            "2025-01-01",
        "end_date":
            "2025-03-31",
        "first_full_week":
            None,
        "last_full_week_end":
            None,
        "use_case":
            (
                "Full-month comparison across all operators; "
                "Lime April is incomplete"
            ),
    },
    {
        "window_name":
            "2025_detailed_common",
        "year": 2025,
        "temporal_level":
            "daily_hourly",
        "start_date":
            "2025-01-01",
        "end_date":
            "2025-04-29",
        "first_full_week":
            None,
        "last_full_week_end":
            None,
        "use_case":
            (
                "Common exact date window across all operators"
            ),
    },
    {
        "window_name":
            "2025_weekly_common_full_weeks",
        "year": 2025,
        "temporal_level":
            "weekly",
        "start_date":
            "2025-01-06",
        "end_date":
            "2025-04-27",
        "first_full_week":
            "2025-01-06",
        "last_full_week_end":
            "2025-04-27",
        "use_case":
            (
                "Monday-Sunday complete weeks available "
                "for all operators"
            ),
    },
]


# ============================================================
# LOAD AUDIT TABLES
# ============================================================

def load_audit_tables():

    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(
            SUMMARY_FILE
        )

    if not COVERAGE_FILE.exists():
        raise FileNotFoundError(
            COVERAGE_FILE
        )

    summary = pd.read_csv(
        SUMMARY_FILE
    )

    coverage = pd.read_csv(
        COVERAGE_FILE
    )

    return summary, coverage


# ============================================================
# COVERAGE REGISTRY
# ============================================================

def build_coverage_registry(
    harmonization_coverage
):

    registry = pd.DataFrame(
        COVERAGE_REGISTRY
    )

    registry["detail_start"] = (
        pd.to_datetime(
            registry["detail_start"]
        )
    )

    registry["detail_end"] = (
        pd.to_datetime(
            registry["detail_end"]
        )
    )

    audit = (
        harmonization_coverage[
            [
                "operator",
                "year",
                "rows",
                "min_source_period",
                "max_source_period",
                "months_present",
                "observed_start_min",
                "observed_start_max",
                "temporal_detail_available",
            ]
        ]
        .copy()
    )

    audit[
        "observed_start_min"
    ] = pd.to_datetime(
        audit["observed_start_min"],
        errors="coerce",
    )

    audit[
        "observed_start_max"
    ] = pd.to_datetime(
        audit["observed_start_max"],
        errors="coerce",
    )

    registry = registry.merge(
        audit,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # Cross-check source-period coverage
    # --------------------------------------------------------

    assert (
        registry["monthly_start"]
        ==
        registry["min_source_period"]
    ).all()

    assert (
        registry["monthly_end"]
        ==
        registry["max_source_period"]
    ).all()

    return registry


# ============================================================
# MONTHLY AGGREGATION
#
# IMPORTANT:
# Monthly counts use source_period, NOT start_time_local.
# This allows VOI January 2024 to remain valid for
# month-level trip-volume analysis.
# ============================================================

def build_monthly_counts(
    frames,
    coverage_registry,
    harmonization_summary,
):

    parts = []

    for (
        operator,
        year
    ), df in frames.items():

        monthly = (
            df.groupby(
                "source_period",
                as_index=False,
            )
            .size()
            .rename(
                columns={
                    "size":
                        "trip_count"
                }
            )
        )

        monthly[
            "operator"
        ] = operator

        monthly[
            "year"
        ] = year

        registry_row = (
            coverage_registry.loc[
                (
                    coverage_registry[
                        "operator"
                    ] == operator
                )
                &
                (
                    coverage_registry[
                        "year"
                    ] == year
                )
            ]
            .iloc[0]
        )

        partial_month = (
            registry_row[
                "partial_month"
            ]
        )

        if pd.isna(
            partial_month
        ):

            monthly[
                "is_full_source_month"
            ] = True

        else:

            monthly[
                "is_full_source_month"
            ] = (
                monthly[
                    "source_period"
                ]
                != partial_month
            )

        parts.append(
            monthly
        )

    result = pd.concat(
        parts,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Determine which months are complete for ALL operators
    # --------------------------------------------------------

    common_status = (
        result.groupby(
            [
                "year",
                "source_period",
            ]
        )
        .agg(
            operators_present=(
                "operator",
                "nunique",
            ),
            all_operators_full_month=(
                "is_full_source_month",
                "all",
            ),
        )
        .reset_index()
    )

    common_status[
        "common_full_month_all_operators"
    ] = (
        (
            common_status[
                "operators_present"
            ] == 3
        )
        &
        common_status[
            "all_operators_full_month"
        ]
    )

    result = result.merge(
        common_status[
            [
                "year",
                "source_period",
                "common_full_month_all_operators",
            ]
        ],
        on=[
            "year",
            "source_period",
        ],
        how="left",
    )

    # --------------------------------------------------------
    # Reconciliation:
    # monthly total must equal harmonized row count
    # --------------------------------------------------------

    monthly_totals = (
        result.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )["trip_count"]
        .sum()
        .rename(
            columns={
                "trip_count":
                    "monthly_total"
            }
        )
    )

    expected = (
        harmonization_summary[
            [
                "operator",
                "year",
                "rows",
            ]
        ]
        .rename(
            columns={
                "rows":
                    "expected_rows"
            }
        )
    )

    check = monthly_totals.merge(
        expected,
        on=[
            "operator",
            "year",
        ],
        validate="one_to_one",
    )

    assert (
        check[
            "monthly_total"
        ]
        ==
        check[
            "expected_rows"
        ]
    ).all(), (
        "Monthly aggregation does not reconcile "
        "with harmonized row counts."
    )

    return result


# ============================================================
# DAILY AGGREGATION
#
# Only trips with detailed local timestamps are used.
# Missing calendar dates inside operator coverage are
# explicitly represented with trip_count = 0.
# ============================================================

def build_daily_counts(
    frames,
    coverage_registry,
    harmonization_summary,
):

    parts = []

    for (
        operator,
        year
    ), df in frames.items():

        registry_row = (
            coverage_registry.loc[
                (
                    coverage_registry[
                        "operator"
                    ] == operator
                )
                &
                (
                    coverage_registry[
                        "year"
                    ] == year
                )
            ]
            .iloc[0]
        )

        detail_start = (
            registry_row[
                "detail_start"
            ]
        )

        detail_end = (
            registry_row[
                "detail_end"
            ]
        )

        temporal = df.loc[
            df[
                "valid_temporal_detail"
            ]
            &
            df[
                "start_time_local"
            ].notna()
        ].copy()

        temporal[
            "date"
        ] = (
            temporal[
                "start_time_local"
            ]
            .dt.normalize()
        )

        observed = (
            temporal.groupby(
                "date"
            )
            .size()
            .rename(
                "trip_count"
            )
        )

        calendar = pd.DataFrame(
            {
                "date":
                    pd.date_range(
                        detail_start,
                        detail_end,
                        freq="D",
                    )
            }
        )

        daily = calendar.merge(
            observed,
            left_on="date",
            right_index=True,
            how="left",
        )

        daily[
            "trip_count"
        ] = (
            daily[
                "trip_count"
            ]
            .fillna(0)
            .astype("int64")
        )

        daily[
            "operator"
        ] = operator

        daily[
            "year"
        ] = year

        daily[
            "weekday"
        ] = (
            daily[
                "date"
            ]
            .dt.day_name()
        )

        daily[
            "weekday_number"
        ] = (
            daily[
                "date"
            ]
            .dt.weekday
        )

        daily[
            "is_weekend"
        ] = (
            daily[
                "weekday_number"
            ] >= 5
        )

        # ----------------------------------------------------
        # Common all-operator detailed window
        # ----------------------------------------------------

        if year == 2024:

            common_start = pd.Timestamp(
                "2024-02-01"
            )

            common_end = pd.Timestamp(
                "2024-12-31"
            )

        elif year == 2025:

            common_start = pd.Timestamp(
                "2025-01-01"
            )

            common_end = pd.Timestamp(
                "2025-04-29"
            )

        else:

            raise ValueError(
                f"Unexpected year: {year}"
            )

        daily[
            "within_common_detailed_window"
        ] = (
            daily[
                "date"
            ].between(
                common_start,
                common_end,
                inclusive="both",
            )
        )

        parts.append(
            daily
        )

    result = pd.concat(
        parts,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Daily totals must reconcile to temporal_detail_available
    # --------------------------------------------------------

    actual = (
        result.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )["trip_count"]
        .sum()
        .rename(
            columns={
                "trip_count":
                    "daily_total"
            }
        )
    )

    expected = (
        harmonization_summary[
            [
                "operator",
                "year",
                "temporal_detail_available",
            ]
        ]
    )

    check = actual.merge(
        expected,
        on=[
            "operator",
            "year",
        ],
        validate="one_to_one",
    )

    assert (
        check[
            "daily_total"
        ]
        ==
        check[
            "temporal_detail_available"
        ]
    ).all(), (
        "Daily aggregation does not reconcile "
        "with detailed temporal availability."
    )

    return result


# ============================================================
# WEEKLY AGGREGATION
#
# Monday-Sunday calendar weeks.
# Partial weeks are retained but explicitly flagged.
# ============================================================

def build_weekly_counts(
    daily
):

    df = daily.copy()

    df[
        "week_start"
    ] = (
        df["date"]
        - pd.to_timedelta(
            df["weekday_number"],
            unit="D",
        )
    )

    weekly = (
        df.groupby(
            [
                "operator",
                "year",
                "week_start",
            ],
            as_index=False,
        )
        .agg(
            trip_count=(
                "trip_count",
                "sum",
            ),
            days_in_operator_coverage=(
                "date",
                "count",
            ),
            days_in_common_window=(
                "within_common_detailed_window",
                "sum",
            ),
        )
    )

    weekly[
        "week_end"
    ] = (
        weekly[
            "week_start"
        ]
        + pd.Timedelta(
            days=6
        )
    )

    weekly[
        "full_week_for_operator"
    ] = (
        weekly[
            "days_in_operator_coverage"
        ] == 7
    )

    weekly[
        "full_week_common_all_operators"
    ] = (
        weekly[
            "days_in_common_window"
        ] == 7
    )

    return weekly


# ============================================================
# ANNUAL / PERIOD SUMMARY
# ============================================================

def build_year_summary(
    monthly,
):

    yearly = (
        monthly.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            trip_count=(
                "trip_count",
                "sum",
            ),
            months_present=(
                "source_period",
                "nunique",
            ),
            full_months_present=(
                "is_full_source_month",
                "sum",
            ),
        )
    )

    yearly[
        "annual_total_comparable"
    ] = (
        yearly[
            "year"
        ] == 2024
    )

    yearly[
        "coverage_label"
    ] = yearly.apply(
        lambda r:
            "complete_2024"
            if r["year"] == 2024
            else "partial_2025",
        axis=1,
    )

    return yearly


# ============================================================
# LOAD HARMONIZED DATA
# ============================================================

def load_harmonized_frames():

    columns = [
        "operator",
        "trip_uid",
        "start_time_local",
        "source_period",
        "year",
        "valid_monthly_period",
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

        assert (
            df[
                "valid_monthly_period"
            ]
            .all()
        )

        frames[
            (
                operator,
                year,
            )
        ] = df

    return frames


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 105
    )

    print(
        "EXERCISE 1 — COVERAGE-AWARE TEMPORAL STRUCTURING"
    )

    print(
        "=" * 105
    )

    summary, audit_coverage = (
        load_audit_tables()
    )

    coverage_registry = (
        build_coverage_registry(
            audit_coverage
        )
    )

    comparison_windows = (
        pd.DataFrame(
            COMPARISON_WINDOWS
        )
    )

    frames = (
        load_harmonized_frames()
    )

    monthly = (
        build_monthly_counts(
            frames,
            coverage_registry,
            summary,
        )
    )

    daily = (
        build_daily_counts(
            frames,
            coverage_registry,
            summary,
        )
    )

    weekly = (
        build_weekly_counts(
            daily
        )
    )

    yearly = (
        build_year_summary(
            monthly
        )
    )

    # ========================================================
    # COMPARISON-READY SUBSETS
    # ========================================================

    monthly_common = monthly.loc[
        monthly[
            "common_full_month_all_operators"
        ]
    ].copy()

    daily_common = daily.loc[
        daily[
            "within_common_detailed_window"
        ]
    ].copy()

    weekly_common = weekly.loc[
        weekly[
            "full_week_common_all_operators"
        ]
    ].copy()

    # ========================================================
    # SAVE TABLES
    # ========================================================

    coverage_registry.to_csv(
        TABLE_DIR
        / "temporal_coverage_registry.csv",
        index=False,
    )

    comparison_windows.to_csv(
        TABLE_DIR
        / "temporal_comparison_windows.csv",
        index=False,
    )

    monthly.to_csv(
        TABLE_DIR
        / "monthly_trip_counts.csv",
        index=False,
    )

    monthly_common.to_csv(
        TABLE_DIR
        / "monthly_trip_counts_common_full_months.csv",
        index=False,
    )

    daily.to_csv(
        TABLE_DIR
        / "daily_trip_counts.csv",
        index=False,
    )

    daily_common.to_csv(
        TABLE_DIR
        / "daily_trip_counts_common_windows.csv",
        index=False,
    )

    weekly.to_csv(
        TABLE_DIR
        / "weekly_trip_counts.csv",
        index=False,
    )

    weekly_common.to_csv(
        TABLE_DIR
        / "weekly_trip_counts_common_full_weeks.csv",
        index=False,
    )

    yearly.to_csv(
        TABLE_DIR
        / "yearly_trip_counts_with_coverage.csv",
        index=False,
    )

    # Parquet versions for later analysis
    monthly.to_parquet(
        OUTPUT_DIR
        / "monthly_trip_counts.parquet",
        index=False,
    )

    daily.to_parquet(
        OUTPUT_DIR
        / "daily_trip_counts.parquet",
        index=False,
    )

    weekly.to_parquet(
        OUTPUT_DIR
        / "weekly_trip_counts.parquet",
        index=False,
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print(
        "\nCoverage registry:"
    )

    print(
        coverage_registry[
            [
                "operator",
                "year",
                "monthly_start",
                "monthly_end",
                "detail_start",
                "detail_end",
                "partial_month",
                "temporal_detail_available",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nComparison windows:"
    )

    print(
        comparison_windows[
            [
                "window_name",
                "temporal_level",
                "start_date",
                "end_date",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nCommon FULL months available "
        "for all three operators:"
    )

    common_months = (
        monthly_common[
            [
                "year",
                "source_period",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "year",
                "source_period",
            ]
        )
    )

    print(
        common_months.to_string(
            index=False
        )
    )

    print(
        "\nAnnual / partial-year trip totals:"
    )

    print(
        yearly.to_string(
            index=False
        )
    )

    print(
        "\nDaily detailed-temporal reconciliation:"
    )

    daily_check = (
        daily.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )["trip_count"]
        .sum()
    )

    print(
        daily_check.to_string(
            index=False
        )
    )

    print(
        "\nCommon-window daily trip totals:"
    )

    common_daily_totals = (
        daily_common.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_count",
                "sum",
            ),
            days=(
                "date",
                "nunique",
            ),
        )
    )

    common_daily_totals[
        "avg_trips_per_day"
    ] = (
        common_daily_totals[
            "trips"
        ]
        /
        common_daily_totals[
            "days"
        ]
    )

    common_daily_totals[
        "avg_trips_per_day"
    ] = (
        common_daily_totals[
            "avg_trips_per_day"
        ]
        .round(2)
    )

    print(
        common_daily_totals.to_string(
            index=False
        )
    )

    print(
        "\nFull common weeks:"
    )

    common_week_counts = (
        weekly_common.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            full_weeks=(
                "week_start",
                "nunique",
            ),
            trips=(
                "trip_count",
                "sum",
            ),
        )
    )

    print(
        common_week_counts.to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION:"
        "\n- Monthly counts reconcile with ALL harmonized trips."
        "\n- Daily counts reconcile with temporal-detail availability."
        "\n- VOI January 2024 is included in monthly counts but excluded "
        "from day/hour-level analysis."
        "\n- Partial 2025 months are retained but explicitly flagged."
        "\n- Cross-operator weekly comparison uses complete "
        "Monday-Sunday weeks only."
        "\n- 2025 annual totals are NOT treated as comparable."
    )


if __name__ == "__main__":
    main()