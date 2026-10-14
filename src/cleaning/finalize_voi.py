from pathlib import Path
import re

import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "voi"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned" / "voi"
AUDIT_DIR = PROJECT_ROOT / "audit" / "voi"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. CONSTANTS
# ============================================================

TRIP_ID = "Identificativo noleggio"

SPEED_WARNING_KMH = 40
HAVERSINE_MAX_PREZONE_KM = 30

# Broad Torino bounding box.
# This is NOT the final official spatial zoning validation.
TORINO_LAT_MIN = 44.90
TORINO_LAT_MAX = 45.20
TORINO_LON_MIN = 7.40
TORINO_LON_MAX = 7.90


# These fields define the physical/logical trip.
# Prenotazione is intentionally excluded because audit showed
# that some duplicate trip IDs differ only in Prenotazione.
TRIP_DEFINING_COLUMNS = [
    "Targa veicolo",
    "Data inizio corsa",
    "Data fine corsa",
    "Lat inizio corsa_coordinate",
    "Lon inizio corsa_coordinate",
    "Lat fine corsa_coordinate",
    "Lon fine corsa_coordinate",
    "Tempo Tot",
    "KM Tot",
    "Batteria inizio",
    "Batteria fine",
]


# ============================================================
# 3. FILE DISCOVERY
# ============================================================

def discover_files():

    files = sorted(
        INTERIM_DIR.glob(
            "voi_*_typed_flagged.parquet"
        )
    )

    pattern = re.compile(
        r"voi_(\d{4}-\d{2})_typed_flagged\.parquet"
    )

    discovered = []

    for path in files:

        match = pattern.fullmatch(
            path.name
        )

        if match:

            discovered.append(
                (
                    match.group(1),
                    path
                )
            )

    if not discovered:

        raise FileNotFoundError(
            f"No VOI interim files found in:\n"
            f"{INTERIM_DIR}"
        )

    print(
        f"Discovered {len(discovered)} VOI interim files."
    )

    return discovered


# ============================================================
# 4. LOAD ALL MONTHLY INTERIM FILES
# ============================================================

def load_all():

    parts = []

    for period, path in discover_files():

        df = pd.read_parquet(
            path
        )

        parts.append(
            df
        )

    combined = pd.concat(
        parts,
        ignore_index=True
    )

    return combined


# ============================================================
# 5. RESERVATION NORMALIZATION
# ============================================================

def normalize_reservation_value(value):

    if pd.isna(value):
        return pd.NA

    text = (
        str(value)
        .strip()
        .lower()
    )

    if text in {
        "sì",
        "si",
        "yes",
        "y",
        "1",
        "true",
    }:
        return "Sì"

    if text in {
        "no",
        "n",
        "0",
        "false",
    }:
        return "No"

    return str(value).strip()


def reservation_values_string(series):

    normalized = (
        series
        .map(
            normalize_reservation_value
        )
        .astype("string")
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return "|".join(
        normalized
    )


# ============================================================
# 6. DEDUPLICATION
# ============================================================

def build_canonical_trips(df):

    print(
        "\nChecking duplicate consistency..."
    )

    # --------------------------------------------------------
    # Verify that duplicate trip IDs do not disagree in
    # trip-defining fields.
    # --------------------------------------------------------

    defining_variants = (
        df[
            [TRIP_ID]
            + TRIP_DEFINING_COLUMNS
        ]
        .drop_duplicates()
        .groupby(
            TRIP_ID
        )
        .size()
    )

    conflicting = (
        defining_variants > 1
    )

    if conflicting.any():

        bad_ids = (
            conflicting[
                conflicting
            ]
            .index
            .tolist()
        )

        raise ValueError(
            f"Trip-defining conflicts found for "
            f"{len(bad_ids):,} trip IDs."
        )

    print(
        "Trip-defining duplicate consistency: PASSED"
    )

    # --------------------------------------------------------
    # Duplicate-group size
    # --------------------------------------------------------

    group_size = (
        df.groupby(
            TRIP_ID
        )
        .size()
        .rename(
            "DUPLICATE_GROUP_SIZE"
        )
    )

    # --------------------------------------------------------
    # Prenotazione metadata
    # --------------------------------------------------------

    reservation_metadata = (
        df.groupby(
            TRIP_ID
        )[
            "Prenotazione"
        ]
        .agg(
            PRENOTAZIONE_VALUES=
                reservation_values_string,

            PRENOTAZIONE_VARIANTS=
                lambda x:
                x.map(
                    normalize_reservation_value
                )
                .astype("string")
                .dropna()
                .nunique()
        )
    )

    reservation_metadata[
        "PRENOTAZIONE_CONFLICT"
    ] = (
        reservation_metadata[
            "PRENOTAZIONE_VARIANTS"
        ] > 1
    )

    # --------------------------------------------------------
    # Canonical representative:
    # one row per Identificativo noleggio
    # --------------------------------------------------------

    canonical = (
        df.sort_values(
            [
                "SOURCE_PERIOD",
                "SOURCE_ROW",
            ]
        )
        .drop_duplicates(
            subset=[
                TRIP_ID
            ],
            keep="first"
        )
        .copy()
    )

    canonical = canonical.merge(
        group_size,
        left_on=TRIP_ID,
        right_index=True,
        how="left",
    )

    canonical = canonical.merge(
        reservation_metadata,
        left_on=TRIP_ID,
        right_index=True,
        how="left",
    )

    canonical[
        "DUPLICATE_ROWS_COLLAPSED"
    ] = (
        canonical[
            "DUPLICATE_GROUP_SIZE"
        ] - 1
    )

    # --------------------------------------------------------
    # Clean reservation value
    # --------------------------------------------------------

    canonical[
        "PRENOTAZIONE_CLEAN"
    ] = (
        canonical[
            "Prenotazione"
        ]
        .map(
            normalize_reservation_value
        )
        .astype("string")
    )

    # Do not arbitrarily resolve conflicting reservation values.
    canonical.loc[
        canonical[
            "PRENOTAZIONE_CONFLICT"
        ],
        "PRENOTAZIONE_CLEAN"
    ] = pd.NA

    return canonical


# ============================================================
# 7. TEMPORAL FIELDS
# ============================================================

def add_temporal_fields(df):

    df = df.copy()

    # --------------------------------------------------------
    # VOI raw timestamps were empirically shown to be UTC.
    #
    # January 2024 malformed timestamps remain NaT because
    # day/hour/minute information is absent from the source.
    # --------------------------------------------------------

    df[
        "START_TIME_UTC"
    ] = pd.to_datetime(
        df[
            "START_TIME_RAW"
        ],
        errors="coerce",
        utc=True,
    )

    df[
        "END_TIME_UTC"
    ] = pd.to_datetime(
        df[
            "END_TIME_RAW"
        ],
        errors="coerce",
        utc=True,
    )

    # --------------------------------------------------------
    # Convert UTC to Torino local time
    # --------------------------------------------------------

    df[
        "START_TIME_LOCAL"
    ] = (
        df[
            "START_TIME_UTC"
        ]
        .dt.tz_convert(
            "Europe/Rome"
        )
        .dt.tz_localize(
            None
        )
    )

    df[
        "END_TIME_LOCAL"
    ] = (
        df[
            "END_TIME_UTC"
        ]
        .dt.tz_convert(
            "Europe/Rome"
        )
        .dt.tz_localize(
            None
        )
    )

    # --------------------------------------------------------
    # Temporal-detail availability
    # --------------------------------------------------------

    df[
        "HAS_TEMPORAL_DETAIL"
    ] = (
        df[
            "START_TIME_UTC"
        ].notna()
        &
        df[
            "END_TIME_UTC"
        ].notna()
    )

    df[
        "FLAG_TEMPORAL_DETAIL_UNAVAILABLE"
    ] = (
        ~df[
            "HAS_TEMPORAL_DETAIL"
        ]
    )

    df[
        "FLAG_JAN2024_TEMPORAL_DAMAGE"
    ] = (
        (
            df[
                "SOURCE_PERIOD"
            ] == "2024-01"
        )
        &
        df[
            "FLAG_TEMPORAL_DETAIL_UNAVAILABLE"
        ]
    )

    # --------------------------------------------------------
    # Duration computed from UTC timestamps
    # --------------------------------------------------------

    df[
        "DURATION_FROM_UTC_MIN"
    ] = (
        df[
            "END_TIME_UTC"
        ]
        -
        df[
            "START_TIME_UTC"
        ]
    ).dt.total_seconds() / 60

    # --------------------------------------------------------
    # Final clean duration
    #
    # Priority:
    # 1. positive UTC timestamp duration
    # 2. positive provider Tempo Tot
    #
    # Provider fallback is necessary for January 2024.
    # --------------------------------------------------------

    df[
        "DURATION_MIN_CLEAN"
    ] = np.nan

    df[
        "DURATION_SOURCE"
    ] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="string",
    )

    valid_utc_duration = (
        df[
            "DURATION_FROM_UTC_MIN"
        ].notna()
        &
        (
            df[
                "DURATION_FROM_UTC_MIN"
            ] > 0
        )
    )

    df.loc[
        valid_utc_duration,
        "DURATION_MIN_CLEAN"
    ] = (
        df.loc[
            valid_utc_duration,
            "DURATION_FROM_UTC_MIN"
        ]
    )

    df.loc[
        valid_utc_duration,
        "DURATION_SOURCE"
    ] = (
        "utc_timestamp"
    )

    provider_fallback = (
        ~valid_utc_duration
        &
        df[
            "Tempo Tot"
        ].notna()
        &
        (
            df[
                "Tempo Tot"
            ] > 0
        )
    )

    df.loc[
        provider_fallback,
        "DURATION_MIN_CLEAN"
    ] = (
        df.loc[
            provider_fallback,
            "Tempo Tot"
        ]
    )

    df.loc[
        provider_fallback,
        "DURATION_SOURCE"
    ] = (
        "provider_tempo_tot"
    )

    df[
        "FLAG_DURATION_PROVIDER_FALLBACK"
    ] = (
        provider_fallback
    )

    df[
        "VALID_DURATION"
    ] = (
        df[
            "DURATION_MIN_CLEAN"
        ].notna()
        &
        (
            df[
                "DURATION_MIN_CLEAN"
            ] > 0
        )
    )

    df[
        "FLAG_INVALID_DURATION"
    ] = (
        ~df[
            "VALID_DURATION"
        ]
    )

    # Even January 2024 has a reliable month label
    # from the source file.
    df[
        "VALID_MONTHLY_PERIOD"
    ] = (
        df[
            "SOURCE_PERIOD"
        ].notna()
    )

    return df


# ============================================================
# 8. SPATIAL FIELDS
# ============================================================

def add_spatial_fields(df):

    df = df.copy()

    coordinate_columns = [
        "Lat inizio corsa_coordinate",
        "Lon inizio corsa_coordinate",
        "Lat fine corsa_coordinate",
        "Lon fine corsa_coordinate",
    ]

    df[
        "HAS_COMPLETE_COORDINATES"
    ] = (
        df[
            coordinate_columns
        ]
        .notna()
        .all(
            axis=1
        )
    )

    # --------------------------------------------------------
    # Broad Torino check
    # --------------------------------------------------------

    start_outside = (
        (
            df[
                "Lat inizio corsa_coordinate"
            ] < TORINO_LAT_MIN
        )
        |
        (
            df[
                "Lat inizio corsa_coordinate"
            ] > TORINO_LAT_MAX
        )
        |
        (
            df[
                "Lon inizio corsa_coordinate"
            ] < TORINO_LON_MIN
        )
        |
        (
            df[
                "Lon inizio corsa_coordinate"
            ] > TORINO_LON_MAX
        )
    )

    end_outside = (
        (
            df[
                "Lat fine corsa_coordinate"
            ] < TORINO_LAT_MIN
        )
        |
        (
            df[
                "Lat fine corsa_coordinate"
            ] > TORINO_LAT_MAX
        )
        |
        (
            df[
                "Lon fine corsa_coordinate"
            ] < TORINO_LON_MIN
        )
        |
        (
            df[
                "Lon fine corsa_coordinate"
            ] > TORINO_LON_MAX
        )
    )

    df[
        "FLAG_OUTSIDE_TORINO_BROAD"
    ] = (
        start_outside
        |
        end_outside
    )

    df[
        "FLAG_HAVERSINE_OVER_30KM"
    ] = (
        df[
            "HAVERSINE_KM"
        ].notna()
        &
        (
            df[
                "HAVERSINE_KM"
            ]
            > HAVERSINE_MAX_PREZONE_KM
        )
    )

    # --------------------------------------------------------
    # Preliminary spatial validity.
    # Final validity will later use official Torino zoning.
    # --------------------------------------------------------

    df[
        "VALID_SPATIAL_PREZONE"
    ] = (
        df[
            "HAS_COMPLETE_COORDINATES"
        ]
        &
        ~df[
            "FLAG_OUTSIDE_TORINO_BROAD"
        ]
        &
        ~df[
            "FLAG_HAVERSINE_OVER_30KM"
        ]
    )

    return df


# ============================================================
# 9. DISTANCE / SPEED FIELDS
# ============================================================

def add_distance_speed_fields(df):

    df = df.copy()

    # --------------------------------------------------------
    # Methodological metadata
    #
    # Audit showed that KM Tot is virtually identical to
    # Haversine start-end displacement.
    #
    # Therefore it is NOT interpreted as travelled route
    # length.
    # --------------------------------------------------------

    df[
        "DISTANCE_MEASURE_TYPE"
    ] = (
        "endpoint_displacement"
    )

    # --------------------------------------------------------
    # Zero displacement
    # --------------------------------------------------------

    df[
        "FLAG_ZERO_DISPLACEMENT"
    ] = (
        df[
            "KM Tot"
        ].notna()
        &
        (
            df[
                "KM Tot"
            ] == 0
        )
    )

    # --------------------------------------------------------
    # Distance validity
    #
    # Zero is retained.
    # Spatially invalid endpoints cannot produce valid
    # displacement measurements.
    # --------------------------------------------------------

    df[
        "VALID_DISTANCE"
    ] = (
        df[
            "KM Tot"
        ].notna()
        &
        (
            df[
                "KM Tot"
            ] >= 0
        )
        &
        df[
            "VALID_SPATIAL_PREZONE"
        ]
    )

    df[
        "DISTANCE_KM_CLEAN"
    ] = (
        df[
            "KM Tot"
        ]
        .where(
            df[
                "VALID_DISTANCE"
            ]
        )
    )

    # --------------------------------------------------------
    # Displacement-based speed
    # --------------------------------------------------------

    speed_input = (
        df[
            "VALID_DISTANCE"
        ]
        &
        df[
            "VALID_DURATION"
        ]
    )

    df[
        "SPEED_KMH_CLEAN"
    ] = np.nan

    df.loc[
        speed_input,
        "SPEED_KMH_CLEAN"
    ] = (
        df.loc[
            speed_input,
            "DISTANCE_KM_CLEAN"
        ]
        /
        (
            df.loc[
                speed_input,
                "DURATION_MIN_CLEAN"
            ]
            / 60
        )
    )

    # --------------------------------------------------------
    # Kinematic warning
    # --------------------------------------------------------

    df[
        "FLAG_KINEMATIC_WARNING"
    ] = (
        df[
            "SPEED_KMH_CLEAN"
        ].notna()
        &
        (
            df[
                "SPEED_KMH_CLEAN"
            ] > SPEED_WARNING_KMH
        )
    )

    df[
        "VALID_SPEED"
    ] = (
        df[
            "SPEED_KMH_CLEAN"
        ].notna()
        &
        ~df[
            "FLAG_KINEMATIC_WARNING"
        ]
    )

    # --------------------------------------------------------
    # Informational duration tails
    # --------------------------------------------------------

    df[
        "FLAG_LONG_DURATION_60"
    ] = (
        df[
            "VALID_DURATION"
        ]
        &
        (
            df[
                "DURATION_MIN_CLEAN"
            ] > 60
        )
    )

    df[
        "FLAG_LONG_DURATION_120"
    ] = (
        df[
            "VALID_DURATION"
        ]
        &
        (
            df[
                "DURATION_MIN_CLEAN"
            ] > 120
        )
    )

    df[
        "FLAG_LONG_DURATION_180"
    ] = (
        df[
            "VALID_DURATION"
        ]
        &
        (
            df[
                "DURATION_MIN_CLEAN"
            ] > 180
        )
    )

    # --------------------------------------------------------
    # Long displacement flag
    # --------------------------------------------------------

    df[
        "FLAG_LONG_DISPLACEMENT_20"
    ] = (
        df[
            "VALID_DISTANCE"
        ]
        &
        (
            df[
                "DISTANCE_KM_CLEAN"
            ] > 20
        )
    )

    return df


# ============================================================
# 10. BATTERY VALIDITY
# ============================================================

def add_battery_fields(df):

    df = df.copy()

    df[
        "VALID_BATTERY"
    ] = (
        df[
            "Batteria inizio"
        ].notna()
        &
        df[
            "Batteria fine"
        ].notna()
        &
        df[
            "Batteria inizio"
        ].between(
            0,
            100,
            inclusive="both"
        )
        &
        df[
            "Batteria fine"
        ].between(
            0,
            100,
            inclusive="both"
        )
    )

    return df


# ============================================================
# 11. CORE TRIP RECORD VALIDITY
# ============================================================

def add_core_validity(df):

    df = df.copy()

    df[
        "VALID_TRIP_RECORD"
    ] = (
        df[
            TRIP_ID
        ].notna()
        &
        df[
            "Targa veicolo"
        ].notna()
    )

    return df


# ============================================================
# 12. PARQUET DTYPE STABILIZATION
#
# IMPORTANT:
# This function is TOP-LEVEL, not inside main().
#
# Some VOI Excel files store raw timestamps as integers while
# others store them as strings. Pandas therefore may preserve
# some columns as object dtype.
#
# PyArrow cannot safely serialize mixed int/string object
# columns. Object columns are therefore standardized to pandas
# StringDtype before writing Parquet.
# ============================================================

def stabilize_parquet_dtypes(df):

    df = df.copy()

    # Convert every remaining Python-object column to a stable
    # pandas string dtype.
    #
    # Numeric, datetime, timezone-aware datetime and boolean
    # columns are left untouched.
    for col in df.columns:

        if pd.api.types.is_object_dtype(
            df[col].dtype
        ):

            df[col] = (
                df[col]
                .astype("string")
            )

    # Explicitly guarantee known identifier/raw-text columns
    # are strings even if pandas inferred another extension
    # dtype.
    explicit_string_columns = [
        "Data inizio corsa",
        "Data fine corsa",
        "START_TIMESTAMP_CODE",
        "END_TIMESTAMP_CODE",
        "SOURCE_PERIOD",
        "SOURCE_FILE",
        "Identificativo noleggio",
        "Targa veicolo",
        "Prenotazione",
        "PRENOTAZIONE_VALUES",
        "PRENOTAZIONE_CLEAN",
        "DURATION_SOURCE",
        "DISTANCE_MEASURE_TYPE",
    ]

    for col in explicit_string_columns:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype("string")
            )

    return df


# ============================================================
# 13. FINAL VALIDATION
# ============================================================

def validate_final(df):

    print(
        "\nPost-cleaning validation:"
    )

    # --------------------------------------------------------
    # One canonical record per trip
    # --------------------------------------------------------

    assert df[
        TRIP_ID
    ].is_unique, (
        "Trip IDs are not unique after canonicalization."
    )

    # --------------------------------------------------------
    # Core identifiers
    # --------------------------------------------------------

    assert df[
        "VALID_TRIP_RECORD"
    ].all(), (
        "At least one canonical trip lacks a core identifier."
    )

    # --------------------------------------------------------
    # Timezone validation
    #
    # Every parsed UTC timestamp should fall into its source
    # month after conversion to Europe/Rome.
    # --------------------------------------------------------

    temporal = df.loc[
        df[
            "START_TIME_LOCAL"
        ].notna()
    ].copy()

    local_period = (
        temporal[
            "START_TIME_LOCAL"
        ]
        .dt.to_period("M")
        .astype(str)
    )

    expected_period = (
        temporal[
            "SOURCE_PERIOD"
        ]
        .astype(str)
    )

    assert (
        local_period.values
        ==
        expected_period.values
    ).all(), (
        "UTC -> Europe/Rome month validation failed."
    )

    # --------------------------------------------------------
    # Provider duration vs timestamp-derived duration
    # --------------------------------------------------------

    comparable = (
        df[
            "DURATION_FROM_UTC_MIN"
        ].notna()
        &
        df[
            "Tempo Tot"
        ].notna()
    )

    temporal_difference = (
        df.loc[
            comparable,
            "DURATION_FROM_UTC_MIN"
        ]
        -
        df.loc[
            comparable,
            "Tempo Tot"
        ]
    ).abs()

    assert (
        temporal_difference
        <= 1.01
    ).all(), (
        "Temporal discrepancy greater than 1 minute found."
    )

    # --------------------------------------------------------
    # Clean duration
    # --------------------------------------------------------

    assert (
        df.loc[
            df[
                "VALID_DURATION"
            ],
            "DURATION_MIN_CLEAN"
        ] > 0
    ).all(), (
        "A valid clean duration is non-positive."
    )

    # --------------------------------------------------------
    # Clean distance
    # --------------------------------------------------------

    assert (
        df.loc[
            df[
                "VALID_DISTANCE"
            ],
            "DISTANCE_KM_CLEAN"
        ] >= 0
    ).all(), (
        "A valid clean distance is negative."
    )

    # --------------------------------------------------------
    # Invalid spatial measurements cannot be valid distance
    # --------------------------------------------------------

    assert not (
        (
            ~df[
                "VALID_SPATIAL_PREZONE"
            ]
        )
        &
        df[
            "VALID_DISTANCE"
        ]
    ).any(), (
        "Spatially invalid record classified as valid distance."
    )

    # --------------------------------------------------------
    # Valid clean speed must satisfy threshold
    # --------------------------------------------------------

    assert (
        df.loc[
            df[
                "VALID_SPEED"
            ],
            "SPEED_KMH_CLEAN"
        ]
        <= SPEED_WARNING_KMH
    ).all(), (
        "Valid speed exceeds kinematic threshold."
    )

    print(
        "Validation checks: PASSED"
    )


# ============================================================
# 14. MONTHLY SUMMARY
# ============================================================

def build_monthly_summary(
    raw,
    clean
):

    raw_counts = (
        raw.groupby(
            "SOURCE_PERIOD"
        )
        .size()
        .rename(
            "rows_input"
        )
    )

    records = []

    for period, group in clean.groupby(
        "SOURCE_PERIOD",
        sort=True
    ):

        rows_input = int(
            raw_counts.loc[
                period
            ]
        )

        rows_output = len(
            group
        )

        records.append(
            {
                "period":
                    period,

                "year":
                    int(
                        str(period)[:4]
                    ),

                "rows_input":
                    rows_input,

                "rows_output":
                    rows_output,

                "duplicate_rows_collapsed":
                    rows_input
                    - rows_output,

                "reservation_conflict":
                    int(
                        group[
                            "PRENOTAZIONE_CONFLICT"
                        ].sum()
                    ),

                "temporal_detail_available":
                    int(
                        group[
                            "HAS_TEMPORAL_DETAIL"
                        ].sum()
                    ),

                "temporal_detail_unavailable":
                    int(
                        group[
                            "FLAG_TEMPORAL_DETAIL_UNAVAILABLE"
                        ].sum()
                    ),

                "duration_provider_fallback":
                    int(
                        group[
                            "FLAG_DURATION_PROVIDER_FALLBACK"
                        ].sum()
                    ),

                "valid_duration":
                    int(
                        group[
                            "VALID_DURATION"
                        ].sum()
                    ),

                "invalid_duration":
                    int(
                        (
                            ~group[
                                "VALID_DURATION"
                            ]
                        ).sum()
                    ),

                "complete_coordinates":
                    int(
                        group[
                            "HAS_COMPLETE_COORDINATES"
                        ].sum()
                    ),

                "valid_spatial_prezone":
                    int(
                        group[
                            "VALID_SPATIAL_PREZONE"
                        ].sum()
                    ),

                "outside_torino_broad":
                    int(
                        group[
                            "FLAG_OUTSIDE_TORINO_BROAD"
                        ].sum()
                    ),

                "haversine_over_30km":
                    int(
                        group[
                            "FLAG_HAVERSINE_OVER_30KM"
                        ].sum()
                    ),

                "zero_displacement_retained":
                    int(
                        group[
                            "FLAG_ZERO_DISPLACEMENT"
                        ].sum()
                    ),

                "valid_distance":
                    int(
                        group[
                            "VALID_DISTANCE"
                        ].sum()
                    ),

                "invalid_distance":
                    int(
                        (
                            ~group[
                                "VALID_DISTANCE"
                            ]
                        ).sum()
                    ),

                "valid_speed":
                    int(
                        group[
                            "VALID_SPEED"
                        ].sum()
                    ),

                "kinematic_warning":
                    int(
                        group[
                            "FLAG_KINEMATIC_WARNING"
                        ].sum()
                    ),

                "long_duration_gt60":
                    int(
                        group[
                            "FLAG_LONG_DURATION_60"
                        ].sum()
                    ),

                "long_duration_gt120":
                    int(
                        group[
                            "FLAG_LONG_DURATION_120"
                        ].sum()
                    ),

                "long_duration_gt180":
                    int(
                        group[
                            "FLAG_LONG_DURATION_180"
                        ].sum()
                    ),

                "long_displacement_gt20":
                    int(
                        group[
                            "FLAG_LONG_DISPLACEMENT_20"
                        ].sum()
                    ),

                "valid_battery":
                    int(
                        group[
                            "VALID_BATTERY"
                        ].sum()
                    ),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# 15. SAVE AUDIT SUBSETS
# ============================================================

def save_audit_subsets(df):

    # --------------------------------------------------------
    # Prenotazione conflicts
    # --------------------------------------------------------

    df.loc[
        df[
            "PRENOTAZIONE_CONFLICT"
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_reservation_conflict_trips.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Temporal detail unavailable
    # --------------------------------------------------------

    df.loc[
        df[
            "FLAG_TEMPORAL_DETAIL_UNAVAILABLE"
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_temporal_detail_unavailable.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Invalid duration
    # --------------------------------------------------------

    df.loc[
        ~df[
            "VALID_DURATION"
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_invalid_duration_trips.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Spatial invalidity
    # --------------------------------------------------------

    df.loc[
        ~df[
            "VALID_SPATIAL_PREZONE"
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_spatial_invalid_prezone.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Kinematic warnings
    # --------------------------------------------------------

    df.loc[
        df[
            "FLAG_KINEMATIC_WARNING"
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_kinematic_warnings.csv",
        index=False,
    )


# ============================================================
# 16. SAVE YEARLY PARQUET + READBACK VALIDATION
# ============================================================

def save_yearly_cleaned(
    clean,
    year
):

    year_df = clean.loc[
        clean[
            "SOURCE_PERIOD"
        ].str.startswith(
            str(year)
        )
    ].copy()

    output_path = (
        CLEANED_DIR
        / f"voi_{year}_clean.parquet"
    )

    # Remove old or partially written output first
    if output_path.exists():

        output_path.unlink()

        print(
            f"Removed previous file -> "
            f"{output_path}"
        )

    # --------------------------------------------------------
    # Write Parquet
    # --------------------------------------------------------

    year_df.to_parquet(
        output_path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    # --------------------------------------------------------
    # Read-back verification
    # --------------------------------------------------------

    check = pd.read_parquet(
        output_path,
        engine="pyarrow",
    )

    assert (
        len(check)
        ==
        len(year_df)
    ), (
        f"{year}: Parquet read-back row count mismatch."
    )

    assert (
        check[
            TRIP_ID
        ].nunique(
            dropna=True
        )
        ==
        len(year_df)
    ), (
        f"{year}: Parquet read-back trip IDs are not unique."
    )

    print(
        f"Saved {year}: "
        f"{len(year_df):,} trips -> "
        f"{output_path}"
    )

    print(
        f"Read-back validation {year}: PASSED"
    )


# ============================================================
# 17. MAIN PIPELINE
# ============================================================

def main():

    print(
        "\n"
        + "=" * 100
    )

    print(
        "FINALIZING VOI"
    )

    print(
        "=" * 100
    )

    # ========================================================
    # LOAD
    # ========================================================

    raw = load_all()

    print(
        f"\nRaw rows loaded: "
        f"{len(raw):,}"
    )

    print(
        f"Unique trip IDs: "
        f"{raw[TRIP_ID].nunique():,}"
    )

    # ========================================================
    # DEDUPLICATION
    # ========================================================

    clean = build_canonical_trips(
        raw
    )

    print(
        f"\nCanonical unique trips: "
        f"{len(clean):,}"
    )

    print(
        f"Duplicate rows collapsed: "
        f"{len(raw) - len(clean):,}"
    )

    # ========================================================
    # QUALITY / CLEANING FIELDS
    # ========================================================

    clean = add_temporal_fields(
        clean
    )

    clean = add_spatial_fields(
        clean
    )

    clean = add_distance_speed_fields(
        clean
    )

    clean = add_battery_fields(
        clean
    )

    clean = add_core_validity(
        clean
    )

    # ========================================================
    # SCIENTIFIC VALIDATION
    # ========================================================

    validate_final(
        clean
    )

    # ========================================================
    # PARQUET DTYPE STABILIZATION
    #
    # This happens AFTER analytical validation so changing raw
    # object columns to strings cannot affect calculations.
    # ========================================================

    clean = stabilize_parquet_dtypes(
        clean
    )

    # ========================================================
    # SAVE YEARLY CLEANED FILES
    # ========================================================

    save_yearly_cleaned(
        clean,
        2024
    )

    save_yearly_cleaned(
        clean,
        2025
    )

    # ========================================================
    # SAVE AUDIT SUBSETS
    # ========================================================

    save_audit_subsets(
        clean
    )

    # ========================================================
    # MONTHLY CLEANING SUMMARY
    # ========================================================

    monthly = build_monthly_summary(
        raw,
        clean
    )

    monthly_path = (
        AUDIT_DIR
        / "voi_final_monthly_cleaning_summary.csv"
    )

    monthly.to_csv(
        monthly_path,
        index=False
    )

    # ========================================================
    # YEARLY SUMMARY
    # ========================================================

    numeric_columns = [
        col
        for col in monthly.columns
        if col not in [
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
        / "voi_final_cleaning_summary.csv"
    )

    yearly.to_csv(
        yearly_path,
        index=False
    )

    # ========================================================
    # FINAL TERMINAL SUMMARY
    # ========================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "VOI CLEANING FINALIZATION COMPLETED"
    )

    print(
        "=" * 110
    )

    print(
        yearly.to_string(
            index=False
        )
    )

    print(
        f"\nMonthly summary -> "
        f"{monthly_path}"
    )

    print(
        f"Final summary -> "
        f"{yearly_path}"
    )

    print(
        "\nCleaning policy applied:"
    )

    print(
        "- One canonical row retained per trip ID."
    )

    print(
        "- Duplicate rows were collapsed only after confirming "
        "trip-defining fields were identical."
    )

    print(
        "- Prenotazione conflicts were retained as quality flags "
        "and were not arbitrarily resolved."
    )

    print(
        "- VOI raw timestamps were interpreted as UTC and "
        "converted to Europe/Rome."
    )

    print(
        "- January 2024 trips were retained, but detailed "
        "timestamps remain unavailable."
    )

    print(
        "- Provider Tempo Tot is used as duration fallback "
        "when detailed timestamps are unavailable."
    )

    print(
        "- KM Tot is treated as endpoint displacement, not "
        "travelled route distance."
    )

    print(
        "- Zero-displacement trips were retained."
    )

    print(
        "- Spatially implausible or incomplete measurements "
        "were excluded only from spatial/distance analyses."
    )

    print(
        "- Kinematic anomalies were flagged rather than "
        "globally deleted."
    )

    print(
        "- Remaining mixed Excel object columns were "
        "standardized before Parquet serialization."
    )


# ============================================================
# 18. EXECUTION
# ============================================================

if __name__ == "__main__":
    main()