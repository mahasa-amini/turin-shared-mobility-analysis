from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "harmonized"
    / "all_operators_2024_harmonized.parquet"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "fleet_exposure"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_5"
    / "fleet_exposure"
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# ANALYTICAL WINDOW
# =============================================================================

COMMON_START = pd.Timestamp(
    "2024-02-01 00:00:00"
)

COMMON_END_EXCLUSIVE = pd.Timestamp(
    "2025-01-01 00:00:00"
)

COMMON_DAYS = (
    COMMON_END_EXCLUSIVE.normalize()
    - COMMON_START.normalize()
).days

EXPECTED_COMMON_DAYS = 335

assert COMMON_DAYS == EXPECTED_COMMON_DAYS


OPERATORS = [
    "bird",
    "lime",
    "voi",
]


# =============================================================================
# LOAD
# =============================================================================

def load_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            INPUT_FILE
        )

    df = pd.read_parquet(
        INPUT_FILE,
        columns=[
            "operator",
            "trip_uid",
            "vehicle_uid",
            "start_time_local",
            "source_period",
        ],
    )

    df["operator"] = (
        df["operator"]
        .astype("string")
        .str.lower()
    )

    df["start_time_local"] = pd.to_datetime(
        df["start_time_local"],
        errors="coerce",
    )

    assert df["trip_uid"].is_unique

    assert set(
        df["operator"].dropna().unique()
    ) == set(OPERATORS)

    return df


# =============================================================================
# COMMON DETAILED-TIME WINDOW
# =============================================================================

def build_common_window(df):

    common = df.loc[
        (
            df["start_time_local"]
            >= COMMON_START
        )
        &
        (
            df["start_time_local"]
            <
            COMMON_END_EXCLUSIVE
        )
    ].copy()

    common["activity_date"] = (
        common["start_time_local"]
        .dt.normalize()
    )

    # ---------------------------------------------------------
    # Coverage validation
    # ---------------------------------------------------------

    coverage = (
        common.groupby(
            "operator",
            observed=True,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            ),

            first_date=(
                "activity_date",
                "min",
            ),

            last_date=(
                "activity_date",
                "max",
            ),

            calendar_dates_with_trips=(
                "activity_date",
                "nunique",
            ),
        )
        .reset_index()
    )

    return (
        common,
        coverage,
    )


# =============================================================================
# DAILY ACTIVE VEHICLE POPULATION
# =============================================================================

def build_daily_active_fleet(common):

    daily = (
        common.groupby(
            [
                "operator",
                "activity_date",
            ],
            observed=True,
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
        .reset_index()
    )

    # Explicit full calendar grid
    dates = pd.date_range(
        COMMON_START.normalize(),
        COMMON_END_EXCLUSIVE.normalize()
        - pd.Timedelta(days=1),
        freq="D",
    )

    grid = pd.MultiIndex.from_product(
        [
            OPERATORS,
            dates,
        ],
        names=[
            "operator",
            "activity_date",
        ],
    ).to_frame(
        index=False
    )

    daily = grid.merge(
        daily,
        on=[
            "operator",
            "activity_date",
        ],
        how="left",
        validate="one_to_one",
    )

    daily[
        [
            "trips",
            "active_vehicles",
        ]
    ] = (
        daily[
            [
                "trips",
                "active_vehicles",
            ]
        ]
        .fillna(0)
        .astype(int)
    )

    assert len(daily) == (
        len(OPERATORS)
        * COMMON_DAYS
    )

    return daily


# =============================================================================
# VEHICLE-LEVEL EXPOSURE
# =============================================================================

def build_vehicle_exposure(common):

    vehicle = (
        common.groupby(
            [
                "operator",
                "vehicle_uid",
            ],
            observed=True,
        )
        .agg(
            first_observed_date=(
                "activity_date",
                "min",
            ),

            last_observed_date=(
                "activity_date",
                "max",
            ),

            active_days=(
                "activity_date",
                "nunique",
            ),

            trips=(
                "trip_uid",
                "count",
            ),
        )
        .reset_index()
    )

    vehicle[
        "service_span_days"
    ] = (
        (
            vehicle[
                "last_observed_date"
            ]
            -
            vehicle[
                "first_observed_date"
            ]
        )
        .dt.days
        + 1
    )

    assert (
        vehicle[
            "service_span_days"
        ]
        >= 1
    ).all()

    assert (
        vehicle[
            "active_days"
        ]
        <=
        vehicle[
            "service_span_days"
        ]
    ).all()

    vehicle[
        "active_day_share_of_service_span_pct"
    ] = (
        vehicle[
            "active_days"
        ]
        /
        vehicle[
            "service_span_days"
        ]
        * 100
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

    return vehicle


# =============================================================================
# MONTHLY VEHICLE EXPOSURE
# =============================================================================

def build_monthly_fleet(common):

    common = common.copy()

    common[
        "month"
    ] = (
        common[
            "activity_date"
        ]
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        common.groupby(
            [
                "operator",
                "month",
            ],
            observed=True,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            ),

            unique_active_vehicles=(
                "vehicle_uid",
                "nunique",
            ),

            active_vehicle_days=(
                "vehicle_uid",
                lambda x: np.nan,
            ),
        )
        .reset_index()
    )

    # Recalculate actual active vehicle-days cleanly
    vehicle_day = (
        common[
            [
                "operator",
                "month",
                "activity_date",
                "vehicle_uid",
            ]
        ]
        .drop_duplicates()
    )

    vehicle_days = (
        vehicle_day.groupby(
            [
                "operator",
                "month",
            ],
            observed=True,
        )
        .size()
        .rename(
            "active_vehicle_days"
        )
        .reset_index()
    )

    monthly = (
        monthly.drop(
            columns=[
                "active_vehicle_days"
            ]
        )
        .merge(
            vehicle_days,
            on=[
                "operator",
                "month",
            ],
            how="left",
            validate="one_to_one",
        )
    )

    return monthly


# =============================================================================
# FLEET SCENARIO SUMMARY
# =============================================================================

def build_fleet_summary(
    common,
    daily,
    vehicle,
):

    rows = []

    for operator in OPERATORS:

        trips = common.loc[
            common["operator"]
            == operator
        ]

        daily_op = daily.loc[
            daily["operator"]
            == operator
        ]

        vehicle_op = vehicle.loc[
            vehicle["operator"]
            == operator
        ]

        unique_ids = (
            vehicle_op[
                "vehicle_uid"
            ]
            .nunique()
        )

        total_active_vehicle_days = (
            vehicle_op[
                "active_days"
            ]
            .sum()
        )

        total_service_span_days = (
            vehicle_op[
                "service_span_days"
            ]
            .sum()
        )

        mean_daily_active = (
            daily_op[
                "active_vehicles"
            ]
            .mean()
        )

        median_daily_active = (
            daily_op[
                "active_vehicles"
            ]
            .median()
        )

        p90_daily_active = (
            daily_op[
                "active_vehicles"
            ]
            .quantile(0.90)
        )

        p95_daily_active = (
            daily_op[
                "active_vehicles"
            ]
            .quantile(0.95)
        )

        max_daily_active = (
            daily_op[
                "active_vehicles"
            ]
            .max()
        )

        service_span_equivalent = (
            total_service_span_days
            /
            COMMON_DAYS
        )

        active_day_equivalent = (
            total_active_vehicle_days
            /
            COMMON_DAYS
        )

        # active_day_equivalent should exactly match
        # mean daily active vehicles apart from floating precision
        assert np.isclose(
            active_day_equivalent,
            mean_daily_active,
            atol=1e-10,
        )

        rows.append(
            {
                "operator":
                    operator,

                "analysis_window":
                    "2024-02-01_to_2024-12-31",

                "calendar_days":
                    COMMON_DAYS,

                "common_window_trips":
                    len(trips),

                "unique_vehicle_ids":
                    unique_ids,

                "total_active_vehicle_days":
                    total_active_vehicle_days,

                "total_service_span_days":
                    total_service_span_days,

                # ---------------------------------------------------------
                # Observed daily activity
                # ---------------------------------------------------------

                "mean_daily_active_vehicles":
                    mean_daily_active,

                "median_daily_active_vehicles":
                    median_daily_active,

                "p90_daily_active_vehicles":
                    p90_daily_active,

                "p95_daily_active_vehicles":
                    p95_daily_active,

                "max_daily_active_vehicles":
                    max_daily_active,

                # ---------------------------------------------------------
                # Fleet proxies
                # ---------------------------------------------------------

                "fleet_lower_proxy":
                    mean_daily_active,

                "fleet_base_service_span_equivalent":
                    service_span_equivalent,

                "fleet_upper_proxy_unique_ids":
                    unique_ids,

                # ---------------------------------------------------------
                # Ratios
                # ---------------------------------------------------------

                "base_to_lower_multiplier":
                    (
                        service_span_equivalent
                        /
                        mean_daily_active
                    ),

                "upper_to_base_multiplier":
                    (
                        unique_ids
                        /
                        service_span_equivalent
                    ),

                "mean_vehicle_active_days":
                    vehicle_op[
                        "active_days"
                    ].mean(),

                "median_vehicle_active_days":
                    vehicle_op[
                        "active_days"
                    ].median(),

                "mean_vehicle_service_span_days":
                    vehicle_op[
                        "service_span_days"
                    ].mean(),

                "median_vehicle_service_span_days":
                    vehicle_op[
                        "service_span_days"
                    ].median(),

                "mean_active_day_share_of_service_span_pct":
                    vehicle_op[
                        "active_day_share_of_service_span_pct"
                    ].mean(),

                "median_active_day_share_of_service_span_pct":
                    vehicle_op[
                        "active_day_share_of_service_span_pct"
                    ].median(),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# SERVICE-SPAN DISTRIBUTION
# =============================================================================

def build_service_span_distribution(
    vehicle,
):

    rows = []

    for operator, group in (
        vehicle.groupby(
            "operator",
            observed=True,
        )
    ):

        span = group[
            "service_span_days"
        ]

        active = group[
            "active_days"
        ]

        rows.append(
            {
                "operator":
                    operator,

                "vehicles":
                    len(group),

                "mean_service_span_days":
                    span.mean(),

                "median_service_span_days":
                    span.median(),

                "p10_service_span_days":
                    span.quantile(0.10),

                "p25_service_span_days":
                    span.quantile(0.25),

                "p75_service_span_days":
                    span.quantile(0.75),

                "p90_service_span_days":
                    span.quantile(0.90),

                "mean_active_days":
                    active.mean(),

                "median_active_days":
                    active.median(),

                "p90_active_days":
                    active.quantile(0.90),

                "vehicles_seen_1_day":
                    (
                        span == 1
                    ).sum(),

                "vehicles_seen_le_7_days":
                    (
                        span <= 7
                    ).sum(),

                "vehicles_seen_ge_180_days":
                    (
                        span >= 180
                    ).sum(),

                "vehicles_seen_ge_300_days":
                    (
                        span >= 300
                    ).sum(),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    common,
    daily,
    vehicle,
    summary,
):

    # ---------------------------------------------------------
    # Trip reconciliation
    # ---------------------------------------------------------

    trip_counts = (
        common.groupby(
            "operator",
            observed=True,
        )
        .size()
    )

    summary_counts = (
        summary.set_index(
            "operator"
        )[
            "common_window_trips"
        ]
    )

    for operator in OPERATORS:

        assert (
            int(
                trip_counts[
                    operator
                ]
            )
            ==
            int(
                summary_counts[
                    operator
                ]
            )
        )

    # ---------------------------------------------------------
    # Vehicle-day reconciliation
    # ---------------------------------------------------------

    direct_vehicle_days = (
        common[
            [
                "operator",
                "activity_date",
                "vehicle_uid",
            ]
        ]
        .drop_duplicates()
        .groupby(
            "operator",
            observed=True,
        )
        .size()
    )

    vehicle_level_days = (
        vehicle.groupby(
            "operator",
            observed=True,
        )[
            "active_days"
        ]
        .sum()
    )

    for operator in OPERATORS:

        assert (
            int(
                direct_vehicle_days[
                    operator
                ]
            )
            ==
            int(
                vehicle_level_days[
                    operator
                ]
            )
        )

    # ---------------------------------------------------------
    # Fleet hierarchy
    # ---------------------------------------------------------

    for _, row in summary.iterrows():

        assert (
            row[
                "fleet_lower_proxy"
            ]
            <=
            row[
                "fleet_base_service_span_equivalent"
            ]
            + 1e-9
        )

        assert (
            row[
                "fleet_base_service_span_equivalent"
            ]
            <=
            row[
                "fleet_upper_proxy_unique_ids"
            ]
            + 1e-9
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 120
    )

    print(
        "EXERCISE 5 — FLEET EXPOSURE AUDIT"
    )

    print(
        "=" * 120
    )

    print(
        "\nCommon detailed-time window:"
        "\n2024-02-01 -> 2024-12-31"
        f"\nCalendar days: {COMMON_DAYS}"
    )

    df = load_data()

    (
        common,
        coverage,
    ) = build_common_window(
        df
    )

    daily = build_daily_active_fleet(
        common
    )

    vehicle = build_vehicle_exposure(
        common
    )

    monthly = build_monthly_fleet(
        common
    )

    summary = build_fleet_summary(
        common,
        daily,
        vehicle,
    )

    span_distribution = (
        build_service_span_distribution(
            vehicle
        )
    )

    validate(
        common,
        daily,
        vehicle,
        summary,
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    coverage.to_csv(
        AUDIT_DIR
        / "common_window_coverage_2024.csv",
        index=False,
    )

    daily.to_csv(
        TABLE_DIR
        / "daily_active_fleet_common_window_2024.csv",
        index=False,
    )

    monthly.to_csv(
        TABLE_DIR
        / "monthly_fleet_activity_common_window_2024.csv",
        index=False,
    )

    vehicle.to_csv(
        TABLE_DIR
        / "vehicle_exposure_common_window_2024.csv",
        index=False,
    )

    summary.to_csv(
        TABLE_DIR
        / "fleet_exposure_scenarios_2024.csv",
        index=False,
    )

    span_distribution.to_csv(
        TABLE_DIR
        / "vehicle_service_span_distribution_2024.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL
    # =========================================================================

    pd.set_option(
        "display.max_columns",
        None,
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "COMMON-WINDOW COVERAGE"
    )

    print(
        "=" * 120
    )

    print(
        coverage.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "FLEET EXPOSURE SCENARIOS"
    )

    print(
        "=" * 120
    )

    print(
        summary
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "VEHICLE SERVICE-SPAN DISTRIBUTION"
    )

    print(
        "=" * 120
    )

    print(
        span_distribution
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "DAILY ACTIVE VEHICLE SUMMARY"
    )

    print(
        "=" * 120
    )

    daily_summary = (
        daily.groupby(
            "operator",
            observed=True,
        )[
            "active_vehicles"
        ]
        .agg(
            [
                "mean",
                "median",
                "min",
                "max",
            ]
        )
        .reset_index()
    )

    print(
        daily_summary
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\nINTERPRETATION:"
        "\n- fleet_lower_proxy = mean number of vehicles that generated at least one trip per day."
        "\n- fleet_base_service_span_equivalent assumes a vehicle remains part of the operational fleet"
        "\n  continuously between its first and last observed trip."
        "\n- fleet_upper_proxy_unique_ids treats every distinct vehicle ID observed during Feb-Dec as"
        "\n  if it represented a full fleet unit."
        "\n- The lower proxy is likely conservative because deployed vehicles may receive zero trips"
        "\n  on some days."
        "\n- The upper proxy may overstate annual fleet exposure because vehicles can enter or leave"
        "\n  service during the year."
        "\n- The service-span proxy is therefore used as the primary fleet-exposure scenario,"
        "\n  but remains an analytical proxy rather than an observed accounting fleet."
        "\n- VOI January 2024 is excluded because detailed timestamps are unavailable."
        "\n- No financial cost is calculated in this audit."
    )


if __name__ == "__main__":
    main()