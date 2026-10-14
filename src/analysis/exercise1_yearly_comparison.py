from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MONTHLY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "temporal"
    / "monthly_trip_counts_with_trends.parquet"
)

COVERAGE_FILE = (
    PROJECT_ROOT
    / "audit"
    / "harmonization"
    / "harmonization_coverage.csv"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "temporal"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "temporal"
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD
# ============================================================

def load_data():

    if not MONTHLY_FILE.exists():
        raise FileNotFoundError(
            MONTHLY_FILE
        )

    if not COVERAGE_FILE.exists():
        raise FileNotFoundError(
            COVERAGE_FILE
        )

    monthly = pd.read_parquet(
        MONTHLY_FILE
    )

    coverage = pd.read_csv(
        COVERAGE_FILE
    )

    monthly[
        "month_number"
    ] = (
        pd.PeriodIndex(
            monthly[
                "source_period"
            ],
            freq="M",
        )
        .month
    )

    if (
        "days_in_month"
        not in monthly.columns
    ):

        monthly[
            "days_in_month"
        ] = (
            pd.PeriodIndex(
                monthly[
                    "source_period"
                ],
                freq="M",
            )
            .days_in_month
        )

    return monthly, coverage


# ============================================================
# 2024 FULL-YEAR
# ============================================================

def build_2024_full_year(
    monthly
):

    data = monthly.loc[
        monthly[
            "year"
        ] == 2024
    ].copy()

    check = (
        data.groupby(
            "operator"
        )[
            "source_period"
        ]
        .nunique()
    )

    assert (
        check == 12
    ).all()

    summary = (
        data.groupby(
            "operator",
            as_index=False,
        )
        .agg(
            full_year_trips=(
                "trip_count",
                "sum",
            ),
            months=(
                "source_period",
                "nunique",
            ),
        )
    )

    system_total = (
        summary[
            "full_year_trips"
        ].sum()
    )

    summary[
        "system_share_pct"
    ] = (
        summary[
            "full_year_trips"
        ]
        / system_total
        * 100
    )

    summary[
        "annual_total_comparable"
    ] = True

    return (
        summary,
        int(system_total),
    )


# ============================================================
# 2025 OBSERVED COVERAGE
#
# These totals are descriptive only.
# ============================================================

def build_2025_observed(
    monthly,
    coverage
):

    data = monthly.loc[
        monthly[
            "year"
        ] == 2025
    ].copy()

    observed = (
        data.groupby(
            "operator",
            as_index=False,
        )
        .agg(
            observed_trips=(
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
            first_month=(
                "source_period",
                "min",
            ),
            last_month=(
                "source_period",
                "max",
            ),
        )
    )

    coverage_2025 = (
        coverage.loc[
            coverage[
                "year"
            ] == 2025,
            [
                "operator",
                "observed_start_min",
                "observed_start_max",
            ],
        ]
        .copy()
    )

    observed = observed.merge(
        coverage_2025,
        on="operator",
        how="left",
        validate="one_to_one",
    )

    observed[
        "annual_total_comparable"
    ] = False

    observed[
        "interpretation"
    ] = (
        "partial_2025_observed_only"
    )

    return observed


# ============================================================
# COMMON JAN-MAR YOY
#
# Full months for all operators in both years.
# ============================================================

def build_common_yoy(
    monthly
):

    matched = monthly.loc[
        monthly[
            "year"
        ].isin(
            [
                2024,
                2025,
            ]
        )
        &
        monthly[
            "month_number"
        ].isin(
            [
                1,
                2,
                3,
            ]
        )
        &
        monthly[
            "is_full_source_month"
        ]
    ].copy()

    check = (
        matched.groupby(
            [
                "operator",
                "year",
            ]
        )[
            "month_number"
        ]
        .nunique()
    )

    assert (
        check == 3
    ).all()

    # --------------------------------------------------------
    # Operator-level Jan-Mar
    # --------------------------------------------------------

    operator_summary = (
        matched.groupby(
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
            calendar_days=(
                "days_in_month",
                "sum",
            ),
        )
    )

    operator_summary[
        "avg_trips_per_calendar_day"
    ] = (
        operator_summary[
            "trips"
        ]
        /
        operator_summary[
            "calendar_days"
        ]
    )

    # --------------------------------------------------------
    # System totals by year
    # --------------------------------------------------------

    system_summary = (
        operator_summary.groupby(
            "year",
            as_index=False,
        )
        .agg(
            system_trips=(
                "trips",
                "sum",
            ),
            calendar_days=(
                "calendar_days",
                "max",
            ),
        )
    )

    system_summary[
        "system_avg_trips_per_calendar_day"
    ] = (
        system_summary[
            "system_trips"
        ]
        /
        system_summary[
            "calendar_days"
        ]
    )

    # --------------------------------------------------------
    # Operator share of total system activity
    # --------------------------------------------------------

    operator_summary = (
        operator_summary.merge(
            system_summary[
                [
                    "year",
                    "system_trips",
                ]
            ],
            on="year",
            how="left",
        )
    )

    operator_summary[
        "system_share_pct"
    ] = (
        operator_summary[
            "trips"
        ]
        /
        operator_summary[
            "system_trips"
        ]
        * 100
    )

    return (
        matched,
        operator_summary,
        system_summary,
    )


# ============================================================
# OPERATOR YOY COMPARISON
# ============================================================

def build_operator_yoy_comparison(
    operator_summary
):

    metrics = [
        "trips",
        "avg_trips_per_calendar_day",
        "system_share_pct",
    ]

    pivot = (
        operator_summary.pivot(
            index="operator",
            columns="year",
            values=metrics,
        )
    )

    pivot.columns = [
        f"{metric}_{year}"
        for metric, year
        in pivot.columns
    ]

    pivot = (
        pivot.reset_index()
    )

    pivot[
        "trip_growth_pct"
    ] = (
        (
            pivot[
                "trips_2025"
            ]
            /
            pivot[
                "trips_2024"
            ]
        )
        - 1
    ) * 100

    pivot[
        "daily_rate_growth_pct"
    ] = (
        (
            pivot[
                "avg_trips_per_calendar_day_2025"
            ]
            /
            pivot[
                "avg_trips_per_calendar_day_2024"
            ]
        )
        - 1
    ) * 100

    pivot[
        "system_share_change_percentage_points"
    ] = (
        pivot[
            "system_share_pct_2025"
        ]
        -
        pivot[
            "system_share_pct_2024"
        ]
    )

    return pivot


# ============================================================
# SYSTEM YOY
# ============================================================

def build_system_yoy_comparison(
    system_summary
):

    y2024 = (
        system_summary.loc[
            system_summary[
                "year"
            ] == 2024
        ]
        .iloc[0]
    )

    y2025 = (
        system_summary.loc[
            system_summary[
                "year"
            ] == 2025
        ]
        .iloc[0]
    )

    result = pd.DataFrame(
        [
            {
                "comparison_window":
                    "Jan-Mar",

                "system_trips_2024":
                    int(
                        y2024[
                            "system_trips"
                        ]
                    ),

                "system_trips_2025":
                    int(
                        y2025[
                            "system_trips"
                        ]
                    ),

                "system_trip_growth_pct":
                    (
                        y2025[
                            "system_trips"
                        ]
                        /
                        y2024[
                            "system_trips"
                        ]
                        - 1
                    ) * 100,

                "system_daily_rate_2024":
                    y2024[
                        "system_avg_trips_per_calendar_day"
                    ],

                "system_daily_rate_2025":
                    y2025[
                        "system_avg_trips_per_calendar_day"
                    ],

                "system_daily_rate_growth_pct":
                    (
                        y2025[
                            "system_avg_trips_per_calendar_day"
                        ]
                        /
                        y2024[
                            "system_avg_trips_per_calendar_day"
                        ]
                        - 1
                    ) * 100,
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
        + "=" * 110
    )

    print(
        "EXERCISE 1 — YEARLY MOBILITY COMPARISON"
    )

    print(
        "=" * 110
    )

    monthly, coverage = (
        load_data()
    )

    (
        full_2024,
        system_total_2024,
    ) = (
        build_2024_full_year(
            monthly
        )
    )

    observed_2025 = (
        build_2025_observed(
            monthly,
            coverage,
        )
    )

    (
        matched,
        operator_summary,
        system_summary,
    ) = (
        build_common_yoy(
            monthly
        )
    )

    operator_yoy = (
        build_operator_yoy_comparison(
            operator_summary
        )
    )

    system_yoy = (
        build_system_yoy_comparison(
            system_summary
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    full_2024.to_csv(
        TABLE_DIR
        / "yearly_2024_full_year_operator_summary.csv",
        index=False,
    )

    observed_2025.to_csv(
        TABLE_DIR
        / "yearly_2025_observed_coverage.csv",
        index=False,
    )

    operator_summary.to_csv(
        TABLE_DIR
        / "yearly_common_jan_mar_operator_summary.csv",
        index=False,
    )

    operator_yoy.to_csv(
        TABLE_DIR
        / "yearly_common_jan_mar_yoy_comparison.csv",
        index=False,
    )

    system_summary.to_csv(
        TABLE_DIR
        / "yearly_common_jan_mar_system_summary.csv",
        index=False,
    )

    system_yoy.to_csv(
        TABLE_DIR
        / "yearly_common_jan_mar_system_yoy.csv",
        index=False,
    )

    matched.to_parquet(
        OUTPUT_DIR
        / "yearly_common_jan_mar_source_data.parquet",
        index=False,
    )

    # ========================================================
    # TERMINAL
    # ========================================================

    pd.set_option(
        "display.max_columns",
        None
    )

    print(
        "\n2024 FULL-YEAR mobility totals:"
    )

    display_2024 = (
        full_2024.copy()
    )

    display_2024[
        "system_share_pct"
    ] = (
        display_2024[
            "system_share_pct"
        ].round(2)
    )

    print(
        display_2024.to_string(
            index=False
        )
    )

    print(
        f"\n2024 total system trips: "
        f"{system_total_2024:,}"
    )

    print(
        "\n2025 observed coverage "
        "(NOT annual-comparable totals):"
    )

    print(
        observed_2025.to_string(
            index=False
        )
    )

    print(
        "\nCommon Jan-Mar operator YoY comparison:"
    )

    display_yoy = (
        operator_yoy.copy()
    )

    numeric_cols = [
        "trips_2024",
        "trips_2025",
        "avg_trips_per_calendar_day_2024",
        "avg_trips_per_calendar_day_2025",
        "system_share_pct_2024",
        "system_share_pct_2025",
        "trip_growth_pct",
        "daily_rate_growth_pct",
        "system_share_change_percentage_points",
    ]

    for col in numeric_cols:

        display_yoy[col] = (
            display_yoy[col]
            .round(2)
        )

    print(
        display_yoy.to_string(
            index=False
        )
    )

    print(
        "\nCommon Jan-Mar SYSTEM YoY comparison:"
    )

    display_system = (
        system_yoy.copy()
    )

    for col in [
        "system_trip_growth_pct",
        "system_daily_rate_2024",
        "system_daily_rate_2025",
        "system_daily_rate_growth_pct",
    ]:

        display_system[col] = (
            display_system[col]
            .round(2)
        )

    print(
        display_system.to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
        "\n- 2024 is the only complete calendar year for all three operators."
        "\n- 2025 observed totals are retained for descriptive purposes only."
        "\n- Direct 2024-vs-2025 annual-total comparison is prohibited."
        "\n- Cross-operator YoY comparison uses Jan-Mar, the common full-month window."
        "\n- Daily-rate comparison controls for leap-year month-length difference."
        "\n- Operator system-share changes describe observed trip shares, not market share "
        "in a commercial or revenue sense."
    )


if __name__ == "__main__":
    main()