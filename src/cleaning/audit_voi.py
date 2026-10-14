from pathlib import Path
from collections import defaultdict
import re

import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "voi"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "voi"
AUDIT_DIR = PROJECT_ROOT / "audit" / "voi"

INTERIM_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. EXPECTED RAW SCHEMA
# ============================================================

EXPECTED_COLUMNS = [
    "Identificativo noleggio",
    "Targa veicolo",
    "Data inizio corsa",
    "Data fine corsa",
    "Lat inizio corsa_coordinate",
    "Lon inizio corsa_coordinate",
    "Lat fine corsa_coordinate",
    "Lon fine corsa_coordinate",
    "Tempo Tot",
    "KM Tot",
    "Prenotazione",
    "Batteria inizio",
    "Batteria fine",
]


# ============================================================
# 3. AUDIT-ONLY THRESHOLDS
#
# IMPORTANT:
# These thresholds are only used to FLAG suspicious records.
# They are NOT final cleaning rules yet.
# ============================================================

SPEED_CHECK_KMH = 40
GPS_JUMP_CHECK_KM = 30

# Broad Torino check only.
# Official zoning will be used later for final spatial validity.
TORINO_LAT_MIN = 44.90
TORINO_LAT_MAX = 45.20
TORINO_LON_MIN = 7.40
TORINO_LON_MAX = 7.90


# ============================================================
# 4. FILE DISCOVERY
# ============================================================

def infer_period(filename):
    """
    Extract YYYY-MM from a VOI filename.

    Supports examples such as:
        DATINOLEGGI_202401.xlsx
        DATINOLEGGI_2025-01.xlsx
        DATINOLEGGI_Operator B(Voi)_202503.xlsx
    """

    name = Path(filename).stem

    match = re.search(
        r"(20\d{2})[-_]?([01]\d)",
        name
    )

    if not match:
        raise ValueError(
            f"Cannot infer YYYY-MM from filename: {filename}"
        )

    year = int(match.group(1))
    month = int(match.group(2))

    if month < 1 or month > 12:
        raise ValueError(
            f"Invalid month inferred from filename: {filename}"
        )

    return f"{year:04d}-{month:02d}"


def discover_files():
    """
    Discover all VOI Excel files automatically.
    """

    files = sorted(
        list(RAW_DIR.glob("*.xlsx"))
        + list(RAW_DIR.glob("*.xls"))
    )

    if not files:
        raise FileNotFoundError(
            f"No VOI Excel files found in:\n{RAW_DIR}"
        )

    discovered = []
    seen_periods = set()

    for path in files:

        period = infer_period(
            path.name
        )

        if period in seen_periods:
            raise ValueError(
                f"More than one VOI file detected for {period}"
            )

        seen_periods.add(period)

        discovered.append(
            (
                period,
                path
            )
        )

    discovered.sort(
        key=lambda x: x[0]
    )

    print(
        f"Discovered {len(discovered)} VOI files:"
    )

    for period, path in discovered:
        print(
            f"  {period} -> {path.name}"
        )

    return discovered


# ============================================================
# 5. NUMERIC / TEMPORAL HELPERS
# ============================================================

def to_numeric_safe(series):
    """
    Convert Excel numeric fields safely to standard NumPy float64.

    Important:
    Explicit float64 conversion avoids pandas nullable Float64
    vs NumPy float64 assignment conflicts.
    """

    text = (
        series
        .astype("string")
        .str.strip()
        .str.replace(
            ",",
            ".",
            regex=False
        )
    )

    numeric = pd.to_numeric(
        text,
        errors="coerce"
    )

    return numeric.astype(
        "float64"
    )


def normalize_compact_timestamp(series):
    """
    Convert timestamp-like Excel values to clean digit strings.

    Example:
        20240215123045.0
        ->
        20240215123045
    """

    text = (
        series
        .astype("string")
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True
        )
    )

    digits = (
        text
        .str.replace(
            r"\D",
            "",
            regex=True
        )
    )

    digits = digits.where(
        digits.str.len() > 0
    )

    return digits


# ============================================================
# 6. HAVERSINE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Vectorized Haversine distance.

    Inputs are NumPy float arrays.
    Output is NumPy float64 array in kilometers.
    """

    earth_radius_km = 6371.0088

    lat1 = np.radians(
        np.asarray(
            lat1,
            dtype="float64"
        )
    )

    lon1 = np.radians(
        np.asarray(
            lon1,
            dtype="float64"
        )
    )

    lat2 = np.radians(
        np.asarray(
            lat2,
            dtype="float64"
        )
    )

    lon2 = np.radians(
        np.asarray(
            lon2,
            dtype="float64"
        )
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(
            dlat / 2
        ) ** 2
        +
        np.cos(lat1)
        * np.cos(lat2)
        * np.sin(
            dlon / 2
        ) ** 2
    )

    # Numerical safety
    a = np.clip(
        a,
        0,
        1
    )

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return (
        earth_radius_km
        * c
    ).astype(
        "float64"
    )


# ============================================================
# 7. LOAD ONE MONTH
# ============================================================

def load_file(
    period,
    path
):
    """
    Read one monthly VOI workbook.
    """

    print("\n")
    print("=" * 100)
    print(f"LOADING VOI {period}")
    print(f"File: {path.name}")
    print("=" * 100)

    df = pd.read_excel(
        path,
        engine="openpyxl",
        dtype=object,
    )

    # Remove accidental whitespace from column names
    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    print(
        f"Raw rows: {len(df):,}"
    )

    return df


# ============================================================
# 8. SCHEMA VALIDATION
# ============================================================

def validate_schema(
    df,
    period
):
    """
    Ensure all required VOI fields exist.
    """

    missing = [
        col
        for col in EXPECTED_COLUMNS
        if col not in df.columns
    ]

    unexpected = [
        col
        for col in df.columns
        if col not in EXPECTED_COLUMNS
    ]

    if missing:

        print(
            f"\nActual columns found in {period}:"
        )

        for col in df.columns:
            print(
                repr(col)
            )

        raise ValueError(
            f"{period}: missing expected columns: {missing}"
        )

    if unexpected:

        print(
            f"WARNING {period}: "
            f"unexpected columns: {unexpected}"
        )

    print(
        "Schema validation: OK"
    )


# ============================================================
# 9. TRACEABILITY
# ============================================================

def add_traceability(
    df,
    period,
    path
):
    """
    Preserve source location for every row.
    """

    df = df.copy()

    df.insert(
        0,
        "SOURCE_PERIOD",
        period
    )

    df.insert(
        1,
        "SOURCE_FILE",
        path.name
    )

    df.insert(
        2,
        "SOURCE_ROW",
        np.arange(
            1,
            len(df) + 1,
            dtype="int64"
        )
    )

    return df


# ============================================================
# 10. TYPE CONVERSION
# ============================================================

def convert_types(df):
    """
    Parse timestamps and convert numeric variables.

    Raw columns are preserved.
    Parsed/typed analytical columns are added separately.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Timestamp codes
    # --------------------------------------------------------

    df["START_TIMESTAMP_CODE"] = (
        normalize_compact_timestamp(
            df["Data inizio corsa"]
        )
    )

    df["END_TIMESTAMP_CODE"] = (
        normalize_compact_timestamp(
            df["Data fine corsa"]
        )
    )

    # --------------------------------------------------------
    # Parsed datetime
    # --------------------------------------------------------

    df["START_TIME_RAW"] = pd.to_datetime(
        df["START_TIMESTAMP_CODE"],
        format="%Y%m%d%H%M%S",
        errors="coerce",
    )

    df["END_TIME_RAW"] = pd.to_datetime(
        df["END_TIMESTAMP_CODE"],
        format="%Y%m%d%H%M%S",
        errors="coerce",
    )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    numeric_columns = [
        "Lat inizio corsa_coordinate",
        "Lon inizio corsa_coordinate",
        "Lat fine corsa_coordinate",
        "Lon fine corsa_coordinate",
        "Tempo Tot",
        "KM Tot",
        "Batteria inizio",
        "Batteria fine",
    ]

    for col in numeric_columns:

        df[col] = to_numeric_safe(
            df[col]
        )

    return df


# ============================================================
# 11. DERIVED QUALITY VARIABLES
# ============================================================

def add_derived_features(df):
    """
    Generate analytical variables without modifying raw values.
    """

    df = df.copy()

    # ========================================================
    # 11.1 TIMESTAMP-BASED DURATION
    # ========================================================

    df["DURATION_FROM_TIMESTAMPS_MIN"] = (
        df["END_TIME_RAW"]
        - df["START_TIME_RAW"]
    ).dt.total_seconds() / 60

    df[
        "DURATION_FROM_TIMESTAMPS_MIN"
    ] = (
        df[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ]
        .astype("float64")
    )

    df["DURATION_DIFFERENCE_MIN"] = (
        df[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ]
        - df["Tempo Tot"]
    ).astype(
        "float64"
    )

    # ========================================================
    # 11.2 REPORTED SPEED
    # ========================================================

    speed_ok = (
        df["KM Tot"].notna()
        & df["Tempo Tot"].notna()
        & (df["KM Tot"] > 0)
        & (df["Tempo Tot"] > 0)
    )

    # Explicit NumPy float64 array
    reported_speed = np.full(
        len(df),
        np.nan,
        dtype="float64"
    )

    speed_mask = speed_ok.to_numpy(
        dtype=bool
    )

    reported_speed[
        speed_mask
    ] = (
        df.loc[
            speed_ok,
            "KM Tot"
        ]
        .to_numpy(
            dtype="float64"
        )
        /
        (
            df.loc[
                speed_ok,
                "Tempo Tot"
            ]
            .to_numpy(
                dtype="float64"
            )
            / 60.0
        )
    )

    df["REPORTED_SPEED_KMH"] = (
        reported_speed
    )

    # ========================================================
    # 11.3 HAVERSINE DISPLACEMENT
    # ========================================================

    coordinate_columns = [
        "Lat inizio corsa_coordinate",
        "Lon inizio corsa_coordinate",
        "Lat fine corsa_coordinate",
        "Lon fine corsa_coordinate",
    ]

    complete_coordinates = (
        df[
            coordinate_columns
        ]
        .notna()
        .all(axis=1)
    )

    haversine_values = np.full(
        len(df),
        np.nan,
        dtype="float64"
    )

    coord_mask = (
        complete_coordinates
        .to_numpy(
            dtype=bool
        )
    )

    if coord_mask.any():

        haversine_values[
            coord_mask
        ] = haversine_km(
            df.loc[
                complete_coordinates,
                "Lat inizio corsa_coordinate"
            ].to_numpy(
                dtype="float64"
            ),

            df.loc[
                complete_coordinates,
                "Lon inizio corsa_coordinate"
            ].to_numpy(
                dtype="float64"
            ),

            df.loc[
                complete_coordinates,
                "Lat fine corsa_coordinate"
            ].to_numpy(
                dtype="float64"
            ),

            df.loc[
                complete_coordinates,
                "Lon fine corsa_coordinate"
            ].to_numpy(
                dtype="float64"
            ),
        )

    df["HAVERSINE_KM"] = (
        haversine_values
    )

    # ========================================================
    # 11.4 SAME START / END COORDINATES
    # ========================================================

    df["SAME_START_END_COORDS"] = (
        complete_coordinates
        &
        (
            df[
                "Lat inizio corsa_coordinate"
            ]
            ==
            df[
                "Lat fine corsa_coordinate"
            ]
        )
        &
        (
            df[
                "Lon inizio corsa_coordinate"
            ]
            ==
            df[
                "Lon fine corsa_coordinate"
            ]
        )
    )

    # ========================================================
    # 11.5 HAVERSINE SPEED
    #
    # Uses operator-provided Tempo Tot because January 2024
    # raw timestamps are known to be damaged.
    # ========================================================

    duration_ok = (
        df["Tempo Tot"].notna()
        & (df["Tempo Tot"] > 0)
        & df["HAVERSINE_KM"].notna()
    )

    haversine_speed = np.full(
        len(df),
        np.nan,
        dtype="float64"
    )

    duration_mask = (
        duration_ok
        .to_numpy(
            dtype=bool
        )
    )

    if duration_mask.any():

        haversine_speed[
            duration_mask
        ] = (
            df.loc[
                duration_ok,
                "HAVERSINE_KM"
            ]
            .to_numpy(
                dtype="float64"
            )
            /
            (
                df.loc[
                    duration_ok,
                    "Tempo Tot"
                ]
                .to_numpy(
                    dtype="float64"
                )
                / 60.0
            )
        )

    df["HAVERSINE_SPEED_KMH"] = (
        haversine_speed
    )

    # ========================================================
    # 11.6 BATTERY CHANGE
    # ========================================================

    df["BATTERY_CHANGE"] = (
        df["Batteria fine"]
        - df["Batteria inizio"]
    ).astype(
        "float64"
    )

    # ========================================================
    # 11.7 PERIOD ENCODED INSIDE RAW TIMESTAMP CODE
    # ========================================================

    df["START_CODE_PERIOD"] = (
        df[
            "START_TIMESTAMP_CODE"
        ]
        .str.slice(
            0,
            6
        )
    )

    df["END_CODE_PERIOD"] = (
        df[
            "END_TIMESTAMP_CODE"
        ]
        .str.slice(
            0,
            6
        )
    )

    return df


# ============================================================
# 12. AUDIT FLAGS
# ============================================================

def add_audit_flags(df):
    """
    Flag potentially problematic observations.
    Nothing is deleted here.
    """

    df = df.copy()

    # ========================================================
    # 12.1 IDENTIFIERS
    # ========================================================

    df["FLAG_MISSING_TRIP_ID"] = (
        df[
            "Identificativo noleggio"
        ]
        .isna()
    )

    df["FLAG_MISSING_VEHICLE_ID"] = (
        df[
            "Targa veicolo"
        ]
        .isna()
    )

    # ========================================================
    # 12.2 RAW TIMESTAMP MISSINGNESS
    # ========================================================

    df[
        "FLAG_MISSING_START_TIMESTAMP_RAW"
    ] = (
        df[
            "Data inizio corsa"
        ]
        .isna()
    )

    df[
        "FLAG_MISSING_END_TIMESTAMP_RAW"
    ] = (
        df[
            "Data fine corsa"
        ]
        .isna()
    )

    # ========================================================
    # 12.3 TIMESTAMP PARSING
    # ========================================================

    df["FLAG_INVALID_START_DATETIME"] = (
        df["START_TIME_RAW"].isna()
        &
        df[
            "Data inizio corsa"
        ].notna()
    )

    df["FLAG_INVALID_END_DATETIME"] = (
        df["END_TIME_RAW"].isna()
        &
        df[
            "Data fine corsa"
        ].notna()
    )

    # Known pattern:
    # YYYYMM00HHMMSS
    # means the day field is missing/invalid.
    df["FLAG_START_DAY_ZERO"] = (
        df[
            "START_TIMESTAMP_CODE"
        ]
        .str.slice(
            6,
            8
        )
        .eq("00")
        .fillna(False)
    )

    df["FLAG_END_DAY_ZERO"] = (
        df[
            "END_TIMESTAMP_CODE"
        ]
        .str.slice(
            6,
            8
        )
        .eq("00")
        .fillna(False)
    )

    # ========================================================
    # 12.4 TEMPORAL CONSISTENCY
    # ========================================================

    df["FLAG_REVERSED_TIMESTAMP"] = (
        df["START_TIME_RAW"].notna()
        &
        df["END_TIME_RAW"].notna()
        &
        (
            df["END_TIME_RAW"]
            < df["START_TIME_RAW"]
        )
    )

    df[
        "FLAG_DURATION_TS_NON_POSITIVE"
    ] = (
        df[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ]
        .notna()
        &
        (
            df[
                "DURATION_FROM_TIMESTAMPS_MIN"
            ]
            <= 0
        )
    )

    df["FLAG_DURATION_NON_POSITIVE"] = (
        df["Tempo Tot"].notna()
        &
        (
            df["Tempo Tot"]
            <= 0
        )
    )

    # ========================================================
    # 12.5 DISTANCE
    # ========================================================

    df[
        "FLAG_DISTANCE_NON_POSITIVE"
    ] = (
        df["KM Tot"].notna()
        &
        (
            df["KM Tot"]
            <= 0
        )
    )

    # ========================================================
    # 12.6 SPEED
    # ========================================================

    df[
        "FLAG_REPORTED_SPEED_OVER_40"
    ] = (
        df[
            "REPORTED_SPEED_KMH"
        ].notna()
        &
        (
            df[
                "REPORTED_SPEED_KMH"
            ]
            > SPEED_CHECK_KMH
        )
    )

    df[
        "FLAG_HAVERSINE_SPEED_OVER_40"
    ] = (
        df[
            "HAVERSINE_SPEED_KMH"
        ].notna()
        &
        (
            df[
                "HAVERSINE_SPEED_KMH"
            ]
            > SPEED_CHECK_KMH
        )
    )

    # ========================================================
    # 12.7 COORDINATES
    # ========================================================

    start_missing = (
        df[
            [
                "Lat inizio corsa_coordinate",
                "Lon inizio corsa_coordinate",
            ]
        ]
        .isna()
        .any(axis=1)
    )

    end_missing = (
        df[
            [
                "Lat fine corsa_coordinate",
                "Lon fine corsa_coordinate",
            ]
        ]
        .isna()
        .any(axis=1)
    )

    df[
        "FLAG_MISSING_START_COORDINATES"
    ] = (
        start_missing
    )

    df[
        "FLAG_MISSING_END_COORDINATES"
    ] = (
        end_missing
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
            > GPS_JUMP_CHECK_KM
        )
    )

    # ========================================================
    # 12.8 BROAD TORINO CHECK
    #
    # Diagnostic only.
    # Official statistical zoning comes later.
    # ========================================================

    start_outside = (
        (
            df[
                "Lat inizio corsa_coordinate"
            ]
            < TORINO_LAT_MIN
        )
        |
        (
            df[
                "Lat inizio corsa_coordinate"
            ]
            > TORINO_LAT_MAX
        )
        |
        (
            df[
                "Lon inizio corsa_coordinate"
            ]
            < TORINO_LON_MIN
        )
        |
        (
            df[
                "Lon inizio corsa_coordinate"
            ]
            > TORINO_LON_MAX
        )
    )

    end_outside = (
        (
            df[
                "Lat fine corsa_coordinate"
            ]
            < TORINO_LAT_MIN
        )
        |
        (
            df[
                "Lat fine corsa_coordinate"
            ]
            > TORINO_LAT_MAX
        )
        |
        (
            df[
                "Lon fine corsa_coordinate"
            ]
            < TORINO_LON_MIN
        )
        |
        (
            df[
                "Lon fine corsa_coordinate"
            ]
            > TORINO_LON_MAX
        )
    )

    df[
        "FLAG_OUTSIDE_TORINO_BROAD"
    ] = (
        start_outside
        | end_outside
    )

    # ========================================================
    # 12.9 BATTERY
    # ========================================================

    df[
        "FLAG_BATTERY_START_INVALID"
    ] = (
        df[
            "Batteria inizio"
        ].notna()
        &
        (
            (
                df[
                    "Batteria inizio"
                ]
                < 0
            )
            |
            (
                df[
                    "Batteria inizio"
                ]
                > 100
            )
        )
    )

    df[
        "FLAG_BATTERY_END_INVALID"
    ] = (
        df[
            "Batteria fine"
        ].notna()
        &
        (
            (
                df[
                    "Batteria fine"
                ]
                < 0
            )
            |
            (
                df[
                    "Batteria fine"
                ]
                > 100
            )
        )
    )

    df[
        "FLAG_BATTERY_INCREASE"
    ] = (
        df[
            "BATTERY_CHANGE"
        ].notna()
        &
        (
            df[
                "BATTERY_CHANGE"
            ]
            > 0
        )
    )

    # ========================================================
    # 12.10 SOURCE MONTH VS TIMESTAMP-CODE MONTH
    # ========================================================

    source_compact = (
        df[
            "SOURCE_PERIOD"
        ]
        .astype("string")
        .str.replace(
            "-",
            "",
            regex=False
        )
    )

    df[
        "FLAG_START_CODE_PERIOD_MISMATCH"
    ] = (
        df[
            "START_CODE_PERIOD"
        ].notna()
        &
        (
            df[
                "START_CODE_PERIOD"
            ]
            != source_compact
        )
    )

    df[
        "FLAG_END_CODE_PERIOD_MISMATCH"
    ] = (
        df[
            "END_CODE_PERIOD"
        ].notna()
        &
        (
            df[
                "END_CODE_PERIOD"
            ]
            != source_compact
        )
    )

    return df


# ============================================================
# 13. MONTHLY SUMMARY
# ============================================================

def build_month_summary(
    df,
    period
):
    """
    Summarize raw data quality for one month.
    """

    # --------------------------------------------------------
    # Exact duplicates
    # --------------------------------------------------------

    exact_duplicate_rows_all = int(
        df.duplicated(
            subset=EXPECTED_COLUMNS,
            keep=False
        ).sum()
    )

    exact_duplicate_excess = int(
        df.duplicated(
            subset=EXPECTED_COLUMNS,
            keep="first"
        ).sum()
    )

    # --------------------------------------------------------
    # Duplicate trip IDs
    #
    # Missing IDs are excluded from duplicate-ID logic.
    # --------------------------------------------------------

    nonmissing_trip_id = (
        df[
            "Identificativo noleggio"
        ].notna()
    )

    duplicate_trip_mask = (
        nonmissing_trip_id
        &
        df[
            "Identificativo noleggio"
        ]
        .duplicated(
            keep=False
        )
    )

    duplicate_excess_mask = (
        nonmissing_trip_id
        &
        df[
            "Identificativo noleggio"
        ]
        .duplicated(
            keep="first"
        )
    )

    trip_id_dup_rows = int(
        duplicate_trip_mask.sum()
    )

    trip_id_dup_excess = int(
        duplicate_excess_mask.sum()
    )

    duplicate_trip_ids = int(
        df.loc[
            duplicate_trip_mask,
            "Identificativo noleggio"
        ]
        .nunique(
            dropna=True
        )
    )

    reservation_values = sorted(
        df[
            "Prenotazione"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    summary = {
        "period":
            period,

        "year":
            int(
                period[:4]
            ),

        "rows":
            len(df),

        "unique_trip_ids":
            int(
                df[
                    "Identificativo noleggio"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "unique_vehicles":
            int(
                df[
                    "Targa veicolo"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "exact_duplicate_rows_all":
            exact_duplicate_rows_all,

        "exact_duplicate_excess":
            exact_duplicate_excess,

        "duplicate_trip_id_rows":
            trip_id_dup_rows,

        "duplicate_trip_id_excess":
            trip_id_dup_excess,

        "duplicate_trip_ids":
            duplicate_trip_ids,

        "missing_trip_id":
            int(
                df[
                    "FLAG_MISSING_TRIP_ID"
                ].sum()
            ),

        "missing_vehicle_id":
            int(
                df[
                    "FLAG_MISSING_VEHICLE_ID"
                ].sum()
            ),

        "missing_start_timestamp_raw":
            int(
                df[
                    "FLAG_MISSING_START_TIMESTAMP_RAW"
                ].sum()
            ),

        "missing_end_timestamp_raw":
            int(
                df[
                    "FLAG_MISSING_END_TIMESTAMP_RAW"
                ].sum()
            ),

        "invalid_start_datetime":
            int(
                df[
                    "FLAG_INVALID_START_DATETIME"
                ].sum()
            ),

        "invalid_end_datetime":
            int(
                df[
                    "FLAG_INVALID_END_DATETIME"
                ].sum()
            ),

        "start_day_zero":
            int(
                df[
                    "FLAG_START_DAY_ZERO"
                ].sum()
            ),

        "end_day_zero":
            int(
                df[
                    "FLAG_END_DAY_ZERO"
                ].sum()
            ),

        "reversed_timestamp":
            int(
                df[
                    "FLAG_REVERSED_TIMESTAMP"
                ].sum()
            ),

        "timestamp_duration_non_positive":
            int(
                df[
                    "FLAG_DURATION_TS_NON_POSITIVE"
                ].sum()
            ),

        "tempo_tot_non_positive":
            int(
                df[
                    "FLAG_DURATION_NON_POSITIVE"
                ].sum()
            ),

        "km_tot_non_positive":
            int(
                df[
                    "FLAG_DISTANCE_NON_POSITIVE"
                ].sum()
            ),

        "missing_tempo_tot":
            int(
                df[
                    "Tempo Tot"
                ]
                .isna()
                .sum()
            ),

        "missing_km_tot":
            int(
                df[
                    "KM Tot"
                ]
                .isna()
                .sum()
            ),

        "reported_speed_over_40":
            int(
                df[
                    "FLAG_REPORTED_SPEED_OVER_40"
                ].sum()
            ),

        "same_start_end_coords":
            int(
                df[
                    "SAME_START_END_COORDS"
                ].sum()
            ),

        "missing_start_coordinates":
            int(
                df[
                    "FLAG_MISSING_START_COORDINATES"
                ].sum()
            ),

        "missing_end_coordinates":
            int(
                df[
                    "FLAG_MISSING_END_COORDINATES"
                ].sum()
            ),

        "haversine_over_30km":
            int(
                df[
                    "FLAG_HAVERSINE_OVER_30KM"
                ].sum()
            ),

        "haversine_speed_over_40":
            int(
                df[
                    "FLAG_HAVERSINE_SPEED_OVER_40"
                ].sum()
            ),

        "outside_torino_broad":
            int(
                df[
                    "FLAG_OUTSIDE_TORINO_BROAD"
                ].sum()
            ),

        "missing_battery_start":
            int(
                df[
                    "Batteria inizio"
                ]
                .isna()
                .sum()
            ),

        "missing_battery_end":
            int(
                df[
                    "Batteria fine"
                ]
                .isna()
                .sum()
            ),

        "battery_start_invalid":
            int(
                df[
                    "FLAG_BATTERY_START_INVALID"
                ].sum()
            ),

        "battery_end_invalid":
            int(
                df[
                    "FLAG_BATTERY_END_INVALID"
                ].sum()
            ),

        "battery_increase":
            int(
                df[
                    "FLAG_BATTERY_INCREASE"
                ].sum()
            ),

        "start_code_period_mismatch":
            int(
                df[
                    "FLAG_START_CODE_PERIOD_MISMATCH"
                ].sum()
            ),

        "end_code_period_mismatch":
            int(
                df[
                    "FLAG_END_CODE_PERIOD_MISMATCH"
                ].sum()
            ),

        "parsed_start_min":
            df[
                "START_TIME_RAW"
            ].min(),

        "parsed_start_max":
            df[
                "START_TIME_RAW"
            ].max(),

        "tempo_tot_min":
            df[
                "Tempo Tot"
            ].min(),

        "tempo_tot_max":
            df[
                "Tempo Tot"
            ].max(),

        "km_tot_min":
            df[
                "KM Tot"
            ].min(),

        "km_tot_max":
            df[
                "KM Tot"
            ].max(),

        "reservation_values":
            "|".join(
                reservation_values
            ),
    }

    return pd.DataFrame(
        [summary]
    )


# ============================================================
# 14. DUPLICATE-ID CLASSIFICATION
# ============================================================

def classify_duplicate_ids(
    duplicate_rows
):
    """
    Classify repeated trip IDs into:

    1. exact_duplicate
    2. prenotazione_only_conflict
    3. other_field_conflict
    """

    output_columns = [
        "Identificativo noleggio",
        "rows_in_group",
        "source_files",
        "source_periods",
        "exact_variants",
        "variants_excluding_prenotazione",
        "prenotazione_values",
        "duplicate_type",
    ]

    if duplicate_rows.empty:

        return pd.DataFrame(
            columns=output_columns
        )

    rows = []

    comparison_without_reservation = [
        col
        for col in EXPECTED_COLUMNS
        if col != "Prenotazione"
    ]

    for trip_id, group in (
        duplicate_rows.groupby(
            "Identificativo noleggio",
            dropna=False,
            sort=False,
        )
    ):

        exact_variants = (
            group[
                EXPECTED_COLUMNS
            ]
            .drop_duplicates()
            .shape[0]
        )

        variants_without_reservation = (
            group[
                comparison_without_reservation
            ]
            .drop_duplicates()
            .shape[0]
        )

        reservation_values = (
            group[
                "Prenotazione"
            ]
            .astype("string")
            .fillna("<MISSING>")
            .drop_duplicates()
            .tolist()
        )

        if exact_variants == 1:

            duplicate_type = (
                "exact_duplicate"
            )

        elif (
            variants_without_reservation
            == 1
        ):

            duplicate_type = (
                "prenotazione_only_conflict"
            )

        else:

            duplicate_type = (
                "other_field_conflict"
            )

        source_periods = sorted(
            group[
                "SOURCE_PERIOD"
            ]
            .astype(str)
            .unique()
            .tolist()
        )

        rows.append(
            {
                "Identificativo noleggio":
                    trip_id,

                "rows_in_group":
                    len(group),

                "source_files":
                    int(
                        group[
                            "SOURCE_FILE"
                        ].nunique()
                    ),

                "source_periods":
                    "|".join(
                        source_periods
                    ),

                "exact_variants":
                    exact_variants,

                "variants_excluding_prenotazione":
                    variants_without_reservation,

                "prenotazione_values":
                    "|".join(
                        map(
                            str,
                            reservation_values
                        )
                    ),

                "duplicate_type":
                    duplicate_type,
            }
        )

    return pd.DataFrame(
        rows,
        columns=output_columns
    )


# ============================================================
# 15. MAIN PIPELINE
# ============================================================

def main():

    discovered = discover_files()

    monthly_summaries = []

    # Used for global duplicate analysis
    duplicate_parts = []

    unique_vehicles_by_year = defaultdict(
        set
    )

    unique_trip_ids_by_year = defaultdict(
        set
    )

    # ========================================================
    # PROCESS MONTHLY FILES
    # ========================================================

    for period, path in discovered:

        # ----------------------------------------------------
        # Load raw
        # ----------------------------------------------------

        df = load_file(
            period,
            path
        )

        validate_schema(
            df,
            period
        )

        # ----------------------------------------------------
        # Preserve a raw comparison copy BEFORE conversion.
        #
        # This ensures duplicate classification is based on
        # original Excel values rather than cleaned values.
        # ----------------------------------------------------

        raw_for_duplicates = (
            df[
                EXPECTED_COLUMNS
            ]
            .copy()
        )

        # ----------------------------------------------------
        # Traceability
        # ----------------------------------------------------

        df = add_traceability(
            df,
            period,
            path
        )

        # ----------------------------------------------------
        # Type conversion
        # ----------------------------------------------------

        df = convert_types(
            df
        )

        # ----------------------------------------------------
        # Derived features
        # ----------------------------------------------------

        df = add_derived_features(
            df
        )

        # ----------------------------------------------------
        # Audit flags
        # ----------------------------------------------------

        df = add_audit_flags(
            df
        )

        # ----------------------------------------------------
        # Monthly summary
        # ----------------------------------------------------

        summary = build_month_summary(
            df,
            period
        )

        monthly_summaries.append(
            summary
        )

        # ----------------------------------------------------
        # Year-level ID sets
        # ----------------------------------------------------

        year = int(
            period[:4]
        )

        unique_vehicles_by_year[
            year
        ].update(
            df[
                "Targa veicolo"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        unique_trip_ids_by_year[
            year
        ].update(
            df[
                "Identificativo noleggio"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        # ----------------------------------------------------
        # Save monthly interim Parquet
        # ----------------------------------------------------

        interim_path = (
            INTERIM_DIR
            / f"voi_{period}_typed_flagged.parquet"
        )

        df.to_parquet(
            interim_path,
            index=False
        )

        # ----------------------------------------------------
        # Build raw global duplicate table
        # ----------------------------------------------------

        duplicate_part = (
            raw_for_duplicates.copy()
        )

        duplicate_part.insert(
            0,
            "SOURCE_PERIOD",
            period
        )

        duplicate_part.insert(
            1,
            "SOURCE_FILE",
            path.name
        )

        duplicate_part.insert(
            2,
            "SOURCE_ROW",
            np.arange(
                1,
                len(
                    duplicate_part
                ) + 1,
                dtype="int64"
            )
        )

        duplicate_parts.append(
            duplicate_part
        )

        # ----------------------------------------------------
        # Terminal monthly summary
        # ----------------------------------------------------

        duplicate_excess = int(
            (
                df[
                    "Identificativo noleggio"
                ].notna()
                &
                df[
                    "Identificativo noleggio"
                ]
                .duplicated(
                    keep="first"
                )
            ).sum()
        )

        print(
            f"{period}: "
            f"rows={len(df):,} | "
            f"trip_ids="
            f"{df['Identificativo noleggio'].nunique(dropna=True):,} | "
            f"vehicles="
            f"{df['Targa veicolo'].nunique(dropna=True):,} | "
            f"invalid_start="
            f"{int(df['FLAG_INVALID_START_DATETIME'].sum()):,} | "
            f"invalid_end="
            f"{int(df['FLAG_INVALID_END_DATETIME'].sum()):,} | "
            f"dup_ID_excess="
            f"{duplicate_excess:,} | "
            f"KM<=0="
            f"{int(df['FLAG_DISTANCE_NON_POSITIVE'].sum()):,} | "
            f"Tempo<=0="
            f"{int(df['FLAG_DURATION_NON_POSITIVE'].sum()):,}"
        )

    # ========================================================
    # 16. MONTHLY AUDIT TABLE
    # ========================================================

    monthly = pd.concat(
        monthly_summaries,
        ignore_index=True
    )

    monthly_path = (
        AUDIT_DIR
        / "voi_monthly_raw_audit.csv"
    )

    monthly.to_csv(
        monthly_path,
        index=False
    )

    # ========================================================
    # 17. GLOBAL DUPLICATE AUDIT
    # ========================================================

    duplicate_base = pd.concat(
        duplicate_parts,
        ignore_index=True
    )

    nonmissing_global_id = (
        duplicate_base[
            "Identificativo noleggio"
        ].notna()
    )

    duplicate_global_mask = (
        nonmissing_global_id
        &
        duplicate_base[
            "Identificativo noleggio"
        ]
        .duplicated(
            keep=False
        )
    )

    duplicate_rows = (
        duplicate_base.loc[
            duplicate_global_mask
        ]
        .copy()
    )

    duplicate_rows_path = (
        AUDIT_DIR
        / "voi_duplicate_trip_id_rows.csv"
    )

    duplicate_rows.to_csv(
        duplicate_rows_path,
        index=False
    )

    # --------------------------------------------------------
    # Duplicate-ID classification
    # --------------------------------------------------------

    duplicate_id_summary = (
        classify_duplicate_ids(
            duplicate_rows
        )
    )

    duplicate_summary_path = (
        AUDIT_DIR
        / "voi_duplicate_trip_id_summary.csv"
    )

    duplicate_id_summary.to_csv(
        duplicate_summary_path,
        index=False
    )

    # --------------------------------------------------------
    # Global exact duplicates
    # --------------------------------------------------------

    exact_dup_all = int(
        duplicate_base
        .duplicated(
            subset=EXPECTED_COLUMNS,
            keep=False
        )
        .sum()
    )

    exact_dup_excess = int(
        duplicate_base
        .duplicated(
            subset=EXPECTED_COLUMNS,
            keep="first"
        )
        .sum()
    )

    global_duplicate_trip_ids = int(
        duplicate_rows[
            "Identificativo noleggio"
        ]
        .nunique(
            dropna=True
        )
    )

    global_duplicate_id_excess = int(
        (
            nonmissing_global_id
            &
            duplicate_base[
                "Identificativo noleggio"
            ]
            .duplicated(
                keep="first"
            )
        ).sum()
    )

    # ========================================================
    # 18. YEARLY AUDIT SUMMARY
    # ========================================================

    count_columns = [
        "rows",
        "exact_duplicate_rows_all",
        "exact_duplicate_excess",
        "duplicate_trip_id_rows",
        "duplicate_trip_id_excess",
        "duplicate_trip_ids",
        "missing_trip_id",
        "missing_vehicle_id",
        "missing_start_timestamp_raw",
        "missing_end_timestamp_raw",
        "invalid_start_datetime",
        "invalid_end_datetime",
        "start_day_zero",
        "end_day_zero",
        "reversed_timestamp",
        "timestamp_duration_non_positive",
        "tempo_tot_non_positive",
        "km_tot_non_positive",
        "missing_tempo_tot",
        "missing_km_tot",
        "reported_speed_over_40",
        "same_start_end_coords",
        "missing_start_coordinates",
        "missing_end_coordinates",
        "haversine_over_30km",
        "haversine_speed_over_40",
        "outside_torino_broad",
        "missing_battery_start",
        "missing_battery_end",
        "battery_start_invalid",
        "battery_end_invalid",
        "battery_increase",
        "start_code_period_mismatch",
        "end_code_period_mismatch",
    ]

    yearly = (
        monthly
        .groupby(
            "year"
        )[
            count_columns
        ]
        .sum()
        .reset_index()
    )

    yearly["unique_vehicles"] = (
        yearly[
            "year"
        ]
        .map(
            lambda y:
            len(
                unique_vehicles_by_year[
                    int(y)
                ]
            )
        )
    )

    yearly["unique_trip_ids"] = (
        yearly[
            "year"
        ]
        .map(
            lambda y:
            len(
                unique_trip_ids_by_year[
                    int(y)
                ]
            )
        )
    )

    yearly_path = (
        AUDIT_DIR
        / "voi_yearly_raw_audit.csv"
    )

    yearly.to_csv(
        yearly_path,
        index=False
    )

    # ========================================================
    # 19. TERMINAL OUTPUT
    # ========================================================

    print("\n")
    print("=" * 110)
    print("VOI RAW AUDIT COMPLETED")
    print("=" * 110)

    print(
        "\nMonthly coverage / structure:"
    )

    monthly_display_columns = [
        "period",
        "rows",
        "unique_trip_ids",
        "unique_vehicles",
        "invalid_start_datetime",
        "invalid_end_datetime",
        "duplicate_trip_id_excess",
        "start_code_period_mismatch",
        "km_tot_non_positive",
        "tempo_tot_non_positive",
    ]

    print(
        monthly[
            monthly_display_columns
        ]
        .to_string(
            index=False
        )
    )

    print(
        "\nYearly audit summary:"
    )

    yearly_display_columns = [
        "year",
        "rows",
        "unique_trip_ids",
        "unique_vehicles",
        "missing_trip_id",
        "missing_vehicle_id",
        "invalid_start_datetime",
        "invalid_end_datetime",
        "start_day_zero",
        "end_day_zero",
        "duplicate_trip_id_excess",
        "km_tot_non_positive",
        "tempo_tot_non_positive",
        "reported_speed_over_40",
        "same_start_end_coords",
        "missing_start_coordinates",
        "missing_end_coordinates",
        "haversine_over_30km",
        "haversine_speed_over_40",
        "outside_torino_broad",
        "missing_battery_start",
        "missing_battery_end",
        "battery_start_invalid",
        "battery_end_invalid",
        "battery_increase",
        "start_code_period_mismatch",
        "end_code_period_mismatch",
    ]

    print(
        yearly[
            yearly_display_columns
        ]
        .to_string(
            index=False
        )
    )

    print(
        "\nGlobal duplicate-ID audit:"
    )

    print(
        f"Total raw rows: "
        f"{len(duplicate_base):,}"
    )

    print(
        f"Global exact duplicate rows "
        f"(all rows belonging to exact-duplicate groups): "
        f"{exact_dup_all:,}"
    )

    print(
        f"Global exact duplicate excess rows: "
        f"{exact_dup_excess:,}"
    )

    print(
        f"Trip IDs appearing more than once: "
        f"{global_duplicate_trip_ids:,}"
    )

    print(
        f"Excess rows by trip ID: "
        f"{global_duplicate_id_excess:,}"
    )

    if not duplicate_id_summary.empty:

        print(
            "\nDuplicate-ID types:"
        )

        print(
            duplicate_id_summary[
                "duplicate_type"
            ]
            .value_counts()
            .to_string()
        )

        print(
            "\nRows contained in duplicate-ID groups:"
        )

        duplicate_type_rows = (
            duplicate_id_summary
            .groupby(
                "duplicate_type"
            )[
                "rows_in_group"
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        print(
            duplicate_type_rows
            .to_string()
        )

    # ========================================================
    # 20. OUTPUT LOCATIONS
    # ========================================================

    print(
        f"\nMonthly audit -> "
        f"{monthly_path}"
    )

    print(
        f"Yearly audit -> "
        f"{yearly_path}"
    )

    print(
        f"Duplicate rows -> "
        f"{duplicate_rows_path}"
    )

    print(
        f"Duplicate-ID summary -> "
        f"{duplicate_summary_path}"
    )

    print(
        "\nIMPORTANT:"
        "\n- No VOI records were deleted."
        "\n- Duplicate trip IDs were classified, not resolved."
        "\n- Invalid timestamps were flagged, not reconstructed."
        "\n- January 2024 temporal damage remains untouched."
        "\n- Numeric columns were standardized explicitly to "
        "NumPy float64 to avoid pandas dtype conflicts."
        "\n- Spatial thresholds are audit-only and not final "
        "Torino zoning rules."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()