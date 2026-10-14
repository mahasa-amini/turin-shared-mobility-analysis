from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "bird"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned" / "bird"
AUDIT_DIR = PROJECT_ROOT / "audit" / "bird"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


FILES = {
    2024: INTERIM_DIR / "bird_2024_typed_flagged.parquet",
    2025: INTERIM_DIR / "bird_2025_typed_flagged.parquet",
}


# ============================================================
# CLEANING / VALIDATION THRESHOLDS
# ============================================================

# Used only for speed-based analyses
REPORTED_SPEED_MAX_KMH = 30

# Very large endpoint displacement: clear spatial problem
HAVERSINE_MAX_KM = 30

# Conservative threshold for clearly impossible endpoint movement.
# This is intentionally higher than the 30 km/h audit threshold.
HAVERSINE_SPEED_CLEAR_ERROR_KMH = 40

# Warning only: does NOT invalidate the trip automatically
GEOMETRY_RATIO_WARNING = 1.10
GEOMETRY_ABSOLUTE_EXCESS_KM = 0.10


# ============================================================
# QUALITY VARIABLES
# ============================================================

def add_final_quality_fields(df):
    df = df.copy()

    # --------------------------------------------------------
    # 1. BASIC TRIP / TEMPORAL VALIDITY
    # --------------------------------------------------------

    df["VALID_TRIP_RECORD"] = (
        df["ID_VEICOLO"].notna()
        & df["START_TIME"].notna()
        & df["END_TIME_RAW"].notna()
        & df["DURATA_MIN"].notna()
        & (df["DURATA_MIN"] > 0)
    )

    df["VALID_TEMPORAL"] = df["VALID_TRIP_RECORD"]

    # Important:
    # DST records are valid trips, but their raw local timestamps
    # are temporally ambiguous.
    df["TEMPORAL_DST_AMBIGUOUS"] = (
        df["FLAG_POSSIBLE_DST"]
    )

    # --------------------------------------------------------
    # 2. DISTANCE VALIDITY
    # --------------------------------------------------------

    df["VALID_DISTANCE"] = (
        df["DISTANZA_KM"].notna()
        & (df["DISTANZA_KM"] > 0)
    )

    # Keep raw DISTANZA_KM untouched.
    # Create a clean analytical version instead.
    df["DISTANCE_KM_CLEAN"] = (
        df["DISTANZA_KM"]
        .where(df["VALID_DISTANCE"])
    )

    # --------------------------------------------------------
    # 3. REPORTED SPEED VALIDITY
    # --------------------------------------------------------

    df["VALID_SPEED"] = (
        df["VALID_DISTANCE"]
        & df["DURATA_MIN"].notna()
        & (df["DURATA_MIN"] > 0)
        & df["SPEED_KMH"].notna()
        & (df["SPEED_KMH"] <= REPORTED_SPEED_MAX_KMH)
    )

    df["SPEED_KMH_CLEAN"] = (
        df["SPEED_KMH"]
        .where(df["VALID_SPEED"])
    )

    # --------------------------------------------------------
    # 4. HAVERSINE SPEED
    # --------------------------------------------------------

    df["HAVERSINE_SPEED_KMH"] = np.nan

    valid_duration = (
        df["DURATA_MIN"].notna()
        & (df["DURATA_MIN"] > 0)
    )

    df.loc[
        valid_duration,
        "HAVERSINE_SPEED_KMH"
    ] = (
        df.loc[
            valid_duration,
            "HAVERSINE_KM"
        ]
        /
        (
            df.loc[
                valid_duration,
                "DURATA_MIN"
            ]
            / 60
        )
    )

    # --------------------------------------------------------
    # 5. COORDINATE COMPLETENESS
    # --------------------------------------------------------

    coordinate_columns = [
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
    ]

    df["HAS_COMPLETE_COORDINATES"] = (
        df[coordinate_columns]
        .notna()
        .all(axis=1)
    )

    # --------------------------------------------------------
    # 6. CLEAR SPATIAL ERRORS
    # --------------------------------------------------------

    df["FLAG_SPATIAL_CLEAR_ERROR"] = (
        (df["HAVERSINE_KM"] > HAVERSINE_MAX_KM)
        |
        (
            df["HAVERSINE_SPEED_KMH"]
            > HAVERSINE_SPEED_CLEAR_ERROR_KMH
        )
    )

    # PREZONE because later Exercise 2 will perform
    # the definitive spatial validation using Torino polygons.
    df["VALID_SPATIAL_PREZONE"] = (
        df["HAS_COMPLETE_COORDINATES"]
        & ~df["FLAG_SPATIAL_CLEAR_ERROR"]
    )

    # --------------------------------------------------------
    # 7. REPORTED DISTANCE VS ENDPOINT GEOMETRY
    # --------------------------------------------------------

    df["HAVERSINE_TO_REPORTED_RATIO"] = np.nan

    valid_reported_distance = (
        df["DISTANZA_KM"] > 0
    )

    df.loc[
        valid_reported_distance,
        "HAVERSINE_TO_REPORTED_RATIO"
    ] = (
        df.loc[
            valid_reported_distance,
            "HAVERSINE_KM"
        ]
        /
        df.loc[
            valid_reported_distance,
            "DISTANZA_KM"
        ]
    )

    df["GEOMETRY_EXCESS_KM"] = (
        df["HAVERSINE_KM"]
        - df["DISTANZA_KM"]
    )

    # WARNING ONLY.
    # We cannot know automatically whether the GPS endpoint
    # or Bird's reported route distance is responsible.
    df["FLAG_DISTANCE_GEOMETRY_MISMATCH"] = (
        df["VALID_DISTANCE"]
        &
        (
            df["HAVERSINE_TO_REPORTED_RATIO"]
            > GEOMETRY_RATIO_WARNING
        )
        &
        (
            df["GEOMETRY_EXCESS_KM"]
            > GEOMETRY_ABSOLUTE_EXCESS_KM
        )
    )

    # --------------------------------------------------------
    # 8. INFORMATIONAL TAIL FLAGS
    # --------------------------------------------------------

    df["FLAG_LONG_DURATION_180"] = (
        df["DURATA_MIN"] > 180
    )

    df["FLAG_LONG_DISTANCE_30"] = (
        df["DISTANZA_KM"] > 30
    )

    # Explicitly retain short-displacement trips
    df["SMALL_DISPLACEMENT_RETAINED"] = (
        df["HAVERSINE_KM"] < 0.020
    )

    return df


# ============================================================
# CLEANING SUMMARY
# ============================================================

def build_summary(df, year):

    summary = {
        "year": year,

        "rows_input": len(df),

        # We deliberately retain all valid trip records
        "rows_output": len(df),

        "valid_trip_record":
            int(df["VALID_TRIP_RECORD"].sum()),

        "valid_temporal":
            int(df["VALID_TEMPORAL"].sum()),

        "dst_ambiguous_retained":
            int(df["TEMPORAL_DST_AMBIGUOUS"].sum()),

        "valid_distance":
            int(df["VALID_DISTANCE"].sum()),

        "invalid_distance":
            int((~df["VALID_DISTANCE"]).sum()),

        "valid_speed":
            int(df["VALID_SPEED"].sum()),

        "invalid_speed_for_speed_analysis":
            int((~df["VALID_SPEED"]).sum()),

        "complete_coordinates":
            int(df["HAS_COMPLETE_COORDINATES"].sum()),

        "clear_spatial_errors":
            int(df["FLAG_SPATIAL_CLEAR_ERROR"].sum()),

        "valid_spatial_prezone":
            int(df["VALID_SPATIAL_PREZONE"].sum()),

        "distance_geometry_mismatch_warning":
            int(
                df[
                    "FLAG_DISTANCE_GEOMETRY_MISMATCH"
                ].sum()
            ),

        "small_displacement_retained":
            int(
                df[
                    "SMALL_DISPLACEMENT_RETAINED"
                ].sum()
            ),

        "long_duration_over_180":
            int(df["FLAG_LONG_DURATION_180"].sum()),

        "long_distance_over_30":
            int(df["FLAG_LONG_DISTANCE_30"].sum()),
    }

    return pd.DataFrame([summary])


# ============================================================
# POST-CLEANING VALIDATION
# ============================================================

def validate_output(df, year):

    print("\nPost-cleaning validation:")

    assert len(df) > 0

    assert df["VALID_TRIP_RECORD"].all(), (
        f"{year}: at least one structurally invalid trip exists."
    )

    # Clean analytical distance must never be <= 0
    bad_clean_distance = (
        df["DISTANCE_KM_CLEAN"].notna()
        & (df["DISTANCE_KM_CLEAN"] <= 0)
    )

    assert not bad_clean_distance.any()

    # Clean speed must respect analytical threshold
    bad_clean_speed = (
        df["SPEED_KMH_CLEAN"].notna()
        & (
            df["SPEED_KMH_CLEAN"]
            > REPORTED_SPEED_MAX_KMH
        )
    )

    assert not bad_clean_speed.any()

    print("Validation checks: PASSED")


# ============================================================
# SAVE
# ============================================================

def save_cleaned(df, year):

    output = (
        CLEANED_DIR
        / f"bird_{year}_clean.parquet"
    )

    df.to_parquet(
        output,
        index=False
    )

    print(
        f"Cleaned dataset saved -> {output}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    summaries = []

    for year, path in FILES.items():

        print("\n")
        print("=" * 80)
        print(f"FINALIZING BIRD {year}")
        print("=" * 80)

        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_parquet(path)

        print(
            f"Input rows: {len(df):,}"
        )

        df = add_final_quality_fields(df)

        validate_output(df, year)

        summary = build_summary(
            df,
            year
        )

        summaries.append(summary)

        save_cleaned(
            df,
            year
        )

        print("\nCleaning summary:")
        print(
            summary
            .set_index("year")
            .T
            .to_string()
        )

    final_summary = pd.concat(
        summaries,
        ignore_index=True
    )

    summary_path = (
        AUDIT_DIR
        / "bird_final_cleaning_summary.csv"
    )

    final_summary.to_csv(
        summary_path,
        index=False
    )

    print("\n")
    print("=" * 80)
    print("BIRD CLEANING FINALIZATION COMPLETED")
    print("=" * 80)

    print(
        final_summary.to_string(
            index=False
        )
    )

    print(
        f"\nSummary saved -> {summary_path}"
    )

    print(
        "\nImportant:"
        "\nNo valid trip was globally deleted."
        "\nInvalid measurements are represented through "
        "analysis-specific validity fields."
    )


if __name__ == "__main__":
    main()