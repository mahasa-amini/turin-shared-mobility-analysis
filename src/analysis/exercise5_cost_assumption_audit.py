from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

ASSUMPTIONS = (
    ROOT
    / "config"
    / "exercise_5"
    / "cost_assumptions_2024.csv"
)


def main():

    df = pd.read_csv(
        ASSUMPTIONS
    )

    required_scenarios = {
        "low",
        "base",
        "high",
    }

    assert set(df["scenario"]) == required_scenarios

    assert df["scenario"].is_unique

    # Recalculate depreciation rather than trusting CSV blindly
    df["depreciation_check"] = (
        df["acquisition_cost_eur_per_vehicle"]
        /
        df["useful_life_years"]
    )

    assert (
        (
            df["depreciation_check"]
            -
            df["annual_depreciation_eur_per_vehicle"]
        )
        .abs()
        < 0.001
    ).all()

    df["direct_vehicle_opex_eur_per_trip"] = (
        df["spares_maintenance_eur_per_trip"]
        +
        df["vehicle_personnel_charging_eur_per_trip"]
        +
        df["other_direct_vehicle_opex_eur_per_trip"]
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 5 — COST ASSUMPTION AUDIT"
    )

    print(
        "=" * 110
    )

    cols = [
        "scenario",
        "fleet_proxy",
        "acquisition_cost_eur_per_vehicle",
        "useful_life_years",
        "annual_depreciation_eur_per_vehicle",
        "direct_vehicle_opex_eur_per_trip",
        "market_overhead_including_insurance_eur_per_vehicle_year",
        "energy_intensity_kwh_per_km",
        "electricity_price_eur_per_kwh",
    ]

    print(
        df[
            cols
        ]
        .round(4)
        .to_string(
            index=False
        )
    )

    print(
        "\nIMPORTANT:"
        "\n- Base direct OPEX is anchored to VOI Group 2024 published financials."
        "\n- Low/high direct OPEX are sensitivity assumptions, not published operator costs."
        "\n- Market overhead includes insurance; insurance must NOT be added again."
        "\n- Purchase prices are industry proxies, not disclosed Bird/Lime/VOI procurement prices."
        "\n- Fleet size is scenario-dependent because deployed fleet is not directly observed."
        "\n- Electricity assumptions are kept separate and will be reported explicitly."
    )


if __name__ == "__main__":
    main()