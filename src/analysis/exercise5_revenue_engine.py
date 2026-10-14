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

TARIFF_FILE = (
    PROJECT_ROOT
    / "config"
    / "exercise_5"
    / "tariffs_2024.csv"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_5"
    / "revenue"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "revenue"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_5"
    / "revenue"
)

for path in [
    PROCESSED_DIR,
    TABLE_DIR,
    AUDIT_DIR,
]:
    path.mkdir(
        parents=True,
        exist_ok=True,
    )


# =============================================================================
# EXPECTED 2024 POPULATION
# =============================================================================

EXPECTED_TRIPS = {
    "bird": 390844,
    "lime": 1196200,
    "voi": 106115,
}

EXPECTED_OPERATORS = {
    "bird",
    "lime",
    "voi",
}


# =============================================================================
# LOAD DATA
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
            "source_period",
            "duration_min_clean",
            "valid_duration",
        ],
    )

    df[
        "operator"
    ] = (
        df[
            "operator"
        ]
        .astype("string")
        .str.lower()
    )

    df[
        "source_period"
    ] = (
        df[
            "source_period"
        ]
        .astype("string")
    )

    # ---------------------------------------------------------
    # Structural validation
    # ---------------------------------------------------------

    assert df[
        "trip_uid"
    ].is_unique

    assert set(
        df[
            "operator"
        ].unique()
    ) == EXPECTED_OPERATORS

    assert len(df) == sum(
        EXPECTED_TRIPS.values()
    )

    observed_counts = (
        df.groupby(
            "operator"
        )
        .size()
        .to_dict()
    )

    assert (
        observed_counts
        ==
        EXPECTED_TRIPS
    ), (
        "2024 trip counts do not match "
        "the harmonized population."
    )

    return df


def load_tariffs():

    if not TARIFF_FILE.exists():
        raise FileNotFoundError(
            TARIFF_FILE
        )

    tariffs = pd.read_csv(
        TARIFF_FILE
    )

    tariffs[
        "operator"
    ] = (
        tariffs[
            "operator"
        ]
        .astype("string")
        .str.lower()
    )

    tariffs = tariffs.loc[
        tariffs[
            "year"
        ]
        == 2024
    ].copy()

    assert set(
        tariffs[
            "operator"
        ]
    ) == EXPECTED_OPERATORS

    assert tariffs[
        "operator"
    ].is_unique

    assert (
        tariffs[
            "unlock_fee_eur"
        ]
        >= 0
    ).all()

    assert (
        tariffs[
            "per_minute_eur"
        ]
        >= 0
    ).all()

    return tariffs


# =============================================================================
# REVENUE CALCULATION
# =============================================================================

def build_trip_revenue(
    df,
    tariffs,
):

    data = df.merge(
        tariffs[
            [
                "operator",
                "unlock_fee_eur",
                "per_minute_eur",
            ]
        ],
        on="operator",
        how="left",
        validate="many_to_one",
    )

    assert data[
        "unlock_fee_eur"
    ].notna().all()

    assert data[
        "per_minute_eur"
    ].notna().all()

    # -------------------------------------------------------------------------
    # Duration usability for fare estimation
    # -------------------------------------------------------------------------

    data[
        "revenue_duration_estimable"
    ] = (
        data[
            "valid_duration"
        ]
        .fillna(False)
        .astype(bool)
        &
        data[
            "duration_min_clean"
        ]
        .notna()
        &
        (
            data[
                "duration_min_clean"
            ]
            > 0
        )
    )

    # -------------------------------------------------------------------------
    # PAYG unlock revenue
    #
    # Under the base PAYG assumption every observed trip generates one unlock.
    # This is a scenario assumption, not observed accounting revenue.
    # -------------------------------------------------------------------------

    data[
        "unlock_revenue_eur"
    ] = (
        data[
            "unlock_fee_eur"
        ]
        .astype(float)
    )

    # -------------------------------------------------------------------------
    # Continuous-duration primary scenario
    # -------------------------------------------------------------------------

    data[
        "billed_minutes_continuous"
    ] = np.where(
        data[
            "revenue_duration_estimable"
        ],
        data[
            "duration_min_clean"
        ],
        np.nan,
    )

    data[
        "time_revenue_continuous_eur"
    ] = (
        data[
            "billed_minutes_continuous"
        ]
        *
        data[
            "per_minute_eur"
        ]
    )

    data[
        "gross_payg_continuous_eur"
    ] = np.where(
        data[
            "revenue_duration_estimable"
        ],
        (
            data[
                "unlock_revenue_eur"
            ]
            +
            data[
                "time_revenue_continuous_eur"
            ]
        ),
        np.nan,
    )

    # -------------------------------------------------------------------------
    # Ceil-to-minute sensitivity scenario
    #
    # This is NOT treated as a verified historical billing rule
    # for all operators.
    # -------------------------------------------------------------------------

    data[
        "billed_minutes_ceil"
    ] = np.where(
        data[
            "revenue_duration_estimable"
        ],
        np.ceil(
            data[
                "duration_min_clean"
            ]
        ),
        np.nan,
    )

    data[
        "time_revenue_ceil_eur"
    ] = (
        data[
            "billed_minutes_ceil"
        ]
        *
        data[
            "per_minute_eur"
        ]
    )

    data[
        "gross_payg_ceil_eur"
    ] = np.where(
        data[
            "revenue_duration_estimable"
        ],
        (
            data[
                "unlock_revenue_eur"
            ]
            +
            data[
                "time_revenue_ceil_eur"
            ]
        ),
        np.nan,
    )

    # -------------------------------------------------------------------------
    # All-trip lower bounds
    #
    # For trips with unusable duration, the unlock component is known under
    # the PAYG assumption, but the time-based component cannot be estimated.
    # Missing time revenue is therefore treated as zero ONLY for the explicit
    # lower-bound measure.
    # -------------------------------------------------------------------------

    data[
        "payg_continuous_lower_bound_eur"
    ] = (
        data[
            "unlock_revenue_eur"
        ]
        +
        data[
            "time_revenue_continuous_eur"
        ]
        .fillna(0.0)
    )

    data[
        "payg_ceil_lower_bound_eur"
    ] = (
        data[
            "unlock_revenue_eur"
        ]
        +
        data[
            "time_revenue_ceil_eur"
        ]
        .fillna(0.0)
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    assert (
        data[
            "unlock_revenue_eur"
        ]
        >= 0
    ).all()

    assert (
        data.loc[
            data[
                "revenue_duration_estimable"
            ],
            "gross_payg_continuous_eur",
        ]
        >=
        data.loc[
            data[
                "revenue_duration_estimable"
            ],
            "unlock_revenue_eur",
        ]
    ).all()

    assert (
        data.loc[
            data[
                "revenue_duration_estimable"
            ],
            "gross_payg_ceil_eur",
        ]
        >=
        data.loc[
            data[
                "revenue_duration_estimable"
            ],
            "gross_payg_continuous_eur",
        ]
    ).all()

    return data


# =============================================================================
# OPERATOR SUMMARY
# =============================================================================

def build_operator_summary(
    data,
):

    rows = []

    for operator, df in (
        data.groupby(
            "operator",
            observed=True,
        )
    ):

        estimable = df.loc[
            df[
                "revenue_duration_estimable"
            ]
        ]

        observed_trips = len(df)

        estimable_trips = len(
            estimable
        )

        unestimable_trips = (
            observed_trips
            -
            estimable_trips
        )

        unlock_revenue = (
            df[
                "unlock_revenue_eur"
            ]
            .sum()
        )

        time_cont = (
            df[
                "time_revenue_continuous_eur"
            ]
            .sum(
                min_count=1
            )
        )

        time_ceil = (
            df[
                "time_revenue_ceil_eur"
            ]
            .sum(
                min_count=1
            )
        )

        revenue_cont_lb = (
            df[
                "payg_continuous_lower_bound_eur"
            ]
            .sum()
        )

        revenue_ceil_lb = (
            df[
                "payg_ceil_lower_bound_eur"
            ]
            .sum()
        )

        rounding_uplift = (
            revenue_ceil_lb
            -
            revenue_cont_lb
        )

        unique_vehicles = (
            df[
                "vehicle_uid"
            ]
            .nunique()
        )

        rows.append(
            {
                "operator":
                    operator,

                "observed_trips":
                    observed_trips,

                "duration_estimable_trips":
                    estimable_trips,

                "duration_unestimable_trips":
                    unestimable_trips,

                "duration_estimable_pct":
                    (
                        estimable_trips
                        /
                        observed_trips
                        * 100
                    ),

                "unique_observed_vehicles":
                    unique_vehicles,

                "mean_valid_duration_min":
                    estimable[
                        "duration_min_clean"
                    ].mean(),

                "median_valid_duration_min":
                    estimable[
                        "duration_min_clean"
                    ].median(),

                "unlock_revenue_all_trips_eur":
                    unlock_revenue,

                "time_revenue_continuous_known_eur":
                    time_cont,

                "gross_payg_continuous_lower_bound_eur":
                    revenue_cont_lb,

                "time_revenue_ceil_known_eur":
                    time_ceil,

                "gross_payg_ceil_lower_bound_eur":
                    revenue_ceil_lb,

                "ceil_uplift_eur":
                    rounding_uplift,

                "ceil_uplift_pct":
                    (
                        rounding_uplift
                        /
                        revenue_cont_lb
                        * 100
                    ),

                "mean_revenue_per_estimable_trip_continuous_eur":
                    estimable[
                        "gross_payg_continuous_eur"
                    ].mean(),

                "median_revenue_per_estimable_trip_continuous_eur":
                    estimable[
                        "gross_payg_continuous_eur"
                    ].median(),

                "p90_revenue_per_estimable_trip_continuous_eur":
                    estimable[
                        "gross_payg_continuous_eur"
                    ].quantile(
                        0.90
                    ),

                "continuous_revenue_per_observed_vehicle_eur":
                    (
                        revenue_cont_lb
                        /
                        unique_vehicles
                    ),

                "unlock_share_of_continuous_lower_bound_pct":
                    (
                        unlock_revenue
                        /
                        revenue_cont_lb
                        * 100
                    ),

                "time_share_of_continuous_lower_bound_pct":
                    (
                        time_cont
                        /
                        revenue_cont_lb
                        * 100
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# MONTHLY SUMMARY
# =============================================================================

def build_monthly_summary(
    data,
):

    monthly = (
        data.groupby(
            [
                "operator",
                "source_period",
            ],
            observed=True,
        )
        .agg(
            observed_trips=(
                "trip_uid",
                "count",
            ),

            duration_estimable_trips=(
                "revenue_duration_estimable",
                "sum",
            ),

            unique_observed_vehicles=(
                "vehicle_uid",
                "nunique",
            ),

            unlock_revenue_eur=(
                "unlock_revenue_eur",
                "sum",
            ),

            time_revenue_continuous_known_eur=(
                "time_revenue_continuous_eur",
                "sum",
            ),

            gross_payg_continuous_lower_bound_eur=(
                "payg_continuous_lower_bound_eur",
                "sum",
            ),

            gross_payg_ceil_lower_bound_eur=(
                "payg_ceil_lower_bound_eur",
                "sum",
            ),
        )
        .reset_index()
    )

    monthly[
        "duration_unestimable_trips"
    ] = (
        monthly[
            "observed_trips"
        ]
        -
        monthly[
            "duration_estimable_trips"
        ]
    )

    monthly[
        "mean_continuous_revenue_per_trip_eur"
    ] = (
        monthly[
            "gross_payg_continuous_lower_bound_eur"
        ]
        /
        monthly[
            "observed_trips"
        ]
    )

    return monthly


# =============================================================================
# VEHICLE SUMMARY
# =============================================================================

def build_vehicle_summary(
    data,
):

    vehicle = (
        data.groupby(
            [
                "operator",
                "vehicle_uid",
            ],
            observed=True,
        )
        .agg(
            observed_trips=(
                "trip_uid",
                "count",
            ),

            duration_estimable_trips=(
                "revenue_duration_estimable",
                "sum",
            ),

            first_source_period=(
                "source_period",
                "min",
            ),

            last_source_period=(
                "source_period",
                "max",
            ),

            unlock_revenue_eur=(
                "unlock_revenue_eur",
                "sum",
            ),

            time_revenue_continuous_known_eur=(
                "time_revenue_continuous_eur",
                "sum",
            ),

            gross_payg_continuous_lower_bound_eur=(
                "payg_continuous_lower_bound_eur",
                "sum",
            ),

            gross_payg_ceil_lower_bound_eur=(
                "payg_ceil_lower_bound_eur",
                "sum",
            ),
        )
        .reset_index()
    )

    vehicle[
        "mean_continuous_revenue_per_trip_eur"
    ] = (
        vehicle[
            "gross_payg_continuous_lower_bound_eur"
        ]
        /
        vehicle[
            "observed_trips"
        ]
    )

    return vehicle


# =============================================================================
# RECONCILIATION
# =============================================================================

def validate_reconciliation(
    data,
    operator_summary,
    monthly_summary,
    vehicle_summary,
):

    for operator in sorted(
        EXPECTED_OPERATORS
    ):

        df = data.loc[
            data[
                "operator"
            ]
            == operator
        ]

        op = operator_summary.loc[
            operator_summary[
                "operator"
            ]
            == operator
        ].iloc[0]

        monthly = monthly_summary.loc[
            monthly_summary[
                "operator"
            ]
            == operator
        ]

        vehicle = vehicle_summary.loc[
            vehicle_summary[
                "operator"
            ]
            == operator
        ]

        # -----------------------------------------------------
        # Trip counts
        # -----------------------------------------------------

        assert int(
            monthly[
                "observed_trips"
            ].sum()
        ) == len(df)

        assert int(
            vehicle[
                "observed_trips"
            ].sum()
        ) == len(df)

        # -----------------------------------------------------
        # Revenue reconciliation
        # -----------------------------------------------------

        trip_revenue = (
            df[
                "payg_continuous_lower_bound_eur"
            ]
            .sum()
        )

        monthly_revenue = (
            monthly[
                "gross_payg_continuous_lower_bound_eur"
            ]
            .sum()
        )

        vehicle_revenue = (
            vehicle[
                "gross_payg_continuous_lower_bound_eur"
            ]
            .sum()
        )

        assert np.isclose(
            trip_revenue,
            monthly_revenue,
            rtol=0,
            atol=0.01,
        )

        assert np.isclose(
            trip_revenue,
            vehicle_revenue,
            rtol=0,
            atol=0.01,
        )

        assert np.isclose(
            trip_revenue,
            op[
                "gross_payg_continuous_lower_bound_eur"
            ],
            rtol=0,
            atol=0.01,
        )

        # -----------------------------------------------------
        # Full-year monthly coverage
        # -----------------------------------------------------

        assert monthly[
            "source_period"
        ].nunique() == 12


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 120
    )

    print(
        "EXERCISE 5 — 2024 PAYG REVENUE ENGINE"
    )

    print(
        "=" * 120
    )

    data = load_data()

    tariffs = load_tariffs()

    revenue = build_trip_revenue(
        data,
        tariffs,
    )

    operator_summary = (
        build_operator_summary(
            revenue
        )
    )

    monthly_summary = (
        build_monthly_summary(
            revenue
        )
    )

    vehicle_summary = (
        build_vehicle_summary(
            revenue
        )
    )

    validate_reconciliation(
        revenue,
        operator_summary,
        monthly_summary,
        vehicle_summary,
    )

    # =========================================================================
    # SAVE TRIP-LEVEL REVENUE
    # =========================================================================

    trip_output = (
        PROCESSED_DIR
        / "trip_payg_revenue_2024.parquet"
    )

    revenue.to_parquet(
        trip_output,
        index=False,
    )

    operator_summary.to_csv(
        TABLE_DIR
        / "payg_revenue_operator_summary_2024.csv",
        index=False,
    )

    monthly_summary.to_csv(
        TABLE_DIR
        / "payg_revenue_monthly_2024.csv",
        index=False,
    )

    vehicle_summary.to_csv(
        TABLE_DIR
        / "payg_revenue_by_vehicle_2024.csv",
        index=False,
    )

    # =========================================================================
    # UNESTIMABLE DURATION AUDIT
    # =========================================================================

    unestimable = revenue.loc[
        ~revenue[
            "revenue_duration_estimable"
        ],
        [
            "operator",
            "trip_uid",
            "vehicle_uid",
            "source_period",
            "duration_min_clean",
            "valid_duration",
            "unlock_fee_eur",
            "per_minute_eur",
        ],
    ].copy()

    unestimable.to_csv(
        AUDIT_DIR
        / "revenue_duration_unestimable_trips_2024.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL
    # =========================================================================

    pd.set_option(
        "display.max_columns",
        None,
    )

    display = (
        operator_summary.copy()
    )

    money_cols = [
        col
        for col in display.columns
        if (
            col.endswith("_eur")
            or "revenue" in col
        )
        and (
            display[col].dtype
            != "object"
        )
    ]

    for col in money_cols:
        display[col] = (
            display[col]
            .round(2)
        )

    display[
        "duration_estimable_pct"
    ] = (
        display[
            "duration_estimable_pct"
        ]
        .round(4)
    )

    display[
        "ceil_uplift_pct"
    ] = (
        display[
            "ceil_uplift_pct"
        ]
        .round(3)
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "OPERATOR PAYG REVENUE SUMMARY"
    )

    print(
        "=" * 120
    )

    print(
        display.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "MONTHLY REVENUE RECONCILIATION"
    )

    print(
        "=" * 120
    )

    monthly_display = (
        monthly_summary.copy()
    )

    for col in [
        "unlock_revenue_eur",
        "time_revenue_continuous_known_eur",
        "gross_payg_continuous_lower_bound_eur",
        "gross_payg_ceil_lower_bound_eur",
        "mean_continuous_revenue_per_trip_eur",
    ]:

        monthly_display[col] = (
            monthly_display[col]
            .round(2)
        )

    print(
        monthly_display.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "REVENUE DATA-QUALITY AUDIT"
    )

    print(
        "=" * 120
    )

    print(
        revenue.groupby(
            "operator",
            observed=True,
        )
        .agg(
            observed_trips=(
                "trip_uid",
                "count",
            ),

            duration_estimable=(
                "revenue_duration_estimable",
                "sum",
            ),
        )
        .assign(
            duration_unestimable=lambda x:
                (
                    x[
                        "observed_trips"
                    ]
                    -
                    x[
                        "duration_estimable"
                    ]
                )
        )
        .to_string()
    )

    print(
        "\nVALIDATION:"
        "\n- All cleaned/harmonized 2024 trip records enter the PAYG revenue population."
        "\n- One unlock fee is assigned to each observed trip under the PAYG base scenario."
        "\n- Time-based revenue is calculated only where cleaned duration is valid and positive."
        "\n- Trips with unusable duration are retained; their unknown time charge is not imputed."
        "\n- Continuous observed minutes are the primary pricing scenario."
        "\n- Ceil-to-minute billing is a sensitivity scenario."
        "\n- Subscription/pass adoption is NOT inferred from trip data."
        "\n- Monthly revenue uses source_period, so VOI January 2024 remains included."
        "\n- Trip-, monthly-, vehicle-, and operator-level revenues reconcile."
        "\n- Outputs represent estimated gross PAYG fare revenue, not audited company accounting revenue."
    )

    print(
        f"\nTrip-level revenue -> "
        f"{trip_output}"
    )


if __name__ == "__main__":
    main()