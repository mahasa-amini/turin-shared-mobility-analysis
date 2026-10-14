from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# CONFIG
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

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OPERATORS = [
    "bird",
    "lime",
    "voi",
]


# Primary operational-parking definition
MAX_RELOCATION_M = 100.0
MAX_PARKING_MIN = 7 * 24 * 60   # 10,080 min


# =============================================================================
# LOAD
# =============================================================================

def load_operator(operator):

    parking_file = (
        PARKING_DIR
        / f"{operator}_parking_interval_candidates_2024.parquet"
    )

    zoned_file = (
        ZONED_DIR
        / f"{operator}_2024_zoned.parquet"
    )

    if not parking_file.exists():
        raise FileNotFoundError(parking_file)

    if not zoned_file.exists():
        raise FileNotFoundError(zoned_file)

    parking = pd.read_parquet(
        parking_file
    )

    zoned = pd.read_parquet(
        zoned_file,
        columns=[
            "trip_uid",
            "destination_zone_id",
            "destination_zone_assigned",
            "destination_assignment_status",
        ],
    )

    assert zoned["trip_uid"].is_unique

    data = parking.merge(
        zoned,
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

    data[
        "destination_zone_id"
    ] = (
        data[
            "destination_zone_id"
        ]
        .astype("string")
    )

    return data


# =============================================================================
# VALIDITY FLAGS
# =============================================================================

def add_validity_flags(data):

    df = data.copy()

    df[
        "valid_parking_next_trip"
    ] = (
        df[
            "has_next_trip"
        ]
        .fillna(False)
        .astype(bool)
    )

    df[
        "valid_parking_elapsed"
    ] = (
        df[
            "dst_elapsed_resolved"
        ]
        .fillna(False)
        .astype(bool)
        &
        (
            df[
                "parking_gap_elapsed_min"
            ]
            > 0
        )
    )

    df[
        "valid_parking_spatial_continuity"
    ] = (
        df[
            "relocation_distance_m"
        ]
        .notna()
        &
        (
            df[
                "relocation_distance_m"
            ]
            <= MAX_RELOCATION_M
        )
    )

    df[
        "valid_parking_zone"
    ] = (
        df[
            "destination_zone_assigned"
        ]
        &
        df[
            "destination_zone_id"
        ]
        .notna()
    )

    df[
        "valid_parking_operational_duration"
    ] = (
        df[
            "parking_gap_elapsed_min"
        ]
        .notna()
        &
        (
            df[
                "parking_gap_elapsed_min"
            ]
            <= MAX_PARKING_MIN
        )
    )

    df[
        "valid_parking_event"
    ] = (
        df[
            "valid_parking_next_trip"
        ]
        &
        df[
            "valid_parking_elapsed"
        ]
        &
        df[
            "valid_parking_spatial_continuity"
        ]
        &
        df[
            "valid_parking_zone"
        ]
        &
        df[
            "valid_parking_operational_duration"
        ]
    )

    return df


# =============================================================================
# MUTUALLY EXCLUSIVE EXCLUSION REASON
#
# Precedence is used only so audit counts reconcile exactly.
# =============================================================================

def add_exclusion_reason(df):

    reason = pd.Series(
        "valid",
        index=df.index,
        dtype="string",
    )

    remaining = pd.Series(
        True,
        index=df.index,
    )

    rules = [
        (
            "no_next_trip",
            ~df[
                "valid_parking_next_trip"
            ],
        ),

        (
            "elapsed_time_unresolved",
            ~df[
                "dst_elapsed_resolved"
            ]
            .fillna(False),
        ),

        (
            "non_positive_gap",
            df[
                "parking_gap_elapsed_min"
            ]
            .notna()
            &
            (
                df[
                    "parking_gap_elapsed_min"
                ]
                <= 0
            ),
        ),

        (
            "missing_relocation_distance",
            df[
                "relocation_distance_m"
            ]
            .isna(),
        ),

        (
            "destination_zone_unassigned",
            ~df[
                "valid_parking_zone"
            ],
        ),

        (
            "relocation_over_100m",
            df[
                "relocation_distance_m"
            ]
            .notna()
            &
            (
                df[
                    "relocation_distance_m"
                ]
                > MAX_RELOCATION_M
            ),
        ),

        (
            "parking_gap_over_7d",
            df[
                "parking_gap_elapsed_min"
            ]
            .notna()
            &
            (
                df[
                    "parking_gap_elapsed_min"
                ]
                > MAX_PARKING_MIN
            ),
        ),
    ]

    for label, mask in rules:

        select = (
            remaining
            &
            mask.fillna(False)
        )

        reason.loc[
            select
        ] = label

        remaining.loc[
            select
        ] = False

    # Anything marked valid must satisfy the canonical rule.
    assert (
        (
            reason == "valid"
        )
        ==
        df[
            "valid_parking_event"
        ]
    ).all()

    df[
        "parking_exclusion_reason"
    ] = reason

    return df


# =============================================================================
# TEMPORAL FEATURES
# =============================================================================

def add_parking_features(valid):

    df = valid.copy()

    # Parking begins when the previous trip ends.
    df[
        "parking_start_time_local"
    ] = pd.to_datetime(
        df[
            "end_time_local"
        ]
    )

    # Parking ends when the next observed trip begins.
    df[
        "parking_end_time_local"
    ] = pd.to_datetime(
        df[
            "next_start_time_local"
        ]
    )

    df[
        "parking_duration_min"
    ] = (
        df[
            "parking_gap_elapsed_min"
        ]
        .astype(float)
    )

    df[
        "parking_duration_h"
    ] = (
        df[
            "parking_duration_min"
        ]
        / 60.0
    )

    df[
        "parking_duration_d"
    ] = (
        df[
            "parking_duration_h"
        ]
        / 24.0
    )

    df[
        "parking_start_date"
    ] = (
        df[
            "parking_start_time_local"
        ]
        .dt.normalize()
    )

    df[
        "parking_start_hour"
    ] = (
        df[
            "parking_start_time_local"
        ]
        .dt.hour
        .astype("int8")
    )

    df[
        "parking_start_weekday_number"
    ] = (
        df[
            "parking_start_time_local"
        ]
        .dt.weekday
        .astype("int8")
    )

    df[
        "parking_start_weekday"
    ] = (
        df[
            "parking_start_time_local"
        ]
        .dt.day_name()
        .astype("string")
    )

    df[
        "parking_start_month"
    ] = (
        df[
            "parking_start_time_local"
        ]
        .dt.to_period("M")
        .astype("string")
    )

    # -------------------------------------------------------------------------
    # Same conventional periods as Exercise 2.
    # This allows direct OD × parking overlays later.
    # -------------------------------------------------------------------------

    hour = df[
        "parking_start_hour"
    ]

    df[
        "conventional_period"
    ] = "Off-peak"

    df.loc[
        hour.isin(
            [7, 8, 9]
        ),
        "conventional_period",
    ] = "AM peak"

    df.loc[
        hour.isin(
            [16, 17, 18, 19]
        ),
        "conventional_period",
    ] = "PM peak"

    df[
        "conventional_period"
    ] = pd.Categorical(
        df[
            "conventional_period"
        ],
        categories=[
            "AM peak",
            "PM peak",
            "Off-peak",
        ],
        ordered=True,
    )

    # Useful for tracing the parking interval.
    df[
        "parking_event_uid"
    ] = (
        df[
            "trip_uid"
        ]
        .astype("string")
        +
        "__TO__"
        +
        df[
            "next_trip_uid"
        ]
        .astype("string")
    )

    assert df[
        "parking_event_uid"
    ].is_unique

    return df


# =============================================================================
# SUMMARY
# =============================================================================

def summarize_valid_events(
    operator,
    candidates,
    valid,
):

    gap = valid[
        "parking_duration_min"
    ]

    return {
        "operator":
            operator,

        "candidate_events":
            len(candidates),

        "valid_parking_events":
            len(valid),

        "valid_share_of_candidates_pct":
            (
                len(valid)
                /
                len(candidates)
                * 100
            ),

        "zones_with_valid_parking":
            valid[
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

        "mean_parking_h":
            (
                gap.mean()
                / 60
            ),

        "median_parking_h":
            (
                gap.median()
                / 60
            ),

        "mean_relocation_m":
            valid[
                "relocation_distance_m"
            ].mean(),

        "median_relocation_m":
            valid[
                "relocation_distance_m"
            ].median(),
    }


# =============================================================================
# OPTIONAL CROSS-CHECK AGAINST PREVIOUS SENSITIVITY OUTPUT
# =============================================================================

def expected_count_from_sensitivity(
    operator,
):

    path = (
        AUDIT_DIR
        / "parking_duration_cap_sensitivity_2024.csv"
    )

    if not path.exists():
        return None

    table = pd.read_csv(
        path
    )

    row = table.loc[
        (
            table[
                "operator"
            ]
            == operator
        )
        &
        (
            table[
                "relocation_threshold_m"
            ]
            == 100
        )
        &
        (
            table[
                "duration_rule"
            ]
            == "<=7d"
        )
    ]

    if len(row) != 1:
        return None

    return int(
        row.iloc[0][
            "parking_events"
        ]
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 4 — FINALIZING OPERATIONAL PARKING EVENTS"
    )

    print(
        "=" * 110
    )

    print(
        "\nCanonical definition:"
        "\n- next trip observed"
        "\n- DST-resolved positive elapsed gap"
        "\n- official destination zone assigned"
        "\n- current destination → next origin <= 100 m"
        "\n- parking gap <= 7 days"
    )

    summaries = []
    exclusion_tables = []

    for operator in OPERATORS:

        print(
            "\n"
            + "-" * 90
        )

        print(
            f"Processing "
            f"{operator.upper()}"
        )

        print(
            "-" * 90
        )

        data = load_operator(
            operator
        )

        data = add_validity_flags(
            data
        )

        data = add_exclusion_reason(
            data
        )

        # -----------------------------------------------------
        # Exclusion audit
        # -----------------------------------------------------

        exclusion = (
            data[
                "parking_exclusion_reason"
            ]
            .value_counts(
                dropna=False
            )
            .rename_axis(
                "reason"
            )
            .reset_index(
                name="count"
            )
        )

        exclusion.insert(
            0,
            "operator",
            operator,
        )

        exclusion[
            "share_of_candidates_pct"
        ] = (
            exclusion[
                "count"
            ]
            /
            len(data)
            * 100
        )

        exclusion_tables.append(
            exclusion
        )

        # -----------------------------------------------------
        # Valid canonical parking population
        # -----------------------------------------------------

        valid = data.loc[
            data[
                "valid_parking_event"
            ]
        ].copy()

        valid = add_parking_features(
            valid
        )

        expected = (
            expected_count_from_sensitivity(
                operator
            )
        )

        if expected is not None:

            if len(valid) != expected:

                raise AssertionError(
                    f"{operator}: "
                    f"valid count {len(valid):,} "
                    f"does not match sensitivity "
                    f"count {expected:,}"
                )

            print(
                f"Sensitivity reconciliation: PASSED "
                f"({len(valid):,} events)"
            )

        # -----------------------------------------------------
        # Validation
        # -----------------------------------------------------

        assert (
            valid[
                "parking_duration_min"
            ]
            > 0
        ).all()

        assert (
            valid[
                "parking_duration_min"
            ]
            <= MAX_PARKING_MIN
        ).all()

        assert (
            valid[
                "relocation_distance_m"
            ]
            <= MAX_RELOCATION_M
        ).all()

        assert (
            valid[
                "destination_zone_id"
            ]
            .notna()
            .all()
        )

        assert (
            valid[
                "parking_start_time_local"
            ]
            <
            valid[
                "parking_end_time_local"
            ]
        ).all()

        # -----------------------------------------------------
        # Save
        # -----------------------------------------------------

        output_path = (
            PARKING_DIR
            / f"{operator}_parking_events_2024.parquet"
        )

        valid.to_parquet(
            output_path,
            index=False,
        )

        print(
            f"Saved -> "
            f"{output_path}"
        )

        summaries.append(
            summarize_valid_events(
                operator,
                data,
                valid,
            )
        )

    # =========================================================================
    # COMBINED OUTPUTS
    # =========================================================================

    summary = pd.DataFrame(
        summaries
    )

    exclusions = pd.concat(
        exclusion_tables,
        ignore_index=True,
    )

    summary.to_csv(
        AUDIT_DIR
        / "final_parking_event_summary_2024.csv",
        index=False,
    )

    exclusions.to_csv(
        AUDIT_DIR
        / "parking_event_exclusion_reasons_2024.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL
    # =========================================================================

    pd.set_option(
        "display.max_columns",
        None
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "FINAL PARKING EVENT SUMMARY"
    )

    print(
        "=" * 110
    )

    display = summary.copy()

    for col in [
        "valid_share_of_candidates_pct",
        "mean_parking_min",
        "median_parking_min",
        "p75_parking_min",
        "p90_parking_min",
        "p95_parking_min",
        "p99_parking_min",
        "mean_parking_h",
        "median_parking_h",
        "mean_relocation_m",
        "median_relocation_m",
    ]:

        display[
            col
        ] = (
            display[
                col
            ]
            .round(2)
        )

    print(
        display.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "MUTUALLY EXCLUSIVE EXCLUSION REASONS"
    )

    print(
        "=" * 110
    )

    exclusion_display = (
        exclusions.copy()
    )

    exclusion_display[
        "share_of_candidates_pct"
    ] = (
        exclusion_display[
            "share_of_candidates_pct"
        ]
        .round(3)
    )

    print(
        exclusion_display.to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION:"
        "\n- Primary relocation threshold = 100 m."
        "\n- Primary operational-duration cap = 7 days."
        "\n- Duration sensitivity remains available in audit outputs."
        "\n- Parking is assigned to the destination zone of the preceding trip."
        "\n- Parking start time is the end time of the preceding trip."
        "\n- AM/PM/off-peak definitions match Exercise 2."
        "\n- No parking duration is substituted with trip duration."
    )


if __name__ == "__main__":
    main()