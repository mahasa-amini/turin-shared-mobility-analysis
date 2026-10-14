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
    / "weekly_trip_counts.parquet"
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

def load_weekly():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            INPUT_FILE
        )

    df = pd.read_parquet(
        INPUT_FILE
    )

    df["week_start"] = pd.to_datetime(
        df["week_start"]
    )

    df["week_end"] = pd.to_datetime(
        df["week_end"]
    )

    return df


# ============================================================
# ADD TREND FEATURES
# ============================================================

def add_weekly_features(df):

    df = df.copy()

    df = df.sort_values(
        [
            "operator",
            "year",
            "week_start",
        ]
    )

    # --------------------------------------------------------
    # Sequence number inside each operator-year
    # --------------------------------------------------------

    df["week_index"] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )
        .cumcount()
        + 1
    )

    # --------------------------------------------------------
    # Four-week moving average
    #
    # Descriptive smoothing only.
    # --------------------------------------------------------

    df["rolling_mean_4w"] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )["trip_count"]
        .transform(
            lambda s:
                s.rolling(
                    window=4,
                    min_periods=2,
                ).mean()
        )
    )

    return df


# ============================================================
# SUMMARY FOR FULL WEEKS AVAILABLE TO EACH OPERATOR
# ============================================================

def build_full_week_summary(df):

    full = df.loc[
        df[
            "full_week_for_operator"
        ]
    ].copy()

    records = []

    for (
        operator,
        year
    ), group in full.groupby(
        [
            "operator",
            "year",
        ]
    ):

        group = group.sort_values(
            "week_start"
        )

        mean = (
            group[
                "trip_count"
            ].mean()
        )

        median = (
            group[
                "trip_count"
            ].median()
        )

        std = (
            group[
                "trip_count"
            ].std()
        )

        cv = (
            std / mean
            if mean > 0
            else np.nan
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

        min_row = group.loc[
            min_idx
        ]

        max_row = group.loc[
            max_idx
        ]

        # ----------------------------------------------------
        # Descriptive linear slope
        #
        # Not a causal or forecasting model.
        # ----------------------------------------------------

        x = np.arange(
            len(group),
            dtype=float,
        )

        y = (
            group[
                "trip_count"
            ]
            .to_numpy(
                dtype=float
            )
        )

        if len(group) >= 2:

            slope = np.polyfit(
                x,
                y,
                1,
            )[0]

        else:

            slope = np.nan

        normalized_slope_pct = (
            slope / mean * 100
            if mean > 0
            else np.nan
        )

        records.append(
            {
                "operator":
                    operator,

                "year":
                    int(year),

                "first_full_week":
                    group[
                        "week_start"
                    ].min(),

                "last_full_week":
                    group[
                        "week_end"
                    ].max(),

                "full_weeks":
                    len(group),

                "total_trips":
                    int(
                        group[
                            "trip_count"
                        ].sum()
                    ),

                "mean_weekly_trips":
                    mean,

                "median_weekly_trips":
                    median,

                "std_weekly_trips":
                    std,

                "coefficient_of_variation":
                    cv,

                "min_weekly_trips":
                    int(
                        min_row[
                            "trip_count"
                        ]
                    ),

                "min_week_start":
                    min_row[
                        "week_start"
                    ],

                "max_weekly_trips":
                    int(
                        max_row[
                            "trip_count"
                        ]
                    ),

                "max_week_start":
                    max_row[
                        "week_start"
                    ],

                "linear_slope_trips_per_week":
                    slope,

                "normalized_slope_pct_of_mean_per_week":
                    normalized_slope_pct,
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# COMMON FULL-WEEK DATA
# ============================================================

def build_common_week_data(df):

    common = df.loc[
        df[
            "full_week_common_all_operators"
        ]
    ].copy()

    return common


# ============================================================
# MATCHED YOY FULL-WEEK WINDOW
#
# 2024:
# Monday 5 Feb -> Sunday 28 Apr
#
# 2025:
# Monday 3 Feb -> Sunday 27 Apr
#
# Exactly 12 complete weeks per operator-year.
# ============================================================

def build_matched_yoy_weeks(df):

    windows = {
        2024: (
            pd.Timestamp(
                "2024-02-05"
            ),
            pd.Timestamp(
                "2024-04-22"
            ),
        ),
        2025: (
            pd.Timestamp(
                "2025-02-03"
            ),
            pd.Timestamp(
                "2025-04-21"
            ),
        ),
    }

    parts = []

    for year, (
        start_week,
        end_week
    ) in windows.items():

        subset = df.loc[
            (df["year"] == year)
            &
            (
                df[
                    "week_start"
                ].between(
                    start_week,
                    end_week,
                    inclusive="both",
                )
            )
            &
            (
                df[
                    "full_week_common_all_operators"
                ]
            )
        ].copy()

        subset = subset.sort_values(
            [
                "operator",
                "week_start",
            ]
        )

        subset[
            "matched_week_index"
        ] = (
            subset.groupby(
                "operator"
            )
            .cumcount()
            + 1
        )

        parts.append(
            subset
        )

    matched = pd.concat(
        parts,
        ignore_index=True
    )

    check = (
        matched.groupby(
            [
                "operator",
                "year",
            ]
        )[
            "week_start"
        ]
        .nunique()
    )

    assert (
        check == 12
    ).all(), (
        "Matched YoY weekly window does not "
        "contain exactly 12 weeks per operator-year."
    )

    return matched


# ============================================================
# MATCHED YOY SUMMARY
# ============================================================

def build_matched_yoy_summary(
    matched
):

    records = []

    for (
        operator,
        year
    ), group in matched.groupby(
        [
            "operator",
            "year",
        ]
    ):

        group = group.sort_values(
            "matched_week_index"
        )

        mean = (
            group[
                "trip_count"
            ].mean()
        )

        median = (
            group[
                "trip_count"
            ].median()
        )

        std = (
            group[
                "trip_count"
            ].std()
        )

        cv = (
            std / mean
            if mean > 0
            else np.nan
        )

        x = (
            group[
                "matched_week_index"
            ]
            .to_numpy(
                dtype=float
            )
        )

        y = (
            group[
                "trip_count"
            ]
            .to_numpy(
                dtype=float
            )
        )

        slope = np.polyfit(
            x,
            y,
            1,
        )[0]

        slope_pct = (
            slope / mean * 100
            if mean > 0
            else np.nan
        )

        # ----------------------------------------------------
        # Early vs late seasonal activity
        #
        # Average of first four weeks vs last four weeks.
        # ----------------------------------------------------

        first4_mean = (
            group.head(4)[
                "trip_count"
            ].mean()
        )

        last4_mean = (
            group.tail(4)[
                "trip_count"
            ].mean()
        )

        first_to_last_change_pct = (
            (
                last4_mean
                /
                first4_mean
            )
            - 1
        ) * 100

        records.append(
            {
                "operator":
                    operator,

                "year":
                    int(year),

                "weeks":
                    len(group),

                "trips":
                    int(
                        group[
                            "trip_count"
                        ].sum()
                    ),

                "mean_weekly_trips":
                    mean,

                "median_weekly_trips":
                    median,

                "std_weekly_trips":
                    std,

                "coefficient_of_variation":
                    cv,

                "linear_slope_trips_per_week":
                    slope,

                "normalized_slope_pct_of_mean_per_week":
                    slope_pct,

                "first_4_week_mean":
                    first4_mean,

                "last_4_week_mean":
                    last4_mean,

                "first_to_last_4w_change_pct":
                    first_to_last_change_pct,
            }
        )

    summary = pd.DataFrame(
        records
    )

    # --------------------------------------------------------
    # Explicit 2025 vs 2024 comparison
    # --------------------------------------------------------

    pivot = (
        summary.pivot(
            index="operator",
            columns="year",
            values="mean_weekly_trips",
        )
        .reset_index()
    )

    pivot.columns.name = None

    pivot = pivot.rename(
        columns={
            2024:
                "mean_weekly_trips_2024",
            2025:
                "mean_weekly_trips_2025",
        }
    )

    pivot[
        "absolute_change"
    ] = (
        pivot[
            "mean_weekly_trips_2025"
        ]
        -
        pivot[
            "mean_weekly_trips_2024"
        ]
    )

    pivot[
        "pct_change_2025_vs_2024"
    ] = (
        (
            pivot[
                "mean_weekly_trips_2025"
            ]
            /
            pivot[
                "mean_weekly_trips_2024"
            ]
        )
        - 1
    ) * 100

    return (
        summary,
        pivot,
    )


# ============================================================
# SYSTEM-WIDE COMMON WEEK TOTALS
#
# Sum of Bird + Lime + VOI for weeks where all operators
# have complete temporal coverage.
# ============================================================

def build_system_weekly_totals(
    common
):

    system = (
        common.groupby(
            [
                "year",
                "week_start",
                "week_end",
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

    return system


# ============================================================
# OPERATOR SHARES WITHIN COMMON WEEKS
# ============================================================

def build_operator_weekly_shares(
    common
):

    system = (
        common.groupby(
            [
                "year",
                "week_start",
            ]
        )["trip_count"]
        .sum()
        .rename(
            "system_trip_count"
        )
        .reset_index()
    )

    shares = common.merge(
        system,
        on=[
            "year",
            "week_start",
        ],
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
        "EXERCISE 1 — WEEKLY MOBILITY TREND ANALYSIS"
    )

    print(
        "=" * 110
    )

    weekly = load_weekly()

    weekly = add_weekly_features(
        weekly
    )

    full_summary = (
        build_full_week_summary(
            weekly
        )
    )

    common = (
        build_common_week_data(
            weekly
        )
    )

    matched = (
        build_matched_yoy_weeks(
            weekly
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

    system_weekly = (
        build_system_weekly_totals(
            common
        )
    )

    weekly_shares = (
        build_operator_weekly_shares(
            common
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    weekly.to_parquet(
        OUTPUT_DIR
        / "weekly_trip_counts_with_trends.parquet",
        index=False,
    )

    matched.to_parquet(
        OUTPUT_DIR
        / "weekly_matched_yoy.parquet",
        index=False,
    )

    full_summary.to_csv(
        TABLE_DIR
        / "weekly_full_coverage_summary.csv",
        index=False,
    )

    matched_summary.to_csv(
        TABLE_DIR
        / "weekly_matched_yoy_summary.csv",
        index=False,
    )

    yoy_comparison.to_csv(
        TABLE_DIR
        / "weekly_matched_yoy_comparison.csv",
        index=False,
    )

    system_weekly.to_csv(
        TABLE_DIR
        / "weekly_system_common_totals.csv",
        index=False,
    )

    weekly_shares.to_csv(
        TABLE_DIR
        / "weekly_operator_shares.csv",
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
        "\nFull-week descriptive summary "
        "(operator-specific coverage):"
    )

    display = (
        full_summary.copy()
    )

    numeric_cols = [
        "mean_weekly_trips",
        "median_weekly_trips",
        "std_weekly_trips",
        "coefficient_of_variation",
        "linear_slope_trips_per_week",
        "normalized_slope_pct_of_mean_per_week",
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
        "\nMatched YoY full-week window:"
        "\n2024: 5 Feb – 28 Apr"
        "\n2025: 3 Feb – 27 Apr"
        "\n12 complete Monday-Sunday weeks "
        "per operator-year"
    )

    matched_display = (
        matched_summary.copy()
    )

    matched_numeric = [
        "mean_weekly_trips",
        "median_weekly_trips",
        "std_weekly_trips",
        "coefficient_of_variation",
        "linear_slope_trips_per_week",
        "normalized_slope_pct_of_mean_per_week",
        "first_4_week_mean",
        "last_4_week_mean",
        "first_to_last_4w_change_pct",
    ]

    for col in matched_numeric:

        matched_display[col] = (
            matched_display[col]
            .round(2)
        )

    print(
        "\nMatched-period weekly statistics:"
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
        "mean_weekly_trips_2024",
        "mean_weekly_trips_2025",
        "absolute_change",
        "pct_change_2025_vs_2024",
    ]:

        yoy_display[col] = (
            yoy_display[col]
            .round(2)
        )

    print(
        "\n2025 vs 2024 matched-period "
        "mean weekly trips:"
    )

    print(
        yoy_display.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # System-wide extrema
    # --------------------------------------------------------

    print(
        "\nSystem-wide common-week extrema:"
    )

    for year, group in (
        system_weekly.groupby(
            "year"
        )
    ):

        minimum = group.loc[
            group[
                "system_trip_count"
            ].idxmin()
        ]

        maximum = group.loc[
            group[
                "system_trip_count"
            ].idxmax()
        ]

        print(
            f"\n{year}:"
        )

        print(
            "Minimum common week: "
            f"{minimum['week_start'].date()} "
            f"-> {minimum['week_end'].date()} | "
            f"{int(minimum['system_trip_count']):,} trips"
        )

        print(
            "Maximum common week: "
            f"{maximum['week_start'].date()} "
            f"-> {maximum['week_end'].date()} | "
            f"{int(maximum['system_trip_count']):,} trips"
        )

    print(
        "\nIMPORTANT:"
        "\n- Only complete Monday-Sunday weeks are used "
        "for comparative weekly analysis."
        "\n- Four-week moving averages are descriptive only."
        "\n- Linear slopes describe direction within the observed "
        "window; they are not forecasting models."
        "\n- Matched YoY comparison uses 12 full weeks in the "
        "same Feb-Apr seasonal period."
        "\n- Operator weekly shares are calculated only when "
        "all three operators have complete coverage."
    )


if __name__ == "__main__":
    main()