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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "hourly"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "hourly"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# INPUT FILES
# ============================================================

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


OPERATORS = [
    "bird",
    "lime",
    "voi",
]


WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# ============================================================
# EXPECTED COUNTS
#
# 2024 common detailed-time window:
# Feb 1-Dec 31
#
# These have already been reconciled against the temporal
# analysis.
# ============================================================

EXPECTED_2024_COMMON = {
    "bird": 369969,
    "lime": 1147117,
    "voi": 100879,
}


# ============================================================
# MATCHED FULL-WEEK YOY COUNTS
#
# 2024: Mon 5 Feb - Sun 28 Apr
# 2025: Mon 3 Feb - Sun 27 Apr
#
# Exactly:
# 12 complete Monday-Sunday weeks
# 84 calendar days
# 12 occurrences of every weekday
#
# Counts reconcile with the already validated weekly analysis.
# ============================================================

EXPECTED_MATCHED = {
    ("bird", 2024): 70766,
    ("bird", 2025): 94723,

    ("lime", 2024): 184223,
    ("lime", 2025): 326846,

    ("voi", 2024): 15882,
    ("voi", 2025): 31222,
}


MATCHED_WINDOWS = {
    2024: (
        pd.Timestamp("2024-02-05"),
        pd.Timestamp("2024-04-28"),
    ),

    2025: (
        pd.Timestamp("2025-02-03"),
        pd.Timestamp("2025-04-27"),
    ),
}


# ============================================================
# TRANSPORT PEAK DEFINITION
#
# PREDEFINED transport-analysis periods.
#
# AM peak: 07:00-09:59
# PM peak: 16:00-19:59
#
# These are NOT assumed automatically to be the actual
# e-scooter demand peaks.
# ============================================================

AM_PEAK_HOURS = {
    7,
    8,
    9,
}

PM_PEAK_HOURS = {
    16,
    17,
    18,
    19,
}

TRANSPORT_PEAK_HOURS = (
    AM_PEAK_HOURS
    | PM_PEAK_HOURS
)


# ============================================================
# LOAD HARMONIZED DATA
# ============================================================

def load_frames():

    columns = [
        "operator",
        "year",
        "trip_uid",
        "start_time_local",
        "valid_trip_record",
        "valid_temporal_detail",
    ]

    frames = {}

    for (
        operator,
        year,
    ), path in FILES.items():

        if not path.exists():

            raise FileNotFoundError(
                path
            )

        print(
            f"Loading {operator.upper()} {year}..."
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
        # Only valid trip records with detailed timestamps
        # can enter hour-of-day analysis.
        # ----------------------------------------------------

        df = df.loc[
            df[
                "valid_trip_record"
            ]
            &
            df[
                "valid_temporal_detail"
            ]
            &
            df[
                "start_time_local"
            ].notna()
        ].copy()

        assert (
            df[
                "trip_uid"
            ].is_unique
        ), (
            f"{operator} {year}: "
            "trip_uid must remain unique."
        )

        frames[
            (
                operator,
                year,
            )
        ] = df

    return frames


# ============================================================
# TEMPORAL FEATURES
# ============================================================

def add_time_features(
    df
):

    data = df.copy()

    data[
        "date"
    ] = (
        data[
            "start_time_local"
        ]
        .dt.normalize()
    )

    data[
        "hour"
    ] = (
        data[
            "start_time_local"
        ]
        .dt.hour
    )

    data[
        "weekday_number"
    ] = (
        data[
            "start_time_local"
        ]
        .dt.weekday
    )

    data[
        "weekday"
    ] = (
        data[
            "start_time_local"
        ]
        .dt.day_name()
    )

    data[
        "is_weekend"
    ] = (
        data[
            "weekday_number"
        ] >= 5
    )

    data[
        "day_type"
    ] = np.where(
        data[
            "is_weekend"
        ],
        "Weekend",
        "Weekday",
    )

    # --------------------------------------------------------
    # Conventional 3-period classification
    # --------------------------------------------------------

    data[
        "transport_period"
    ] = "Off-peak"

    data.loc[
        data[
            "hour"
        ].isin(
            AM_PEAK_HOURS
        ),
        "transport_period",
    ] = "AM peak"

    data.loc[
        data[
            "hour"
        ].isin(
            PM_PEAK_HOURS
        ),
        "transport_period",
    ] = "PM peak"

    # --------------------------------------------------------
    # Binary conventional peak / off-peak
    # --------------------------------------------------------

    data[
        "is_transport_peak"
    ] = (
        data[
            "hour"
        ].isin(
            TRANSPORT_PEAK_HOURS
        )
    )

    return data


# ============================================================
# 2024 COMMON DETAILED-TIME WINDOW
#
# Feb 1-Dec 31
#
# Bird + Lime + VOI all have detailed timestamps over
# this common comparison interval.
#
# VOI January is deliberately excluded.
# ============================================================

def build_2024_common(
    frames
):

    parts = []

    for operator in OPERATORS:

        df = frames[
            (
                operator,
                2024,
            )
        ]

        data = add_time_features(
            df
        )

        data = data.loc[
            data[
                "date"
            ].between(
                "2024-02-01",
                "2024-12-31",
                inclusive="both",
            )
        ].copy()

        actual = len(
            data
        )

        expected = (
            EXPECTED_2024_COMMON[
                operator
            ]
        )

        assert (
            actual
            ==
            expected
        ), (
            f"{operator} 2024 common-window count "
            f"does not reconcile: "
            f"{actual:,} != {expected:,}"
        )

        parts.append(
            data
        )

    common = pd.concat(
        parts,
        ignore_index=True,
    )

    assert (
        common[
            "date"
        ].nunique()
        == 335
    ), (
        "2024 common window must contain "
        "335 calendar days."
    )

    return common


# ============================================================
# MATCHED YOY — 12 COMPLETE WEEKS
#
# 2024:
# Mon 5 Feb - Sun 28 Apr
#
# 2025:
# Mon 3 Feb - Sun 27 Apr
#
# Exactly:
# 84 days
# 12 Mondays
# ...
# 12 Sundays
#
# February 29, 2024 IS retained.
#
# This is preferable to an 88-day date-matched window for
# hourly / weekday analysis because weekday composition is
# exactly identical.
# ============================================================

def build_matched_yoy(
    frames
):

    parts = []

    for (
        operator,
        year,
    ), df in frames.items():

        data = add_time_features(
            df
        )

        (
            start_date,
            end_date,
        ) = (
            MATCHED_WINDOWS[
                year
            ]
        )

        data = data.loc[
            data[
                "date"
            ].between(
                start_date,
                end_date,
                inclusive="both",
            )
        ].copy()

        # ----------------------------------------------------
        # Trip-count reconciliation
        # ----------------------------------------------------

        expected = (
            EXPECTED_MATCHED[
                (
                    operator,
                    year,
                )
            ]
        )

        actual = len(
            data
        )

        assert (
            actual
            ==
            expected
        ), (
            f"{operator} {year}: "
            f"matched count {actual:,} "
            f"!= expected {expected:,}"
        )

        # ----------------------------------------------------
        # 84 calendar days
        # ----------------------------------------------------

        assert (
            data[
                "date"
            ].nunique()
            == 84
        ), (
            f"{operator} {year}: "
            "matched window must contain 84 days."
        )

        # ----------------------------------------------------
        # Exactly 12 occurrences of each weekday
        # ----------------------------------------------------

        weekday_counts = (
            data[
                [
                    "date",
                    "weekday_number",
                ]
            ]
            .drop_duplicates()
            .groupby(
                "weekday_number"
            )[
                "date"
            ]
            .nunique()
        )

        assert (
            len(
                weekday_counts
            )
            == 7
        )

        assert (
            weekday_counts
            == 12
        ).all(), (
            f"{operator} {year}: "
            "each weekday must occur exactly 12 times."
        )

        parts.append(
            data
        )

    matched = pd.concat(
        parts,
        ignore_index=True,
    )

    return matched


# ============================================================
# 2024 CALENDAR
# ============================================================

def build_2024_calendar():

    calendar = pd.DataFrame(
        {
            "date":
                pd.date_range(
                    "2024-02-01",
                    "2024-12-31",
                    freq="D",
                )
        }
    )

    assert (
        len(
            calendar
        )
        == 335
    )

    calendar[
        "weekday_number"
    ] = (
        calendar[
            "date"
        ]
        .dt.weekday
    )

    calendar[
        "weekday"
    ] = (
        calendar[
            "date"
        ]
        .dt.day_name()
    )

    counts = (
        calendar.groupby(
            [
                "weekday_number",
                "weekday",
            ],
            as_index=False,
        )
        .agg(
            weekday_occurrences=(
                "date",
                "nunique",
            )
        )
    )

    return (
        calendar,
        counts,
    )


# ============================================================
# GENERAL HOURLY PROFILE
# ============================================================

def build_hourly_profile(
    data,
    calendar_days,
):

    observed = (
        data.groupby(
            [
                "operator",
                "year",
                "hour",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            )
        )
    )

    # --------------------------------------------------------
    # Complete 24-hour grid for every operator-year.
    #
    # Prevents missing hours from disappearing from output.
    # --------------------------------------------------------

    operator_years = (
        data[
            [
                "operator",
                "year",
            ]
        ]
        .drop_duplicates()
    )

    grids = []

    for _, row in (
        operator_years.iterrows()
    ):

        grids.append(
            pd.DataFrame(
                {
                    "operator":
                        row[
                            "operator"
                        ],

                    "year":
                        row[
                            "year"
                        ],

                    "hour":
                        range(
                            24
                        ),
                }
            )
        )

    grid = pd.concat(
        grids,
        ignore_index=True,
    )

    profile = grid.merge(
        observed,
        on=[
            "operator",
            "year",
            "hour",
        ],
        how="left",
        validate="one_to_one",
    )

    profile[
        "trips"
    ] = (
        profile[
            "trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    profile[
        "calendar_days"
    ] = (
        calendar_days
    )

    profile[
        "mean_trips_per_day_at_hour"
    ] = (
        profile[
            "trips"
        ]
        /
        calendar_days
    )

    operator_totals = (
        data.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            operator_total_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    profile = profile.merge(
        operator_totals,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="many_to_one",
    )

    profile[
        "trip_share_pct"
    ] = (
        profile[
            "trips"
        ]
        /
        profile[
            "operator_total_trips"
        ]
        * 100
    )

    # --------------------------------------------------------
    # Normalized hourly activity index
    #
    # 100 = mean activity across the 24 hourly bins.
    # --------------------------------------------------------

    average_hour_rate = (
        profile.groupby(
            [
                "operator",
                "year",
            ]
        )[
            "mean_trips_per_day_at_hour"
        ]
        .transform(
            "mean"
        )
    )

    profile[
        "hourly_activity_index"
    ] = (
        profile[
            "mean_trips_per_day_at_hour"
        ]
        /
        average_hour_rate
        * 100
    )

    return profile


# ============================================================
# HOURLY × WEEKDAY PROFILE — 2024 COMMON WINDOW
# ============================================================

def build_hourly_weekday_profile(
    common_2024,
    weekday_counts,
):

    observed = (
        common_2024.groupby(
            [
                "operator",
                "weekday_number",
                "weekday",
                "hour",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            )
        )
    )

    # --------------------------------------------------------
    # Complete operator × weekday × hour grid
    # --------------------------------------------------------

    grid = (
        pd.MultiIndex.from_product(
            [
                OPERATORS,
                range(7),
                range(24),
            ],
            names=[
                "operator",
                "weekday_number",
                "hour",
            ],
        )
        .to_frame(
            index=False
        )
    )

    weekday_lookup = (
        weekday_counts[
            [
                "weekday_number",
                "weekday",
                "weekday_occurrences",
            ]
        ]
    )

    grid = grid.merge(
        weekday_lookup,
        on="weekday_number",
        how="left",
        validate="many_to_one",
    )

    result = grid.merge(
        observed[
            [
                "operator",
                "weekday_number",
                "hour",
                "trips",
            ]
        ],
        on=[
            "operator",
            "weekday_number",
            "hour",
        ],
        how="left",
        validate="one_to_one",
    )

    result[
        "trips"
    ] = (
        result[
            "trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    result[
        "mean_trips_per_weekday_occurrence_at_hour"
    ] = (
        result[
            "trips"
        ]
        /
        result[
            "weekday_occurrences"
        ]
    )

    # --------------------------------------------------------
    # Overall operator mean trip count per calendar hour
    # --------------------------------------------------------

    operator_total = (
        common_2024.groupby(
            "operator",
            as_index=False,
        )
        .agg(
            operator_total_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    operator_total[
        "operator_mean_trips_per_calendar_hour"
    ] = (
        operator_total[
            "operator_total_trips"
        ]
        /
        (
            335
            * 24
        )
    )

    result = result.merge(
        operator_total[
            [
                "operator",
                "operator_mean_trips_per_calendar_hour",
            ]
        ],
        on="operator",
        how="left",
        validate="many_to_one",
    )

    result[
        "hour_weekday_activity_index"
    ] = (
        result[
            "mean_trips_per_weekday_occurrence_at_hour"
        ]
        /
        result[
            "operator_mean_trips_per_calendar_hour"
        ]
        * 100
    )

    return result


# ============================================================
# SYSTEM-WIDE HOURLY PROFILE — 2024
# ============================================================

def build_system_hourly_2024(
    common_2024
):

    system = (
        common_2024.groupby(
            "hour",
            as_index=False,
        )
        .agg(
            system_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    # Complete 0-23 structure
    hours = pd.DataFrame(
        {
            "hour":
                range(
                    24
                )
        }
    )

    system = hours.merge(
        system,
        on="hour",
        how="left",
        validate="one_to_one",
    )

    system[
        "system_trips"
    ] = (
        system[
            "system_trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    system[
        "calendar_days"
    ] = 335

    system[
        "mean_system_trips_per_day_at_hour"
    ] = (
        system[
            "system_trips"
        ]
        /
        335
    )

    total = int(
        system[
            "system_trips"
        ]
        .sum()
    )

    expected_total = sum(
        EXPECTED_2024_COMMON.values()
    )

    assert (
        total
        ==
        expected_total
    )

    system[
        "system_trip_share_pct"
    ] = (
        system[
            "system_trips"
        ]
        /
        total
        * 100
    )

    system[
        "activity_rank"
    ] = (
        system[
            "mean_system_trips_per_day_at_hour"
        ]
        .rank(
            method="first",
            ascending=False,
        )
        .astype(int)
    )

    # --------------------------------------------------------
    # Top 25% of 24 hourly bins = six hours.
    # --------------------------------------------------------

    system[
        "empirical_peak_2024"
    ] = (
        system[
            "activity_rank"
        ]
        <= 6
    )

    return system.sort_values(
        "hour"
    )


# ============================================================
# EMPIRICAL PEAK HOURS
# ============================================================

def get_empirical_peak_hours(
    system_hourly
):

    peak = (
        system_hourly.loc[
            system_hourly[
                "empirical_peak_2024"
            ]
        ]
        .sort_values(
            "activity_rank"
        )
        .copy()
    )

    assert (
        len(
            peak
        )
        == 6
    )

    peak_hours = set(
        peak[
            "hour"
        ]
        .astype(int)
        .tolist()
    )

    return (
        peak,
        peak_hours,
    )


# ============================================================
# CONVENTIONAL PERIOD SUMMARY
#
# Produces:
#
# 1. AM / PM / Off-peak detail
# 2. Binary Transport peak / Off-peak
#
# Critical:
# Mean trips per CLOCK HOUR is calculated because the
# categories contain different numbers of hours.
# ============================================================

def summarize_periods(
    data,
    calendar_days,
):

    # ========================================================
    # DETAILED 3-CLASS SUMMARY
    # ========================================================

    detailed = (
        data.groupby(
            [
                "operator",
                "year",
                "transport_period",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            )
        )
    )

    hours_per_day = {
        "AM peak": 3,
        "PM peak": 4,
        "Off-peak": 17,
    }

    detailed[
        "hours_per_day"
    ] = (
        detailed[
            "transport_period"
        ]
        .map(
            hours_per_day
        )
    )

    detailed[
        "calendar_days"
    ] = (
        calendar_days
    )

    detailed[
        "available_clock_hours"
    ] = (
        detailed[
            "hours_per_day"
        ]
        *
        calendar_days
    )

    detailed[
        "mean_trips_per_calendar_day"
    ] = (
        detailed[
            "trips"
        ]
        /
        calendar_days
    )

    detailed[
        "mean_trips_per_clock_hour"
    ] = (
        detailed[
            "trips"
        ]
        /
        detailed[
            "available_clock_hours"
        ]
    )

    operator_totals = (
        data.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            operator_total_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    detailed = detailed.merge(
        operator_totals,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="many_to_one",
    )

    detailed[
        "trip_share_pct"
    ] = (
        detailed[
            "trips"
        ]
        /
        detailed[
            "operator_total_trips"
        ]
        * 100
    )

    # ========================================================
    # BINARY PEAK / OFF-PEAK
    # ========================================================

    binary_data = (
        data.copy()
    )

    binary_data[
        "peak_group"
    ] = np.where(
        binary_data[
            "is_transport_peak"
        ],
        "Transport peak",
        "Off-peak",
    )

    binary = (
        binary_data.groupby(
            [
                "operator",
                "year",
                "peak_group",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            )
        )
    )

    binary_hours = {
        "Transport peak": 7,
        "Off-peak": 17,
    }

    binary[
        "hours_per_day"
    ] = (
        binary[
            "peak_group"
        ]
        .map(
            binary_hours
        )
    )

    binary[
        "calendar_days"
    ] = (
        calendar_days
    )

    binary[
        "available_clock_hours"
    ] = (
        binary[
            "hours_per_day"
        ]
        *
        calendar_days
    )

    binary[
        "mean_trips_per_calendar_day"
    ] = (
        binary[
            "trips"
        ]
        /
        calendar_days
    )

    binary[
        "mean_trips_per_clock_hour"
    ] = (
        binary[
            "trips"
        ]
        /
        binary[
            "available_clock_hours"
        ]
    )

    binary = binary.merge(
        operator_totals,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="many_to_one",
    )

    binary[
        "trip_share_pct"
    ] = (
        binary[
            "trips"
        ]
        /
        binary[
            "operator_total_trips"
        ]
        * 100
    )

    return (
        detailed,
        binary,
    )


# ============================================================
# EMPIRICAL PEAK SUMMARY
#
# The six highest-demand system-wide hours are identified
# using the 2024 common baseline.
#
# Those SAME six hours are then applied to the matched
# 2024 and 2025 windows.
# ============================================================

def build_empirical_peak_summary(
    data,
    peak_hours,
    calendar_days,
):

    df = data.copy()

    df[
        "empirical_peak_group"
    ] = np.where(
        df[
            "hour"
        ].isin(
            peak_hours
        ),
        "2024 empirical peak hours",
        "Other hours",
    )

    result = (
        df.groupby(
            [
                "operator",
                "year",
                "empirical_peak_group",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            )
        )
    )

    hours_per_day = {
        "2024 empirical peak hours": 6,
        "Other hours": 18,
    }

    result[
        "hours_per_day"
    ] = (
        result[
            "empirical_peak_group"
        ]
        .map(
            hours_per_day
        )
    )

    result[
        "calendar_days"
    ] = (
        calendar_days
    )

    result[
        "available_clock_hours"
    ] = (
        result[
            "hours_per_day"
        ]
        *
        calendar_days
    )

    result[
        "mean_trips_per_calendar_day"
    ] = (
        result[
            "trips"
        ]
        /
        calendar_days
    )

    result[
        "mean_trips_per_clock_hour"
    ] = (
        result[
            "trips"
        ]
        /
        result[
            "available_clock_hours"
        ]
    )

    total = (
        df.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            operator_total_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    result = result.merge(
        total,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="many_to_one",
    )

    result[
        "trip_share_pct"
    ] = (
        result[
            "trips"
        ]
        /
        result[
            "operator_total_trips"
        ]
        * 100
    )

    return result


# ============================================================
# OPERATOR PEAK HOUR BY WEEKDAY — 2024
# ============================================================

def build_weekday_peak_hours(
    hourly_weekday
):

    idx = (
        hourly_weekday.groupby(
            [
                "operator",
                "weekday_number",
                "weekday",
            ]
        )[
            "mean_trips_per_weekday_occurrence_at_hour"
        ]
        .idxmax()
    )

    result = (
        hourly_weekday.loc[
            idx,
            [
                "operator",
                "weekday_number",
                "weekday",
                "hour",
                "mean_trips_per_weekday_occurrence_at_hour",
                "hour_weekday_activity_index",
            ],
        ]
        .sort_values(
            [
                "operator",
                "weekday_number",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# SYSTEM HOURLY × WEEKDAY PROFILE
# ============================================================

def build_system_hourly_weekday(
    common_2024,
    weekday_counts,
):

    observed = (
        common_2024.groupby(
            [
                "weekday_number",
                "weekday",
                "hour",
            ],
            as_index=False,
        )
        .agg(
            system_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    grid = (
        pd.MultiIndex.from_product(
            [
                range(7),
                range(24),
            ],
            names=[
                "weekday_number",
                "hour",
            ],
        )
        .to_frame(
            index=False
        )
    )

    grid = grid.merge(
        weekday_counts,
        on="weekday_number",
        how="left",
        validate="many_to_one",
    )

    result = grid.merge(
        observed[
            [
                "weekday_number",
                "hour",
                "system_trips",
            ]
        ],
        on=[
            "weekday_number",
            "hour",
        ],
        how="left",
        validate="one_to_one",
    )

    result[
        "system_trips"
    ] = (
        result[
            "system_trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    result[
        "mean_system_trips_per_weekday_occurrence_at_hour"
    ] = (
        result[
            "system_trips"
        ]
        /
        result[
            "weekday_occurrences"
        ]
    )

    return result


# ============================================================
# SYSTEM PEAK HOUR BY WEEKDAY
# ============================================================

def build_system_weekday_peak_hours(
    system_hourly_weekday
):

    idx = (
        system_hourly_weekday.groupby(
            [
                "weekday_number",
                "weekday",
            ]
        )[
            "mean_system_trips_per_weekday_occurrence_at_hour"
        ]
        .idxmax()
    )

    result = (
        system_hourly_weekday.loc[
            idx,
            [
                "weekday_number",
                "weekday",
                "hour",
                "mean_system_trips_per_weekday_occurrence_at_hour",
            ],
        ]
        .sort_values(
            "weekday_number"
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# MATCHED PEAK/OFF-PEAK YOY COMPARISON
#
# Percentage changes are used for volumes / rates.
#
# Trip-share change is reported in PERCENTAGE POINTS:
#
# share_2025 - share_2024
#
# Example:
# 37.5% -> 38.2%
# = +0.7 percentage points
#
# NOT +1.9 percentage points.
# ============================================================

def build_matched_peak_yoy(
    binary
):

    # --------------------------------------------------------
    # Trips
    # --------------------------------------------------------

    trips = (
        binary.pivot(
            index=[
                "operator",
                "peak_group",
            ],
            columns="year",
            values="trips",
        )
        .reset_index()
        .rename(
            columns={
                2024:
                    "trips_2024",

                2025:
                    "trips_2025",
            }
        )
    )

    # --------------------------------------------------------
    # Mean trips / calendar day
    # --------------------------------------------------------

    daily = (
        binary.pivot(
            index=[
                "operator",
                "peak_group",
            ],
            columns="year",
            values=(
                "mean_trips_per_calendar_day"
            ),
        )
        .reset_index()
        .rename(
            columns={
                2024:
                    "mean_trips_per_calendar_day_2024",

                2025:
                    "mean_trips_per_calendar_day_2025",
            }
        )
    )

    # --------------------------------------------------------
    # Mean trips / clock hour
    # --------------------------------------------------------

    hourly = (
        binary.pivot(
            index=[
                "operator",
                "peak_group",
            ],
            columns="year",
            values=(
                "mean_trips_per_clock_hour"
            ),
        )
        .reset_index()
        .rename(
            columns={
                2024:
                    "mean_trips_per_clock_hour_2024",

                2025:
                    "mean_trips_per_clock_hour_2025",
            }
        )
    )

    # --------------------------------------------------------
    # Trip shares
    # --------------------------------------------------------

    shares = (
        binary.pivot(
            index=[
                "operator",
                "peak_group",
            ],
            columns="year",
            values="trip_share_pct",
        )
        .reset_index()
        .rename(
            columns={
                2024:
                    "trip_share_pct_2024",

                2025:
                    "trip_share_pct_2025",
            }
        )
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    result = (
        trips
        .merge(
            daily,
            on=[
                "operator",
                "peak_group",
            ],
            validate="one_to_one",
        )
        .merge(
            hourly,
            on=[
                "operator",
                "peak_group",
            ],
            validate="one_to_one",
        )
        .merge(
            shares,
            on=[
                "operator",
                "peak_group",
            ],
            validate="one_to_one",
        )
    )

    # --------------------------------------------------------
    # Percentage changes
    # --------------------------------------------------------

    result[
        "trips_pct_change_2025_vs_2024"
    ] = (
        (
            result[
                "trips_2025"
            ]
            /
            result[
                "trips_2024"
            ]
        )
        - 1
    ) * 100

    result[
        "mean_trips_per_calendar_day_pct_change_2025_vs_2024"
    ] = (
        (
            result[
                "mean_trips_per_calendar_day_2025"
            ]
            /
            result[
                "mean_trips_per_calendar_day_2024"
            ]
        )
        - 1
    ) * 100

    result[
        "mean_trips_per_clock_hour_pct_change_2025_vs_2024"
    ] = (
        (
            result[
                "mean_trips_per_clock_hour_2025"
            ]
            /
            result[
                "mean_trips_per_clock_hour_2024"
            ]
        )
        - 1
    ) * 100

    # --------------------------------------------------------
    # Share change = percentage points
    # --------------------------------------------------------

    result[
        "trip_share_change_percentage_points"
    ] = (
        result[
            "trip_share_pct_2025"
        ]
        -
        result[
            "trip_share_pct_2024"
        ]
    )

    return result


# ============================================================
# VALIDATE MATCHED CALENDAR STRUCTURE
# ============================================================

def build_matched_calendar_validation(
    matched
):

    calendar = (
        matched[
            [
                "operator",
                "year",
                "date",
                "weekday_number",
                "weekday",
            ]
        ]
        .drop_duplicates()
    )

    summary = (
        calendar.groupby(
            [
                "operator",
                "year",
            ],
            as_index=False,
        )
        .agg(
            calendar_days=(
                "date",
                "nunique",
            ),
            first_date=(
                "date",
                "min",
            ),
            last_date=(
                "date",
                "max",
            ),
        )
    )

    weekday = (
        calendar.groupby(
            [
                "operator",
                "year",
                "weekday_number",
                "weekday",
            ],
            as_index=False,
        )
        .agg(
            weekday_occurrences=(
                "date",
                "nunique",
            )
        )
    )

    assert (
        summary[
            "calendar_days"
        ] == 84
    ).all()

    assert (
        weekday[
            "weekday_occurrences"
        ] == 12
    ).all()

    return (
        summary,
        weekday,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 118
    )

    print(
        "EXERCISE 1 — HOURLY × WEEKDAY "
        "AND PEAK/OFF-PEAK STRUCTURE"
    )

    print(
        "=" * 118
    )

    # ========================================================
    # LOAD
    # ========================================================

    frames = (
        load_frames()
    )

    # ========================================================
    # DATA WINDOWS
    # ========================================================

    common_2024 = (
        build_2024_common(
            frames
        )
    )

    matched = (
        build_matched_yoy(
            frames
        )
    )

    (
        matched_calendar_summary,
        matched_weekday_validation,
    ) = (
        build_matched_calendar_validation(
            matched
        )
    )

    (
        calendar_2024,
        weekday_counts,
    ) = (
        build_2024_calendar()
    )

    # ========================================================
    # HOURLY PROFILES
    # ========================================================

    hourly_2024 = (
        build_hourly_profile(
            common_2024,
            calendar_days=335,
        )
    )

    hourly_matched = (
        build_hourly_profile(
            matched,
            calendar_days=84,
        )
    )

    hourly_weekday_2024 = (
        build_hourly_weekday_profile(
            common_2024,
            weekday_counts,
        )
    )

    system_hourly_2024 = (
        build_system_hourly_2024(
            common_2024
        )
    )

    # ========================================================
    # EMPIRICAL PEAK HOURS
    # ========================================================

    (
        empirical_peak_table,
        empirical_peak_hours,
    ) = (
        get_empirical_peak_hours(
            system_hourly_2024
        )
    )

    # ========================================================
    # CONVENTIONAL PEAK / OFF-PEAK
    # ========================================================

    (
        transport_period_2024,
        peak_binary_2024,
    ) = (
        summarize_periods(
            common_2024,
            calendar_days=335,
        )
    )

    (
        transport_period_matched,
        peak_binary_matched,
    ) = (
        summarize_periods(
            matched,
            calendar_days=84,
        )
    )

    # ========================================================
    # EMPIRICAL PEAK SUMMARY
    # ========================================================

    empirical_summary_2024 = (
        build_empirical_peak_summary(
            common_2024,
            empirical_peak_hours,
            calendar_days=335,
        )
    )

    empirical_summary_matched = (
        build_empirical_peak_summary(
            matched,
            empirical_peak_hours,
            calendar_days=84,
        )
    )

    # ========================================================
    # YOY PEAK COMPARISON
    # ========================================================

    peak_yoy = (
        build_matched_peak_yoy(
            peak_binary_matched
        )
    )

    # ========================================================
    # WEEKDAY × HOUR PEAKS
    # ========================================================

    weekday_peak_hours = (
        build_weekday_peak_hours(
            hourly_weekday_2024
        )
    )

    system_hourly_weekday = (
        build_system_hourly_weekday(
            common_2024,
            weekday_counts,
        )
    )

    system_weekday_peak_hours = (
        build_system_weekday_peak_hours(
            system_hourly_weekday
        )
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    expected_2024_total = sum(
        EXPECTED_2024_COMMON.values()
    )

    actual_2024_total = int(
        hourly_2024[
            "trips"
        ].sum()
    )

    assert (
        actual_2024_total
        ==
        expected_2024_total
    )

    for (
        operator,
        year,
    ), expected in (
        EXPECTED_MATCHED.items()
    ):

        actual = int(
            hourly_matched.loc[
                (
                    hourly_matched[
                        "operator"
                    ]
                    == operator
                )
                &
                (
                    hourly_matched[
                        "year"
                    ]
                    == year
                ),
                "trips",
            ].sum()
        )

        assert (
            actual
            ==
            expected
        ), (
            f"{operator} {year}: "
            f"{actual:,} != {expected:,}"
        )

    # ========================================================
    # SAVE PROCESSED PARQUETS
    # ========================================================

    hourly_weekday_2024.to_parquet(
        OUTPUT_DIR
        / "hourly_weekday_profile_2024_common.parquet",
        index=False,
    )

    hourly_matched.to_parquet(
        OUTPUT_DIR
        / "hourly_profile_matched_12_full_weeks_yoy.parquet",
        index=False,
    )

    system_hourly_weekday.to_parquet(
        OUTPUT_DIR
        / "system_hourly_weekday_2024_common.parquet",
        index=False,
    )

    # ========================================================
    # SAVE TABLES
    # ========================================================

    hourly_2024.to_csv(
        TABLE_DIR
        / "hourly_profile_2024_common.csv",
        index=False,
    )

    hourly_matched.to_csv(
        TABLE_DIR
        / "hourly_profile_matched_12_full_weeks_yoy.csv",
        index=False,
    )

    hourly_weekday_2024.to_csv(
        TABLE_DIR
        / "hourly_weekday_profile_2024_common.csv",
        index=False,
    )

    system_hourly_2024.to_csv(
        TABLE_DIR
        / "system_hourly_profile_2024_common.csv",
        index=False,
    )

    empirical_peak_table.to_csv(
        TABLE_DIR
        / "empirical_peak_hours_2024.csv",
        index=False,
    )

    transport_period_2024.to_csv(
        TABLE_DIR
        / "transport_period_summary_2024_common.csv",
        index=False,
    )

    peak_binary_2024.to_csv(
        TABLE_DIR
        / "peak_offpeak_summary_2024_common.csv",
        index=False,
    )

    transport_period_matched.to_csv(
        TABLE_DIR
        / "transport_period_summary_matched_12_full_weeks_yoy.csv",
        index=False,
    )

    peak_binary_matched.to_csv(
        TABLE_DIR
        / "peak_offpeak_summary_matched_12_full_weeks_yoy.csv",
        index=False,
    )

    peak_yoy.to_csv(
        TABLE_DIR
        / "peak_offpeak_matched_12_full_weeks_yoy_comparison.csv",
        index=False,
    )

    empirical_summary_2024.to_csv(
        TABLE_DIR
        / "empirical_peak_summary_2024.csv",
        index=False,
    )

    empirical_summary_matched.to_csv(
        TABLE_DIR
        / "empirical_peak_summary_matched_12_full_weeks_yoy.csv",
        index=False,
    )

    weekday_peak_hours.to_csv(
        TABLE_DIR
        / "operator_weekday_peak_hours_2024.csv",
        index=False,
    )

    system_hourly_weekday.to_csv(
        TABLE_DIR
        / "system_hourly_weekday_2024_common.csv",
        index=False,
    )

    system_weekday_peak_hours.to_csv(
        TABLE_DIR
        / "system_weekday_peak_hours_2024.csv",
        index=False,
    )

    matched_calendar_summary.to_csv(
        TABLE_DIR
        / "matched_12_full_weeks_calendar_validation.csv",
        index=False,
    )

    matched_weekday_validation.to_csv(
        TABLE_DIR
        / "matched_12_full_weeks_weekday_validation.csv",
        index=False,
    )

    # ========================================================
    # TERMINAL SETTINGS
    # ========================================================

    pd.set_option(
        "display.max_columns",
        None,
    )

    pd.set_option(
        "display.width",
        200,
    )

    # ========================================================
    # TERMINAL — MATCHED CALENDAR
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "MATCHED FULL-WEEK YOY WINDOW"
    )

    print(
        "-" * 118
    )

    calendar_display = (
        matched_calendar_summary.copy()
    )

    calendar_display[
        "first_date"
    ] = (
        calendar_display[
            "first_date"
        ]
        .dt.date
    )

    calendar_display[
        "last_date"
    ] = (
        calendar_display[
            "last_date"
        ]
        .dt.date
    )

    print(
        calendar_display.to_string(
            index=False,
        )
    )

    print(
        "\nWeekday composition check:"
    )

    weekday_check = (
        matched_weekday_validation[
            [
                "operator",
                "year",
                "weekday",
                "weekday_occurrences",
            ]
        ]
    )

    print(
        weekday_check.to_string(
            index=False,
        )
    )

    # ========================================================
    # TERMINAL — EMPIRICAL 2024 PEAK
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "2024 EMPIRICAL SYSTEM PEAK HOURS "
        "(TOP 6 OF 24)"
    )

    print(
        "-" * 118
    )

    empirical_display = (
        empirical_peak_table[
            [
                "activity_rank",
                "hour",
                "system_trips",
                "mean_system_trips_per_day_at_hour",
                "system_trip_share_pct",
            ]
        ]
        .copy()
    )

    empirical_display[
        "mean_system_trips_per_day_at_hour"
    ] = (
        empirical_display[
            "mean_system_trips_per_day_at_hour"
        ]
        .round(2)
    )

    empirical_display[
        "system_trip_share_pct"
    ] = (
        empirical_display[
            "system_trip_share_pct"
        ]
        .round(2)
    )

    print(
        empirical_display.to_string(
            index=False,
        )
    )

    empirical_total_share = (
        empirical_peak_table[
            "system_trip_share_pct"
        ]
        .sum()
    )

    print(
        f"\nCombined trip share of the six "
        f"empirical peak hours: "
        f"{empirical_total_share:.2f}%"
    )

    # ========================================================
    # TERMINAL — 2024 CONVENTIONAL PERIODS
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "2024 CONVENTIONAL TRANSPORT-PERIOD SUMMARY"
    )

    print(
        "-" * 118
    )

    display_period = (
        transport_period_2024[
            [
                "operator",
                "transport_period",
                "trips",
                "mean_trips_per_calendar_day",
                "mean_trips_per_clock_hour",
                "trip_share_pct",
            ]
        ]
        .copy()
    )

    for col in [
        "mean_trips_per_calendar_day",
        "mean_trips_per_clock_hour",
        "trip_share_pct",
    ]:

        display_period[
            col
        ] = (
            display_period[
                col
            ]
            .round(2)
        )

    print(
        display_period.to_string(
            index=False,
        )
    )

    # ========================================================
    # TERMINAL — SYSTEM WEEKDAY PEAKS
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "2024 SYSTEM PEAK HOUR BY WEEKDAY"
    )

    print(
        "-" * 118
    )

    display_system_peaks = (
        system_weekday_peak_hours.copy()
    )

    display_system_peaks[
        "mean_system_trips_per_weekday_occurrence_at_hour"
    ] = (
        display_system_peaks[
            "mean_system_trips_per_weekday_occurrence_at_hour"
        ]
        .round(2)
    )

    print(
        display_system_peaks.to_string(
            index=False,
        )
    )

    # ========================================================
    # TERMINAL — OPERATOR WEEKDAY PEAKS
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "2024 OPERATOR PEAK HOUR BY WEEKDAY"
    )

    print(
        "-" * 118
    )

    display_operator_peaks = (
        weekday_peak_hours.copy()
    )

    for col in [
        "mean_trips_per_weekday_occurrence_at_hour",
        "hour_weekday_activity_index",
    ]:

        display_operator_peaks[
            col
        ] = (
            display_operator_peaks[
                col
            ]
            .round(2)
        )

    print(
        display_operator_peaks.to_string(
            index=False,
        )
    )

    # ========================================================
    # TERMINAL — MATCHED FULL-WEEK PEAK/OFF-PEAK
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "MATCHED 12-FULL-WEEK "
        "CONVENTIONAL PEAK/OFF-PEAK SUMMARY"
    )

    print(
        "-" * 118
    )

    matched_display = (
        peak_binary_matched[
            [
                "operator",
                "year",
                "peak_group",
                "trips",
                "mean_trips_per_calendar_day",
                "mean_trips_per_clock_hour",
                "trip_share_pct",
            ]
        ]
        .copy()
    )

    for col in [
        "mean_trips_per_calendar_day",
        "mean_trips_per_clock_hour",
        "trip_share_pct",
    ]:

        matched_display[
            col
        ] = (
            matched_display[
                col
            ]
            .round(2)
        )

    print(
        matched_display.to_string(
            index=False,
        )
    )

    # ========================================================
    # TERMINAL — YOY CHANGES
    # ========================================================

    print(
        "\n"
        + "-" * 118
    )

    print(
        "MATCHED 2025 VS 2024 "
        "PEAK/OFF-PEAK CHANGES"
    )

    print(
        "-" * 118
    )

    yoy_display = (
        peak_yoy.copy()
    )

    numeric_cols = [
        col
        for col
        in yoy_display.columns
        if col not in [
            "operator",
            "peak_group",
        ]
    ]

    for col in numeric_cols:

        yoy_display[
            col
        ] = (
            pd.to_numeric(
                yoy_display[
                    col
                ],
                errors="coerce",
            )
            .round(2)
        )

    print(
        yoy_display.to_string(
            index=False,
        )
    )

    # ========================================================
    # FINAL MESSAGE
    # ========================================================

    print(
        "\n"
        + "=" * 118
    )

    print(
        "VALIDATION / INTERPRETATION"
    )

    print(
        "=" * 118
    )

    print(
        "- 2024 hourly × weekday baseline uses "
        "Feb 1-Dec 31, the common detailed-time window."
    )

    print(
        "- VOI January 2024 is excluded from hourly analysis "
        "because detailed timestamps are unavailable."
    )

    print(
        "- Matched hourly YoY uses 12 complete "
        "Monday-Sunday weeks per year."
    )

    print(
        "- Matched 2024 window: "
        "Feb 5-Apr 28."
    )

    print(
        "- Matched 2025 window: "
        "Feb 3-Apr 27."
    )

    print(
        "- Each matched operator-year contains exactly "
        "84 calendar days."
    )

    print(
        "- Every weekday occurs exactly 12 times "
        "in each matched year."
    )

    print(
        "- February 29, 2024 is retained in the "
        "full-week comparison."
    )

    print(
        "- Conventional AM peak = 07:00-09:59."
    )

    print(
        "- Conventional PM peak = 16:00-19:59."
    )

    print(
        "- Conventional peak definitions are not assumed "
        "to be actual scooter-demand peaks."
    )

    print(
        "- Empirical peak hours are the six highest "
        "system-wide hourly bins in the 2024 baseline."
    )

    print(
        "- The same 2024 empirical peak hours are held fixed "
        "when applied to 2025."
    )

    print(
        "- Peak/off-peak intensity is compared using "
        "mean trips per clock-hour."
    )

    print(
        "- Trip-share changes are reported in "
        "percentage points, not percentage change."
    )

    print(
        "- Hourly × weekday tables are ready for "
        "heatmap visualization."
    )

    print(
        "\nAnalysis completed successfully."
    )


if __name__ == "__main__":
    main()