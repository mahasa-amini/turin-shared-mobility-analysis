import pandas as pd


# ============================================================
# STAGE 4A — PRIVATE CAR COST MODEL
# Representative vehicle:
# Volkswagen Polo 1.0 TSI Edition Plus 95 CV Manual
# ============================================================


# ------------------------------------------------------------
# VEHICLE CHARACTERISTICS
# ------------------------------------------------------------

registration_year = 2026
purchase_year = 2026

displacement_cc = 999
power_kw = 70
fuel_type = "petrol"

purchase_price_eur = 25_100.0

# WLTP low-phase used as an urban-consumption proxy
urban_consumption_l_per_100km = 6.5

# Combined WLTP used only for annual fuel reference
combined_consumption_l_per_100km = 5.1


# ------------------------------------------------------------
# OWNERSHIP ASSUMPTIONS
# ------------------------------------------------------------

annual_km = 10_000.0

useful_life_years = 8
residual_value_eur = 9_000.0
amortisation_rate = 0.03


# ------------------------------------------------------------
# FIXED COSTS
# ------------------------------------------------------------

rca_insurance_eur_year = 423.40

# Piemonte Euro 4+ tariff for vehicle between 53 and 100 kW
bollo_rate_eur_per_kw = 2.73
bollo_eur_year = power_kw * bollo_rate_eur_per_kw

shelter_eur_year = 0.0

# New car:
# revision at years 4, 6 and 8
revision_cost_eur = 78.75
number_of_revisions_over_life = 3

revision_eur_year = (
    revision_cost_eur
    * number_of_revisions_over_life
    / useful_life_years
)


# ------------------------------------------------------------
# TECHNICAL DEPRECIATION
# Formula supplied by the exercise
# ------------------------------------------------------------

P = purchase_price_eur
VR = residual_value_eur
n = useful_life_years
i = amortisation_rate

annual_depreciation_eur = (
    (P - VR)
    * (
        ((1 + i) ** n * i)
        /
        (((1 + i) ** n) - 1)
    )
    +
    (VR * i)
)


# ------------------------------------------------------------
# VARIABLE NON-FUEL COSTS
# ------------------------------------------------------------

tyres_eur_year = 80.0

# Included in Volkswagen We Care maintenance plan
engine_oil_eur_year = 0.0

repair_eur_year = 120.0

# VW We Care Essential:
# 6 years / 90,000 km = EUR 1,620
maintenance_eur_year = 1_620.0 / 6.0


# ------------------------------------------------------------
# FUEL
# Piemonte petrol self-service
# 18 August 2026
# ------------------------------------------------------------

fuel_price_eur_per_litre = 1.987


# ------------------------------------------------------------
# REFERENCE HOME ↔ POLITO TRIP
# ------------------------------------------------------------

outbound_distance_km = 3.7
return_distance_km = 4.1

round_trip_distance_km = (
    outbound_distance_km
    +
    return_distance_km
)

parking_hours = 9.0
parking_rate_eur_per_hour = 1.70

parking_cost_eur_day = (
    parking_hours
    *
    parking_rate_eur_per_hour
)


# ============================================================
# ANNUAL COST CALCULATION
# ============================================================

total_fixed_cost_eur_year = (
    rca_insurance_eur_year
    +
    bollo_eur_year
    +
    annual_depreciation_eur
    +
    shelter_eur_year
    +
    revision_eur_year
)

total_variable_nonfuel_eur_year = (
    tyres_eur_year
    +
    engine_oil_eur_year
    +
    repair_eur_year
    +
    maintenance_eur_year
)

annual_allocatable_cost_eur = (
    total_fixed_cost_eur_year
    +
    total_variable_nonfuel_eur_year
)

ownership_nonfuel_cost_eur_per_km = (
    annual_allocatable_cost_eur
    /
    annual_km
)


# ------------------------------------------------------------
# Annual fuel reference
# Not used directly for the urban trip calculation
# ------------------------------------------------------------

annual_fuel_litres_reference = (
    annual_km
    *
    combined_consumption_l_per_100km
    / 100
)

annual_fuel_cost_reference_eur = (
    annual_fuel_litres_reference
    *
    fuel_price_eur_per_litre
)


# ============================================================
# TRIP-SPECIFIC URBAN FUEL COST
# ============================================================

urban_fuel_cost_eur_per_km = (
    urban_consumption_l_per_100km
    / 100
    *
    fuel_price_eur_per_litre
)


def calculate_direction_cost(distance_km):

    ownership_cost = (
        distance_km
        *
        ownership_nonfuel_cost_eur_per_km
    )

    fuel_cost = (
        distance_km
        *
        urban_fuel_cost_eur_per_km
    )

    total = (
        ownership_cost
        +
        fuel_cost
    )

    return {
        "distance_km": distance_km,
        "ownership_nonfuel_eur": ownership_cost,
        "fuel_eur": fuel_cost,
        "total_before_parking_eur": total,
    }


outbound = calculate_direction_cost(
    outbound_distance_km
)

return_trip = calculate_direction_cost(
    return_distance_km
)


round_trip_before_parking_eur = (
    outbound["total_before_parking_eur"]
    +
    return_trip["total_before_parking_eur"]
)

round_trip_total_eur = (
    round_trip_before_parking_eur
    +
    parking_cost_eur_day
)


# ============================================================
# OUTPUT TABLES
# ============================================================

vehicle_table = pd.DataFrame(
    {
        "item": [
            "Registration year",
            "Purchase year",
            "Displacement (cc)",
            "Maximum power (kW)",
            "Fuel type",
            "Urban consumption (L/100 km)",
            "Annual kilometres",
            "Useful life (years)",
            "Purchase price (EUR)",
            "Residual value (EUR)",
            "Amortisation rate",
        ],
        "value": [
            registration_year,
            purchase_year,
            displacement_cc,
            power_kw,
            fuel_type,
            urban_consumption_l_per_100km,
            annual_km,
            useful_life_years,
            purchase_price_eur,
            residual_value_eur,
            amortisation_rate,
        ],
    }
)


annual_cost_table = pd.DataFrame(
    {
        "cost_item": [
            "RCA insurance",
            "Property tax (bollo)",
            "Technical depreciation",
            "Shelter",
            "Revision",
            "Tyres",
            "Engine oil",
            "Repair contingency",
            "Maintenance",
        ],
        "eur_per_year": [
            rca_insurance_eur_year,
            bollo_eur_year,
            annual_depreciation_eur,
            shelter_eur_year,
            revision_eur_year,
            tyres_eur_year,
            engine_oil_eur_year,
            repair_eur_year,
            maintenance_eur_year,
        ],
    }
)


trip_table = pd.DataFrame(
    [
        {
            "direction": "Home -> Polito",
            **outbound,
        },
        {
            "direction": "Polito -> Home",
            **return_trip,
        },
    ]
)


# ============================================================
# PRINT
# ============================================================

print(
    "\n"
    + "=" * 95
)

print(
    "STAGE 4A — PRIVATE CAR COST MODEL"
)

print(
    "=" * 95
)

print(
    "\nVEHICLE CHARACTERISTICS"
)

print(
    vehicle_table.to_string(
        index=False
    )
)


print(
    "\nANNUAL COST STRUCTURE"
)

print(
    annual_cost_table.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


print(
    "\nCOST SUMMARY"
)

print(
    f"Annual technical depreciation: "
    f"EUR {annual_depreciation_eur:.2f}"
)

print(
    f"Total fixed costs: "
    f"EUR {total_fixed_cost_eur_year:.2f}/year"
)

print(
    f"Total variable non-fuel costs: "
    f"EUR {total_variable_nonfuel_eur_year:.2f}/year"
)

print(
    f"Ownership + non-fuel cost: "
    f"EUR {ownership_nonfuel_cost_eur_per_km:.4f}/km"
)

print(
    f"Urban fuel cost: "
    f"EUR {urban_fuel_cost_eur_per_km:.4f}/km"
)

print(
    f"Annual combined-WLTP fuel reference: "
    f"EUR {annual_fuel_cost_reference_eur:.2f}/year"
)


print(
    "\nHOME ↔ POLITO TRIP COST"
)

print(
    trip_table.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)

print(
    f"\nRound-trip distance: "
    f"{round_trip_distance_km:.1f} km"
)

print(
    f"Round-trip vehicle cost before parking: "
    f"EUR {round_trip_before_parking_eur:.2f}"
)

print(
    f"Parking cost (9 h): "
    f"EUR {parking_cost_eur_day:.2f}"
)

print(
    f"ROUND-TRIP MONETARY COST INCLUDING PARKING: "
    f"EUR {round_trip_total_eur:.2f}"
)


print(
    "\nVALIDATION / INTERPRETATION"
)

print(
    "- Fuel is calculated separately at trip level "
    "using the urban-consumption proxy."
)

print(
    "- Engine oil is not added separately because "
    "it is included in the maintenance plan."
)

print(
    "- Parking is a trip-specific cost and is not "
    "included in annual ownership costs."
)

print(
    "- RCA is a generic national baseline, not a "
    "personal insurance quotation."
)

print(
    "- Residual value, amortisation rate, tyre cost "
    "and repair contingency are explicit model assumptions."
)