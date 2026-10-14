from pathlib import Path
import re

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "lime"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned" / "lime"
AUDIT_DIR = PROJECT_ROOT / "audit" / "lime"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. CLEANING / VALIDATION CONSTANTS
# ============================================================

# DST discrepancies in the raw local timestamps are
# approximately +/- 60 minutes.
DST_MIN_DIFFERENCE = 55
DST_MAX_DIFFERENCE = 65


# Audit showed that anomalous very-large distance values
# are represented by exactly 100 km.
#
# These trips are retained, but the reported distance
# measurement is treated as invalid.
DISTANCE_SENTINEL_VALUE = 100


# Used only for diagnostic / analytical speed validity.
# This does NOT globally remove the trip.
APPROX_SPEED_MAX_KMH = 40


# Because Lime distance is rounded to whole kilometres,
# speed estimates for extremely short trips are unstable.
MIN_DURATION_FOR_SPEED_MIN = 1.0


# Broad Torino bounding box.
#
# IMPORTANT:
# This is only a PRE-ZONE spatial validity check.
# Final spatial validation will later use the official
# Torino statistical-zone polygons.
TORINO_LAT_MIN = 44.90
TORINO_LAT_MAX = 45.20
TORINO_LON_MIN = 7.40
TORINO_LON_MAX = 7.90


# Extremely large straight-line displacement.
HAVERSINE_MAX_PREZONE_KM = 30


# ============================================================
# 3. FILE DISCOVERY
# ============================================================

def discover_files():
    """
    Discover all monthly Lime interim Parquet files.

    Expected format:
        lime_2024-01_typed_flagged.parquet
        lime_2024-02_typed_flagged.parquet
        ...
    """

    files = sorted(
        INTERIM_DIR.glob(
            "lime_*_typed_flagged.parquet"
        )
    )

    pattern = re.compile(
        r"lime_(\d{4})-(\d{2})_typed_flagged\.parquet"
    )

    discovered = []

    for path in files:

        match = pattern.fullmatch(
            path.name
        )

        if match is None:
            continue

        year = int(
            match.group(1)
        )

        month = int(
            match.group(2)
        )

        discovered.append(
            (
                year,
                month,
                path,
            )
        )

    if not discovered:
        raise FileNotFoundError(
            f"No Lime interim files found in:\n"
            f"{INTERIM_DIR}"
        )

    return discovered


# ============================================================
# 4. FINAL QUALITY FIELDS
# ============================================================

def add_final_quality_fields(df):
    """
    Add final Lime cleaning and validity variables.

    Core methodological principle:
    measurement-specific problems do not necessarily imply
    that the complete trip should be removed.
    """

    df = df.copy()


    # ========================================================
    # 4.1 DST IDENTIFICATION
    # ========================================================

    diff = (
        df["DURATION_DIFFERENCE_MIN"]
    )

    # Spring:
    # raw wall-clock elapsed time is approximately
    # 60 minutes longer than actual elapsed duration.
    df["FLAG_DST_SPRING_FORWARD"] = (
        diff.between(
            DST_MIN_DIFFERENCE,
            DST_MAX_DIFFERENCE,
            inclusive="both",
        )
    )

    # Autumn:
    # raw wall-clock elapsed time is approximately
    # 60 minutes shorter than actual elapsed duration.
    df["FLAG_DST_FALL_BACK"] = (
        diff.between(
            -DST_MAX_DIFFERENCE,
            -DST_MIN_DIFFERENCE,
            inclusive="both",
        )
    )

    df["FLAG_DST"] = (
        df["FLAG_DST_SPRING_FORWARD"]
        | df["FLAG_DST_FALL_BACK"]
    )


    # ========================================================
    # 4.2 PRECISE CLEAN DURATION
    # ========================================================

    df["DST_CORRECTION_MIN"] = 0.0

    # Spring forward:
    # remove the artificial +60 wall-clock minutes.
    df.loc[
        df["FLAG_DST_SPRING_FORWARD"],
        "DST_CORRECTION_MIN",
    ] = -60.0

    # Autumn fall back:
    # restore the missing 60 wall-clock minutes.
    df.loc[
        df["FLAG_DST_FALL_BACK"],
        "DST_CORRECTION_MIN",
    ] = 60.0


    df["DURATION_MIN_CLEAN"] = (
        df["DURATION_FROM_TIMESTAMPS_MIN"]
        + df["DST_CORRECTION_MIN"]
    )


    # Preserve the operator-reported integer-rounded value.
    df["DURATION_REPORTED_ROUNDED_MIN"] = (
        df["DURATA_MIN"]
    )

    df["FLAG_REPORTED_DURATION_ZERO"] = (
        df["DURATA_MIN"] == 0
    )


    # ========================================================
    # 4.3 ESSENTIAL TRIP STRUCTURE
    # ========================================================

    essential_columns = [
        "ID_VEICOLO",
        "START_TIME",
        "END_TIME_RAW",
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
    ]

    df["HAS_ESSENTIAL_FIELDS"] = (
        df[essential_columns]
        .notna()
        .all(axis=1)
    )


    # ========================================================
    # 4.4 ZERO / NEGATIVE ELAPSED DURATION
    # ========================================================

    df["FLAG_ZERO_ELAPSED_TRIP"] = (
        df["DURATION_MIN_CLEAN"] == 0
    )

    df["FLAG_NEGATIVE_ELAPSED_TRIP"] = (
        df["DURATION_MIN_CLEAN"] < 0
    )


    # A valid trip record must have:
    #
    # - essential structural information
    # - a valid clean duration
    # - strictly positive elapsed time
    #
    # This is one of the few criteria that causes the
    # complete record to be globally removed.
    df["VALID_TRIP_RECORD"] = (
        df["HAS_ESSENTIAL_FIELDS"]
        & df["DURATION_MIN_CLEAN"].notna()
        & (
            df["DURATION_MIN_CLEAN"] > 0
        )
    )

    df["VALID_TEMPORAL"] = (
        df["VALID_TRIP_RECORD"]
    )


    # ========================================================
    # 4.5 DISTANCE QUALITY
    # ========================================================

    # Zero is retained.
    #
    # Audit demonstrated that DISTANZA_KM is integer-rounded
    # and zero-distance trips generally have displacement
    # below approximately 0.5 km.
    df["FLAG_DISTANCE_ROUNDED_ZERO"] = (
        df["DISTANZA_KM"] == 0
    )


    # Sentinel / corrupted reported distance.
    df["FLAG_DISTANCE_SENTINEL_100"] = (
        df["DISTANZA_KM"]
        == DISTANCE_SENTINEL_VALUE
    )


    # Negative distance would also be invalid,
    # although none were found in the audit.
    df["FLAG_DISTANCE_NEGATIVE"] = (
        df["DISTANZA_KM"] < 0
    )


    df["VALID_DISTANCE"] = (
        df["DISTANZA_KM"].notna()
        & (
            df["DISTANZA_KM"] >= 0
        )
        & ~df["FLAG_DISTANCE_SENTINEL_100"]
    )


    # --------------------------------------------------------
    # CRITICAL PARQUET SCHEMA FIX
    # --------------------------------------------------------
    #
    # Force FLOAT64 consistently for every monthly chunk.
    #
    # Without this, months with no invalid distances could
    # produce int64, while months containing invalid sentinel
    # values become float64 after inserting NaN.
    #
    # That would create a monthly Arrow schema mismatch.

    df["DISTANCE_KM_CLEAN"] = (
        df["DISTANZA_KM"]
        .astype("float64")
    )

    df.loc[
        ~df["VALID_DISTANCE"],
        "DISTANCE_KM_CLEAN",
    ] = np.nan


    # ========================================================
    # 4.6 DISTANCE ROUNDING INTERVAL
    # ========================================================

    # Since DISTANZA_KM is rounded to the nearest integer,
    # the underlying operator-measured distance is expected
    # approximately within +/- 0.5 km of the reported value.

    df["DISTANCE_LOWER_BOUND_KM"] = np.nan
    df["DISTANCE_UPPER_BOUND_KM"] = np.nan


    valid_distance_mask = (
        df["VALID_DISTANCE"]
    )


    df.loc[
        valid_distance_mask,
        "DISTANCE_LOWER_BOUND_KM",
    ] = np.maximum(
        df.loc[
            valid_distance_mask,
            "DISTANZA_KM",
        ].astype("float64")
        - 0.5,
        0.0,
    )


    df.loc[
        valid_distance_mask,
        "DISTANCE_UPPER_BOUND_KM",
    ] = (
        df.loc[
            valid_distance_mask,
            "DISTANZA_KM",
        ].astype("float64")
        + 0.5
    )


    # ========================================================
    # 4.7 APPROXIMATE REPORTED SPEED
    # ========================================================

    # Lime distance is integer-rounded, therefore this speed
    # cannot be interpreted with the same precision as Bird.

    speed_input = (
        df["VALID_DISTANCE"]
        & (
            df["DISTANCE_KM_CLEAN"] > 0
        )
        & df["VALID_TEMPORAL"]
    )


    df["SPEED_KMH_APPROX"] = np.nan


    df.loc[
        speed_input,
        "SPEED_KMH_APPROX",
    ] = (
        df.loc[
            speed_input,
            "DISTANCE_KM_CLEAN",
        ]
        /
        (
            df.loc[
                speed_input,
                "DURATION_MIN_CLEAN",
            ]
            / 60
        )
    )


    # Speed validity is metric-specific.
    #
    # The complete trip is NOT globally removed when this
    # condition is false.
    df["VALID_SPEED_APPROX"] = (
        speed_input
        & (
            df["DURATION_MIN_CLEAN"]
            >= MIN_DURATION_FOR_SPEED_MIN
        )
        & (
            df["SPEED_KMH_APPROX"]
            <= APPROX_SPEED_MAX_KMH
        )
    )


    # ========================================================
    # 4.8 HAVERSINE SPEED
    # ========================================================

    df["HAVERSINE_SPEED_CLEAN_KMH"] = np.nan


    valid_haversine_speed = (
        df["VALID_TEMPORAL"]
        & df["HAVERSINE_KM"].notna()
    )


    df.loc[
        valid_haversine_speed,
        "HAVERSINE_SPEED_CLEAN_KMH",
    ] = (
        df.loc[
            valid_haversine_speed,
            "HAVERSINE_KM",
        ]
        /
        (
            df.loc[
                valid_haversine_speed,
                "DURATION_MIN_CLEAN",
            ]
            / 60
        )
    )


    # Warning only.
    #
    # This does not automatically invalidate the complete
    # spatial trip because very short temporal intervals may
    # generate unstable kinematic estimates.
    df["FLAG_KINEMATIC_INCONSISTENCY"] = (
        df["HAVERSINE_SPEED_CLEAN_KMH"]
        .notna()
        & (
            df["HAVERSINE_SPEED_CLEAN_KMH"]
            > APPROX_SPEED_MAX_KMH
        )
    )


    # ========================================================
    # 4.9 COORDINATE COMPLETENESS
    # ========================================================

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


    # ========================================================
    # 4.10 BROAD TORINO SPATIAL CHECK
    # ========================================================

    start_outside = (
        (
            df["LATITUDINE_INIZIO_CORSA"]
            < TORINO_LAT_MIN
        )
        |
        (
            df["LATITUDINE_INIZIO_CORSA"]
            > TORINO_LAT_MAX
        )
        |
        (
            df["LONGITUTIDE_INIZIO_CORSA"]
            < TORINO_LON_MIN
        )
        |
        (
            df["LONGITUTIDE_INIZIO_CORSA"]
            > TORINO_LON_MAX
        )
    )


    end_outside = (
        (
            df["LATITUDINE_FINE_CORSA"]
            < TORINO_LAT_MIN
        )
        |
        (
            df["LATITUDINE_FINE_CORSA"]
            > TORINO_LAT_MAX
        )
        |
        (
            df["LONGITUTIDE_FINE_CORSA"]
            < TORINO_LON_MIN
        )
        |
        (
            df["LONGITUTIDE_FINE_CORSA"]
            > TORINO_LON_MAX
        )
    )


    df["FLAG_OUTSIDE_TORINO_BROAD"] = (
        start_outside
        | end_outside
    )


    df["FLAG_HAVERSINE_OVER_30KM"] = (
        df["HAVERSINE_KM"].notna()
        & (
            df["HAVERSINE_KM"]
            > HAVERSINE_MAX_PREZONE_KM
        )
    )


    # PREZONE spatial validity.
    #
    # Final OD spatial validity will later use the official
    # Torino zoning polygons.
    df["VALID_SPATIAL_PREZONE"] = (
        df["HAS_COMPLETE_COORDINATES"]
        & ~df["FLAG_OUTSIDE_TORINO_BROAD"]
        & ~df["FLAG_HAVERSINE_OVER_30KM"]
    )


    # ========================================================
    # 4.11 INFORMATIONAL LONG-TRIP FLAGS
    # ========================================================
    #
    # IMPORTANT:
    # Only VALID distance measurements can be classified as
    # long-distance trips.
    #
    # The 100-km sentinel records must therefore never enter
    # these categories.

    df["FLAG_LONG_DISTANCE_20"] = (
        df["VALID_DISTANCE"]
        & (
            df["DISTANCE_KM_CLEAN"] >= 20
        )
    )

    df["FLAG_LONG_DISTANCE_30"] = (
        df["VALID_DISTANCE"]
        & (
            df["DISTANCE_KM_CLEAN"] >= 30
        )
    )


    df["FLAG_LONG_DURATION_60"] = (
        df["DURATION_MIN_CLEAN"] > 60
    )

    df["FLAG_LONG_DURATION_120"] = (
        df["DURATION_MIN_CLEAN"] > 120
    )

    df["FLAG_LONG_DURATION_180"] = (
        df["DURATION_MIN_CLEAN"] > 180
    )


    # ========================================================
    # 4.12 BATTERY VALIDITY
    # ========================================================

    df["VALID_BATTERY"] = (
        df["BATTERIA_INIZIO_CORSA"].between(
            0,
            100,
            inclusive="both",
        )
        &
        df["BATTERIA_FINE_CORSA"].between(
            0,
            100,
            inclusive="both",
        )
    )


    return df


# ============================================================
# 5. MONTH VALIDATION
# ============================================================

def validate_month(df, period):
    """
    Post-cleaning validation for each monthly chunk.

    No rows are written to the final yearly dataset until
    these checks pass.
    """

    # --------------------------------------------------------
    # 5.1 Unexplained temporal inconsistencies
    # --------------------------------------------------------

    unexplained_temporal = (
        (
            df["DURATION_DIFFERENCE_MIN"]
            .abs()
            > 1.01
        )
        &
        ~df["FLAG_DST"]
    )

    assert not unexplained_temporal.any(), (
        f"{period}: unexplained temporal inconsistencies found."
    )


    # --------------------------------------------------------
    # 5.2 Verify duration rounding logic
    #
    # After DST correction, precise duration should remain
    # within approximately +/- 0.5 minute of Lime's
    # integer-rounded duration.
    # --------------------------------------------------------

    duration_rounding_residual = (
        df["DURATION_MIN_CLEAN"]
        - df["DURATA_MIN"]
    ).abs()


    bad_rounding = (
        duration_rounding_residual
        > 0.500001
    )


    assert not bad_rounding.any(), (
        f"{period}: clean duration is inconsistent "
        f"with Lime nearest-minute rounding."
    )


    # --------------------------------------------------------
    # 5.3 Retained trips must have positive duration
    # --------------------------------------------------------

    retained = (
        df["VALID_TRIP_RECORD"]
    )


    assert (
        df.loc[
            retained,
            "DURATION_MIN_CLEAN",
        ] > 0
    ).all(), (
        f"{period}: non-positive duration survived "
        f"trip filtering."
    )


    # --------------------------------------------------------
    # 5.4 Negative distances
    # --------------------------------------------------------

    assert not (
        df["DISTANZA_KM"] < 0
    ).any(), (
        f"{period}: negative distance found."
    )


    # --------------------------------------------------------
    # 5.5 Sentinel distances must not enter clean distance
    # --------------------------------------------------------

    sentinel = (
        df["FLAG_DISTANCE_SENTINEL_100"]
    )


    assert (
        df.loc[
            sentinel,
            "DISTANCE_KM_CLEAN",
        ]
        .isna()
        .all()
    ), (
        f"{period}: sentinel distance entered "
        f"DISTANCE_KM_CLEAN."
    )


    # --------------------------------------------------------
    # 5.6 Zero reported distances remain legitimate
    # --------------------------------------------------------

    zero_distance = (
        df["FLAG_DISTANCE_ROUNDED_ZERO"]
        & df["VALID_DISTANCE"]
    )


    assert (
        df.loc[
            zero_distance,
            "DISTANCE_KM_CLEAN",
        ] == 0
    ).all(), (
        f"{period}: rounded zero-distance handling failed."
    )


    # --------------------------------------------------------
    # 5.7 Sentinel distances must NEVER be classified as
    #     genuine long-distance trips
    # --------------------------------------------------------

    sentinel_classified_as_long = (
        df["FLAG_DISTANCE_SENTINEL_100"]
        &
        (
            df["FLAG_LONG_DISTANCE_20"]
            | df["FLAG_LONG_DISTANCE_30"]
        )
    )


    assert not sentinel_classified_as_long.any(), (
        f"{period}: 100-km sentinel incorrectly entered "
        f"long-distance trip flags."
    )


    # --------------------------------------------------------
    # 5.8 Long-distance flags must require valid distance
    # --------------------------------------------------------

    invalid_distance_long_trip = (
        ~df["VALID_DISTANCE"]
        &
        (
            df["FLAG_LONG_DISTANCE_20"]
            | df["FLAG_LONG_DISTANCE_30"]
        )
    )


    assert not invalid_distance_long_trip.any(), (
        f"{period}: invalid distance measurement entered "
        f"long-distance classification."
    )


    print(
        "Validation checks: PASSED"
    )


# ============================================================
# 6. MONTHLY CLEANING SUMMARY
# ============================================================

def build_month_summary(
    df,
    period,
    rows_output,
):

    return {
        "period":
            period,

        "year":
            int(period[:4]),

        "rows_input":
            len(df),

        "rows_output":
            rows_output,

        "rows_removed":
            len(df) - rows_output,

        "removed_zero_elapsed":
            int(
                df[
                    "FLAG_ZERO_ELAPSED_TRIP"
                ].sum()
            ),

        "removed_negative_elapsed":
            int(
                df[
                    "FLAG_NEGATIVE_ELAPSED_TRIP"
                ].sum()
            ),

        "dst_corrected":
            int(
                df[
                    "FLAG_DST"
                ].sum()
            ),

        "reported_duration_zero_retained":
            int(
                (
                    df["FLAG_REPORTED_DURATION_ZERO"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "reported_distance_zero_retained":
            int(
                (
                    df["FLAG_DISTANCE_ROUNDED_ZERO"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "distance_sentinel_100":
            int(
                df[
                    "FLAG_DISTANCE_SENTINEL_100"
                ].sum()
            ),

        "valid_distance":
            int(
                (
                    df["VALID_DISTANCE"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "valid_speed_approx":
            int(
                (
                    df["VALID_SPEED_APPROX"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "kinematic_warning":
            int(
                (
                    df["FLAG_KINEMATIC_INCONSISTENCY"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "valid_spatial_prezone":
            int(
                (
                    df["VALID_SPATIAL_PREZONE"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "outside_torino_broad":
            int(
                (
                    df["FLAG_OUTSIDE_TORINO_BROAD"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "haversine_over_30km":
            int(
                (
                    df["FLAG_HAVERSINE_OVER_30KM"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "long_distance_ge20":
            int(
                (
                    df["FLAG_LONG_DISTANCE_20"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "long_distance_ge30":
            int(
                (
                    df["FLAG_LONG_DISTANCE_30"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "long_duration_gt60":
            int(
                (
                    df["FLAG_LONG_DURATION_60"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "long_duration_gt120":
            int(
                (
                    df["FLAG_LONG_DURATION_120"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),

        "long_duration_gt180":
            int(
                (
                    df["FLAG_LONG_DURATION_180"]
                    & df["VALID_TRIP_RECORD"]
                ).sum()
            ),
    }


# ============================================================
# 7. SCHEMA COMPARISON HELPER
# ============================================================

def get_schema_differences(
    expected_schema,
    actual_schema,
):
    """
    Return human-readable differences between Arrow schemas.
    """

    expected = {
        field.name: field.type
        for field in expected_schema
    }

    actual = {
        field.name: field.type
        for field in actual_schema
    }

    differences = []

    expected_names = set(
        expected.keys()
    )

    actual_names = set(
        actual.keys()
    )


    missing_columns = (
        expected_names
        - actual_names
    )

    extra_columns = (
        actual_names
        - expected_names
    )


    for column in sorted(
        missing_columns
    ):

        differences.append(
            f"{column}: missing from current month"
        )


    for column in sorted(
        extra_columns
    ):

        differences.append(
            f"{column}: unexpected column "
            f"({actual[column]})"
        )


    common_columns = (
        expected_names
        & actual_names
    )


    for column in sorted(
        common_columns
    ):

        if (
            expected[column]
            != actual[column]
        ):

            differences.append(
                f"{column}: "
                f"expected={expected[column]}, "
                f"actual={actual[column]}"
            )


    return differences


# ============================================================
# 8. PROCESS ONE YEAR
# ============================================================

def process_year(
    year,
    year_files,
):

    print("\n")
    print("=" * 90)
    print(
        f"FINALIZING LIME {year}"
    )
    print("=" * 90)


    output_path = (
        CLEANED_DIR
        / f"lime_{year}_clean.parquet"
    )


    # Remove any partial output generated by an earlier failed
    # execution.
    if output_path.exists():

        output_path.unlink()

        print(
            f"Removed previous partial file -> "
            f"{output_path}"
        )


    writer = None

    canonical_schema = None

    month_summaries = []

    invalid_trip_rows = []

    sentinel_rows = []

    kinematic_rows = []


    try:

        for (
            year_,
            month,
            path,
        ) in year_files:

            period = (
                f"{year_}-{month:02d}"
            )


            print("\n")
            print("-" * 70)
            print(
                f"Processing {period}..."
            )
            print("-" * 70)


            # =================================================
            # LOAD MONTH
            # =================================================

            df = pd.read_parquet(
                path
            )


            print(
                f"Input rows: {len(df):,}"
            )


            # =================================================
            # ADD FINAL CLEANING VARIABLES
            # =================================================

            df = add_final_quality_fields(
                df
            )


            # =================================================
            # VALIDATE
            # =================================================

            validate_month(
                df,
                period,
            )


            # =================================================
            # AUDIT SUBSETS BEFORE FILTERING
            # =================================================

            invalid_trip_rows.append(

                df.loc[
                    ~df["VALID_TRIP_RECORD"]
                ].copy()

            )


            sentinel_rows.append(

                df.loc[
                    df[
                        "FLAG_DISTANCE_SENTINEL_100"
                    ]
                ].copy()

            )


            kinematic_rows.append(

                df.loc[
                    df[
                        "FLAG_KINEMATIC_INCONSISTENCY"
                    ]
                ].copy()

            )


            # =================================================
            # FINAL CANONICAL CLEAN DATA
            # =================================================

            # Only records that cannot represent a positive
            # elapsed trip are globally removed.
            #
            # Measurement-specific anomalies remain available
            # through validity flags.

            clean = (
                df.loc[
                    df["VALID_TRIP_RECORD"]
                ]
                .copy()
            )


            rows_output = (
                len(clean)
            )


            # =================================================
            # MONTHLY SUMMARY
            # =================================================

            month_summary = (
                build_month_summary(
                    df=df,
                    period=period,
                    rows_output=rows_output,
                )
            )


            month_summaries.append(
                month_summary
            )


            # =================================================
            # CONVERT TO ARROW
            # =================================================

            table = (
                pa.Table.from_pandas(
                    clean,
                    preserve_index=False,
                )
            )


            # Remove pandas metadata from the Arrow schema.
            #
            # The dataset does not need pandas index metadata,
            # and removing it makes multi-month schema handling
            # more robust.
            table = (
                table.replace_schema_metadata(
                    None
                )
            )


            # =================================================
            # CREATE YEARLY PARQUET WRITER
            # =================================================

            if writer is None:

                canonical_schema = (
                    table.schema
                )

                writer = (
                    pq.ParquetWriter(
                        output_path,
                        canonical_schema,
                        compression="snappy",
                    )
                )

                print(
                    "Canonical yearly Parquet schema "
                    "established."
                )


            else:

                # Compare field names and Arrow types.
                differences = (
                    get_schema_differences(
                        expected_schema=canonical_schema,
                        actual_schema=table.schema,
                    )
                )


                if differences:

                    raise TypeError(
                        f"\n{period}: monthly schema "
                        f"mismatch detected:\n"
                        + "\n".join(
                            differences
                        )
                    )


            # =================================================
            # WRITE MONTH INTO YEARLY PARQUET
            # =================================================

            writer.write_table(
                table
            )


            # =================================================
            # TERMINAL SUMMARY
            # =================================================

            print(
                f"{period}: "
                f"input={len(df):,} | "
                f"output={rows_output:,} | "
                f"removed={len(df)-rows_output:,} | "
                f"DST={int(df['FLAG_DST'].sum()):,} | "
                f"dist0 retained="
                f"{int((df['FLAG_DISTANCE_ROUNDED_ZERO'] & df['VALID_TRIP_RECORD']).sum()):,} | "
                f"dist100="
                f"{int(df['FLAG_DISTANCE_SENTINEL_100'].sum()):,} | "
                f"kinematic warnings="
                f"{int((df['FLAG_KINEMATIC_INCONSISTENCY'] & df['VALID_TRIP_RECORD']).sum()):,}"
            )


    finally:

        # Ensure a valid Parquet footer is always written
        # whenever the writer has been created.
        if writer is not None:

            writer.close()


    # ========================================================
    # 8.1 COMBINE YEARLY AUDIT SUBSETS
    # ========================================================

    invalid = pd.concat(
        invalid_trip_rows,
        ignore_index=True,
    )


    sentinel = pd.concat(
        sentinel_rows,
        ignore_index=True,
    )


    kinematic = pd.concat(
        kinematic_rows,
        ignore_index=True,
    )


    # ========================================================
    # 8.2 SAVE REMOVED TRIPS
    # ========================================================

    invalid_path = (
        AUDIT_DIR
        / f"lime_{year}_removed_invalid_trip_records.csv"
    )


    invalid.to_csv(
        invalid_path,
        index=False,
    )


    # ========================================================
    # 8.3 SAVE DISTANCE SENTINELS
    # ========================================================

    sentinel_path = (
        AUDIT_DIR
        / f"lime_{year}_distance_100_records.csv"
    )


    sentinel.to_csv(
        sentinel_path,
        index=False,
    )


    # ========================================================
    # 8.4 SAVE KINEMATIC WARNINGS
    # ========================================================

    kinematic_path = (
        AUDIT_DIR
        / f"lime_{year}_kinematic_warnings.csv"
    )


    kinematic.to_csv(
        kinematic_path,
        index=False,
    )


    # ========================================================
    # 8.5 MONTHLY FINAL SUMMARY
    # ========================================================

    summary = pd.DataFrame(
        month_summaries
    )


    monthly_summary_path = (
        AUDIT_DIR
        / f"lime_{year}_final_monthly_summary.csv"
    )


    summary.to_csv(
        monthly_summary_path,
        index=False,
    )


    print("\n")

    print(
        f"Cleaned dataset saved -> "
        f"{output_path}"
    )

    print(
        f"Removed trip audit -> "
        f"{invalid_path}"
    )

    print(
        f"Distance sentinel audit -> "
        f"{sentinel_path}"
    )

    print(
        f"Kinematic warning audit -> "
        f"{kinematic_path}"
    )


    return summary


# ============================================================
# 9. MAIN PIPELINE
# ============================================================

def main():

    discovered = (
        discover_files()
    )


    print(
        f"Discovered "
        f"{len(discovered)} Lime interim files."
    )


    years = sorted(
        {
            year
            for (
                year,
                _,
                _,
            ) in discovered
        }
    )


    all_summaries = []


    for year in years:

        year_files = [
            item
            for item in discovered
            if item[0] == year
        ]


        # Ensure strict chronological month order.
        year_files = sorted(
            year_files,
            key=lambda x: x[1],
        )


        summary = (
            process_year(
                year=year,
                year_files=year_files,
            )
        )


        all_summaries.append(
            summary
        )


    # ========================================================
    # 9.1 COMBINE ALL MONTHLY SUMMARIES
    # ========================================================

    monthly = pd.concat(
        all_summaries,
        ignore_index=True,
    )


    all_monthly_path = (
        AUDIT_DIR
        / "lime_final_monthly_cleaning_summary.csv"
    )


    monthly.to_csv(
        all_monthly_path,
        index=False,
    )


    # ========================================================
    # 9.2 YEARLY SUMMARY
    # ========================================================

    numeric_columns = [
        column
        for column in monthly.columns
        if column not in [
            "period",
            "year",
        ]
    ]


    yearly = (
        monthly
        .groupby(
            "year"
        )[
            numeric_columns
        ]
        .sum()
        .reset_index()
    )


    yearly_path = (
        AUDIT_DIR
        / "lime_final_cleaning_summary.csv"
    )


    yearly.to_csv(
        yearly_path,
        index=False,
    )


    # ========================================================
    # 9.3 FINAL OUTPUT
    # ========================================================

    print("\n")
    print("=" * 100)
    print(
        "LIME CLEANING FINALIZATION COMPLETED"
    )
    print("=" * 100)


    print(
        yearly.to_string(
            index=False
        )
    )


    print(
        f"\nMonthly summary saved -> "
        f"{all_monthly_path}"
    )

    print(
        f"Final yearly summary saved -> "
        f"{yearly_path}"
    )


    print(
        "\nCleaning policy applied:"
    )

    print(
        "- Exact zero/negative elapsed non-trips "
        "were removed."
    )

    print(
        "- Lime's rounded zero-duration values were "
        "retained when precise timestamp duration "
        "was positive."
    )

    print(
        "- Lime's rounded zero-distance trips were retained."
    )

    print(
        "- DST elapsed durations were corrected."
    )

    print(
        "- 100-km sentinel distance measurements were "
        "invalidated for distance analysis, while the "
        "underlying trips were retained."
    )

    print(
        "- Long-distance flags use only valid distance "
        "measurements; 100-km sentinel values are excluded."
    )

    print(
        "- Kinematic inconsistencies were flagged rather "
        "than globally removed."
    )

    print(
        "- Spatial validity remains PREZONE until official "
        "Torino statistical zoning is applied."
    )


# ============================================================
# 10. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()