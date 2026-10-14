from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUDIT_DIR = PROJECT_ROOT / "audit"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


BIRD_FILE = (
    AUDIT_DIR
    / "bird"
    / "bird_final_cleaning_summary.csv"
)

LIME_FILE = (
    AUDIT_DIR
    / "lime"
    / "lime_final_cleaning_summary.csv"
)

VOI_FILE = (
    AUDIT_DIR
    / "voi"
    / "voi_final_cleaning_summary.csv"
)

HARMONIZATION_FILE = (
    AUDIT_DIR
    / "harmonization"
    / "harmonization_summary.csv"
)


# ============================================================
# HELPERS
# ============================================================

def require_file(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )


def load_inputs():

    for path in [
        BIRD_FILE,
        LIME_FILE,
        VOI_FILE,
        HARMONIZATION_FILE,
    ]:
        require_file(path)

    bird = pd.read_csv(BIRD_FILE)
    lime = pd.read_csv(LIME_FILE)
    voi = pd.read_csv(VOI_FILE)
    harmonized = pd.read_csv(
        HARMONIZATION_FILE
    )

    return bird, lime, voi, harmonized


# ============================================================
# ROW-LEVEL CLEANING IMPACT
# ============================================================

def build_cleaning_impact(
    bird,
    lime,
    voi,
    harmonized,
):

    records = []

    # --------------------------------------------------------
    # Bird
    # --------------------------------------------------------

    for _, row in bird.iterrows():

        records.append(
            {
                "operator": "bird",
                "year": int(row["year"]),
                "rows_before_cleaning":
                    int(row["rows_input"]),
                "rows_after_cleaning":
                    int(row["rows_output"]),
                "rows_removed_or_collapsed":
                    int(
                        row["rows_input"]
                        - row["rows_output"]
                    ),
                "row_level_action":
                    "No global row removal",
            }
        )

    # --------------------------------------------------------
    # Lime
    # --------------------------------------------------------

    for _, row in lime.iterrows():

        records.append(
            {
                "operator": "lime",
                "year": int(row["year"]),
                "rows_before_cleaning":
                    int(row["rows_input"]),
                "rows_after_cleaning":
                    int(row["rows_output"]),
                "rows_removed_or_collapsed":
                    int(row["rows_removed"]),
                "row_level_action":
                    (
                        "Removed exact zero/negative "
                        "elapsed non-trips"
                    ),
            }
        )

    # --------------------------------------------------------
    # VOI
    # --------------------------------------------------------

    for _, row in voi.iterrows():

        records.append(
            {
                "operator": "voi",
                "year": int(row["year"]),
                "rows_before_cleaning":
                    int(row["rows_input"]),
                "rows_after_cleaning":
                    int(row["rows_output"]),
                "rows_removed_or_collapsed":
                    int(
                        row[
                            "duplicate_rows_collapsed"
                        ]
                    ),
                "row_level_action":
                    (
                        "Collapsed duplicate rows to "
                        "one canonical trip per trip ID"
                    ),
            }
        )

    impact = pd.DataFrame(records)

    impact[
        "retention_rate_pct"
    ] = (
        impact["rows_after_cleaning"]
        / impact["rows_before_cleaning"]
        * 100
    )

    impact[
        "removed_or_collapsed_pct"
    ] = (
        impact[
            "rows_removed_or_collapsed"
        ]
        / impact["rows_before_cleaning"]
        * 100
    )

    # --------------------------------------------------------
    # Cross-check with harmonized row counts
    # --------------------------------------------------------

    harmonized_counts = (
        harmonized[
            [
                "operator",
                "year",
                "rows",
            ]
        ]
        .rename(
            columns={
                "rows":
                    "harmonized_rows"
            }
        )
    )

    impact = impact.merge(
        harmonized_counts,
        on=[
            "operator",
            "year",
        ],
        how="left",
        validate="one_to_one",
    )

    impact[
        "cleaned_harmonized_match"
    ] = (
        impact[
            "rows_after_cleaning"
        ]
        ==
        impact[
            "harmonized_rows"
        ]
    )

    assert (
        impact[
            "cleaned_harmonized_match"
        ]
        .all()
    ), (
        "Cleaned and harmonized row counts "
        "do not reconcile."
    )

    return impact


# ============================================================
# BAD-DATA INVENTORY
#
# IMPORTANT:
# Counts within this table may overlap.
# They must NOT be summed to obtain removed rows.
# ============================================================

def build_bad_data_inventory(
    bird,
    lime,
    voi,
):

    issues = []

    def add(
        operator,
        year,
        category,
        issue,
        count,
        treatment,
        affects,
    ):

        issues.append(
            {
                "operator":
                    operator,

                "year":
                    int(year),

                "category":
                    category,

                "issue":
                    issue,

                "count":
                    int(count),

                "treatment":
                    treatment,

                "affects_analysis":
                    affects,
            }
        )

    # ========================================================
    # BIRD
    # ========================================================

    for _, r in bird.iterrows():

        y = r["year"]

        add(
            "bird",
            y,
            "distance",
            "Non-positive reported distance",
            r["invalid_distance"],
            (
                "Trip retained; distance "
                "measurement invalidated"
            ),
            "distance / speed",
        )

        add(
            "bird",
            y,
            "speed",
            "Invalid for reported-speed analysis",
            r[
                "invalid_speed_for_speed_analysis"
            ],
            (
                "Trip retained; speed value "
                "excluded from speed analysis"
            ),
            "speed",
        )

        add(
            "bird",
            y,
            "temporal",
            "DST-ambiguous local timestamps",
            r["dst_ambiguous_retained"],
            (
                "Trip retained; provider duration "
                "used for elapsed-time analysis"
            ),
            "clock-time interpretation",
        )

        add(
            "bird",
            y,
            "spatial",
            "Clear pre-zone spatial errors",
            r["clear_spatial_errors"],
            (
                "Trip retained globally; excluded "
                "from spatial analyses"
            ),
            "OD / maps / spatial analysis",
        )

        add(
            "bird",
            y,
            "consistency",
            "Distance-geometry mismatch warning",
            r[
                "distance_geometry_mismatch_warning"
            ],
            (
                "Diagnostic flag only; "
                "no automatic row deletion"
            ),
            "distance-quality assessment",
        )

        add(
            "bird",
            y,
            "spatial",
            "Small endpoint displacement",
            r[
                "small_displacement_retained"
            ],
            (
                "Retained intentionally; not "
                "treated as invalid trip"
            ),
            "none automatically",
        )

    # ========================================================
    # LIME
    # ========================================================

    for _, r in lime.iterrows():

        y = r["year"]

        add(
            "lime",
            y,
            "temporal",
            "Exact zero elapsed non-trip",
            r["removed_zero_elapsed"],
            "Removed globally",
            "all analyses",
        )

        add(
            "lime",
            y,
            "temporal",
            "Negative elapsed non-trip",
            r["removed_negative_elapsed"],
            "Removed globally",
            "all analyses",
        )

        add(
            "lime",
            y,
            "temporal",
            "DST elapsed-time inconsistency",
            r["dst_corrected"],
            (
                "Elapsed duration corrected "
                "using DST rule"
            ),
            "duration",
        )

        add(
            "lime",
            y,
            "temporal",
            "Reported duration rounded to zero",
            r[
                "reported_duration_zero_retained"
            ],
            (
                "Retained; precise timestamp-based "
                "duration used"
            ),
            "duration",
        )

        add(
            "lime",
            y,
            "distance",
            "Reported distance rounded to zero",
            r[
                "reported_distance_zero_retained"
            ],
            (
                "Retained; zero interpreted as "
                "coarse integer-km measurement"
            ),
            "distance precision",
        )

        add(
            "lime",
            y,
            "distance",
            "100-km sentinel distance",
            r["distance_sentinel_100"],
            (
                "Trip retained; distance "
                "measurement invalidated"
            ),
            "distance / speed",
        )

        add(
            "lime",
            y,
            "kinematic",
            "Kinematic inconsistency warning",
            r["kinematic_warning"],
            (
                "Flagged; not globally removed"
            ),
            "speed / diagnostics",
        )

        add(
            "lime",
            y,
            "spatial",
            "Outside broad Torino extent",
            r["outside_torino_broad"],
            (
                "Excluded from spatial-valid "
                "pre-zone subset"
            ),
            "OD / maps",
        )

        add(
            "lime",
            y,
            "spatial",
            "Endpoint displacement >30 km",
            r["haversine_over_30km"],
            (
                "Excluded from spatial-valid "
                "pre-zone subset"
            ),
            "OD / maps",
        )

    # ========================================================
    # VOI
    # ========================================================

    for _, r in voi.iterrows():

        y = r["year"]

        add(
            "voi",
            y,
            "duplicates",
            "Duplicate source rows",
            r[
                "duplicate_rows_collapsed"
            ],
            (
                "Collapsed to one canonical "
                "trip per trip ID"
            ),
            "all analyses",
        )

        add(
            "voi",
            y,
            "categorical",
            "Reservation-status conflict",
            r["reservation_conflict"],
            (
                "Trip retained; reservation "
                "status set unresolved and flagged"
            ),
            "reservation-specific analysis",
        )

        add(
            "voi",
            y,
            "temporal",
            "Detailed timestamp unavailable",
            r[
                "temporal_detail_unavailable"
            ],
            (
                "Trip retained; source month "
                "available but day/hour unavailable"
            ),
            (
                "daily / hourly / weekday / "
                "parking analysis"
            ),
        )

        add(
            "voi",
            y,
            "temporal",
            "Provider-duration fallback",
            r[
                "duration_provider_fallback"
            ],
            (
                "Tempo Tot used when detailed "
                "timestamp unavailable"
            ),
            "duration provenance",
        )

        add(
            "voi",
            y,
            "temporal",
            "Invalid duration measurement",
            r["invalid_duration"],
            (
                "Trip retained; duration "
                "measurement invalidated"
            ),
            "duration / speed",
        )

        incomplete_coords = (
            int(r["rows_output"])
            - int(
                r["complete_coordinates"]
            )
        )

        add(
            "voi",
            y,
            "spatial",
            "Incomplete coordinates",
            incomplete_coords,
            (
                "Trip retained; excluded from "
                "spatial analysis"
            ),
            "OD / maps / distance",
        )

        add(
            "voi",
            y,
            "spatial",
            "Outside broad Torino extent",
            r["outside_torino_broad"],
            (
                "Excluded from spatial-valid "
                "pre-zone subset"
            ),
            "OD / maps",
        )

        add(
            "voi",
            y,
            "spatial",
            "Endpoint displacement >30 km",
            r["haversine_over_30km"],
            (
                "Excluded from spatial-valid "
                "pre-zone subset"
            ),
            "OD / maps",
        )

        add(
            "voi",
            y,
            "distance",
            "Invalid displacement measurement",
            r["invalid_distance"],
            (
                "Trip retained; displacement "
                "excluded from distance analysis"
            ),
            "distance / speed",
        )

        add(
            "voi",
            y,
            "kinematic",
            "Kinematic inconsistency warning",
            r["kinematic_warning"],
            (
                "Flagged; not globally removed"
            ),
            "speed / diagnostics",
        )

        battery_unavailable_or_invalid = (
            int(r["rows_output"])
            - int(r["valid_battery"])
        )

        add(
            "voi",
            y,
            "battery",
            "Battery unavailable or invalid",
            battery_unavailable_or_invalid,
            (
                "Trip retained; battery-specific "
                "analysis excludes these records"
            ),
            "battery analysis",
        )

    inventory = pd.DataFrame(
        issues
    )
    # ========================================================
    # SEMANTIC CLASSIFICATION OF DATA-QUALITY EVENTS
    #
    # Important:
    # Not every flagged condition is "bad data".
    # Some are measurement limitations, corrected values,
    # diagnostic warnings, or valid characteristics that
    # were intentionally retained.
    # ========================================================

    ISSUE_CLASS_MAP = {

        # ----------------------------------------------------
        # BIRD
        # ----------------------------------------------------

        "Non-positive reported distance":
            "field_level_error_or_limitation",

        "Invalid for reported-speed analysis":
            "field_level_error_or_limitation",

        "DST-ambiguous local timestamps":
            "field_level_error_or_limitation",

        "Clear pre-zone spatial errors":
            "field_level_error_or_limitation",

        "Distance-geometry mismatch warning":
            "diagnostic_warning",

        "Small endpoint displacement":
            "retained_valid_characteristic",

        # ----------------------------------------------------
        # LIME
        # ----------------------------------------------------

        "Exact zero elapsed non-trip":
            "row_level_error",

        "Negative elapsed non-trip":
            "row_level_error",

        "DST elapsed-time inconsistency":
            "corrected_measurement",

        "Reported duration rounded to zero":
            "measurement_granularity",

        "Reported distance rounded to zero":
            "measurement_granularity",

        "100-km sentinel distance":
            "field_level_error_or_limitation",

        "Kinematic inconsistency warning":
            "diagnostic_warning",

        "Outside broad Torino extent":
            "field_level_error_or_limitation",

        "Endpoint displacement >30 km":
            "field_level_error_or_limitation",

        # ----------------------------------------------------
        # VOI
        # ----------------------------------------------------

        "Duplicate source rows":
            "row_level_error",

        "Reservation-status conflict":
            "field_level_error_or_limitation",

        "Detailed timestamp unavailable":
            "field_level_error_or_limitation",

        "Provider-duration fallback":
            "corrected_measurement",

        "Invalid duration measurement":
            "field_level_error_or_limitation",

        "Incomplete coordinates":
            "field_level_error_or_limitation",

        "Invalid displacement measurement":
            "field_level_error_or_limitation",

        "Battery unavailable or invalid":
            "field_level_error_or_limitation",
    }


    inventory[
        "issue_class"
    ] = inventory[
        "issue"
    ].map(
        ISSUE_CLASS_MAP
    )


    # --------------------------------------------------------
    # Validation:
    # every quality issue must have an explicit classification
    # --------------------------------------------------------

    unclassified = (
        inventory.loc[
            inventory[
                "issue_class"
            ].isna(),
            "issue",
        ]
        .drop_duplicates()
        .tolist()
    )

    assert not unclassified, (
        "Unclassified data-quality issues found: "
        f"{unclassified}"
    )

    return inventory


# ============================================================
# AGGREGATED TABLES
# ============================================================

def build_operator_totals(impact):

    totals = (
        impact
        .groupby(
            "operator",
            as_index=False
        )
        .agg(
            rows_before_cleaning=(
                "rows_before_cleaning",
                "sum",
            ),
            rows_after_cleaning=(
                "rows_after_cleaning",
                "sum",
            ),
            rows_removed_or_collapsed=(
                "rows_removed_or_collapsed",
                "sum",
            ),
        )
    )

    totals[
        "retention_rate_pct"
    ] = (
        totals["rows_after_cleaning"]
        / totals["rows_before_cleaning"]
        * 100
    )

    totals[
        "removed_or_collapsed_pct"
    ] = (
        totals[
            "rows_removed_or_collapsed"
        ]
        / totals["rows_before_cleaning"]
        * 100
    )

    return totals


def build_year_totals(impact):

    totals = (
        impact
        .groupby(
            "year",
            as_index=False
        )
        .agg(
            rows_before_cleaning=(
                "rows_before_cleaning",
                "sum",
            ),
            rows_after_cleaning=(
                "rows_after_cleaning",
                "sum",
            ),
            rows_removed_or_collapsed=(
                "rows_removed_or_collapsed",
                "sum",
            ),
        )
    )

    totals[
        "retention_rate_pct"
    ] = (
        totals["rows_after_cleaning"]
        / totals["rows_before_cleaning"]
        * 100
    )

    return totals


def build_grand_total(impact):

    before = int(
        impact[
            "rows_before_cleaning"
        ].sum()
    )

    after = int(
        impact[
            "rows_after_cleaning"
        ].sum()
    )

    removed = (
        before - after
    )

    return pd.DataFrame(
        [
            {
                "rows_before_cleaning":
                    before,

                "rows_after_cleaning":
                    after,

                "rows_removed_or_collapsed":
                    removed,

                "retention_rate_pct":
                    after / before * 100,

                "removed_or_collapsed_pct":
                    removed / before * 100,
            }
        ]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 100
    )

    print(
        "EXERCISE 1 — CLEANING IMPACT ANALYSIS"
    )

    print(
        "=" * 100
    )

    bird, lime, voi, harmonized = (
        load_inputs()
    )

    impact = build_cleaning_impact(
        bird,
        lime,
        voi,
        harmonized,
    )

    inventory = build_bad_data_inventory(
        bird,
        lime,
        voi,
    )

    operator_totals = (
        build_operator_totals(
            impact
        )
    )

    year_totals = (
        build_year_totals(
            impact
        )
    )

    grand_total = (
        build_grand_total(
            impact
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    impact_path = (
        TABLE_DIR
        / "cleaning_impact_by_operator_year.csv"
    )

    operator_path = (
        TABLE_DIR
        / "cleaning_impact_by_operator.csv"
    )

    year_path = (
        TABLE_DIR
        / "cleaning_impact_by_year.csv"
    )

    total_path = (
        TABLE_DIR
        / "cleaning_impact_total.csv"
    )

    inventory_path = (
        TABLE_DIR
        / "data_quality_inventory.csv"
    )

    impact.to_csv(
        impact_path,
        index=False
    )

    operator_totals.to_csv(
        operator_path,
        index=False
    )

    year_totals.to_csv(
        year_path,
        index=False
    )

    grand_total.to_csv(
        total_path,
        index=False
    )

    inventory.to_csv(
        inventory_path,
        index=False
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print(
        "\nCleaning impact by operator-year:"
    )

    display = impact[
        [
            "operator",
            "year",
            "rows_before_cleaning",
            "rows_after_cleaning",
            "rows_removed_or_collapsed",
            "retention_rate_pct",
            "harmonized_rows",
            "cleaned_harmonized_match",
        ]
    ].copy()

    display[
        "retention_rate_pct"
    ] = (
        display[
            "retention_rate_pct"
        ]
        .round(3)
    )

    print(
        display.to_string(
            index=False
        )
    )

    print(
        "\nOperator totals:"
    )

    display_op = (
        operator_totals.copy()
    )

    display_op[
        "retention_rate_pct"
    ] = (
        display_op[
            "retention_rate_pct"
        ]
        .round(3)
    )

    display_op[
        "removed_or_collapsed_pct"
    ] = (
        display_op[
            "removed_or_collapsed_pct"
        ]
        .round(3)
    )

    print(
        display_op.to_string(
            index=False
        )
    )

    print(
        "\nYear totals:"
    )

    display_year = (
        year_totals.copy()
    )

    display_year[
        "retention_rate_pct"
    ] = (
        display_year[
            "retention_rate_pct"
        ]
        .round(3)
    )

    print(
        display_year.to_string(
            index=False
        )
    )

    print(
        "\nGrand total:"
    )

    display_total = (
        grand_total.copy()
    )

    display_total[
        "retention_rate_pct"
    ] = (
        display_total[
            "retention_rate_pct"
        ]
        .round(3)
    )

    display_total[
        "removed_or_collapsed_pct"
    ] = (
        display_total[
            "removed_or_collapsed_pct"
        ]
        .round(3)
    )

    print(
        display_total.to_string(
            index=False
        )
    )

    print(
        "\nData-quality inventory by operator and issue:"
    )

    issue_summary = (
        inventory
        .groupby(
            [
                "operator",
                "issue_class",
                "issue",
            ],
            as_index=False,
        )["count"]
        .sum()
        .sort_values(
            [
                "operator",
                "issue_class",
                "issue",
            ]
        )
    )
    

    print(
        issue_summary.to_string(
            index=False
        )
    )

    print(
        "\nIMPORTANT:"
        "\n- Data-quality issue counts can overlap and must not be summed "
        "across different issues."
        "\n- 'Rows removed/collapsed' represents the actual row-level "
        "change caused by cleaning."
        "\n- issue_class distinguishes row-level errors, field-level "
        "limitations, corrected measurements, measurement granularity, "
        "diagnostic warnings, and retained valid characteristics."
        "\n- Measurement-specific invalid values remain in the canonical "
        "datasets with validity flags rather than causing automatic "
        "trip deletion."
        "\n- Cleaned row counts reconcile exactly with harmonized datasets."
    )

    print(
        "\nSaved tables:"
    )

    for path in [
        impact_path,
        operator_path,
        year_path,
        total_path,
        inventory_path,
    ]:
        print(path)


if __name__ == "__main__":
    main()