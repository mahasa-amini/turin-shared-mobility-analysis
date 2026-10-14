from pathlib import Path

import pandas as pd


# ============================================================
# STAGE 5 — STANDARD GENERALISED COST
# Home ↔ Politecnico di Torino
# Round-trip comparison
# ============================================================


# ------------------------------------------------------------
# OUTPUT PATH
# ------------------------------------------------------------

OUTPUT_DIR = Path(
    "outputs/tables/generalised_cost"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ------------------------------------------------------------
# VALUE OF TIME
# ------------------------------------------------------------

BASE_VOT_EUR_PER_HOUR = 10.0

SENSITIVITY_VOT = [
    5.0,
    10.0,
    20.0,
]


# ------------------------------------------------------------
# COMMON ROUTE INFORMATION
# ------------------------------------------------------------

outbound_distance_km = 3.7
return_distance_km = 4.1

round_trip_distance_km = (
    outbound_distance_km
    + return_distance_km
)


# ============================================================
# MONETARY COSTS — ROUND TRIP
# ============================================================


# ------------------------------------------------------------
# PRIVATE CAR
# Volkswagen Polo 1.0 TSI petrol
#
# Stage 4 result:
# vehicle cost + fuel + 9 h parking
# ------------------------------------------------------------

private_car_cost = 19.18


# ------------------------------------------------------------
# PRIVATE BICYCLE
# Stage 4 result
# ------------------------------------------------------------

private_bike_cost = 0.775


# ------------------------------------------------------------
# PRIVATE E-SCOOTER
# Stage 4 result including:
# depreciation
# maintenance
# tyres/brakes
# electricity
# RCA
# contrassegno
# ------------------------------------------------------------

private_scooter_cost = 1.663


# ------------------------------------------------------------
# PUBLIC TRANSPORT
#
# Student annual subscription:
# EUR 300/year
#
# University refund:
# EUR 110/year
#
# Net annual cost:
# EUR 190/year
#
# Allocated over 150 university days
# ------------------------------------------------------------

pt_net_annual_cost = 190.0

university_days = 150

public_transport_cost = (
    pt_net_annual_cost
    / university_days
)


# ------------------------------------------------------------
# LIME SHARED BICYCLE
#
# App tariff:
# ride <= 20 min = EUR 1.80
#
# Two rides per university day
# ------------------------------------------------------------

lime_bike_cost_one_way = 1.80

lime_bike_cost = (
    lime_bike_cost_one_way
    * 2
)


# ------------------------------------------------------------
# LIME SHARED E-SCOOTER
#
# App tariff:
# ride <= 20 min = EUR 1.80
#
# Two rides per university day
# ------------------------------------------------------------

lime_scooter_cost_one_way = 1.80

lime_scooter_cost = (
    lime_scooter_cost_one_way
    * 2
)


# ------------------------------------------------------------
# CAR SHARING
#
# Representative service:
# Free2move
#
# Baseline tariff:
# EUR 0.25/min
#
# Driving:
# Home -> Polito = 12 min
# Polito -> Home = 14 min
#
# Fuel and Home Area parking are included
# in the service tariff.
# ------------------------------------------------------------

car_sharing_rate_eur_min = 0.25

car_driving_outbound_min = 12.0
car_driving_return_min = 14.0

car_driving_round_trip_min = (
    car_driving_outbound_min
    + car_driving_return_min
)

car_sharing_cost = (
    car_sharing_rate_eur_min
    * car_driving_round_trip_min
)


# ------------------------------------------------------------
# TAXI
#
# Observed app range:
# EUR 10-16 each direction
#
# Midpoint used in baseline model.
# ------------------------------------------------------------

taxi_low_one_way = 10.0
taxi_high_one_way = 16.0

taxi_base_one_way = (
    taxi_low_one_way
    + taxi_high_one_way
) / 2

taxi_cost = (
    taxi_base_one_way
    * 2
)


# ------------------------------------------------------------
# UBER
#
# Observed quotes:
# Home -> Polito = EUR 25.50
# Polito -> Home = EUR 23.00
# ------------------------------------------------------------

uber_outbound_cost = 25.50
uber_return_cost = 23.00

uber_cost = (
    uber_outbound_cost
    + uber_return_cost
)


# ============================================================
# TIME COMPONENTS
#
# All values below are ROUND-TRIP minutes.
#
# Total door-to-door time =
# travel/riding
# + access/egress
# + waiting
# ============================================================


# ------------------------------------------------------------
# PRIVATE CAR
#
# Google Maps observed driving:
# Home -> Polito = 12 min
# Polito -> Home = 14 min
#
# Total driving = 26 min
#
# Explicit modelling assumption:
# 5 min per direction for:
# - parking search
# - parking manoeuvre
# - walking between parked car and destination
#
# Total parking/access allowance = 10 min
# ------------------------------------------------------------

private_car_travel_min = 26.0

private_car_access_min = 10.0

private_car_waiting_min = 0.0


# ------------------------------------------------------------
# CAR SHARING
#
# Same road corridor:
# 26 min driving
#
# Agreed assumption:
# 5 min access/search per direction
#
# Total access = 10 min
# ------------------------------------------------------------

car_sharing_travel_min = 26.0

car_sharing_access_min = 10.0

car_sharing_waiting_min = 0.0


# ------------------------------------------------------------
# PRIVATE BICYCLE
#
# Google Maps:
# Home -> Polito = 16 min
# Polito -> Home = 16 min
#
# Round trip = 32 min
# ------------------------------------------------------------

private_bike_travel_min = 32.0

private_bike_access_min = 0.0

private_bike_waiting_min = 0.0


# ------------------------------------------------------------
# LIME BIKE SHARING
#
# Same cycling route and riding time:
# 32 min total
#
# Agreed assumption:
# 3 min vehicle access/search per direction
#
# Total access = 6 min
# ------------------------------------------------------------

lime_bike_travel_min = 32.0

lime_bike_access_min = 6.0

lime_bike_waiting_min = 0.0


# ------------------------------------------------------------
# E-SCOOTER TRAVEL TIME
#
# Explicit modelling assumption:
# average operating speed = 15 km/h
# ------------------------------------------------------------

scooter_speed_kmh = 15.0


scooter_outbound_min = (
    outbound_distance_km
    / scooter_speed_kmh
    * 60
)


scooter_return_min = (
    return_distance_km
    / scooter_speed_kmh
    * 60
)


scooter_round_trip_riding_min = (
    scooter_outbound_min
    + scooter_return_min
)


# ------------------------------------------------------------
# PRIVATE E-SCOOTER
# ------------------------------------------------------------

private_scooter_travel_min = (
    scooter_round_trip_riding_min
)

private_scooter_access_min = 0.0

private_scooter_waiting_min = 0.0


# ------------------------------------------------------------
# LIME SHARED E-SCOOTER
#
# Same modelled riding time
#
# Agreed assumption:
# 3 min access/search per direction
#
# Total access = 6 min
# ------------------------------------------------------------

lime_scooter_travel_min = (
    scooter_round_trip_riding_min
)

lime_scooter_access_min = 6.0

lime_scooter_waiting_min = 0.0


# ------------------------------------------------------------
# TAXI
#
# Road travel:
# 12 + 14 = 26 min
#
# Exact taxi waiting time unavailable.
#
# Explicit assumption:
# 5 min dispatch/wait per direction
#
# Total waiting = 10 min
# ------------------------------------------------------------

taxi_travel_min = 26.0

taxi_access_min = 0.0

taxi_waiting_min = 10.0


# ------------------------------------------------------------
# UBER
#
# Road travel:
# 26 min total
#
# Observed pickup estimates:
# outbound = 6 min
# return = 3 min
#
# Total waiting = 9 min
# ------------------------------------------------------------

uber_travel_min = 26.0

uber_access_min = 0.0

uber_waiting_min = 9.0


# ------------------------------------------------------------
# PUBLIC TRANSPORT
#
# Home -> Polito:
# walk = 8 min
# Tram 10 = 13 min
# final walk = 2 min
# total = 23 min
#
# Polito -> Home:
# walk = 2 min
# Tram 10 = 13 min
# final walk = 8 min
# total = 23 min
#
# Round trip:
# in-vehicle = 26 min
# walking access/egress = 20 min
# total = 46 min
#
# No transfer.
# No additional waiting time is invented.
# ------------------------------------------------------------

pt_travel_min = 26.0

pt_access_min = 20.0

pt_waiting_min = 0.0


# ============================================================
# MASTER INPUT TABLE
# ============================================================

modes = pd.DataFrame(
    [
        {
            "mode": "Private car",
            "monetary_cost_eur":
                private_car_cost,
            "travel_min":
                private_car_travel_min,
            "access_egress_min":
                private_car_access_min,
            "waiting_min":
                private_car_waiting_min,
        },

        {
            "mode": "Car sharing",
            "monetary_cost_eur":
                car_sharing_cost,
            "travel_min":
                car_sharing_travel_min,
            "access_egress_min":
                car_sharing_access_min,
            "waiting_min":
                car_sharing_waiting_min,
        },

        {
            "mode": "Private bicycle",
            "monetary_cost_eur":
                private_bike_cost,
            "travel_min":
                private_bike_travel_min,
            "access_egress_min":
                private_bike_access_min,
            "waiting_min":
                private_bike_waiting_min,
        },

        {
            "mode": "Bike sharing",
            "monetary_cost_eur":
                lime_bike_cost,
            "travel_min":
                lime_bike_travel_min,
            "access_egress_min":
                lime_bike_access_min,
            "waiting_min":
                lime_bike_waiting_min,
        },

        {
            "mode": "Private e-scooter",
            "monetary_cost_eur":
                private_scooter_cost,
            "travel_min":
                private_scooter_travel_min,
            "access_egress_min":
                private_scooter_access_min,
            "waiting_min":
                private_scooter_waiting_min,
        },

        {
            "mode": "Shared e-scooter",
            "monetary_cost_eur":
                lime_scooter_cost,
            "travel_min":
                lime_scooter_travel_min,
            "access_egress_min":
                lime_scooter_access_min,
            "waiting_min":
                lime_scooter_waiting_min,
        },

        {
            "mode": "Taxi",
            "monetary_cost_eur":
                taxi_cost,
            "travel_min":
                taxi_travel_min,
            "access_egress_min":
                taxi_access_min,
            "waiting_min":
                taxi_waiting_min,
        },

        {
            "mode": "Ride hailing (Uber)",
            "monetary_cost_eur":
                uber_cost,
            "travel_min":
                uber_travel_min,
            "access_egress_min":
                uber_access_min,
            "waiting_min":
                uber_waiting_min,
        },

        {
            "mode": "Public transport",
            "monetary_cost_eur":
                public_transport_cost,
            "travel_min":
                pt_travel_min,
            "access_egress_min":
                pt_access_min,
            "waiting_min":
                pt_waiting_min,
        },
    ]
)


# ============================================================
# TOTAL DOOR-TO-DOOR TIME
# ============================================================

modes["total_time_min"] = (
    modes["travel_min"]
    + modes["access_egress_min"]
    + modes["waiting_min"]
)


# ============================================================
# BASELINE GENERALISED COST
#
# GC =
# monetary cost
# + VOT × door-to-door time
# ============================================================

modes["time_cost_eur"] = (
    modes["total_time_min"]
    / 60
    * BASE_VOT_EUR_PER_HOUR
)


modes["generalised_cost_eur"] = (
    modes["monetary_cost_eur"]
    + modes["time_cost_eur"]
)


modes["gc_rank"] = (
    modes[
        "generalised_cost_eur"
    ]
    .rank(
        method="min"
    )
    .astype(int)
)


baseline = (
    modes
    .sort_values(
        "generalised_cost_eur"
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# VOT SENSITIVITY
# ============================================================

sensitivity_rows = []


for vot in SENSITIVITY_VOT:

    for _, row in modes.iterrows():

        time_cost = (
            row["total_time_min"]
            / 60
            * vot
        )

        generalised_cost = (
            row["monetary_cost_eur"]
            + time_cost
        )

        sensitivity_rows.append(
            {
                "vot_eur_hour":
                    vot,

                "mode":
                    row["mode"],

                "monetary_cost_eur":
                    row[
                        "monetary_cost_eur"
                    ],

                "total_time_min":
                    row[
                        "total_time_min"
                    ],

                "time_cost_eur":
                    time_cost,

                "generalised_cost_eur":
                    generalised_cost,
            }
        )


sensitivity = pd.DataFrame(
    sensitivity_rows
)


sensitivity["rank"] = (
    sensitivity
    .groupby(
        "vot_eur_hour"
    )[
        "generalised_cost_eur"
    ]
    .rank(
        method="min"
    )
    .astype(int)
)


sensitivity = (
    sensitivity
    .sort_values(
        [
            "vot_eur_hour",
            "generalised_cost_eur",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# SAVE TABLES
# ============================================================

modes.to_csv(
    OUTPUT_DIR
    / "stage5_master_modes.csv",
    index=False,
)


baseline.to_csv(
    OUTPUT_DIR
    / "stage5_baseline_generalised_cost.csv",
    index=False,
)


sensitivity.to_csv(
    OUTPUT_DIR
    / "stage5_vot_sensitivity.csv",
    index=False,
)


# ============================================================
# PRINT
# ============================================================

print(
    "\n"
    + "=" * 115
)

print(
    "STAGE 5 — STANDARD GENERALISED COST MODEL"
)

print(
    "=" * 115
)


# ------------------------------------------------------------
# MASTER TABLE
# ------------------------------------------------------------

print(
    "\nMASTER ROUND-TRIP INPUT TABLE"
)


print(
    modes[
        [
            "mode",
            "monetary_cost_eur",
            "travel_min",
            "access_egress_min",
            "waiting_min",
            "total_time_min",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


# ------------------------------------------------------------
# BASELINE
# ------------------------------------------------------------

print(
    f"\nBASELINE GENERALISED COST "
    f"(VOT = EUR "
    f"{BASE_VOT_EUR_PER_HOUR:.0f}/h)"
)


print(
    baseline[
        [
            "gc_rank",
            "mode",
            "monetary_cost_eur",
            "total_time_min",
            "time_cost_eur",
            "generalised_cost_eur",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


# ------------------------------------------------------------
# VOT SENSITIVITY
# ------------------------------------------------------------

print(
    "\nVOT SENSITIVITY"
)


print(
    sensitivity[
        [
            "vot_eur_hour",
            "rank",
            "mode",
            "generalised_cost_eur",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


# ------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------

print(
    "\nVALIDATION / ASSUMPTIONS"
)


print(
    "- Generalised cost = monetary cost "
    "+ Value of Time × total door-to-door time."
)


print(
    "- Baseline VOT = EUR 10/hour."
)


print(
    "- Sensitivity scenarios = "
    "EUR 5, 10 and 20/hour."
)


print(
    "- Private-car travel uses the observed "
    "26 min driving time plus an explicit "
    "10 min round-trip parking/access allowance."
)


print(
    "- The private-car parking/access allowance "
    "corresponds to 5 min per direction for "
    "parking search and walking."
)


print(
    "- Car sharing includes 5 min "
    "access/search per direction."
)


print(
    "- Shared bike and shared scooter include "
    "3 min access/search per direction."
)


print(
    "- Scooter travel time is modelled at "
    "15 km/h average operating speed."
)


print(
    "- Taxi fare uses the midpoint of the "
    "observed EUR 10-16 one-way range."
)


print(
    "- Taxi waiting time is an explicit "
    "5 min per-direction assumption."
)


print(
    "- Uber waiting time uses the observed "
    "6 min outbound and 3 min return estimates."
)


print(
    "- Public transport cost is the net annual "
    "subscription allocated over "
    "150 university days."
)


print(
    "- No additional PT waiting time is "
    "invented beyond the observed "
    "23 min door-to-door itinerary per direction."
)


print(
    "\nSaved tables -> "
    f"{OUTPUT_DIR}"
)