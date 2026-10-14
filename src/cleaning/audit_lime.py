from pathlib import Path
from collections import defaultdict
import re

import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "lime"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "lime"
AUDIT_DIR = PROJECT_ROOT / "audit" / "lime"

INTERIM_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. EXPECTED SCHEMA
# ============================================================

EXPECTED_COLUMNS = [
    "ID_VEICOLO",
    "DATAORA_INIZIO",
    "DATAORA_FINE",
    "LATITUDINE_INIZIO_CORSA",
    "LONGITUTIDE_INIZIO_CORSA",
    "LATITUDINE_FINE_CORSA",
    "LONGITUTIDE_FINE_CORSA",
    "DISTANZA_KM",
    "DURATA_MIN",
    "RISERVATO",
    "BATTERIA_INIZIO_CORSA",
    "BATTERIA_FINE_CORSA",
    "ANNO_MESE",
]


# ============================================================
# 3. AUDIT THRESHOLDS
#
# IMPORTANT:
# These are NOT final cleaning rules.
# They only identify records requiring inspection.
# ============================================================

GPS_JUMP_CHECK_KM = 30
HAVERSINE_SPEED_CHECK_KMH = 40
DURATION_DIFFERENCE_CHECK_MIN = 1.01

# Broad check only, not final Torino boundary.
TORINO_LAT_MIN = 44.90
TORINO_LAT_MAX = 45.20
TORINO_LON_MIN = 7.40
TORINO_LON_MAX = 7.90


# ============================================================
# 4. FILE DISCOVERY
# ============================================================

def discover_files():

    pattern = "Torino_Corse24-25_*_senza_percorso.csv"

    files = sorted(RAW_DIR.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No Lime CSV files found in:\n{RAW_DIR}"
        )

    discovered = []

    regex = re.compile(
        r"_(\d{4}-\d{2})_senza_percorso\.csv$"
    )

    for path in files:

        match = regex.search(path.name)

        if match is None:
            print(
                f"WARNING: filename does not match expected pattern: "
                f"{path.name}"
            )
            continue

        period = match.group(1)

        discovered.append(
            (period, path)
        )

    if not discovered:
        raise RuntimeError(
            "Files exist, but none matched expected Lime filename format."
        )

    print("\nDiscovered Lime files:")

    for period, path in discovered:
        print(f"  {period} -> {path.name}")

    return discovered


# ============================================================
# 5. HAVERSINE
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):

    earth_radius_km = 6371.0088

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2.0) ** 2
    )

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return earth_radius_km * c


# ============================================================
# 6. LOAD ONE MONTH
# ============================================================

def load_month(period, path):

    df = pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
        low_memory=False,
    )

    print(
        f"\nLoading {period}: "
        f"{len(df):,} rows"
    )

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
        np.arange(1, len(df) + 1)
    )

    return df


# ============================================================
# 7. SCHEMA VALIDATION
# ============================================================

def validate_schema(df, period):

    actual_columns = [
        col for col in df.columns
        if col not in [
            "SOURCE_PERIOD",
            "SOURCE_FILE",
            "SOURCE_ROW",
        ]
    ]

    missing = [
        col for col in EXPECTED_COLUMNS
        if col not in actual_columns
    ]

    unexpected = [
        col for col in actual_columns
        if col not in EXPECTED_COLUMNS
    ]

    if missing:
        raise ValueError(
            f"{period}: missing columns: {missing}"
        )

    if unexpected:
        print(
            f"WARNING {period}: unexpected columns: "
            f"{unexpected}"
        )

    if actual_columns != EXPECTED_COLUMNS:
        print(
            f"WARNING {period}: same columns exist "
            f"but column order differs."
        )


# ============================================================
# 8. TYPE CONVERSION
# ============================================================

def convert_types(df):

    df = df.copy()

    # Temporal
    df["START_TIME"] = pd.to_datetime(
        df["DATAORA_INIZIO"],
        errors="coerce"
    )

    df["END_TIME_RAW"] = pd.to_datetime(
        df["DATAORA_FINE"],
        errors="coerce"
    )

    # Numeric
    numeric_columns = [
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
        "DISTANZA_KM",
        "DURATA_MIN",
        "BATTERIA_INIZIO_CORSA",
        "BATTERIA_FINE_CORSA",
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    return df


# ============================================================
# 9. DERIVED QUALITY VARIABLES
# ============================================================

def add_quality_features(df):

    df = df.copy()

    # --------------------------------------------------------
    # Exact elapsed duration from timestamps
    # --------------------------------------------------------

    df["DURATION_FROM_TIMESTAMPS_MIN"] = (
        df["END_TIME_RAW"]
        - df["START_TIME"]
    ).dt.total_seconds() / 60

    df["DURATION_DIFFERENCE_MIN"] = (
        df["DURATION_FROM_TIMESTAMPS_MIN"]
        - df["DURATA_MIN"]
    )

    # --------------------------------------------------------
    # Lime reported speed
    #
    # IMPORTANT:
    # DISTANZA_KM and DURATA_MIN appear rounded.
    # This speed is therefore diagnostic only.
    # --------------------------------------------------------

    valid_reported_speed = (
        (df["DISTANZA_KM"] > 0)
        & (df["DURATA_MIN"] > 0)
    )

    df["REPORTED_SPEED_KMH"] = np.nan

    df.loc[
        valid_reported_speed,
        "REPORTED_SPEED_KMH"
    ] = (
        df.loc[
            valid_reported_speed,
            "DISTANZA_KM"
        ]
        /
        (
            df.loc[
                valid_reported_speed,
                "DURATA_MIN"
            ]
            / 60
        )
    )

    # --------------------------------------------------------
    # Haversine displacement
    # --------------------------------------------------------

    coordinate_columns = [
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
    ]

    complete_coordinates = (
        df[coordinate_columns]
        .notna()
        .all(axis=1)
    )

    df["HAVERSINE_KM"] = np.nan

    df.loc[
        complete_coordinates,
        "HAVERSINE_KM"
    ] = haversine_km(
        df.loc[
            complete_coordinates,
            "LATITUDINE_INIZIO_CORSA"
        ],
        df.loc[
            complete_coordinates,
            "LONGITUTIDE_INIZIO_CORSA"
        ],
        df.loc[
            complete_coordinates,
            "LATITUDINE_FINE_CORSA"
        ],
        df.loc[
            complete_coordinates,
            "LONGITUTIDE_FINE_CORSA"
        ],
    )

    # --------------------------------------------------------
    # Haversine speed using precise timestamp duration
    # --------------------------------------------------------

    valid_exact_duration = (
        df["DURATION_FROM_TIMESTAMPS_MIN"] > 0
    )

    df["HAVERSINE_SPEED_TS_KMH"] = np.nan

    df.loc[
        valid_exact_duration,
        "HAVERSINE_SPEED_TS_KMH"
    ] = (
        df.loc[
            valid_exact_duration,
            "HAVERSINE_KM"
        ]
        /
        (
            df.loc[
                valid_exact_duration,
                "DURATION_FROM_TIMESTAMPS_MIN"
            ]
            / 60
        )
    )

    # --------------------------------------------------------
    # Same start/end GPS
    # --------------------------------------------------------

    df["SAME_START_END_COORDS"] = (
        (
            df["LATITUDINE_INIZIO_CORSA"]
            == df["LATITUDINE_FINE_CORSA"]
        )
        &
        (
            df["LONGITUTIDE_INIZIO_CORSA"]
            == df["LONGITUTIDE_FINE_CORSA"]
        )
    )

    # --------------------------------------------------------
    # Battery variation
    # --------------------------------------------------------

    df["BATTERY_CHANGE"] = (
        df["BATTERIA_FINE_CORSA"]
        - df["BATTERIA_INIZIO_CORSA"]
    )

    # --------------------------------------------------------
    # Month from timestamp
    # --------------------------------------------------------

    df["START_PERIOD"] = (
        df["START_TIME"]
        .dt.to_period("M")
        .astype("string")
    )

    return df


# ============================================================
# 10. FLAGS
# ============================================================

def add_audit_flags(df):

    df = df.copy()

    essential_columns = [
        "ID_VEICOLO",
        "START_TIME",
        "END_TIME_RAW",
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
        "DISTANZA_KM",
        "DURATA_MIN",
    ]

    df["FLAG_MISSING_ESSENTIAL"] = (
        df[essential_columns]
        .isna()
        .any(axis=1)
    )

    # Distance:
    # zero and negative are separated intentionally.
    df["FLAG_DISTANCE_ZERO"] = (
        df["DISTANZA_KM"] == 0
    )

    df["FLAG_DISTANCE_NEGATIVE"] = (
        df["DISTANZA_KM"] < 0
    )

    df["FLAG_DURATION_NON_POSITIVE"] = (
        df["DURATA_MIN"].notna()
        & (df["DURATA_MIN"] <= 0)
    )

    df["FLAG_TIMESTAMP_DURATION_NON_POSITIVE"] = (
        df["DURATION_FROM_TIMESTAMPS_MIN"].notna()
        & (
            df["DURATION_FROM_TIMESTAMPS_MIN"]
            <= 0
        )
    )

    df["FLAG_REVERSED_TIMESTAMP"] = (
        df["START_TIME"].notna()
        & df["END_TIME_RAW"].notna()
        & (
            df["END_TIME_RAW"]
            < df["START_TIME"]
        )
    )

    # Compare integer DURATA_MIN with precise timestamps.
    df["FLAG_DURATION_DIFFERENCE_GT1"] = (
        df["DURATION_DIFFERENCE_MIN"]
        .abs()
        > DURATION_DIFFERENCE_CHECK_MIN
    )

    df["FLAG_GPS_JUMP_OVER_30KM"] = (
        df["HAVERSINE_KM"].notna()
        & (
            df["HAVERSINE_KM"]
            > GPS_JUMP_CHECK_KM
        )
    )

    df["FLAG_HAVERSINE_SPEED_OVER_40"] = (
        df["HAVERSINE_SPEED_TS_KMH"].notna()
        & (
            df["HAVERSINE_SPEED_TS_KMH"]
            > HAVERSINE_SPEED_CHECK_KMH
        )
    )

    # --------------------------------------------------------
    # Broad Torino location check
    # Audit only — NOT a final spatial filter.
    # --------------------------------------------------------

    start_outside = (
        (df["LATITUDINE_INIZIO_CORSA"] < TORINO_LAT_MIN)
        | (df["LATITUDINE_INIZIO_CORSA"] > TORINO_LAT_MAX)
        | (df["LONGITUTIDE_INIZIO_CORSA"] < TORINO_LON_MIN)
        | (df["LONGITUTIDE_INIZIO_CORSA"] > TORINO_LON_MAX)
    )

    end_outside = (
        (df["LATITUDINE_FINE_CORSA"] < TORINO_LAT_MIN)
        | (df["LATITUDINE_FINE_CORSA"] > TORINO_LAT_MAX)
        | (df["LONGITUTIDE_FINE_CORSA"] < TORINO_LON_MIN)
        | (df["LONGITUTIDE_FINE_CORSA"] > TORINO_LON_MAX)
    )

    df["FLAG_OUTSIDE_TORINO_BROAD"] = (
        start_outside
        | end_outside
    )

    # --------------------------------------------------------
    # Battery
    # --------------------------------------------------------

    df["FLAG_BATTERY_START_INVALID"] = (
        df["BATTERIA_INIZIO_CORSA"].notna()
        &
        (
            (df["BATTERIA_INIZIO_CORSA"] < 0)
            | (df["BATTERIA_INIZIO_CORSA"] > 100)
        )
    )

    df["FLAG_BATTERY_END_INVALID"] = (
        df["BATTERIA_FINE_CORSA"].notna()
        &
        (
            (df["BATTERIA_FINE_CORSA"] < 0)
            | (df["BATTERIA_FINE_CORSA"] > 100)
        )
    )

    df["FLAG_BATTERY_INCREASE_DURING_TRIP"] = (
        df["BATTERY_CHANGE"].notna()
        & (df["BATTERY_CHANGE"] > 0)
    )

    # --------------------------------------------------------
    # File / month consistency
    # --------------------------------------------------------

    df["FLAG_START_MONTH_MISMATCH"] = (
        df["START_PERIOD"].notna()
        &
        (
            df["START_PERIOD"]
            != df["SOURCE_PERIOD"]
        )
    )

    df["FLAG_ANNO_MESE_MISMATCH"] = (
        df["ANNO_MESE"].notna()
        &
        (
            df["ANNO_MESE"].astype(str)
            != df["SOURCE_PERIOD"]
        )
    )

    return df


# ============================================================
# 11. GRANULARITY CHECK
# ============================================================

def count_non_integer(series):

    x = series.dropna()

    if x.empty:
        return 0

    return int(
        (
            ~np.isclose(
                x,
                np.round(x),
                atol=1e-9
            )
        ).sum()
    )


# ============================================================
# 12. BUILD MONTHLY SUMMARY
# ============================================================

def build_summary(
    df,
    period,
    exact_duplicate_rows,
    cross_file_duplicate_candidates,
):

    reservation_values = sorted(
        df["RISERVATO"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    summary = {
        "period": period,
        "year": int(period[:4]),

        "rows": len(df),

        "date_min":
            df["START_TIME"].min(),

        "date_max":
            df["START_TIME"].max(),

        "unique_vehicles":
            df["ID_VEICOLO"].nunique(
                dropna=True
            ),

        "exact_duplicate_rows":
            exact_duplicate_rows,

        "cross_file_duplicate_candidates":
            cross_file_duplicate_candidates,

        "missing_vehicle_id":
            int(
                df["ID_VEICOLO"]
                .isna()
                .sum()
            ),

        "invalid_start_datetime":
            int(
                df["START_TIME"]
                .isna()
                .sum()
            ),

        "invalid_end_datetime":
            int(
                df["END_TIME_RAW"]
                .isna()
                .sum()
            ),

        "missing_start_coordinates":
            int(
                df[
                    [
                        "LATITUDINE_INIZIO_CORSA",
                        "LONGITUTIDE_INIZIO_CORSA",
                    ]
                ]
                .isna()
                .any(axis=1)
                .sum()
            ),

        "missing_end_coordinates":
            int(
                df[
                    [
                        "LATITUDINE_FINE_CORSA",
                        "LONGITUTIDE_FINE_CORSA",
                    ]
                ]
                .isna()
                .any(axis=1)
                .sum()
            ),

        "missing_distance":
            int(
                df["DISTANZA_KM"]
                .isna()
                .sum()
            ),

        "distance_zero":
            int(
                df["FLAG_DISTANCE_ZERO"]
                .sum()
            ),

        "distance_negative":
            int(
                df["FLAG_DISTANCE_NEGATIVE"]
                .sum()
            ),

        "missing_duration":
            int(
                df["DURATA_MIN"]
                .isna()
                .sum()
            ),

        "duration_non_positive":
            int(
                df[
                    "FLAG_DURATION_NON_POSITIVE"
                ]
                .sum()
            ),

        "timestamp_duration_non_positive":
            int(
                df[
                    "FLAG_TIMESTAMP_DURATION_NON_POSITIVE"
                ]
                .sum()
            ),

        "reversed_timestamp":
            int(
                df[
                    "FLAG_REVERSED_TIMESTAMP"
                ]
                .sum()
            ),

        "duration_difference_gt1min":
            int(
                df[
                    "FLAG_DURATION_DIFFERENCE_GT1"
                ]
                .sum()
            ),

        "same_start_end_coords":
            int(
                df["SAME_START_END_COORDS"]
                .sum()
            ),

        "haversine_over_30km":
            int(
                df[
                    "FLAG_GPS_JUMP_OVER_30KM"
                ]
                .sum()
            ),

        "haversine_speed_over_40":
            int(
                df[
                    "FLAG_HAVERSINE_SPEED_OVER_40"
                ]
                .sum()
            ),

        "outside_torino_broad":
            int(
                df[
                    "FLAG_OUTSIDE_TORINO_BROAD"
                ]
                .sum()
            ),

        "distance_non_integer":
            count_non_integer(
                df["DISTANZA_KM"]
            ),

        "duration_non_integer":
            count_non_integer(
                df["DURATA_MIN"]
            ),

        "missing_battery_start":
            int(
                df["BATTERIA_INIZIO_CORSA"]
                .isna()
                .sum()
            ),

        "missing_battery_end":
            int(
                df["BATTERIA_FINE_CORSA"]
                .isna()
                .sum()
            ),

        "battery_start_invalid":
            int(
                df[
                    "FLAG_BATTERY_START_INVALID"
                ]
                .sum()
            ),

        "battery_end_invalid":
            int(
                df[
                    "FLAG_BATTERY_END_INVALID"
                ]
                .sum()
            ),

        "battery_increase_during_trip":
            int(
                df[
                    "FLAG_BATTERY_INCREASE_DURING_TRIP"
                ]
                .sum()
            ),

        "start_month_mismatch":
            int(
                df[
                    "FLAG_START_MONTH_MISMATCH"
                ]
                .sum()
            ),

        "anno_mese_mismatch":
            int(
                df[
                    "FLAG_ANNO_MESE_MISMATCH"
                ]
                .sum()
            ),

        "reservation_values":
            "|".join(
                reservation_values
            ),
    }

    return pd.DataFrame([summary])


# ============================================================
# 13. SAVE MONTHLY INTERIM
# ============================================================

def save_interim(df, period):

    output = (
        INTERIM_DIR
        / f"lime_{period}_typed_flagged.parquet"
    )

    df.to_parquet(
        output,
        index=False
    )


# ============================================================
# 14. EXPORT CRITICAL ANOMALIES
# ============================================================

def export_critical_anomalies(df, period):

    # Zero distance is deliberately NOT included here.
    # It may simply reflect Lime's coarse distance rounding.

    critical_flags = [
        "FLAG_MISSING_ESSENTIAL",
        "FLAG_DISTANCE_NEGATIVE",
        "FLAG_REVERSED_TIMESTAMP",
        "FLAG_GPS_JUMP_OVER_30KM",
        "FLAG_HAVERSINE_SPEED_OVER_40",
        "FLAG_OUTSIDE_TORINO_BROAD",
        "FLAG_BATTERY_START_INVALID",
        "FLAG_BATTERY_END_INVALID",
        "FLAG_START_MONTH_MISMATCH",
        "FLAG_ANNO_MESE_MISMATCH",
    ]

    mask = (
        df[critical_flags]
        .any(axis=1)
    )

    critical = df.loc[
        mask
    ].copy()

    output = (
        AUDIT_DIR
        / f"lime_{period}_critical_anomalies.csv"
    )

    critical.to_csv(
        output,
        index=False
    )

    return len(critical)


# ============================================================
# 15. MAIN
# ============================================================

def main():

    files = discover_files()

    summaries = []

    seen_hashes = set()

    vehicles_by_year = defaultdict(set)

    min_date_by_year = {}
    max_date_by_year = {}

    for period, path in files:

        df = load_month(
            period,
            path
        )

        validate_schema(
            df,
            period
        )

        # ----------------------------------------------------
        # Exact duplicates based on original Lime fields
        # ----------------------------------------------------

        exact_duplicate_rows = int(
            df.duplicated(
                subset=EXPECTED_COLUMNS,
                keep=False
            ).sum()
        )

        # Hash-based cross-file duplicate check
        row_hashes = pd.util.hash_pandas_object(
            df[EXPECTED_COLUMNS],
            index=False
        ).astype("uint64")

        cross_file_duplicate_candidates = int(
            row_hashes.isin(
                seen_hashes
            ).sum()
        )

        seen_hashes.update(
            row_hashes.tolist()
        )

        # ----------------------------------------------------
        # Conversion and features
        # ----------------------------------------------------

        df = convert_types(df)

        df = add_quality_features(df)

        df = add_audit_flags(df)

        # ----------------------------------------------------
        # Update yearly vehicle sets
        # ----------------------------------------------------

        year = int(
            period[:4]
        )

        vehicles_by_year[year].update(
            df["ID_VEICOLO"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        current_min = (
            df["START_TIME"].min()
        )

        current_max = (
            df["START_TIME"].max()
        )

        if year not in min_date_by_year:
            min_date_by_year[year] = current_min
            max_date_by_year[year] = current_max
        else:
            min_date_by_year[year] = min(
                min_date_by_year[year],
                current_min
            )

            max_date_by_year[year] = max(
                max_date_by_year[year],
                current_max
            )

        # ----------------------------------------------------
        # Audit output
        # ----------------------------------------------------

        summary = build_summary(
            df,
            period,
            exact_duplicate_rows,
            cross_file_duplicate_candidates,
        )

        summaries.append(
            summary
        )

        critical_count = (
            export_critical_anomalies(
                df,
                period
            )
        )

        save_interim(
            df,
            period
        )

        print(
            f"{period}: "
            f"rows={len(df):,} | "
            f"vehicles={df['ID_VEICOLO'].nunique():,} | "
            f"zero_dist={int(df['FLAG_DISTANCE_ZERO'].sum()):,} | "
            f"dur<=0={int(df['FLAG_DURATION_NON_POSITIVE'].sum()):,} | "
            f"reversed={int(df['FLAG_REVERSED_TIMESTAMP'].sum()):,} | "
            f"GPS>30km={int(df['FLAG_GPS_JUMP_OVER_30KM'].sum()):,} | "
            f"HavSpeed>40={int(df['FLAG_HAVERSINE_SPEED_OVER_40'].sum()):,} | "
            f"critical={critical_count:,}"
        )

    # ========================================================
    # MONTHLY SUMMARY
    # ========================================================

    monthly = pd.concat(
        summaries,
        ignore_index=True
    )

    monthly_path = (
        AUDIT_DIR
        / "lime_monthly_raw_audit.csv"
    )

    monthly.to_csv(
        monthly_path,
        index=False
    )

    # ========================================================
    # YEARLY SUMMARY
    # ========================================================

    count_columns = [
        "rows",
        "exact_duplicate_rows",
        "cross_file_duplicate_candidates",
        "missing_vehicle_id",
        "invalid_start_datetime",
        "invalid_end_datetime",
        "missing_start_coordinates",
        "missing_end_coordinates",
        "missing_distance",
        "distance_zero",
        "distance_negative",
        "missing_duration",
        "duration_non_positive",
        "timestamp_duration_non_positive",
        "reversed_timestamp",
        "duration_difference_gt1min",
        "same_start_end_coords",
        "haversine_over_30km",
        "haversine_speed_over_40",
        "outside_torino_broad",
        "distance_non_integer",
        "duration_non_integer",
        "missing_battery_start",
        "missing_battery_end",
        "battery_start_invalid",
        "battery_end_invalid",
        "battery_increase_during_trip",
        "start_month_mismatch",
        "anno_mese_mismatch",
    ]

    yearly = (
        monthly
        .groupby("year")[count_columns]
        .sum()
        .reset_index()
    )

    yearly["unique_vehicles"] = (
        yearly["year"]
        .map(
            lambda y: len(
                vehicles_by_year[int(y)]
            )
        )
    )

    yearly["date_min"] = (
        yearly["year"]
        .map(min_date_by_year)
    )

    yearly["date_max"] = (
        yearly["year"]
        .map(max_date_by_year)
    )

    yearly_path = (
        AUDIT_DIR
        / "lime_yearly_raw_audit.csv"
    )

    yearly.to_csv(
        yearly_path,
        index=False
    )

    # ========================================================
    # FINAL TERMINAL OUTPUT
    # ========================================================

    print("\n")
    print("=" * 100)
    print("LIME RAW AUDIT COMPLETED")
    print("=" * 100)

    print("\nMonthly coverage:")

    print(
        monthly[
            [
                "period",
                "rows",
                "date_min",
                "date_max",
                "unique_vehicles",
            ]
        ].to_string(
            index=False
        )
    )

    print("\nYearly audit summary:")

    display_columns = [
        "year",
        "rows",
        "unique_vehicles",
        "date_min",
        "date_max",
        "exact_duplicate_rows",
        "cross_file_duplicate_candidates",
        "missing_vehicle_id",
        "invalid_start_datetime",
        "invalid_end_datetime",
        "missing_start_coordinates",
        "missing_end_coordinates",
        "distance_zero",
        "distance_negative",
        "duration_non_positive",
        "timestamp_duration_non_positive",
        "reversed_timestamp",
        "duration_difference_gt1min",
        "same_start_end_coords",
        "haversine_over_30km",
        "haversine_speed_over_40",
        "outside_torino_broad",
        "distance_non_integer",
        "duration_non_integer",
        "missing_battery_start",
        "missing_battery_end",
        "battery_start_invalid",
        "battery_end_invalid",
        "battery_increase_during_trip",
        "start_month_mismatch",
        "anno_mese_mismatch",
    ]

    print(
        yearly[
            display_columns
        ].to_string(
            index=False
        )
    )

    print(
        f"\nMonthly audit saved -> {monthly_path}"
    )

    print(
        f"Yearly audit saved -> {yearly_path}"
    )

    print(
        "\nIMPORTANT:"
        "\nNo Lime records were deleted."
        "\nZero-distance records are only flagged, not classified as invalid."
        "\nInterim monthly Parquet files were generated for inspection."
    )


if __name__ == "__main__":
    main()