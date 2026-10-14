from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

REVENUE_FILE = (
    ROOT
    / "data"
    / "processed"
    / "exercise_5"
    / "revenue"
    / "trip_payg_revenue_2024.parquet"
)

HARMONIZED_FILE = (
    ROOT
    / "data"
    / "processed"
    / "harmonized"
    / "all_operators_2024_harmonized.parquet"
)

FLEET_FILE = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "fleet_exposure"
    / "fleet_exposure_scenarios_2024.csv"
)

ASSUMPTION_FILE = (
    ROOT
    / "config"
    / "exercise_5"
    / "cost_assumptions_2024.csv"
)

TABLE_DIR = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "costs"
)

AUDIT_DIR = (
    ROOT
    / "audit"
    / "exercise_5"
    / "costs"
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OPERATORS = [
    "bird",
    "lime",
    "voi",
]

SCENARIO_ORDER = [
    "low",
    "base",
    "high",
]

EXPECTED_TRIPS = {
    "bird": 390844,
    "lime": 1196200,
    "voi": 106115,
}


# =============================================================================
# LOAD REVENUE
# =============================================================================

def load_revenue():

    if not REVENUE_FILE.exists():
        raise FileNotFoundError(
            REVENUE_FILE
        )

    df = pd.read_parquet(
        REVENUE_FILE,
        columns=[
            "operator",
            "trip_uid",
            "payg_continuous_lower_bound_eur",
        ],
    )

    df["operator"] = (
        df["operator"]
        .astype("string")
        .str.lower()
    )

    assert df["trip_uid"].is_unique

    observed = (
        df.groupby(
            "operator",
            observed=True,
        )
        .size()
        .to_dict()
    )

    assert (
        observed
        ==
        EXPECTED_TRIPS
    )

    return df


# =============================================================================
# LOAD COMMON DISTANCE PROXY
# =============================================================================

def load_distance():

    if not HARMONIZED_FILE.exists():
        raise FileNotFoundError(
            HARMONIZED_FILE
        )

    df = pd.read_parquet(
        HARMONIZED_FILE,
        columns=[
            "operator",
            "trip_uid",
            "endpoint_displacement_km",
            "valid_endpoint_displacement",
        ],
    )

    df["operator"] = (
        df["operator"]
        .astype("string")
        .str.lower()
    )

    assert df["trip_uid"].is_unique

    numeric_distance = pd.to_numeric(
        df["endpoint_displacement_km"],
        errors="coerce",
    )

    valid_flag = (
        df["valid_endpoint_displacement"]
        .fillna(False)
        .astype(bool)
    )

    df[
        "electricity_distance_estimable"
    ] = (
        valid_flag
        &
        numeric_distance.notna()
        &
        np.isfinite(
            numeric_distance
        )
        &
        (
            numeric_distance
            >= 0
        )
    )

    df[
        "endpoint_distance_used_km"
    ] = np.where(
        df[
            "electricity_distance_estimable"
        ],
        numeric_distance,
        np.nan,
    )

    return df


# =============================================================================
# LOAD FLEET EXPOSURE
# =============================================================================

def load_fleet():

    if not FLEET_FILE.exists():
        raise FileNotFoundError(
            FLEET_FILE
        )

    df = pd.read_csv(
        FLEET_FILE
    )

    df["operator"] = (
        df["operator"]
        .astype("string")
        .str.lower()
    )

    assert set(
        df["operator"]
    ) == set(
        OPERATORS
    )

    assert df["operator"].is_unique

    required = {
        "fleet_lower_proxy",
        "fleet_base_service_span_equivalent",
        "fleet_upper_proxy_unique_ids",
    }

    missing = required - set(
        df.columns
    )

    if missing:
        raise ValueError(
            f"Fleet file missing: {sorted(missing)}"
        )

    for _, row in df.iterrows():

        assert (
            row[
                "fleet_lower_proxy"
            ]
            <=
            row[
                "fleet_base_service_span_equivalent"
            ]
            <=
            row[
                "fleet_upper_proxy_unique_ids"
            ]
        )

    return df


# =============================================================================
# LOAD COST ASSUMPTIONS
# =============================================================================

def load_assumptions():

    if not ASSUMPTION_FILE.exists():
        raise FileNotFoundError(
            ASSUMPTION_FILE
        )

    df = pd.read_csv(
        ASSUMPTION_FILE
    )

    assert set(
        df["scenario"]
    ) == set(
        SCENARIO_ORDER
    )

    assert df[
        "scenario"
    ].is_unique

    df[
        "direct_vehicle_opex_eur_per_trip"
    ] = (
        df[
            "spares_maintenance_eur_per_trip"
        ]
        +
        df[
            "vehicle_personnel_charging_eur_per_trip"
        ]
        +
        df[
            "other_direct_vehicle_opex_eur_per_trip"
        ]
    )

    # ---------------------------------------------------------
    # Depreciation validation
    # ---------------------------------------------------------

    check = (
        df[
            "acquisition_cost_eur_per_vehicle"
        ]
        /
        df[
            "useful_life_years"
        ]
    )

    assert np.allclose(
        check,
        df[
            "annual_depreciation_eur_per_vehicle"
        ],
        atol=0.001,
    )

    return df


# =============================================================================
# OPERATOR REVENUE SUMMARY
# =============================================================================

def build_revenue_summary(
    revenue,
):

    summary = (
        revenue.groupby(
            "operator",
            observed=True,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            ),

            estimated_gross_payg_revenue_eur=(
                "payg_continuous_lower_bound_eur",
                "sum",
            ),
        )
        .reset_index()
    )

    summary[
        "mean_estimated_revenue_per_trip_eur"
    ] = (
        summary[
            "estimated_gross_payg_revenue_eur"
        ]
        /
        summary[
            "trips"
        ]
    )

    return summary


# =============================================================================
# DISTANCE / ELECTRICITY AUDIT
# =============================================================================

def build_distance_summary(
    distance,
):

    rows = []

    for operator, group in (
        distance.groupby(
            "operator",
            observed=True,
        )
    ):

        valid = group.loc[
            group[
                "electricity_distance_estimable"
            ]
        ]

        rows.append(
            {
                "operator":
                    operator,

                "trips":
                    len(group),

                "distance_estimable_trips":
                    len(valid),

                "distance_unestimable_trips":
                    (
                        len(group)
                        -
                        len(valid)
                    ),

                "distance_estimable_pct":
                    (
                        len(valid)
                        /
                        len(group)
                        * 100
                    ),

                "total_endpoint_displacement_km":
                    valid[
                        "endpoint_distance_used_km"
                    ].sum(),

                "mean_endpoint_displacement_km":
                    valid[
                        "endpoint_distance_used_km"
                    ].mean(),

                "median_endpoint_displacement_km":
                    valid[
                        "endpoint_distance_used_km"
                    ].median(),

                "p90_endpoint_displacement_km":
                    valid[
                        "endpoint_distance_used_km"
                    ].quantile(
                        0.90
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# COST ENGINE
# =============================================================================

def build_cost_scenarios(
    revenue_summary,
    distance_summary,
    fleet,
    assumptions,
):

    operator_data = (
        revenue_summary
        .merge(
            distance_summary,
            on=[
                "operator",
                "trips",
            ],
            how="left",
            validate="one_to_one",
        )
        .merge(
            fleet,
            on="operator",
            how="left",
            validate="one_to_one",
        )
    )

    rows = []

    for _, assumption in (
        assumptions.iterrows()
    ):

        scenario = assumption[
            "scenario"
        ]

        fleet_proxy_column = (
            assumption[
                "fleet_proxy"
            ]
        )

        if (
            fleet_proxy_column
            not in operator_data.columns
        ):
            raise ValueError(
                "Unknown fleet proxy column: "
                f"{fleet_proxy_column}"
            )

        for _, op in (
            operator_data.iterrows()
        ):

            operator = op[
                "operator"
            ]

            trips = float(
                op[
                    "trips"
                ]
            )

            revenue = float(
                op[
                    "estimated_gross_payg_revenue_eur"
                ]
            )

            revenue_per_trip = (
                revenue
                /
                trips
            )

            fleet_proxy = float(
                op[
                    fleet_proxy_column
                ]
            )

            # =============================================================
            # CAPITAL STOCK MEMO
            # =============================================================

            acquisition_cost = float(
                assumption[
                    "acquisition_cost_eur_per_vehicle"
                ]
            )

            capital_stock_proxy = (
                fleet_proxy
                *
                acquisition_cost
            )

            # =============================================================
            # DIRECT VEHICLE OPEX
            # =============================================================

            spares_cost = (
                trips
                *
                float(
                    assumption[
                        "spares_maintenance_eur_per_trip"
                    ]
                )
            )

            vehicle_personnel_cost = (
                trips
                *
                float(
                    assumption[
                        "vehicle_personnel_charging_eur_per_trip"
                    ]
                )
            )

            other_direct_cost = (
                trips
                *
                float(
                    assumption[
                        "other_direct_vehicle_opex_eur_per_trip"
                    ]
                )
            )

            direct_vehicle_opex = (
                spares_cost
                +
                vehicle_personnel_cost
                +
                other_direct_cost
            )

            direct_opex_per_trip = (
                direct_vehicle_opex
                /
                trips
            )

            # =============================================================
            # VEHICLE CONTRIBUTION
            # =============================================================

            vehicle_contribution = (
                revenue
                -
                direct_vehicle_opex
            )

            # =============================================================
            # MARKET / LOCAL OVERHEAD
            # Includes insurance in our benchmark.
            # =============================================================

            market_overhead = (
                fleet_proxy
                *
                float(
                    assumption[
                        "market_overhead_including_insurance_eur_per_vehicle_year"
                    ]
                )
            )

            market_ebitda_proxy = (
                vehicle_contribution
                -
                market_overhead
            )

            # =============================================================
            # DEPRECIATION
            # =============================================================

            depreciation = (
                fleet_proxy
                *
                float(
                    assumption[
                        "annual_depreciation_eur_per_vehicle"
                    ]
                )
            )

            # =============================================================
            # PRIMARY COST / OPERATING PROFIT PROXY
            #
            # Electricity is intentionally excluded here because of
            # possible overlap with the published direct OPEX benchmark.
            # =============================================================

            primary_total_cost = (
                direct_vehicle_opex
                +
                market_overhead
                +
                depreciation
            )

            operating_profit_proxy = (
                revenue
                -
                primary_total_cost
            )

            # =============================================================
            # ELECTRICITY MEMO
            #
            # Based on endpoint displacement rather than actual route km.
            # Not part of primary total cost.
            # =============================================================

            endpoint_km = float(
                op[
                    "total_endpoint_displacement_km"
                ]
            )

            energy_intensity = float(
                assumption[
                    "energy_intensity_kwh_per_km"
                ]
            )

            electricity_price = float(
                assumption[
                    "electricity_price_eur_per_kwh"
                ]
            )

            estimated_energy_kwh = (
                endpoint_km
                *
                energy_intensity
            )

            electricity_memo_cost = (
                estimated_energy_kwh
                *
                electricity_price
            )

            # Explicit sensitivity only
            cost_plus_electricity = (
                primary_total_cost
                +
                electricity_memo_cost
            )

            profit_plus_electricity = (
                revenue
                -
                cost_plus_electricity
            )

            # =============================================================
            # BREAK-EVEN
            #
            # Current average fare per trip is held constant.
            # Fixed-like costs = market overhead + depreciation.
            # =============================================================

            contribution_per_trip_before_fixed = (
                revenue_per_trip
                -
                direct_opex_per_trip
            )

            annual_fixed_like_cost = (
                market_overhead
                +
                depreciation
            )

            if (
                contribution_per_trip_before_fixed
                > 0
            ):

                break_even_trips = (
                    annual_fixed_like_cost
                    /
                    contribution_per_trip_before_fixed
                )

                actual_to_break_even_ratio = (
                    trips
                    /
                    break_even_trips
                )

            else:

                break_even_trips = np.inf

                actual_to_break_even_ratio = 0.0

            # =============================================================
            # NORMALIZED METRICS
            # =============================================================

            primary_cost_per_trip = (
                primary_total_cost
                /
                trips
            )

            operating_profit_per_trip = (
                operating_profit_proxy
                /
                trips
            )

            cost_to_revenue_pct = (
                primary_total_cost
                /
                revenue
                * 100
            )

            operating_margin_pct = (
                operating_profit_proxy
                /
                revenue
                * 100
            )

            direct_opex_share_cost_pct = (
                direct_vehicle_opex
                /
                primary_total_cost
                * 100
            )

            market_overhead_share_cost_pct = (
                market_overhead
                /
                primary_total_cost
                * 100
            )

            depreciation_share_cost_pct = (
                depreciation
                /
                primary_total_cost
                * 100
            )

            rows.append(
                {
                    "scenario":
                        scenario,

                    "operator":
                        operator,

                    # -----------------------------------------------------
                    # Activity / revenue
                    # -----------------------------------------------------

                    "trips":
                        int(
                            trips
                        ),

                    "estimated_gross_payg_revenue_eur":
                        revenue,

                    "mean_estimated_revenue_per_trip_eur":
                        revenue_per_trip,

                    # -----------------------------------------------------
                    # Fleet / capital
                    # -----------------------------------------------------

                    "fleet_proxy_method":
                        fleet_proxy_column,

                    "fleet_units_proxy":
                        fleet_proxy,

                    "acquisition_cost_eur_per_vehicle":
                        acquisition_cost,

                    "capital_stock_proxy_eur":
                        capital_stock_proxy,

                    "annual_depreciation_eur":
                        depreciation,

                    # -----------------------------------------------------
                    # Direct OPEX
                    # -----------------------------------------------------

                    "spares_maintenance_cost_eur":
                        spares_cost,

                    "vehicle_personnel_charging_cost_eur":
                        vehicle_personnel_cost,

                    "other_direct_vehicle_opex_eur":
                        other_direct_cost,

                    "direct_vehicle_opex_eur":
                        direct_vehicle_opex,

                    "direct_vehicle_opex_per_trip_eur":
                        direct_opex_per_trip,

                    # -----------------------------------------------------
                    # Intermediate profit
                    # -----------------------------------------------------

                    "vehicle_contribution_eur":
                        vehicle_contribution,

                    "market_overhead_including_insurance_eur":
                        market_overhead,

                    "market_ebitda_proxy_eur":
                        market_ebitda_proxy,

                    # -----------------------------------------------------
                    # Primary profitability
                    # -----------------------------------------------------

                    "primary_total_cost_eur":
                        primary_total_cost,

                    "operating_profit_proxy_eur":
                        operating_profit_proxy,

                    "primary_cost_per_trip_eur":
                        primary_cost_per_trip,

                    "operating_profit_per_trip_eur":
                        operating_profit_per_trip,

                    "cost_to_revenue_pct":
                        cost_to_revenue_pct,

                    "operating_margin_pct":
                        operating_margin_pct,

                    # -----------------------------------------------------
                    # Cost composition
                    # -----------------------------------------------------

                    "direct_opex_share_of_total_cost_pct":
                        direct_opex_share_cost_pct,

                    "market_overhead_share_of_total_cost_pct":
                        market_overhead_share_cost_pct,

                    "depreciation_share_of_total_cost_pct":
                        depreciation_share_cost_pct,

                    # -----------------------------------------------------
                    # Break-even
                    # -----------------------------------------------------

                    "contribution_per_trip_before_fixed_eur":
                        contribution_per_trip_before_fixed,

                    "annual_fixed_like_cost_eur":
                        annual_fixed_like_cost,

                    "break_even_trips":
                        break_even_trips,

                    "actual_trips_to_break_even_ratio":
                        actual_to_break_even_ratio,

                    # -----------------------------------------------------
                    # Electricity memo
                    # -----------------------------------------------------

                    "distance_estimable_pct":
                        op[
                            "distance_estimable_pct"
                        ],

                    "endpoint_displacement_km":
                        endpoint_km,

                    "energy_intensity_kwh_per_km":
                        energy_intensity,

                    "electricity_price_eur_per_kwh":
                        electricity_price,

                    "estimated_energy_from_endpoint_proxy_kwh":
                        estimated_energy_kwh,

                    "electricity_cost_memo_eur":
                        electricity_memo_cost,

                    "total_cost_plus_electricity_sensitivity_eur":
                        cost_plus_electricity,

                    "profit_plus_electricity_sensitivity_eur":
                        profit_plus_electricity,
                }
            )

    result = pd.DataFrame(
        rows
    )

    result[
        "scenario"
    ] = pd.Categorical(
        result[
            "scenario"
        ],
        categories=SCENARIO_ORDER,
        ordered=True,
    )

    result = (
        result.sort_values(
            [
                "scenario",
                "operator",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result


# =============================================================================
# LONG-FORM COST BREAKDOWN
# =============================================================================

def build_cost_breakdown(
    result,
):

    components = {
        "spares_maintenance":
            "spares_maintenance_cost_eur",

        "vehicle_personnel_charging":
            "vehicle_personnel_charging_cost_eur",

        "other_direct_vehicle_opex":
            "other_direct_vehicle_opex_eur",

        "market_overhead_including_insurance":
            "market_overhead_including_insurance_eur",

        "depreciation":
            "annual_depreciation_eur",
    }

    rows = []

    for _, row in (
        result.iterrows()
    ):

        total_cost = row[
            "primary_total_cost_eur"
        ]

        for (
            component_name,
            column_name,
        ) in components.items():

            value = row[
                column_name
            ]

            rows.append(
                {
                    "scenario":
                        row[
                            "scenario"
                        ],

                    "operator":
                        row[
                            "operator"
                        ],

                    "cost_component":
                        component_name,

                    "cost_eur":
                        value,

                    "share_of_primary_total_cost_pct":
                        (
                            value
                            /
                            total_cost
                            * 100
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# VALIDATION
# =============================================================================

def validate_results(
    result,
):

    # -------------------------------------------------------------------------
    # Nine operator × scenario combinations
    # -------------------------------------------------------------------------

    assert len(result) == (
        len(OPERATORS)
        *
        len(SCENARIO_ORDER)
    )

    # -------------------------------------------------------------------------
    # Revenue invariant across cost scenarios
    # -------------------------------------------------------------------------

    for operator in OPERATORS:

        op = result.loc[
            result[
                "operator"
            ]
            == operator
        ]

        assert (
            op[
                "estimated_gross_payg_revenue_eur"
            ]
            .nunique()
            == 1
        )

        assert (
            op[
                "trips"
            ]
            .nunique()
            == 1
        )

    # -------------------------------------------------------------------------
    # Cost reconciliation
    # -------------------------------------------------------------------------

    reconstructed = (
        result[
            "direct_vehicle_opex_eur"
        ]
        +
        result[
            "market_overhead_including_insurance_eur"
        ]
        +
        result[
            "annual_depreciation_eur"
        ]
    )

    assert np.allclose(
        reconstructed,
        result[
            "primary_total_cost_eur"
        ],
        atol=0.01,
    )

    # -------------------------------------------------------------------------
    # Profit reconciliation
    # -------------------------------------------------------------------------

    reconstructed_profit = (
        result[
            "estimated_gross_payg_revenue_eur"
        ]
        -
        result[
            "primary_total_cost_eur"
        ]
    )

    assert np.allclose(
        reconstructed_profit,
        result[
            "operating_profit_proxy_eur"
        ],
        atol=0.01,
    )

    # -------------------------------------------------------------------------
    # Cost scenario monotonicity
    # -------------------------------------------------------------------------

    scenario_rank = {
        "low": 0,
        "base": 1,
        "high": 2,
    }

    temp = result.copy()

    temp[
        "scenario_rank"
    ] = (
        temp[
            "scenario"
        ]
        .astype(str)
        .map(
            scenario_rank
        )
    )

    for operator in OPERATORS:

        op = (
            temp.loc[
                temp[
                    "operator"
                ]
                == operator
            ]
            .sort_values(
                "scenario_rank"
            )
        )

        costs = (
            op[
                "primary_total_cost_eur"
            ]
            .to_numpy()
        )

        assert (
            costs[0]
            <
            costs[1]
            <
            costs[2]
        )

    # -------------------------------------------------------------------------
    # Electricity is NOT included in primary cost
    # -------------------------------------------------------------------------

    assert np.allclose(
        (
            result[
                "primary_total_cost_eur"
            ]
            +
            result[
                "electricity_cost_memo_eur"
            ]
        ),
        result[
            "total_cost_plus_electricity_sensitivity_eur"
        ],
        atol=0.01,
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 125
    )

    print(
        "EXERCISE 5 — COST & PROFITABILITY ENGINE"
    )

    print(
        "=" * 125
    )

    revenue = load_revenue()

    distance = load_distance()

    fleet = load_fleet()

    assumptions = load_assumptions()

    revenue_summary = (
        build_revenue_summary(
            revenue
        )
    )

    distance_summary = (
        build_distance_summary(
            distance
        )
    )

    result = build_cost_scenarios(
        revenue_summary,
        distance_summary,
        fleet,
        assumptions,
    )

    breakdown = (
        build_cost_breakdown(
            result
        )
    )

    validate_results(
        result
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    result.to_csv(
        TABLE_DIR
        / "cost_profitability_scenarios_2024.csv",
        index=False,
    )

    breakdown.to_csv(
        TABLE_DIR
        / "cost_breakdown_long_2024.csv",
        index=False,
    )

    distance_summary.to_csv(
        AUDIT_DIR
        / "electricity_distance_proxy_audit_2024.csv",
        index=False,
    )

    base_case = result.loc[
        result[
            "scenario"
        ]
        == "base"
    ].copy()

    base_case.to_csv(
        TABLE_DIR
        / "base_case_profitability_2024.csv",
        index=False,
    )

    electricity_memo = result[
        [
            "scenario",
            "operator",
            "distance_estimable_pct",
            "endpoint_displacement_km",
            "energy_intensity_kwh_per_km",
            "electricity_price_eur_per_kwh",
            "estimated_energy_from_endpoint_proxy_kwh",
            "electricity_cost_memo_eur",
            "profit_plus_electricity_sensitivity_eur",
        ]
    ].copy()

    electricity_memo.to_csv(
        TABLE_DIR
        / "electricity_cost_memo_2024.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL OUTPUT
    # =========================================================================

    pd.set_option(
        "display.max_columns",
        None,
    )

    print(
        "\n"
        + "=" * 125
    )

    print(
        "DISTANCE PROXY AUDIT"
    )

    print(
        "=" * 125
    )

    print(
        distance_summary
        .round(3)
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Full scenario summary
    # -------------------------------------------------------------------------

    scenario_cols = [
        "scenario",
        "operator",
        "trips",
        "fleet_units_proxy",
        "estimated_gross_payg_revenue_eur",
        "direct_vehicle_opex_eur",
        "market_overhead_including_insurance_eur",
        "annual_depreciation_eur",
        "primary_total_cost_eur",
        "operating_profit_proxy_eur",
        "operating_margin_pct",
        "cost_to_revenue_pct",
    ]

    print(
        "\n"
        + "=" * 125
    )

    print(
        "COST & PROFITABILITY SCENARIOS"
    )

    print(
        "=" * 125
    )

    print(
        result[
            scenario_cols
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Base case
    # -------------------------------------------------------------------------

    base_cols = [
        "operator",
        "trips",
        "fleet_units_proxy",
        "estimated_gross_payg_revenue_eur",
        "spares_maintenance_cost_eur",
        "vehicle_personnel_charging_cost_eur",
        "other_direct_vehicle_opex_eur",
        "direct_vehicle_opex_eur",
        "vehicle_contribution_eur",
        "market_overhead_including_insurance_eur",
        "market_ebitda_proxy_eur",
        "annual_depreciation_eur",
        "primary_total_cost_eur",
        "operating_profit_proxy_eur",
        "operating_margin_pct",
    ]

    print(
        "\n"
        + "=" * 125
    )

    print(
        "BASE CASE — DETAILED COST BUILD-UP"
    )

    print(
        "=" * 125
    )

    print(
        base_case[
            base_cols
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Break-even
    # -------------------------------------------------------------------------

    break_even_cols = [
        "scenario",
        "operator",
        "mean_estimated_revenue_per_trip_eur",
        "direct_vehicle_opex_per_trip_eur",
        "contribution_per_trip_before_fixed_eur",
        "annual_fixed_like_cost_eur",
        "break_even_trips",
        "trips",
        "actual_trips_to_break_even_ratio",
    ]

    print(
        "\n"
        + "=" * 125
    )

    print(
        "BREAK-EVEN ANALYSIS"
    )

    print(
        "=" * 125
    )

    print(
        result[
            break_even_cols
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Electricity
    # -------------------------------------------------------------------------

    electricity_cols = [
        "scenario",
        "operator",
        "distance_estimable_pct",
        "endpoint_displacement_km",
        "estimated_energy_from_endpoint_proxy_kwh",
        "electricity_cost_memo_eur",
        "primary_total_cost_eur",
        "profit_plus_electricity_sensitivity_eur",
    ]

    print(
        "\n"
        + "=" * 125
    )

    print(
        "ELECTRICITY MEMO / SENSITIVITY"
    )

    print(
        "=" * 125
    )

    print(
        result[
            electricity_cols
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # System totals
    # -------------------------------------------------------------------------

    system = (
        result.groupby(
            "scenario",
            observed=True,
        )
        .agg(
            system_revenue_eur=(
                "estimated_gross_payg_revenue_eur",
                "sum",
            ),

            system_primary_cost_eur=(
                "primary_total_cost_eur",
                "sum",
            ),

            system_operating_profit_proxy_eur=(
                "operating_profit_proxy_eur",
                "sum",
            ),
        )
        .reset_index()
    )

    system[
        "system_operating_margin_pct"
    ] = (
        system[
            "system_operating_profit_proxy_eur"
        ]
        /
        system[
            "system_revenue_eur"
        ]
        * 100
    )

    print(
        "\n"
        + "=" * 125
    )

    print(
        "SYSTEM-LEVEL SCENARIO SUMMARY"
    )

    print(
        "=" * 125
    )

    print(
        system
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\nIMPORTANT INTERPRETATION:"
        "\n- Revenue is the locked 2024 estimated gross continuous-PAYG fare revenue."
        "\n- These are modeled profitability proxies, not audited operator financial statements."
        "\n- Direct vehicle OPEX is normalized per trip using the locked benchmark/scenario registry."
        "\n- Market overhead includes insurance; insurance is not added separately."
        "\n- Depreciation uses scenario-specific fleet exposure and useful-life assumptions."
        "\n- Capital stock proxy is not expensed directly; only annual depreciation enters primary cost."
        "\n- Fleet exposure is inferred, not directly observed."
        "\n- Electricity uses common endpoint displacement, not actual ridden route distance."
        "\n- Electricity is a memo/sensitivity item and is NOT included in primary total cost."
        "\n- Low and high cases are scenario envelopes, not confidence intervals."
        "\n- Corporate tax, financing costs and group-level corporate overhead are not included."
        "\n- Positive operating_profit_proxy means profitability only under the stated modeled assumptions."
    )


if __name__ == "__main__":
    main()