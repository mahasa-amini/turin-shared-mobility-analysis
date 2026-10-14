from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "temporal"
    / "monthly_trip_counts.parquet"
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


# ============================================================
# LOAD
# ============================================================

def load_monthly():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            INPUT_FILE
        )

    df = pd.read_parquet(
        INPUT_FILE
    )

    df["period"] = pd.PeriodIndex(
        df["source_period"],
        freq="M",
    )

    df["month_number"] = (
        df["period"].dt.month
    )

    df["month_name"] = (
        df["period"]
        .dt.to_timestamp()
        .dt.month_name()
    )

    df["days_in_month"] = (
        df["period"]
        .dt.days_in_month
    )

    df["trips_per_calendar_day"] = (
        df["trip_count"]
        /
        df["days_in_month"]
    )

    return df


# ============================================================
# MONTH-TO-MONTH FEATURES
# ============================================================

def add_monthly_features(df):

    df = df.copy()

    df = df.sort_values(
        [
            "operator",
            "year",
            "period",
        ]
    )

    df["previous_month_trips"] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )["trip_count"]
        .shift(1)
    )

    df["month_over_month_change_pct"] = (
        (
            df["trip_count"]
            /
            df["previous_month_trips"]
        )
        - 1
    ) * 100

    # 3-month moving average
    df["rolling_mean_3m"] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )["trip_count"]
        .transform(
            lambda s:
                s.rolling(
                    window=3,
                    center=True,
                    min_periods=2,
                ).mean()
        )
    )

    return df


# ============================================================
# FULL-YEAR 2024 SUMMARY
# ============================================================

def build_2024_full_year_summary(df):

    full = df.loc[
        df["year"] == 2024
    ].copy()

    records = []

    for operator, group in full.groupby(
        "operator"
    ):

        group = group.sort_values(
            "month_number"
        )

        assert (
            group["source_period"].nunique()
            == 12
        )

        mean = (
            group["trip_count"].mean()
        )

        median = (
            group["trip_count"].median()
        )

        std = (
            group["trip_count"].std()
        )

        cv = (
            std / mean
            if mean > 0
            else np.nan
        )

        min_idx = (
            group["trip_count"].idxmin()
        )

        max_idx = (
            group["trip_count"].idxmax()
        )

        min_row = group.loc[
            min_idx
        ]

        max_row = group.loc[
            max_idx
        ]

        x = (
            group["month_number"]
            .to_numpy(
                dtype=float
            )
        )

        y = (
            group["trip_count"]
            .to_numpy(
                dtype=float
            )
        )

        slope = np.polyfit(
            x,
            y,
            1,
        )[0]

        normalized_slope = (
            slope / mean * 100
            if mean > 0
            else np.nan
        )

        # ----------------------------------------------------
        # Seasonal blocks
        #
        # Winter = Jan-Feb-Dec
        # Spring = Mar-May
        # Summer = Jun-Aug
        # Autumn = Sep-Nov
        # ----------------------------------------------------

        winter = group.loc[
            group[
                "month_number"
            ].isin(
                [1, 2, 12]
            ),
            "trips_per_calendar_day"
        ].mean()

        spring = group.loc[
            group[
                "month_number"
            ].isin(
                [3, 4, 5]
            ),
            "trips_per_calendar_day"
        ].mean()

        summer = group.loc[
            group[
                "month_number"
            ].isin(
                [6, 7, 8]
            ),
            "trips_per_calendar_day"
        ].mean()

        autumn = group.loc[
            group[
                "month_number"
            ].isin(
                [9, 10, 11]
            ),
            "trips_per_calendar_day"
        ].mean()

        records.append(
            {
                "operator":
                    operator,

                "year":
                    2024,

                "total_trips":
                    int(
                        group[
                            "trip_count"
                        ].sum()
                    ),

                "mean_monthly_trips":
                    mean,

                "median_monthly_trips":
                    median,

                "std_monthly_trips":
                    std,

                "coefficient_of_variation":
                    cv,

                "minimum_month":
                    min_row[
                        "source_period"
                    ],

                "minimum_month_trips":
                    int(
                        min_row[
                            "trip_count"
                        ]
                    ),

                "maximum_month":
                    max_row[
                        "source_period"
                    ],

                "maximum_month_trips":
                    int(
                        max_row[
                            "trip_count"
                        ]
                    ),

                "linear_slope_trips_per_month":
                    slope,

                "normalized_slope_pct_of_mean_per_month":
                    normalized_slope,

                "winter_avg_daily_trips":
                    winter,

                "spring_avg_daily_trips":
                    spring,

                "summer_avg_daily_trips":
                    summer,

                "autumn_avg_daily_trips":
                    autumn,
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# 2025 OPERATOR-SPECIFIC DESCRIPTIVE SUMMARY
#
# NOT directly comparable because coverage differs.
# ============================================================

def build_2025_available_summary(df):

    available = df.loc[
        df["year"] == 2025
    ].copy()

    records = []

    for operator, group in available.groupby(
        "operator"
    ):

        group = group.sort_values(
            "period"
        )

        full_months = group.loc[
            group[
                "is_full_source_month"
            ]
        ].copy()

        records.append(
            {
                "operator":
                    operator,

                "months_present":
                    group[
                        "source_period"
                    ].nunique(),

                "full_months_present":
                    int(
                        group[
                            "is_full_source_month"
                        ].sum()
                    ),

                "first_month":
                    group[
                        "source_period"
                    ].min(),

                "last_month":
                    group[
                        "source_period"
                    ].max(),

                "available_period_trips":
                    int(
                        group[
                            "trip_count"
                        ].sum()
                    ),

                "full_month_only_trips":
                    int(
                        full_months[
                            "trip_count"
                        ].sum()
                    ),

                "mean_full_month_trips":
                    full_months[
                        "trip_count"
                    ].mean(),

                "mean_full_month_daily_rate":
                    full_months[
                        "trips_per_calendar_day"
                    ].mean(),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# MATCHED JAN-MAR YOY DATA
#
# Jan, Feb, Mar are complete for all operators in both years.
# ============================================================

def build_matched_yoy_months(df):

    matched = df.loc[
        df["year"].isin(
            [
                2024,
                2025,
            ]
        )
        &
        df["month_number"].isin(
            [
                1,
                2,
                3,
            ]
        )
        &
        df[
            "is_full_source_month"
        ]
    ].copy()

    matched[
        "matched_month"
    ] = (
        matched[
            "month_number"
        ]
    )

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
    ).all(), (
        "Matched Jan-Mar period does not contain "
        "three full months for every operator-year."
    )

    return matched


# ============================================================
# MONTH-SPECIFIC YOY COMPARISON
# ============================================================

def build_month_specific_yoy(matched):

    base = matched[
        [
            "operator",
            "year",
            "month_number",
            "month_name",
            "trip_count",
            "trips_per_calendar_day",
        ]
    ].copy()

    count_pivot = (
        base.pivot(
            index=[
                "operator",
                "month_number",
                "month_name",
            ],
            columns="year",
            values="trip_count",
        )
        .reset_index()
    )

    count_pivot.columns.name = None

    count_pivot = (
        count_pivot.rename(
            columns={
                2024:
                    "trips_2024",
                2025:
                    "trips_2025",
            }
        )
    )

    rate_pivot = (
        base.pivot(
            index=[
                "operator",
                "month_number",
                "month_name",
            ],
            columns="year",
            values="trips_per_calendar_day",
        )
        .reset_index()
    )

    rate_pivot.columns.name = None

    rate_pivot = (
        rate_pivot.rename(
            columns={
                2024:
                    "avg_daily_rate_2024",
                2025:
                    "avg_daily_rate_2025",
            }
        )
    )

    comparison = count_pivot.merge(
        rate_pivot,
        on=[
            "operator",
            "month_number",
            "month_name",
        ],
        validate="one_to_one",
    )

    comparison[
        "trip_count_pct_change"
    ] = (
        (
            comparison[
                "trips_2025"
            ]
            /
            comparison[
                "trips_2024"
            ]
        )
        - 1
    ) * 100

    comparison[
        "daily_rate_pct_change"
    ] = (
        (
            comparison[
                "avg_daily_rate_2025"
            ]
            /
            comparison[
                "avg_daily_rate_2024"
            ]
        )
        - 1
    ) * 100

    return comparison


# ============================================================
# AGGREGATED JAN-MAR YOY SUMMARY
# ============================================================

def build_matched_yoy_summary(
    matched
):

    summary = (
        matched.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            months=(
                "source_period",
                "nunique",
            ),
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

    summary[
        "avg_trips_per_calendar_day"
    ] = (
        summary[
            "trips"
        ]
        /
        summary[
            "calendar_days"
        ]
    )

    pivot = (
        summary.pivot(
            index="operator",
            columns="year",
            values=[
                "trips",
                "avg_trips_per_calendar_day",
            ],
        )
    )

    pivot.columns = [
        f"{metric}_{year}"
        for metric, year
        in pivot.columns
    ]

    pivot = (
        pivot
        .reset_index()
    )

    pivot[
        "trip_pct_change_2025_vs_2024"
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
        "daily_rate_pct_change_2025_vs_2024"
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

    return (
        summary,
        pivot,
    )


# ============================================================
# SYSTEM 2024 MONTHLY TOTALS
# ============================================================

def build_system_2024(df):

    full = df.loc[
        df["year"] == 2024
    ].copy()

    system = (
        full.groupby(
            [
                "period",
                "source_period",
                "month_number",
                "month_name",
                "days_in_month",
            ],
            as_index=False,
        )
        .agg(
            system_trip_count=(
                "trip_count",
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
        "system_trips_per_calendar_day"
    ] = (
        system[
            "system_trip_count"
        ]
        /
        system[
            "days_in_month"
        ]
    )

    return system


# ============================================================
# 2024 OPERATOR MONTHLY SHARES
# ============================================================

def build_operator_2024_shares(df):

    full = df.loc[
        df["year"] == 2024
    ].copy()

    totals = (
        full.groupby(
            "source_period"
        )[
            "trip_count"
        ]
        .sum()
        .rename(
            "system_trip_count"
        )
        .reset_index()
    )

    shares = full.merge(
        totals,
        on="source_period",
        how="left",
    )

    shares[
        "operator_share_pct"
    ] = (
        shares[
            "trip_count"
        ]
        /
        shares[
            "system_trip_count"
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
        "EXERCISE 1 — MONTHLY MOBILITY TREND ANALYSIS"
    )

    print(
        "=" * 110
    )

    monthly = (
        load_monthly()
    )

    monthly = (
        add_monthly_features(
            monthly
        )
    )

    full_2024_summary = (
        build_2024_full_year_summary(
            monthly
        )
    )

    available_2025 = (
        build_2025_available_summary(
            monthly
        )
    )

    matched = (
        build_matched_yoy_months(
            monthly
        )
    )

    month_specific_yoy = (
        build_month_specific_yoy(
            matched
        )
    )

    (
        matched_summary,
        matched_comparison,
    ) = (
        build_matched_yoy_summary(
            matched
        )
    )

    system_2024 = (
        build_system_2024(
            monthly
        )
    )

    shares_2024 = (
        build_operator_2024_shares(
            monthly
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    monthly.to_parquet(
        OUTPUT_DIR
        / "monthly_trip_counts_with_trends.parquet",
        index=False,
    )

    matched.to_parquet(
        OUTPUT_DIR
        / "monthly_matched_yoy.parquet",
        index=False,
    )

    full_2024_summary.to_csv(
        TABLE_DIR
        / "monthly_2024_full_year_summary.csv",
        index=False,
    )

    available_2025.to_csv(
        TABLE_DIR
        / "monthly_2025_available_summary.csv",
        index=False,
    )

    month_specific_yoy.to_csv(
        TABLE_DIR
        / "monthly_month_specific_yoy.csv",
        index=False,
    )

    matched_summary.to_csv(
        TABLE_DIR
        / "monthly_jan_mar_yoy_summary.csv",
        index=False,
    )

    matched_comparison.to_csv(
        TABLE_DIR
        / "monthly_jan_mar_yoy_comparison.csv",
        index=False,
    )

    system_2024.to_csv(
        TABLE_DIR
        / "monthly_system_2024.csv",
        index=False,
    )

    shares_2024.to_csv(
        TABLE_DIR
        / "monthly_operator_shares_2024.csv",
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
        "\n2024 full-year monthly summary:"
    )

    display = (
        full_2024_summary.copy()
    )

    numeric_cols = [
        "mean_monthly_trips",
        "median_monthly_trips",
        "std_monthly_trips",
        "coefficient_of_variation",
        "linear_slope_trips_per_month",
        "normalized_slope_pct_of_mean_per_month",
        "winter_avg_daily_trips",
        "spring_avg_daily_trips",
        "summer_avg_daily_trips",
        "autumn_avg_daily_trips",
    ]

    for col in numeric_cols:

        display[col] = (
            display[col]
            .round(2)
        )

    print(
        display.to_string(
            index=False
        )
    )

    print(
        "\n2025 available-period summary "
        "(descriptive only; coverage differs):"
    )

    display_2025 = (
        available_2025.copy()
    )

    for col in [
        "mean_full_month_trips",
        "mean_full_month_daily_rate",
    ]:

        display_2025[col] = (
            display_2025[col]
            .round(2)
        )

    print(
        display_2025.to_string(
            index=False
        )
    )

    print(
        "\nMatched Jan-Mar 2024 vs 2025:"
    )

    matched_display = (
        matched_comparison.copy()
    )

    numeric = [
        "trips_2024",
        "trips_2025",
        "avg_trips_per_calendar_day_2024",
        "avg_trips_per_calendar_day_2025",
        "trip_pct_change_2025_vs_2024",
        "daily_rate_pct_change_2025_vs_2024",
    ]

    for col in numeric:

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
        "\nMonth-specific YoY changes:"
    )

    month_display = (
        month_specific_yoy.copy()
    )

    for col in [
        "avg_daily_rate_2024",
        "avg_daily_rate_2025",
        "trip_count_pct_change",
        "daily_rate_pct_change",
    ]:

        month_display[col] = (
            month_display[col]
            .round(2)
        )

    print(
        month_display.to_string(
            index=False
        )
    )

    print(
        "\n2024 system-wide monthly extrema:"
    )

    minimum = system_2024.loc[
        system_2024[
            "system_trip_count"
        ].idxmin()
    ]

    maximum = system_2024.loc[
        system_2024[
            "system_trip_count"
        ].idxmax()
    ]

    print(
        f"Minimum month: "
        f"{minimum['source_period']} | "
        f"{int(minimum['system_trip_count']):,} trips | "
        f"{minimum['system_trips_per_calendar_day']:.2f}/day"
    )

    print(
        f"Maximum month: "
        f"{maximum['source_period']} | "
        f"{int(maximum['system_trip_count']):,} trips | "
        f"{maximum['system_trips_per_calendar_day']:.2f}/day"
    )

    print(
        "\nIMPORTANT:"
        "\n- Monthly counts use source_period and therefore include "
        "VOI January 2024 correctly."
        "\n- Full-year cross-operator comparison is valid for 2024."
        "\n- 2025 available-period totals are descriptive only because "
        "operator coverage differs."
        "\n- Jan-Mar is the common full-month YoY comparison window."
        "\n- Trips per calendar day are used to control for month-length "
        "and leap-year differences."
        "\n- Linear monthly slopes are descriptive, not forecasting models."
    )


if __name__ == "__main__":
    main()