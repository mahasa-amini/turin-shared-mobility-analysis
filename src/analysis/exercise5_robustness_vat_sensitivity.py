from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

COST_RESULT_FILE = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "costs"
    / "cost_profitability_scenarios_2024.csv"
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
    / "robustness"
)

AUDIT_DIR = (
    ROOT
    / "audit"
    / "exercise_5"
    / "robustness"
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

LEVEL_ORDER = [
    "low",
    "base",
    "high",
]

VAT_RATE = 0.22


# =============================================================================
# LOAD
# =============================================================================

def load_inputs():

    if not COST_RESULT_FILE.exists():
        raise FileNotFoundError(
            COST_RESULT_FILE
        )

    if not FLEET_FILE.exists():
        raise FileNotFoundError(
            FLEET_FILE
        )

    if not ASSUMPTION_FILE.exists():
        raise FileNotFoundError(
            ASSUMPTION_FILE
        )

    cost = pd.read_csv(
        COST_RESULT_FILE
    )

    fleet = pd.read_csv(
        FLEET_FILE
    )

    assumptions = pd.read_csv(
        ASSUMPTION_FILE
    )

    # -------------------------------------------------------------------------
    # Standardize
    # -------------------------------------------------------------------------

    cost["operator"] = (
        cost["operator"]
        .astype("string")
        .str.lower()
    )

    fleet["operator"] = (
        fleet["operator"]
        .astype("string")
        .str.lower()
    )

    # -------------------------------------------------------------------------
    # Structural checks
    # -------------------------------------------------------------------------

    assert set(
        cost["operator"]
    ) == set(OPERATORS)

    assert set(
        fleet["operator"]
    ) == set(OPERATORS)

    assert set(
        assumptions["scenario"]
    ) == set(LEVEL_ORDER)

    assert fleet[
        "operator"
    ].is_unique

    assert assumptions[
        "scenario"
    ].is_unique

    # -------------------------------------------------------------------------
    # Reconstruct direct OPEX unit rate
    # -------------------------------------------------------------------------

    assumptions[
        "direct_vehicle_opex_eur_per_trip"
    ] = (
        assumptions[
            "spares_maintenance_eur_per_trip"
        ]
        +
        assumptions[
            "vehicle_personnel_charging_eur_per_trip"
        ]
        +
        assumptions[
            "other_direct_vehicle_opex_eur_per_trip"
        ]
    )

    return (
        cost,
        fleet,
        assumptions,
    )


# =============================================================================
# BASE CASE
# =============================================================================

def build_base_case(
    cost,
):

    base = cost.loc[
        cost[
            "scenario"
        ]
        == "base"
    ].copy()

    assert len(base) == len(
        OPERATORS
    )

    assert base[
        "operator"
    ].is_unique

    return base


# =============================================================================
# VAT SENSITIVITY
# =============================================================================

def build_vat_sensitivity(
    base,
):

    rows = []

    for _, row in (
        base.iterrows()
    ):

        operator = row[
            "operator"
        ]

        gross_revenue = float(
            row[
                "estimated_gross_payg_revenue_eur"
            ]
        )

        cost = float(
            row[
                "primary_total_cost_eur"
            ]
        )

        gross_profit = (
            gross_revenue
            -
            cost
        )

        # ---------------------------------------------------------------------
        # Illustrative VAT extraction
        #
        # If consumer tariff is VAT-inclusive:
        #
        # net revenue = gross / (1 + VAT rate)
        # ---------------------------------------------------------------------

        net_revenue = (
            gross_revenue
            /
            (
                1
                +
                VAT_RATE
            )
        )

        implied_vat_component = (
            gross_revenue
            -
            net_revenue
        )

        net_profit = (
            net_revenue
            -
            cost
        )

        gross_margin = (
            gross_profit
            /
            gross_revenue
            * 100
        )

        net_margin_on_net_revenue = (
            net_profit
            /
            net_revenue
            * 100
        )

        profit_change = (
            net_profit
            -
            gross_profit
        )

        rows.append(
            {
                "operator":
                    operator,

                "vat_rate_assumption_pct":
                    VAT_RATE
                    * 100,

                "gross_payg_fare_eur":
                    gross_revenue,

                "illustrative_net_of_vat_revenue_eur":
                    net_revenue,

                "implied_vat_component_eur":
                    implied_vat_component,

                "base_primary_cost_eur":
                    cost,

                "profit_proxy_gross_fare_basis_eur":
                    gross_profit,

                "margin_gross_fare_basis_pct":
                    gross_margin,

                "profit_proxy_net_of_vat_basis_eur":
                    net_profit,

                "margin_net_of_vat_basis_pct":
                    net_margin_on_net_revenue,

                "profit_change_due_to_vat_extraction_eur":
                    profit_change,

                "remains_profitable_after_vat_sensitivity":
                    (
                        net_profit
                        > 0
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# ONE-AT-A-TIME SENSITIVITY ENGINE
#
# Everything remains at BASE except one parameter block.
# =============================================================================

def build_oat_sensitivity(
    base,
    fleet,
    assumptions,
):

    assumption_lookup = (
        assumptions
        .set_index(
            "scenario"
        )
    )

    base_assumption = (
        assumption_lookup.loc[
            "base"
        ]
    )

    rows = []

    for _, op in (
        base.iterrows()
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

        fleet_row = (
            fleet.loc[
                fleet[
                    "operator"
                ]
                == operator
            ]
            .iloc[0]
        )

        base_fleet = float(
            fleet_row[
                "fleet_base_service_span_equivalent"
            ]
        )

        base_direct_opex_unit = float(
            base_assumption[
                "direct_vehicle_opex_eur_per_trip"
            ]
        )

        base_market_overhead_unit = float(
            base_assumption[
                "market_overhead_including_insurance_eur_per_vehicle_year"
            ]
        )

        base_depreciation_unit = float(
            base_assumption[
                "annual_depreciation_eur_per_vehicle"
            ]
        )

        # =====================================================================
        # Base control
        # =====================================================================

        base_direct_cost = (
            trips
            *
            base_direct_opex_unit
        )

        base_market_cost = (
            base_fleet
            *
            base_market_overhead_unit
        )

        base_depreciation = (
            base_fleet
            *
            base_depreciation_unit
        )

        base_total_cost = (
            base_direct_cost
            +
            base_market_cost
            +
            base_depreciation
        )

        base_profit = (
            revenue
            -
            base_total_cost
        )

        # Must reconcile with Cost Engine
        assert np.isclose(
            base_profit,
            op[
                "operating_profit_proxy_eur"
            ],
            atol=1.0,
        )

        # =====================================================================
        # 1. FLEET EXPOSURE ONLY
        #
        # All cost rates remain BASE.
        # =====================================================================

        fleet_levels = {
            "low":
                float(
                    fleet_row[
                        "fleet_lower_proxy"
                    ]
                ),

            "base":
                float(
                    fleet_row[
                        "fleet_base_service_span_equivalent"
                    ]
                ),

            "high":
                float(
                    fleet_row[
                        "fleet_upper_proxy_unique_ids"
                    ]
                ),
        }

        for level in LEVEL_ORDER:

            tested_fleet = (
                fleet_levels[
                    level
                ]
            )

            direct_cost = (
                trips
                *
                base_direct_opex_unit
            )

            market_cost = (
                tested_fleet
                *
                base_market_overhead_unit
            )

            depreciation = (
                tested_fleet
                *
                base_depreciation_unit
            )

            total_cost = (
                direct_cost
                +
                market_cost
                +
                depreciation
            )

            profit = (
                revenue
                -
                total_cost
            )

            rows.append(
                make_oat_row(
                    operator=operator,
                    driver="fleet_exposure",
                    level=level,
                    tested_value=tested_fleet,
                    tested_unit="fleet_units_proxy",
                    revenue=revenue,
                    total_cost=total_cost,
                    profit=profit,
                    base_profit=base_profit,
                )
            )

        # =====================================================================
        # 2. DEPRECIATION / CAPITAL ONLY
        #
        # Fleet remains BASE.
        # Direct OPEX remains BASE.
        # Market overhead remains BASE.
        # =====================================================================

        for level in LEVEL_ORDER:

            tested_dep_unit = float(
                assumption_lookup.loc[
                    level,
                    "annual_depreciation_eur_per_vehicle",
                ]
            )

            direct_cost = (
                trips
                *
                base_direct_opex_unit
            )

            market_cost = (
                base_fleet
                *
                base_market_overhead_unit
            )

            depreciation = (
                base_fleet
                *
                tested_dep_unit
            )

            total_cost = (
                direct_cost
                +
                market_cost
                +
                depreciation
            )

            profit = (
                revenue
                -
                total_cost
            )

            rows.append(
                make_oat_row(
                    operator=operator,
                    driver="annual_depreciation",
                    level=level,
                    tested_value=tested_dep_unit,
                    tested_unit="eur_per_vehicle_year",
                    revenue=revenue,
                    total_cost=total_cost,
                    profit=profit,
                    base_profit=base_profit,
                )
            )

        # =====================================================================
        # 3. DIRECT VEHICLE OPEX ONLY
        # =====================================================================

        for level in LEVEL_ORDER:

            tested_direct_unit = float(
                assumption_lookup.loc[
                    level,
                    "direct_vehicle_opex_eur_per_trip",
                ]
            )

            direct_cost = (
                trips
                *
                tested_direct_unit
            )

            market_cost = (
                base_fleet
                *
                base_market_overhead_unit
            )

            depreciation = (
                base_fleet
                *
                base_depreciation_unit
            )

            total_cost = (
                direct_cost
                +
                market_cost
                +
                depreciation
            )

            profit = (
                revenue
                -
                total_cost
            )

            rows.append(
                make_oat_row(
                    operator=operator,
                    driver="direct_vehicle_opex",
                    level=level,
                    tested_value=tested_direct_unit,
                    tested_unit="eur_per_trip",
                    revenue=revenue,
                    total_cost=total_cost,
                    profit=profit,
                    base_profit=base_profit,
                )
            )

        # =====================================================================
        # 4. MARKET OVERHEAD ONLY
        # =====================================================================

        for level in LEVEL_ORDER:

            tested_market_unit = float(
                assumption_lookup.loc[
                    level,
                    "market_overhead_including_insurance_eur_per_vehicle_year",
                ]
            )

            direct_cost = (
                trips
                *
                base_direct_opex_unit
            )

            market_cost = (
                base_fleet
                *
                tested_market_unit
            )

            depreciation = (
                base_fleet
                *
                base_depreciation_unit
            )

            total_cost = (
                direct_cost
                +
                market_cost
                +
                depreciation
            )

            profit = (
                revenue
                -
                total_cost
            )

            rows.append(
                make_oat_row(
                    operator=operator,
                    driver="market_overhead",
                    level=level,
                    tested_value=tested_market_unit,
                    tested_unit="eur_per_vehicle_year",
                    revenue=revenue,
                    total_cost=total_cost,
                    profit=profit,
                    base_profit=base_profit,
                )
            )

    result = pd.DataFrame(
        rows
    )

    result[
        "level"
    ] = pd.Categorical(
        result[
            "level"
        ],
        categories=LEVEL_ORDER,
        ordered=True,
    )

    result = (
        result.sort_values(
            [
                "operator",
                "driver",
                "level",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result


def make_oat_row(
    operator,
    driver,
    level,
    tested_value,
    tested_unit,
    revenue,
    total_cost,
    profit,
    base_profit,
):

    margin = (
        profit
        /
        revenue
        * 100
    )

    absolute_profit_change = (
        profit
        -
        base_profit
    )

    if (
        abs(
            base_profit
        )
        > 1e-12
    ):

        relative_profit_change_pct = (
            absolute_profit_change
            /
            abs(
                base_profit
            )
            * 100
        )

    else:

        relative_profit_change_pct = (
            np.nan
        )

    return {
        "operator":
            operator,

        "driver":
            driver,

        "level":
            level,

        "tested_value":
            tested_value,

        "tested_unit":
            tested_unit,

        "revenue_held_constant_eur":
            revenue,

        "total_cost_eur":
            total_cost,

        "operating_profit_proxy_eur":
            profit,

        "operating_margin_pct":
            margin,

        "base_profit_eur":
            base_profit,

        "absolute_profit_change_vs_base_eur":
            absolute_profit_change,

        "relative_profit_change_vs_base_pct":
            relative_profit_change_pct,

        "profitable":
            (
                profit
                > 0
            ),
    }


# =============================================================================
# DRIVER SENSITIVITY SUMMARY
# =============================================================================

def build_driver_summary(
    oat,
):

    rows = []

    for (
        operator,
        driver,
    ), group in (
        oat.groupby(
            [
                "operator",
                "driver",
            ],
            observed=True,
        )
    ):

        low = group.loc[
            group[
                "level"
            ]
            == "low"
        ].iloc[0]

        base = group.loc[
            group[
                "level"
            ]
            == "base"
        ].iloc[0]

        high = group.loc[
            group[
                "level"
            ]
            == "high"
        ].iloc[0]

        low_profit = float(
            low[
                "operating_profit_proxy_eur"
            ]
        )

        base_profit = float(
            base[
                "operating_profit_proxy_eur"
            ]
        )

        high_profit = float(
            high[
                "operating_profit_proxy_eur"
            ]
        )

        sensitivity_range = (
            abs(
                low_profit
                -
                high_profit
            )
        )

        max_abs_change = max(
            abs(
                low_profit
                -
                base_profit
            ),
            abs(
                high_profit
                -
                base_profit
            ),
        )

        sign_changes = (
            (
                low_profit
                > 0
            )
            !=
            (
                high_profit
                > 0
            )
        )

        rows.append(
            {
                "operator":
                    operator,

                "driver":
                    driver,

                "base_profit_eur":
                    base_profit,

                "low_level_profit_eur":
                    low_profit,

                "high_level_profit_eur":
                    high_profit,

                "profit_range_low_to_high_eur":
                    sensitivity_range,

                "max_absolute_change_from_base_eur":
                    max_abs_change,

                "profit_sign_changes_across_range":
                    sign_changes,
            }
        )

    summary = pd.DataFrame(
        rows
    )

    # Rank sensitivity within each operator
    summary[
        "sensitivity_rank"
    ] = (
        summary.groupby(
            "operator",
            observed=True,
        )[
            "max_absolute_change_from_base_eur"
        ]
        .rank(
            method="dense",
            ascending=False,
        )
        .astype(int)
    )

    summary = (
        summary.sort_values(
            [
                "operator",
                "sensitivity_rank",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return summary


# =============================================================================
# COMBINED ROBUSTNESS CLASSIFICATION
# =============================================================================

def build_robustness_summary(
    vat,
    oat,
    driver_summary,
):

    rows = []

    for operator in OPERATORS:

        vat_op = vat.loc[
            vat[
                "operator"
            ]
            == operator
        ].iloc[0]

        oat_op = oat.loc[
            oat[
                "operator"
            ]
            == operator
        ]

        driver_op = driver_summary.loc[
            driver_summary[
                "operator"
            ]
            == operator
        ]

        base_profit = float(
            vat_op[
                "profit_proxy_gross_fare_basis_eur"
            ]
        )

        vat_profit = float(
            vat_op[
                "profit_proxy_net_of_vat_basis_eur"
            ]
        )

        oat_min_profit = (
            oat_op[
                "operating_profit_proxy_eur"
            ]
            .min()
        )

        oat_max_profit = (
            oat_op[
                "operating_profit_proxy_eur"
            ]
            .max()
        )

        most_sensitive_driver = (
            driver_op
            .sort_values(
                "sensitivity_rank"
            )
            .iloc[0][
                "driver"
            ]
        )

        # ---------------------------------------------------------------------
        # Simple descriptive robustness classification
        # ---------------------------------------------------------------------

        if (
            base_profit > 0
            and vat_profit > 0
            and oat_min_profit > 0
        ):

            robustness_class = (
                "positive_across_tested_OAT_and_VAT_cases"
            )

        elif (
            base_profit < 0
            and vat_profit < 0
            and oat_max_profit < 0
        ):

            robustness_class = (
                "negative_across_tested_OAT_and_VAT_cases"
            )

        else:

            robustness_class = (
                "scenario_sensitive"
            )

        rows.append(
            {
                "operator":
                    operator,

                "base_gross_fare_profit_eur":
                    base_profit,

                "illustrative_net_of_vat_profit_eur":
                    vat_profit,

                "minimum_OAT_profit_eur":
                    oat_min_profit,

                "maximum_OAT_profit_eur":
                    oat_max_profit,

                "most_sensitive_OAT_driver":
                    most_sensitive_driver,

                "robustness_class":
                    robustness_class,
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    base,
    vat,
    oat,
):

    # -------------------------------------------------------------------------
    # VAT extraction must reduce revenue
    # -------------------------------------------------------------------------

    assert (
        vat[
            "illustrative_net_of_vat_revenue_eur"
        ]
        <
        vat[
            "gross_payg_fare_eur"
        ]
    ).all()

    # -------------------------------------------------------------------------
    # VAT component reconciliation
    # -------------------------------------------------------------------------

    assert np.allclose(
        (
            vat[
                "gross_payg_fare_eur"
            ]
            -
            vat[
                "illustrative_net_of_vat_revenue_eur"
            ]
        ),
        vat[
            "implied_vat_component_eur"
        ],
        atol=0.01,
    )

    # -------------------------------------------------------------------------
    # OAT design:
    # 3 operators × 4 drivers × 3 levels
    # -------------------------------------------------------------------------

    assert len(oat) == (
        len(OPERATORS)
        * 4
        * 3
    )

    # -------------------------------------------------------------------------
    # Every OAT base row must reconcile to original Base Cost Engine
    # -------------------------------------------------------------------------

    for _, base_row in (
        base.iterrows()
    ):

        operator = base_row[
            "operator"
        ]

        expected_profit = float(
            base_row[
                "operating_profit_proxy_eur"
            ]
        )

        control = oat.loc[
            (
                oat[
                    "operator"
                ]
                == operator
            )
            &
            (
                oat[
                    "level"
                ]
                == "base"
            )
        ]

        assert len(
            control
        ) == 4

        assert np.allclose(
            control[
                "operating_profit_proxy_eur"
            ],
            expected_profit,
            atol=1.0,
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
        "EXERCISE 5 — ROBUSTNESS & VAT SENSITIVITY"
    )

    print(
        "=" * 125
    )

    (
        cost,
        fleet,
        assumptions,
    ) = load_inputs()

    base = build_base_case(
        cost
    )

    vat = build_vat_sensitivity(
        base
    )

    oat = build_oat_sensitivity(
        base,
        fleet,
        assumptions,
    )

    driver_summary = (
        build_driver_summary(
            oat
        )
    )

    robustness = (
        build_robustness_summary(
            vat,
            oat,
            driver_summary,
        )
    )

    validate(
        base,
        vat,
        oat,
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    vat.to_csv(
        TABLE_DIR
        / "vat_sensitivity_2024.csv",
        index=False,
    )

    oat.to_csv(
        TABLE_DIR
        / "one_at_a_time_sensitivity_2024.csv",
        index=False,
    )

    driver_summary.to_csv(
        TABLE_DIR
        / "sensitivity_driver_ranking_2024.csv",
        index=False,
    )

    robustness.to_csv(
        TABLE_DIR
        / "profitability_robustness_summary_2024.csv",
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
        + "=" * 125
    )

    print(
        "VAT SENSITIVITY — BASE COST STRUCTURE"
    )

    print(
        "=" * 125
    )

    vat_cols = [
        "operator",
        "vat_rate_assumption_pct",
        "gross_payg_fare_eur",
        "illustrative_net_of_vat_revenue_eur",
        "implied_vat_component_eur",
        "base_primary_cost_eur",
        "profit_proxy_gross_fare_basis_eur",
        "margin_gross_fare_basis_pct",
        "profit_proxy_net_of_vat_basis_eur",
        "margin_net_of_vat_basis_pct",
        "remains_profitable_after_vat_sensitivity",
    ]

    print(
        vat[
            vat_cols
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 125
    )

    print(
        "ONE-AT-A-TIME PROFIT SENSITIVITY"
    )

    print(
        "=" * 125
    )

    oat_cols = [
        "operator",
        "driver",
        "level",
        "tested_value",
        "tested_unit",
        "total_cost_eur",
        "operating_profit_proxy_eur",
        "operating_margin_pct",
        "absolute_profit_change_vs_base_eur",
        "profitable",
    ]

    print(
        oat[
            oat_cols
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 125
    )

    print(
        "SENSITIVITY DRIVER RANKING"
    )

    print(
        "=" * 125
    )

    print(
        driver_summary
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 125
    )

    print(
        "PROFITABILITY ROBUSTNESS SUMMARY"
    )

    print(
        "=" * 125
    )

    print(
        robustness
        .round(2)
        .to_string(
            index=False
        )
    )

    print(
        "\nINTERPRETATION:"
        "\n- VAT analysis is an illustrative sensitivity, not an audited tax reconstruction."
        "\n- 22% is applied only to test the effect of extracting VAT from consumer-facing gross fare revenue."
        "\n- The primary Base Cost Engine remains unchanged."
        "\n- OAT means ONE parameter block changes while every other assumption remains at Base."
        "\n- Fleet sensitivity changes fleet exposure only."
        "\n- Annual-depreciation sensitivity changes depreciation per vehicle only; Base fleet remains fixed."
        "\n- Direct-OPEX sensitivity changes EUR/trip only."
        "\n- Market-overhead sensitivity changes EUR/vehicle-year only."
        "\n- Low/high values are scenario bounds, not statistical confidence intervals."
        "\n- The driver ranking measures modeled profit sensitivity, not causal importance."
    )


if __name__ == "__main__":
    main()