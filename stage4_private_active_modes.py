import pandas as pd


# ============================================================
# STAGE 4B — PRIVATE BICYCLE + PRIVATE E-SCOOTER
# ============================================================


# ------------------------------------------------------------
# COMMON COMMUTING ASSUMPTIONS
# ------------------------------------------------------------

university_days_per_year = 150

outbound_distance_km = 3.7
return_distance_km = 4.1

round_trip_distance_km = (
    outbound_distance_km
    + return_distance_km
)

annual_commute_km = (
    round_trip_distance_km
    * university_days_per_year
)


# ============================================================
# PRIVATE BICYCLE
# Representative model:
# Decathlon Elops 120
# ============================================================

bike_purchase_price_eur = 299.99
bike_residual_value_eur = 50.0
bike_useful_life_years = 8

bike_maintenance_eur_year = 60.0
bike_tyres_tubes_eur_year = 25.0


bike_depreciation_eur_year = (
    bike_purchase_price_eur
    - bike_residual_value_eur
) / bike_useful_life_years


bike_total_annual_cost_eur = (
    bike_depreciation_eur_year
    + bike_maintenance_eur_year
    + bike_tyres_tubes_eur_year
)


bike_cost_per_university_day_eur = (
    bike_total_annual_cost_eur
    / university_days_per_year
)


bike_cost_per_one_way_trip_eur = (
    bike_cost_per_university_day_eur
    / 2
)


# ============================================================
# PRIVATE E-SCOOTER
# Representative model:
# Xiaomi Electric Scooter 5
# ============================================================

scooter_purchase_price_eur = 399.99
scooter_residual_value_eur = 50.0
scooter_useful_life_years = 4

scooter_maintenance_eur_year = 60.0
scooter_tyres_brakes_eur_year = 40.0
# Mandatory legal costs for private e-scooter
scooter_rca_insurance_eur_year = 50.0

scooter_contrassegno_cost_eur = 35.0

scooter_contrassegno_eur_year = (
    scooter_contrassegno_cost_eur
    / scooter_useful_life_years
)


# ------------------------------------------------------------
# BATTERY / ENERGY
# ------------------------------------------------------------

battery_capacity_wh = 477.0
nominal_range_km = 60.0

charging_loss_factor = 1.15

electricity_price_eur_per_kwh = 0.30


battery_capacity_kwh = (
    battery_capacity_wh
    / 1000
)


nominal_energy_kwh_per_km = (
    battery_capacity_kwh
    / nominal_range_km
)


wall_energy_kwh_per_km = (
    nominal_energy_kwh_per_km
    * charging_loss_factor
)


electricity_cost_eur_per_km = (
    wall_energy_kwh_per_km
    * electricity_price_eur_per_kwh
)


# ------------------------------------------------------------
# SCOOTER DEPRECIATION
# ------------------------------------------------------------

scooter_depreciation_eur_year = (
    scooter_purchase_price_eur
    - scooter_residual_value_eur
) / scooter_useful_life_years


# ------------------------------------------------------------
# ANNUAL SCOOTER COST
# ------------------------------------------------------------

scooter_annual_electricity_eur = (
    annual_commute_km
    * electricity_cost_eur_per_km
)


scooter_total_annual_cost_eur = (
   scooter_depreciation_eur_year
    + scooter_maintenance_eur_year
    + scooter_tyres_brakes_eur_year
    + scooter_rca_insurance_eur_year
    + scooter_contrassegno_eur_year
    + scooter_annual_electricity_eur
)


scooter_cost_per_university_day_eur = (
    scooter_total_annual_cost_eur
    / university_days_per_year
)


# ------------------------------------------------------------
# DIRECTION-SPECIFIC ENERGY COST
# ------------------------------------------------------------

scooter_outbound_energy_cost_eur = (
    outbound_distance_km
    * electricity_cost_eur_per_km
)


scooter_return_energy_cost_eur = (
    return_distance_km
    * electricity_cost_eur_per_km
)


# ============================================================
# OUTPUT TABLES
# ============================================================

bike_table = pd.DataFrame(
    {
        "item": [
            "Purchase price",
            "Residual value",
            "Useful life",
            "Annual depreciation",
            "Maintenance",
            "Tyres / tubes",
            "Total annual cost",
            "Cost per university day",
            "Cost per one-way trip",
        ],
        "value_eur": [
            bike_purchase_price_eur,
            bike_residual_value_eur,
            bike_useful_life_years,
            bike_depreciation_eur_year,
            bike_maintenance_eur_year,
            bike_tyres_tubes_eur_year,
            bike_total_annual_cost_eur,
            bike_cost_per_university_day_eur,
            bike_cost_per_one_way_trip_eur,
        ],
    }
)


scooter_table = pd.DataFrame(
    {
        "item": [
            "Purchase price",
            "Residual value",
            "Useful life",
            "Annual depreciation",
            "Maintenance",
            "Tyres / brakes",
            "Battery capacity Wh",
            "Nominal range km",
            "Electricity EUR/kWh",
            "Electricity EUR/km",
            "Annual electricity",
            "Total annual cost",
            "Cost per university day",
            "RCA insurance / year",
            "Contrassegno annualised",
        ],
        "value": [
            scooter_purchase_price_eur,
            scooter_residual_value_eur,
            scooter_useful_life_years,
            scooter_depreciation_eur_year,
            scooter_maintenance_eur_year,
            scooter_tyres_brakes_eur_year,
            battery_capacity_wh,
            nominal_range_km,
            electricity_price_eur_per_kwh,
            electricity_cost_eur_per_km,
            scooter_annual_electricity_eur,
            scooter_total_annual_cost_eur,
            scooter_cost_per_university_day_eur,
            scooter_rca_insurance_eur_year,
            scooter_contrassegno_eur_year,
        ],
    }
)


# ============================================================
# PRINT
# ============================================================

print(
    "\n"
    + "=" * 100
)

print(
    "STAGE 4B — PRIVATE BICYCLE + PRIVATE E-SCOOTER"
)

print(
    "=" * 100
)


print(
    "\nCOMMON COMMUTING ASSUMPTIONS"
)

print(
    f"University days/year: "
    f"{university_days_per_year}"
)

print(
    f"Round-trip distance: "
    f"{round_trip_distance_km:.1f} km"
)

print(
    f"Annual university commute: "
    f"{annual_commute_km:.1f} km"
)


print(
    "\nPRIVATE BICYCLE"
)

print(
    bike_table.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}",
    )
)


print(
    "\nPRIVATE E-SCOOTER"
)

print(
    scooter_table.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}",
    )
)


print(
    "\nE-SCOOTER DIRECTIONAL ENERGY COST"
)

print(
    f"Home -> Polito: "
    f"EUR {scooter_outbound_energy_cost_eur:.3f}"
)

print(
    f"Polito -> Home: "
    f"EUR {scooter_return_energy_cost_eur:.3f}"
)


print(
    "\nROUND-TRIP MONETARY COST"
)

print(
    f"Private bicycle: "
    f"EUR {bike_cost_per_university_day_eur:.2f}"
)

print(
    f"Private e-scooter: "
    f"EUR {scooter_cost_per_university_day_eur:.2f}"
)


print(
    "\nVALIDATION / INTERPRETATION"
)

print(
    "- Bicycle and scooter are hypothetical "
    "representative ownership scenarios."
)

print(
    "- Capital cost is depreciated using "
    "straight-line depreciation."
)

print(
    "- Annual ownership costs are allocated "
    "over 150 university commuting days."
)

print(
    "- Scooter electricity includes a 15% "
    "charging-loss allowance."
)

print(
    "- Electricity price, useful life, residual "
    "value and maintenance costs are explicit assumptions."
)

print(
    "- Electricity cost is expected to be very small "
    "relative to depreciation and maintenance."
)