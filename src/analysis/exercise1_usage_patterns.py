from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEMPORAL_DIR = (
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
    / "patterns"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "patterns"
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


DAILY_FILE = (
    TEMPORAL_DIR
    / "daily_trip_counts.parquet"
)

MATCHED_DAILY_FILE = (
    TEMPORAL_DIR
    / "daily_trip_counts_matched_yoy.parquet"
)

MONTHLY_FILE = (
    TEMPORAL_DIR
    / "monthly_trip_counts_with_trends.parquet"
)


WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

SEASON_ORDER = [
    "Winter",
    "Spring",
    "Summer",
    "Autumn",
]


# ============================================================
# LOAD
# ============================================================

def load_data():

    for path in [
        DAILY_FILE,
        MATCHED_DAILY_FILE,
        MONTHLY_FILE,
    ]:

        if not path.exists():
            raise FileNotFoundError(
                path
            )

    daily = pd.read_parquet(
        DAILY_FILE
    )

    matched = pd.read_parquet(
        MATCHED_DAILY_FILE
    )

    monthly = pd.read_parquet(
        MONTHLY_FILE
    )

    daily["date"] = pd.to_datetime(
        daily["date"]
    )

    matched["date"] = pd.to_datetime(
        matched["date"]
    )

    return daily, matched, monthly


# ============================================================
# WEEKDAY PROFILE
# ============================================================

def build_weekday_profile(
    df,
):

    data = df.copy()

    if "weekday" not in data.columns:

        data["weekday"] = (
            data["date"]
            .dt.day_name()
        )

    if "weekday_number" not in data.columns:

        data["weekday_number"] = (
            data["date"]
            .dt.weekday
        )

    profile = (
        data.groupby(
            [
                "operator",
                "year",
                "weekday_number",
                "weekday",
            ],
            as_index=False,
        )
        .agg(
            calendar_days=(
                "date",
                "nunique",
            ),
            trips=(
                "trip_count",
                "sum",
            ),
            mean_daily_trips=(
                "trip_count",
                "mean",
            ),
            median_daily_trips=(
                "trip_count",
                "median",
            ),
            std_daily_trips=(
                "trip_count",
                "std",
            ),
        )
    )

    # --------------------------------------------------------
    # Operator-year mean daily activity
    # --------------------------------------------------------

    overall = (
        data.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            total_trips=(
                "trip_count",
                "sum",
            ),
            total_days=(
                "date",
                "nunique",
            ),
        )
    )

    overall[
        "overall_mean_daily_trips"
    ] = (
        overall[
            "total_trips"
        ]
        /
        overall[
            "total_days"
        ]
    )

    profile = profile.merge(
        overall[
            [
                "operator",
                "year",
                "overall_mean_daily_trips",
            ]
        ],
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="many_to_one",
    )

    # --------------------------------------------------------
    # Normalized weekday activity index
    #
    # 100 = operator-year mean daily activity.
    # --------------------------------------------------------

    profile[
        "weekday_activity_index"
    ] = (
        profile[
            "mean_daily_trips"
        ]
        /
        profile[
            "overall_mean_daily_trips"
        ]
        * 100
    )

    return profile


# ============================================================
# WEEKDAY VS WEEKEND SUMMARY
# ============================================================

def build_weekday_weekend_summary(
    df,
):

    data = df.copy()

    if "weekday_number" not in data.columns:

        data["weekday_number"] = (
            data["date"]
            .dt.weekday
        )

    data[
        "day_group"
    ] = (
        data[
            "weekday_number"
        ]
        .ge(5)
        .map(
            {
                False: "Weekday",
                True: "Weekend",
            }
        )
    )

    grouped = (
        data.groupby(
            [
                "operator",
                "year",
                "day_group",
            ],
            as_index=False,
        )
        .agg(
            calendar_days=(
                "date",
                "nunique",
            ),
            trips=(
                "trip_count",
                "sum",
            ),
            mean_daily_trips=(
                "trip_count",
                "mean",
            ),
            median_daily_trips=(
                "trip_count",
                "median",
            ),
            std_daily_trips=(
                "trip_count",
                "std",
            ),
        )
    )

    pivot = (
        grouped.pivot(
            index=[
                "operator",
                "year",
            ],
            columns="day_group",
            values="mean_daily_trips",
        )
        .reset_index()
    )

    pivot.columns.name = None

    pivot = pivot.rename(
        columns={
            "Weekday":
                "weekday_mean_daily_trips",

            "Weekend":
                "weekend_mean_daily_trips",
        }
    )

    pivot[
        "weekend_uplift_pct"
    ] = (
        (
            pivot[
                "weekend_mean_daily_trips"
            ]
            /
            pivot[
                "weekday_mean_daily_trips"
            ]
        )
        - 1
    ) * 100

    return grouped, pivot


# ============================================================
# 2024 COMMON DETAILED WINDOW
#
# Feb 1-Dec 31 for all three operators.
#
# We deliberately exclude Bird/Lime January so all operators
# are compared over the same weekday calendar.
# ============================================================

def build_2024_common_daily(
    daily
):

    data = daily.loc[
        (daily["year"] == 2024)
        &
        (
            daily[
                "date"
            ].between(
                "2024-02-01",
                "2024-12-31",
                inclusive="both",
            )
        )
    ].copy()

    check = (
        data.groupby(
            "operator"
        )[
            "date"
        ]
        .nunique()
    )

    assert (
        check == 335
    ).all(), (
        "2024 common detailed window must "
        "contain 335 days per operator."
    )

    expected_trip_totals = {
        "bird": 369969,
        "lime": 1147117,
        "voi": 100879,
    }

    actual = (
        data.groupby(
            "operator"
        )[
            "trip_count"
        ]
        .sum()
        .to_dict()
    )

    assert (
        actual
        ==
        expected_trip_totals
    ), (
        "2024 common detailed trip totals "
        "do not reconcile."
    )

    return data


# ============================================================
# MATCHED YOY DAILY WINDOW
#
# Already created as:
# 2024 Feb 1-Apr 29 excluding Feb 29
# 2025 Feb 1-Apr 29
#
# 88 days each.
# ============================================================

def validate_matched_daily(
    matched
):

    check = (
        matched.groupby(
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

    return matched.copy()


# ============================================================
# MONTH -> SEASON
# ============================================================

def assign_season(
    month,
):

    if month in [
        12,
        1,
        2,
    ]:
        return "Winter"

    if month in [
        3,
        4,
        5,
    ]:
        return "Spring"

    if month in [
        6,
        7,
        8,
    ]:
        return "Summer"

    if month in [
        9,
        10,
        11,
    ]:
        return "Autumn"

    raise ValueError(
        month
    )


# ============================================================
# 2024 SEASONAL PROFILE
#
# Uses monthly source-period counts.
#
# This permits VOI January 2024 to be included correctly.
# ============================================================

def build_2024_seasonal_profile(
    monthly
):

    data = monthly.loc[
        monthly[
            "year"
        ] == 2024
    ].copy()

    period = pd.PeriodIndex(
        data[
            "source_period"
        ],
        freq="M",
    )

    data[
        "month_number"
    ] = period.month

    data[
        "days_in_month"
    ] = period.days_in_month

    data[
        "season"
    ] = (
        data[
            "month_number"
        ]
        .map(
            assign_season
        )
    )

    # --------------------------------------------------------
    # Weighted seasonal daily rate:
    #
    # total seasonal trips / total seasonal calendar days
    #
    # This is preferable to taking an unweighted mean of
    # monthly daily rates.
    # --------------------------------------------------------

    seasonal = (
        data.groupby(
            [
                "operator",
                "season",
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
            months=(
                "source_period",
                "nunique",
            ),
        )
    )

    assert (
        seasonal[
            "months"
        ] == 3
    ).all()

    seasonal[
        "avg_trips_per_calendar_day"
    ] = (
        seasonal[
            "trips"
        ]
        /
        seasonal[
            "calendar_days"
        ]
    )

    annual = (
        data.groupby(
            "operator",
            as_index=False,
        )
        .agg(
            annual_trips=(
                "trip_count",
                "sum",
            ),
            annual_calendar_days=(
                "days_in_month",
                "sum",
            ),
        )
    )

    annual[
        "annual_avg_daily_trips"
    ] = (
        annual[
            "annual_trips"
        ]
        /
        annual[
            "annual_calendar_days"
        ]
    )

    seasonal = seasonal.merge(
        annual[
            [
                "operator",
                "annual_avg_daily_trips",
            ]
        ],
        on="operator",
        how="left",
        validate="many_to_one",
    )

    seasonal[
        "seasonal_activity_index"
    ] = (
        seasonal[
            "avg_trips_per_calendar_day"
        ]
        /
        seasonal[
            "annual_avg_daily_trips"
        ]
        * 100
    )

    seasonal[
        "season_order"
    ] = (
        seasonal[
            "season"
        ]
        .map(
            {
                "Winter": 1,
                "Spring": 2,
                "Summer": 3,
                "Autumn": 4,
            }
        )
    )

    seasonal = seasonal.sort_values(
        [
            "operator",
            "season_order",
        ]
    )

    # --------------------------------------------------------
    # Reconciliation
    # --------------------------------------------------------

    check = (
        seasonal.groupby(
            "operator"
        )[
            "trips"
        ]
        .sum()
        .to_dict()
    )

    expected = {
        "bird": 390844,
        "lime": 1196200,
        "voi": 106115,
    }

    assert (
        check == expected
    ), (
        "Seasonal 2024 totals do not reconcile."
    )

    return seasonal


# ============================================================
# SYSTEM-WIDE SEASONAL PROFILE
# ============================================================

def build_system_seasonal(
    seasonal
):

    system = (
        seasonal.groupby(
            [
                "season",
                "season_order",
                "calendar_days",
            ],
            as_index=False,
        )
        .agg(
            system_trips=(
                "trips",
                "sum",
            ),
            operators_present=(
                "operator",
                "nunique",
            ),
        )
    )

    assert (
        system[
            "operators_present"
        ] == 3
    ).all()

    system[
        "system_avg_trips_per_day"
    ] = (
        system[
            "system_trips"
        ]
        /
        system[
            "calendar_days"
        ]
    )

    assert (
        int(
            system[
                "system_trips"
            ].sum()
        )
        == 1693159
    )

    return system.sort_values(
        "season_order"
    )


# ============================================================
# SEASONAL OPERATOR SHARES
# ============================================================

def build_seasonal_operator_shares(
    seasonal
):

    totals = (
        seasonal.groupby(
            "season"
        )[
            "trips"
        ]
        .sum()
        .rename(
            "system_season_trips"
        )
        .reset_index()
    )

    shares = seasonal.merge(
        totals,
        on="season",
        how="left",
        validate="many_to_one",
    )

    shares[
        "observed_trip_share_pct"
    ] = (
        shares[
            "trips"
        ]
        /
        shares[
            "system_season_trips"
        ]
        * 100
    )

    return shares


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 1 — WEEKDAY, WEEKEND AND SEASONAL USAGE PATTERNS"
    )

    print(
        "=" * 110
    )

    daily, matched, monthly = (
        load_data()
    )

    # ========================================================
    # 2024 COMMON WEEKDAY ANALYSIS
    # ========================================================

    common_2024 = (
        build_2024_common_daily(
            daily
        )
    )

    weekday_2024 = (
        build_weekday_profile(
            common_2024
        )
    )

    (
        day_group_2024,
        weekend_2024,
    ) = (
        build_weekday_weekend_summary(
            common_2024
        )
    )

    # ========================================================
    # MATCHED YOY WEEKDAY ANALYSIS
    # ========================================================

    matched = (
        validate_matched_daily(
            matched
        )
    )

    weekday_matched = (
        build_weekday_profile(
            matched
        )
    )

    (
        day_group_matched,
        weekend_matched,
    ) = (
        build_weekday_weekend_summary(
            matched
        )
    )

    # ========================================================
    # 2024 SEASONAL ANALYSIS
    # ========================================================

    seasonal_2024 = (
        build_2024_seasonal_profile(
            monthly
        )
    )

    system_seasonal_2024 = (
        build_system_seasonal(
            seasonal_2024
        )
    )

    seasonal_shares_2024 = (
        build_seasonal_operator_shares(
            seasonal_2024
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    common_2024.to_parquet(
        OUTPUT_DIR
        / "daily_2024_common_detailed.parquet",
        index=False,
    )

    weekday_2024.to_csv(
        TABLE_DIR
        / "weekday_profile_2024_common.csv",
        index=False,
    )

    day_group_2024.to_csv(
        TABLE_DIR
        / "weekday_weekend_detail_2024_common.csv",
        index=False,
    )

    weekend_2024.to_csv(
        TABLE_DIR
        / "weekday_weekend_summary_2024_common.csv",
        index=False,
    )

    weekday_matched.to_csv(
        TABLE_DIR
        / "weekday_profile_matched_yoy.csv",
        index=False,
    )

    day_group_matched.to_csv(
        TABLE_DIR
        / "weekday_weekend_detail_matched_yoy.csv",
        index=False,
    )

    weekend_matched.to_csv(
        TABLE_DIR
        / "weekday_weekend_summary_matched_yoy.csv",
        index=False,
    )

    seasonal_2024.to_csv(
        TABLE_DIR
        / "seasonal_profile_2024.csv",
        index=False,
    )

    system_seasonal_2024.to_csv(
        TABLE_DIR
        / "system_seasonal_profile_2024.csv",
        index=False,
    )

    seasonal_shares_2024.to_csv(
        TABLE_DIR
        / "seasonal_operator_shares_2024.csv",
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
        "\n2024 common-window weekday profile "
        "(Feb 1-Dec 31):"
    )

    display_weekday = (
        weekday_2024.copy()
    )

    for col in [
        "mean_daily_trips",
        "median_daily_trips",
        "std_daily_trips",
        "overall_mean_daily_trips",
        "weekday_activity_index",
    ]:

        display_weekday[col] = (
            display_weekday[col]
            .round(2)
        )

    print(
        display_weekday.to_string(
            index=False
        )
    )

    print(
        "\n2024 weekday vs weekend summary:"
    )

    display_weekend = (
        weekend_2024.copy()
    )

    for col in [
        "weekday_mean_daily_trips",
        "weekend_mean_daily_trips",
        "weekend_uplift_pct",
    ]:

        display_weekend[col] = (
            display_weekend[col]
            .round(2)
        )

    print(
        display_weekend.to_string(
            index=False
        )
    )

    print(
        "\nMatched Feb-Apr 2024 vs 2025 "
        "weekday/weekend summary:"
    )

    display_matched = (
        weekend_matched.copy()
    )

    for col in [
        "weekday_mean_daily_trips",
        "weekend_mean_daily_trips",
        "weekend_uplift_pct",
    ]:

        display_matched[col] = (
            display_matched[col]
            .round(2)
        )

    print(
        display_matched.to_string(
            index=False
        )
    )

    print(
        "\n2024 seasonal operator profile:"
    )

    display_seasonal = (
        seasonal_2024.copy()
    )

    for col in [
        "avg_trips_per_calendar_day",
        "annual_avg_daily_trips",
        "seasonal_activity_index",
    ]:

        display_seasonal[col] = (
            display_seasonal[col]
            .round(2)
        )

    print(
        display_seasonal.to_string(
            index=False
        )
    )

    print(
        "\n2024 system seasonal profile:"
    )

    display_system = (
        system_seasonal_2024.copy()
    )

    display_system[
        "system_avg_trips_per_day"
    ] = (
        display_system[
            "system_avg_trips_per_day"
        ]
        .round(2)
    )

    print(
        display_system.to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
        "\n- Weekday comparison for 2024 uses Feb-Dec, the common detailed-time window."
        "\n- VOI January 2024 is not treated as zero weekday activity."
        "\n- Matched YoY weekday analysis uses the same 88-day Feb-Apr window."
        "\n- Weekday activity index = 100 at each operator-year's overall daily mean."
        "\n- Weekend uplift compares average calendar-day activity, not total weekend counts."
        "\n- Seasonal 2024 analysis uses source-period monthly counts and therefore includes "
        "VOI January correctly."
        "\n- Seasonal daily rates are weighted by actual calendar days."
        "\n- Observed trip share is not interpreted as commercial market share."
    )


if __name__ == "__main__":
    main()