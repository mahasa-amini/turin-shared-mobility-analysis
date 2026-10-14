from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PARKING_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "parking"
)

ZONED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "trips_zoned"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_4"
    / "parking"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_4"
    / "parking"
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OPERATORS = [
    "bird",
    "lime",
    "voi",
]

DISTANCE_THRESHOLDS_M = [
    20,
    50,
    100,
    200,
    500,
]


# =============================================================================
# LOAD
# =============================================================================

def load_operator(
    operator,
):

    parking_file = (
        PARKING_DIR
        / f"{operator}_parking_interval_candidates_2024.parquet"
    )

    zoning_file = (
        ZONED_DIR
        / f"{operator}_2024_zoned.parquet"
    )

    if not parking_file.exists():
        raise FileNotFoundError(
            parking_file
        )

    if not zoning_file.exists():
        raise FileNotFoundError(
            zoning_file
        )

    parking = pd.read_parquet(
        parking_file
    )

    zoning = pd.read_parquet(
        zoning_file,
        columns=[
            "trip_uid",
            "destination_zone_id",
            "destination_zone_assigned",
            "destination_assignment_status",
        ],
    )

    assert zoning[
        "trip_uid"
    ].is_unique

    data = parking.merge(
        zoning,
        on="trip_uid",
        how="left",
        validate="many_to_one",
    )

    assert len(data) == len(parking)

    data[
        "destination_zone_assigned"
    ] = (
        data[
            "destination_zone_assigned"
        ]
        .fillna(False)
        .astype(bool)
    )

    return data


# =============================================================================
# BASE TEMPORAL POPULATION
# =============================================================================

def build_base_population(
    data,
):

    base = data.loc[
        data[
            "has_next_trip"
        ]
        &
        data[
            "dst_elapsed_resolved"
        ]
        &
        (
            data[
                "parking_gap_elapsed_min"
            ]
            > 0
        )
        &
        data[
            "relocation_distance_m"
        ]
        .notna()
        &
        data[
            "destination_zone_assigned"
        ]
    ].copy()

    return base


# =============================================================================
# SUMMARY
# =============================================================================

def summarize_threshold(
    data,
    operator,
    threshold,
):

    sample = data.loc[
        data[
            "relocation_distance_m"
        ]
        <= threshold
    ].copy()

    gap = (
        sample[
            "parking_gap_elapsed_min"
        ]
        .astype(float)
    )

    if gap.empty:

        return None

    return {
        "operator":
            operator,

        "relocation_threshold_m":
            threshold,

        "parking_events":
            len(sample),

        "zones_with_parking":
            sample[
                "destination_zone_id"
            ]
            .nunique(),

        "mean_parking_min":
            gap.mean(),

        "median_parking_min":
            gap.median(),

        "p75_parking_min":
            gap.quantile(
                0.75
            ),

        "p90_parking_min":
            gap.quantile(
                0.90
            ),

        "p95_parking_min":
            gap.quantile(
                0.95
            ),

        "p99_parking_min":
            gap.quantile(
                0.99
            ),

        "max_parking_min":
            gap.max(),

        "share_over_6h_pct":
            (
                (
                    gap > 360
                ).mean()
                * 100
            ),

        "share_over_12h_pct":
            (
                (
                    gap > 720
                ).mean()
                * 100
            ),

        "share_over_24h_pct":
            (
                (
                    gap > 1440
                ).mean()
                * 100
            ),

        "share_over_48h_pct":
            (
                (
                    gap > 2880
                ).mean()
                * 100
            ),

        "share_over_7d_pct":
            (
                (
                    gap > 10080
                ).mean()
                * 100
            ),

        "mean_relocation_m":
            sample[
                "relocation_distance_m"
            ].mean(),

        "median_relocation_m":
            sample[
                "relocation_distance_m"
            ].median(),
    }


# =============================================================================
# DURATION-CAP SENSITIVITY
#
# These caps are NOT cleaning rules.
# They only quantify how sensitive the required arithmetic
# mean is to very long stationary gaps.
# =============================================================================

def summarize_duration_caps(
    data,
    operator,
    relocation_threshold=100,
):

    stationary = data.loc[
        data[
            "relocation_distance_m"
        ]
        <= relocation_threshold
    ].copy()

    caps = {
        "uncapped":
            None,

        "<=24h":
            1440,

        "<=48h":
            2880,

        "<=7d":
            10080,
    }

    rows = []

    for label, cap in (
        caps.items()
    ):

        if cap is None:

            sample = (
                stationary.copy()
            )

        else:

            sample = (
                stationary.loc[
                    stationary[
                        "parking_gap_elapsed_min"
                    ]
                    <= cap
                ]
                .copy()
            )

        gap = (
            sample[
                "parking_gap_elapsed_min"
            ]
            .astype(float)
        )

        rows.append(
            {
                "operator":
                    operator,

                "relocation_threshold_m":
                    relocation_threshold,

                "duration_rule":
                    label,

                "parking_events":
                    len(sample),

                "retained_from_stationary_pct":
                    (
                        len(sample)
                        /
                        len(stationary)
                        * 100
                        if len(stationary)
                        else np.nan
                    ),

                "mean_parking_min":
                    (
                        gap.mean()
                        if len(gap)
                        else np.nan
                    ),

                "median_parking_min":
                    (
                        gap.median()
                        if len(gap)
                        else np.nan
                    ),

                "p90_parking_min":
                    (
                        gap.quantile(
                            0.90
                        )
                        if len(gap)
                        else np.nan
                    ),

                "p95_parking_min":
                    (
                        gap.quantile(
                            0.95
                        )
                        if len(gap)
                        else np.nan
                    ),

                "p99_parking_min":
                    (
                        gap.quantile(
                            0.99
                        )
                        if len(gap)
                        else np.nan
                    ),
            }
        )

    return rows


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 4 — PARKING-DEFINITION SENSITIVITY"
    )

    print(
        "=" * 110
    )

    threshold_rows = []
    cap_rows = []
    base_rows = []

    for operator in OPERATORS:

        print(
            f"\nProcessing "
            f"{operator.upper()}..."
        )

        data = load_operator(
            operator
        )

        base = build_base_population(
            data
        )

        base_rows.append(
            {
                "operator":
                    operator,

                "candidate_events":
                    len(data),

                "base_positive_resolved_zoned_events":
                    len(base),

                "base_share_of_candidates_pct":
                    (
                        len(base)
                        /
                        len(data)
                        * 100
                    ),

                "zones_with_base_events":
                    base[
                        "destination_zone_id"
                    ]
                    .nunique(),
            }
        )

        for threshold in (
            DISTANCE_THRESHOLDS_M
        ):

            summary = (
                summarize_threshold(
                    base,
                    operator,
                    threshold,
                )
            )

            if summary is not None:

                threshold_rows.append(
                    summary
                )

        cap_rows.extend(
            summarize_duration_caps(
                base,
                operator,
                relocation_threshold=100,
            )
        )

    base_summary = pd.DataFrame(
        base_rows
    )

    threshold_summary = pd.DataFrame(
        threshold_rows
    )

    cap_summary = pd.DataFrame(
        cap_rows
    )

    # ========================================================
    # SAVE
    # ========================================================

    base_summary.to_csv(
        AUDIT_DIR
        / "parking_base_population_summary_2024.csv",
        index=False,
    )

    threshold_summary.to_csv(
        AUDIT_DIR
        / "parking_relocation_threshold_sensitivity_2024.csv",
        index=False,
    )

    cap_summary.to_csv(
        AUDIT_DIR
        / "parking_duration_cap_sensitivity_2024.csv",
        index=False,
    )

    # ========================================================
    # TERMINAL
    # ========================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "BASE PARKING POPULATION"
    )

    print(
        "=" * 110
    )

    display_base = (
        base_summary.copy()
    )

    display_base[
        "base_share_of_candidates_pct"
    ] = (
        display_base[
            "base_share_of_candidates_pct"
        ]
        .round(2)
    )

    print(
        display_base.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "RELOCATION-THRESHOLD SENSITIVITY"
    )

    print(
        "=" * 110
    )

    display_threshold = (
        threshold_summary.copy()
    )

    numeric_columns = [
        "mean_parking_min",
        "median_parking_min",
        "p75_parking_min",
        "p90_parking_min",
        "p95_parking_min",
        "p99_parking_min",
        "max_parking_min",
        "share_over_6h_pct",
        "share_over_12h_pct",
        "share_over_24h_pct",
        "share_over_48h_pct",
        "share_over_7d_pct",
        "mean_relocation_m",
        "median_relocation_m",
    ]

    for col in numeric_columns:

        display_threshold[
            col
        ] = (
            display_threshold[
                col
            ]
            .round(2)
        )

    print(
        display_threshold.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "DURATION-CAP SENSITIVITY AT 100 m"
    )

    print(
        "=" * 110
    )

    display_cap = (
        cap_summary.copy()
    )

    for col in [
        "retained_from_stationary_pct",
        "mean_parking_min",
        "median_parking_min",
        "p90_parking_min",
        "p95_parking_min",
        "p99_parking_min",
    ]:

        display_cap[
            col
        ] = (
            display_cap[
                col
            ]
            .round(2)
        )

    print(
        display_cap.to_string(
            index=False
        )
    )

    print(
        "\nINTERPRETATION:"
        "\n- No threshold in this script is yet a cleaning rule."
        "\n- 50/100/200 m test spatial-continuity sensitivity."
        "\n- 100 m is the current candidate primary threshold."
        "\n- Duration caps are sensitivity diagnostics only."
        "\n- Official destination-zone assignment is required because "
        "Exercise 4 is a zonal parking analysis."
        "\n- Only positive, DST-resolved parking gaps are evaluated."
    )


if __name__ == "__main__":
    main()