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
    / "daily_trip_counts.parquet"
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

def load_daily():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            INPUT_FILE
        )

    df = pd.read_parquet(
        INPUT_FILE
    )

    df["date"] = pd.to_datetime(
        df["date"]
    )

    return df


# ============================================================
# ADD DAILY TREND FEATURES
# ============================================================

def add_daily_features(df):

    df = df.copy()

    df = df.sort_values(
        [
            "operator",
            "year",
            "date",
        ]
    )

    # --------------------------------------------------------
    # 7-day centered rolling mean
    #
    # Used only as descriptive smoothing.
    # Raw daily counts remain unchanged.
    # --------------------------------------------------------

    df[
        "rolling_mean_7d"
    ] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )["trip_count"]
        .transform(
            lambda s:
                s.rolling(
                    window=7,
                    center=True,
                    min_periods=4,
                ).mean()
        )
    )

    # --------------------------------------------------------
    # 28-day rolling mean
    #
    # Helps reveal slower seasonal movement without
    # replacing monthly analysis.
    # --------------------------------------------------------

    df[
        "rolling_mean_28d"
    ] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )["trip_count"]
        .transform(
            lambda s:
                s.rolling(
                    window=28,
                    center=True,
                    min_periods=14,
                ).mean()
        )
    )

    return df


# ============================================================
# DESCRIPTIVE DAILY SUMMARY
#
# Uses the operator-year's valid detailed timestamp coverage.
# This describes each available dataset, but is NOT used
# directly for 2024-vs-2025 comparison.
# ============================================================

def build_daily_summary(df):

    records = []

    for (
        operator,
        year
    ), group in df.groupby(
        [
            "operator",
            "year",
        ]
    ):

        group = group.sort_values(
            "date"
        )

        mean = (
            group[
                "trip_count"
            ].mean()
        )

        std = (
            group[
                "trip_count"
            ].std()
        )

        median = (
            group[
                "trip_count"
            ].median()
        )

        min_idx = (
            group[
                "trip_count"
            ].idxmin()
        )

        max_idx = (
            group[
                "trip_count"
            ].idxmax()
        )

        minimum = (
            group.loc[
                min_idx
            ]
        )

        maximum = (
            group.loc[
                max_idx
            ]
        )

        zero_days = int(
            (
                group[
                    "trip_count"
                ] == 0
            ).sum()
        )

        # ----------------------------------------------------
        # Very-low-volume days
        #
        # Diagnostic only.
        # A day below 20% of the operator-year median is
        # identified for later inspection.
        # It is NOT automatically called an outage.
        # ----------------------------------------------------

        low_threshold = (
            0.20 * median
        )

        very_low_days = int(
            (
                group[
                    "trip_count"
                ] < low_threshold
            ).sum()
        )

        cv = (
            std / mean
            if mean > 0
            else np.nan
        )

        records.append(
            {
                "operator":
                    operator,

                "year":
                    int(year),

                "coverage_start":
                    group[
                        "date"
                    ].min(),

                "coverage_end":
                    group[
                        "date"
                    ].max(),

                "days":
                    group[
                        "date"
                    ].nunique(),

                "total_trips":
                    int(
                        group[
                            "trip_count"
                        ].sum()
                    ),

                "mean_daily_trips":
                    mean,

                "median_daily_trips":
                    median,

                "std_daily_trips":
                    std,

                "coefficient_of_variation":
                    cv,

                "min_daily_trips":
                    int(
                        minimum[
                            "trip_count"
                        ]
                    ),

                "min_date":
                    minimum[
                        "date"
                    ],

                "max_daily_trips":
                    int(
                        maximum[
                            "trip_count"
                        ]
                    ),

                "max_date":
                    maximum[
                        "date"
                    ],

                "zero_trip_days":
                    zero_days,

                "very_low_days_below_20pct_median":
                    very_low_days,
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# COMMON WITHIN-YEAR WINDOWS
#
# These are useful for pooled Bird/Lime/VOI comparison
# within a particular year.
# ============================================================

def build_common_window_summary(df):

    common = df.loc[
        df[
            "within_common_detailed_window"
        ]
    ].copy()

    summary = (
        common.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            days=(
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

    summary[
        "coefficient_of_variation"
    ] = (
        summary[
            "std_daily_trips"
        ]
        /
        summary[
            "mean_daily_trips"
        ]
    )

    return summary


# ============================================================
# MATCHED 2024-vs-2025 WINDOW
#
# Exact season:
# February 1 – April 29
#
# Feb 29 2024 is excluded only from the YoY comparison
# so both years contain exactly 88 calendar days.
# ============================================================

def build_matched_yoy_data(df):

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

    for year, (
        start,
        end
    ) in windows.items():

        subset = df.loc[
            (df["year"] == year)
            &
            df[
                "date"
            ].between(
                start,
                end,
                inclusive="both",
            )
        ].copy()

        # Remove leap day ONLY for fair YoY normalization.
        if year == 2024:

            subset = subset.loc[
                ~(
                    (
                        subset[
                            "date"
                        ].dt.month == 2
                    )
                    &
                    (
                        subset[
                            "date"
                        ].dt.day == 29
                    )
                )
            ]

        # Comparable calendar key
        subset[
            "month_day"
        ] = (
            subset[
                "date"
            ]
            .dt.strftime(
                "%m-%d"
            )
        )

        parts.append(
            subset
        )

    matched = pd.concat(
        parts,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Validation:
    # each operator must have 88 comparison days per year
    # --------------------------------------------------------

    day_check = (
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
        day_check == 88
    ).all(), (
        "Matched YoY window does not contain "
        "88 days for every operator-year."
    )

    return matched


# ============================================================
# MATCHED YOY SUMMARY
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
            days=(
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

    summary[
        "coefficient_of_variation"
    ] = (
        summary[
            "std_daily_trips"
        ]
        /
        summary[
            "mean_daily_trips"
        ]
    )

    # --------------------------------------------------------
    # Pivot for explicit 2024 -> 2025 comparison
    # --------------------------------------------------------

    pivot = (
        summary.pivot(
            index="operator",
            columns="year",
            values="mean_daily_trips",
        )
        .reset_index()
    )

    pivot.columns.name = None

    pivot = pivot.rename(
        columns={
            2024:
                "mean_daily_trips_2024",
            2025:
                "mean_daily_trips_2025",
        }
    )

    pivot[
        "absolute_change"
    ] = (
        pivot[
            "mean_daily_trips_2025"
        ]
        -
        pivot[
            "mean_daily_trips_2024"
        ]
    )

    pivot[
        "pct_change_2025_vs_2024"
    ] = (
        (
            pivot[
                "mean_daily_trips_2025"
            ]
            /
            pivot[
                "mean_daily_trips_2024"
            ]
        )
        - 1
    ) * 100

    return (
        summary,
        pivot,
    )


# ============================================================
# LOW-DAY DIAGNOSTIC
# ============================================================

def build_low_day_diagnostic(df):

    parts = []

    for (
        operator,
        year
    ), group in df.groupby(
        [
            "operator",
            "year",
        ]
    ):

        median = (
            group[
                "trip_count"
            ].median()
        )

        threshold = (
            0.20 * median
        )

        low = group.loc[
            group[
                "trip_count"
            ] < threshold
        ].copy()

        low[
            "operator_year_median"
        ] = median

        low[
            "threshold_20pct_median"
        ] = threshold

        parts.append(
            low
        )

    if not parts:

        return pd.DataFrame()

    result = pd.concat(
        parts,
        ignore_index=True
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
        "EXERCISE 1 — DAILY MOBILITY TREND ANALYSIS"
    )

    print(
        "=" * 110
    )

    daily = load_daily()

    daily = add_daily_features(
        daily
    )

    overall_summary = (
        build_daily_summary(
            daily
        )
    )

    common_summary = (
        build_common_window_summary(
            daily
        )
    )

    matched = (
        build_matched_yoy_data(
            daily
        )
    )

    (
        matched_summary,
        yoy_comparison,
    ) = (
        build_matched_yoy_summary(
            matched
        )
    )

    low_days = (
        build_low_day_diagnostic(
            daily
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    daily.to_parquet(
        OUTPUT_DIR
        / "daily_trip_counts_with_trends.parquet",
        index=False,
    )

    matched.to_parquet(
        OUTPUT_DIR
        / "daily_trip_counts_matched_yoy.parquet",
        index=False,
    )

    overall_summary.to_csv(
        TABLE_DIR
        / "daily_trend_summary.csv",
        index=False,
    )

    common_summary.to_csv(
        TABLE_DIR
        / "daily_common_window_summary.csv",
        index=False,
    )

    matched_summary.to_csv(
        TABLE_DIR
        / "daily_matched_yoy_summary.csv",
        index=False,
    )

    yoy_comparison.to_csv(
        TABLE_DIR
        / "daily_matched_yoy_comparison.csv",
        index=False,
    )

    low_days.to_csv(
        TABLE_DIR
        / "daily_very_low_volume_diagnostic.csv",
        index=False,
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    pd.set_option(
        "display.max_columns",
        None
    )

    print(
        "\nDaily descriptive summary "
        "(operator-specific available coverage):"
    )

    display = (
        overall_summary.copy()
    )

    for col in [
        "mean_daily_trips",
        "median_daily_trips",
        "std_daily_trips",
        "coefficient_of_variation",
    ]:

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
        "\nMatched YoY window:"
        "\n2024: Feb 1 – Apr 29, excluding Feb 29"
        "\n2025: Feb 1 – Apr 29"
        "\n88 days per operator-year"
    )

    matched_display = (
        matched_summary.copy()
    )

    for col in [
        "mean_daily_trips",
        "median_daily_trips",
        "std_daily_trips",
        "coefficient_of_variation",
    ]:

        matched_display[col] = (
            matched_display[col]
            .round(2)
        )

    print(
        "\nMatched-period descriptive statistics:"
    )

    print(
        matched_display.to_string(
            index=False
        )
    )

    yoy_display = (
        yoy_comparison.copy()
    )

    for col in [
        "mean_daily_trips_2024",
        "mean_daily_trips_2025",
        "absolute_change",
        "pct_change_2025_vs_2024",
    ]:

        yoy_display[col] = (
            yoy_display[col]
            .round(2)
        )

    print(
        "\n2025 vs 2024 matched-period "
        "average daily trips:"
    )

    print(
        yoy_display.to_string(
            index=False
        )
    )

    print(
        "\nVery-low-volume diagnostic:"
    )

    low_summary = (
        low_days.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            low_days=(
                "date",
                "count",
            ),
            minimum_trip_count=(
                "trip_count",
                "min",
            ),
        )
    )

    if low_summary.empty:

        print(
            "No days below 20% of "
            "operator-year median."
        )

    else:

        print(
            low_summary.to_string(
                index=False
            )
        )

    print(
        "\nIMPORTANT:"
        "\n- Raw daily counts were not modified."
        "\n- Rolling means are descriptive smoothing only."
        "\n- Operator-specific annual/partial-year summaries are not "
        "automatically comparable across years."
        "\n- Year-over-year comparison uses the same seasonal window."
        "\n- February 29, 2024 is excluded only from matched YoY analysis."
        "\n- Very-low-volume days are diagnostic flags, not automatically "
        "classified as outages."
    )


if __name__ == "__main__":
    main()