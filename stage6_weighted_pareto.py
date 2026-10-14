from pathlib import Path

import pandas as pd


# ============================================================
# STAGE 6 — WEIGHTED TIME PERCEPTION + PARETO EFFICIENCY
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

INPUT_FILE = Path(
    "outputs/tables/generalised_cost/"
    "stage5_master_modes.csv"
)

OUTPUT_DIR = Path(
    "outputs/tables/generalised_cost"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ------------------------------------------------------------
# PARAMETERS
# ------------------------------------------------------------

BASE_VOT_EUR_PER_HOUR = 10.0

TRAVEL_TIME_WEIGHT = 1.0
ACCESS_EGRESS_WEIGHT = 1.5
WAITING_TIME_WEIGHT = 2.0


# ============================================================
# LOAD
# ============================================================

if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"Stage 5 input not found: {INPUT_FILE}"
    )


df = pd.read_csv(
    INPUT_FILE
)


required_columns = {
    "mode",
    "monetary_cost_eur",
    "travel_min",
    "access_egress_min",
    "waiting_min",
    "total_time_min",
}

missing = (
    required_columns
    - set(df.columns)
)

if missing:

    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# 1. WEIGHTED TIME PERCEPTION
# ============================================================

df["weighted_travel_min"] = (
    df["travel_min"]
    * TRAVEL_TIME_WEIGHT
)

df["weighted_access_egress_min"] = (
    df["access_egress_min"]
    * ACCESS_EGRESS_WEIGHT
)

df["weighted_waiting_min"] = (
    df["waiting_min"]
    * WAITING_TIME_WEIGHT
)

df["perceived_time_min"] = (
    df["weighted_travel_min"]
    + df["weighted_access_egress_min"]
    + df["weighted_waiting_min"]
)


df["weighted_time_cost_eur"] = (
    df["perceived_time_min"]
    / 60
    * BASE_VOT_EUR_PER_HOUR
)


df["weighted_generalised_cost_eur"] = (
    df["monetary_cost_eur"]
    + df["weighted_time_cost_eur"]
)


df["weighted_gc_rank"] = (
    df["weighted_generalised_cost_eur"]
    .rank(
        method="min"
    )
    .astype(int)
)


weighted = (
    df
    .sort_values(
        "weighted_generalised_cost_eur"
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 2. CHANGE RELATIVE TO STANDARD GC
# ============================================================

if "generalised_cost_eur" in df.columns:

    df["weighted_gc_change_eur"] = (
        df["weighted_generalised_cost_eur"]
        - df["generalised_cost_eur"]
    )

    df["weighted_gc_pct_change"] = (
        df["weighted_gc_change_eur"]
        / df["generalised_cost_eur"]
        * 100
    )


# ============================================================
# 3. PARETO EFFICIENCY
#
# Minimise:
# - monetary cost
# - total door-to-door time
#
# A mode is dominated if another mode is:
# cheaper or equal AND faster or equal,
# with at least one strict improvement.
# ============================================================

def is_dominated(
    row,
    dataframe,
):

    for _, other in dataframe.iterrows():

        if (
            other["mode"]
            == row["mode"]
        ):
            continue

        cheaper_or_equal = (
            other["monetary_cost_eur"]
            <= row["monetary_cost_eur"]
        )

        faster_or_equal = (
            other["total_time_min"]
            <= row["total_time_min"]
        )

        strictly_better = (
            other["monetary_cost_eur"]
            < row["monetary_cost_eur"]
            or
            other["total_time_min"]
            < row["total_time_min"]
        )

        if (
            cheaper_or_equal
            and faster_or_equal
            and strictly_better
        ):
            return True

    return False


df["pareto_dominated"] = (
    df.apply(
        lambda row:
        is_dominated(
            row,
            df,
        ),
        axis=1,
    )
)


df["pareto_efficient"] = (
    ~df["pareto_dominated"]
)


pareto = (
    df[
        [
            "mode",
            "monetary_cost_eur",
            "total_time_min",
            "pareto_efficient",
        ]
    ]
    .sort_values(
        [
            "pareto_efficient",
            "monetary_cost_eur",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 4. PT ACCOUNTING VS MARGINAL COST SENSITIVITY
#
# Main model:
# net annual pass / 150 university days.
#
# Alternative:
# marginal monetary cost of an additional trip
# with an already-owned pass = EUR 0.
# ============================================================

pt_row = df.loc[
    df["mode"]
    == "Public transport"
].iloc[0]


pt_sensitivity = []


for scenario, monetary_cost in [
    (
        "Allocated subscription cost",
        pt_row["monetary_cost_eur"],
    ),
    (
        "Marginal cost with existing pass",
        0.0,
    ),
]:

    standard_gc = (
        monetary_cost
        +
        pt_row["total_time_min"]
        / 60
        * BASE_VOT_EUR_PER_HOUR
    )

    weighted_gc = (
        monetary_cost
        +
        pt_row["perceived_time_min"]
        / 60
        * BASE_VOT_EUR_PER_HOUR
    )

    pt_sensitivity.append(
        {
            "scenario": scenario,
            "monetary_cost_eur":
                monetary_cost,
            "standard_gc_eur":
                standard_gc,
            "weighted_gc_eur":
                weighted_gc,
        }
    )


pt_sensitivity = pd.DataFrame(
    pt_sensitivity
)


# ============================================================
# SAVE
# ============================================================

weighted.to_csv(
    OUTPUT_DIR
    / "stage6_weighted_generalised_cost.csv",
    index=False,
)

pareto.to_csv(
    OUTPUT_DIR
    / "stage6_pareto_efficiency.csv",
    index=False,
)

pt_sensitivity.to_csv(
    OUTPUT_DIR
    / "stage6_pt_cost_sensitivity.csv",
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
    "STAGE 6 — WEIGHTED TIME PERCEPTION "
    "+ PARETO EFFICIENCY"
)

print(
    "=" * 115
)


print(
    "\nTIME WEIGHTS"
)

print(
    f"Travel / riding: "
    f"{TRAVEL_TIME_WEIGHT:.1f}"
)

print(
    f"Access / egress: "
    f"{ACCESS_EGRESS_WEIGHT:.1f}"
)

print(
    f"Waiting: "
    f"{WAITING_TIME_WEIGHT:.1f}"
)


print(
    "\nWEIGHTED GENERALISED COST "
    f"(VOT = EUR {BASE_VOT_EUR_PER_HOUR:.0f}/h)"
)

print(
    weighted[
        [
            "weighted_gc_rank",
            "mode",
            "monetary_cost_eur",
            "total_time_min",
            "perceived_time_min",
            "weighted_time_cost_eur",
            "weighted_generalised_cost_eur",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


print(
    "\nPARETO EFFICIENCY "
    "(MONEY VS DOOR-TO-DOOR TIME)"
)

print(
    pareto.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


print(
    "\nPARETO-EFFICIENT MODES"
)

for mode in (
    pareto.loc[
        pareto["pareto_efficient"],
        "mode",
    ]
):

    print(
        f"- {mode}"
    )


print(
    "\nPUBLIC TRANSPORT COST-ALLOCATION SENSITIVITY"
)

print(
    pt_sensitivity.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)


print(
    "\nVALIDATION / INTERPRETATION"
)

print(
    "- Standard travel/riding time keeps weight 1.0."
)

print(
    "- Access/egress time is weighted 1.5."
)

print(
    "- Waiting time is weighted 2.0."
)

print(
    "- These multipliers are explicit behavioural "
    "assumptions, not measured preferences."
)

print(
    "- Pareto efficiency is independent of VOT."
)

print(
    "- A Pareto-efficient mode cannot be made both "
    "cheaper and faster by another observed mode."
)

print(
    "- PT marginal-cost sensitivity distinguishes "
    "accounting allocation from the cost of an "
    "additional trip with an already-owned pass."
)