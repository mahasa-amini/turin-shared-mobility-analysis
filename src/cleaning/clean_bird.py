from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "bird"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "bird"
AUDIT_DIR = PROJECT_ROOT / "audit" / "bird"

INTERIM_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


FILES = {
    2024: RAW_DIR / "Bird Torino - 2024 - Sheet1.csv",
    2025: RAW_DIR / "Bird Torino - 2025 (fino il 18_11_2025) - Sheet1.csv",
}


# ============================================================
# 2. CONSTANTS FOR AUDIT
#    IMPORTANT: these are audit thresholds, not yet final
#    cleaning rules.
# ============================================================

SPEED_CHECK_KMH = 30
GPS_JUMP_CHECK_KM = 30
SMALL_DISPLACEMENT_KM = 0.020  # 20 meters


# ============================================================
# 3. HAVERSINE FUNCTION
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Vectorized Haversine distance between origin and destination.
    Returns straight-line displacement in kilometers.
    """

    earth_radius_km = 6371.0088

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    )

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return earth_radius_km * c


# ============================================================
# 4. LOAD RAW DATA
# ============================================================

def load_bird(year, file_path):
    print(f"\n{'=' * 70}")
    print(f"Loading Bird {year}")
    print(f"File: {file_path.name}")
    print(f"{'=' * 70}")

    if not file_path.exists():
        raise FileNotFoundError(
            f"\nFile not found:\n{file_path}\n"
            f"Check the exact filename inside data/raw/bird/"
        )

    # Preserve literal "N/A" in PERCORSO.
    # Only empty strings are treated as missing.
    df = pd.read_csv(
        file_path,
        keep_default_na=False,
        na_values=[""],
        low_memory=False,
    )

    print(f"Raw rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    # Keep original row location for traceability
    df.insert(0, "SOURCE_YEAR", year)
    df.insert(1, "SOURCE_ROW", np.arange(1, len(df) + 1))
    df.insert(2, "SOURCE_FILE", file_path.name)

    return df


# ============================================================
# 5. SCHEMA VALIDATION
# ============================================================

EXPECTED_COLUMNS = [
    "ID_VEICOLO",
    "DATAORA_INIZIO",
    "DATAORA_FINE",
    "LATITUDINE_INIZIO_CORSA",
    "LONGITUTIDE_INIZIO_CORSA",
    "LATITUDINE_FINE_CORSA",
    "LONGITUTIDE_FINE_CORSA",
    "PERCORSO",
    "DISTANZA_KM",
    "DURATA_MIN",
    "RISERVATO",
]


def validate_schema(df, year):
    actual_columns = [
        c for c in df.columns
        if c not in ["SOURCE_YEAR", "SOURCE_ROW", "SOURCE_FILE"]
    ]

    missing = [c for c in EXPECTED_COLUMNS if c not in actual_columns]
    unexpected = [c for c in actual_columns if c not in EXPECTED_COLUMNS]

    if missing:
        raise ValueError(
            f"Bird {year}: missing expected columns: {missing}"
        )

    if unexpected:
        print(f"WARNING - unexpected columns in {year}: {unexpected}")

    print("Schema validation: OK")


# ============================================================
# 6. TYPE CONVERSION
# ============================================================

def convert_types(df):
    df = df.copy()

    # Datetime
    df["START_TIME"] = pd.to_datetime(
        df["DATAORA_INIZIO"],
        errors="coerce"
    )

    df["END_TIME_RAW"] = pd.to_datetime(
        df["DATAORA_FINE"],
        errors="coerce"
    )

    # Numeric columns
    numeric_columns = [
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
        "DISTANZA_KM",
        "DURATA_MIN",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ============================================================
# 7. DERIVED QUALITY-CHECK VARIABLES
# ============================================================

def add_quality_features(df):
    df = df.copy()

    # --------------------------------------------------------
    # Duration derived from raw timestamps
    # --------------------------------------------------------
    df["DURATION_FROM_TIMESTAMPS_MIN"] = (
        df["END_TIME_RAW"] - df["START_TIME"]
    ).dt.total_seconds() / 60

    df["DURATION_DIFFERENCE_MIN"] = (
        df["DURATION_FROM_TIMESTAMPS_MIN"]
        - df["DURATA_MIN"]
    )

    # Reconstructed end time using operator-reported duration.
    # Do not replace the raw timestamp; keep both.
    df["END_TIME_RECONSTRUCTED"] = (
        df["START_TIME"]
        + pd.to_timedelta(df["DURATA_MIN"], unit="m")
    )

    # --------------------------------------------------------
    # Speed based on Bird's reported distance
    # --------------------------------------------------------
    valid_speed_input = (
        (df["DISTANZA_KM"] > 0)
        & (df["DURATA_MIN"] > 0)
    )

    df["SPEED_KMH"] = np.nan

    df.loc[valid_speed_input, "SPEED_KMH"] = (
        df.loc[valid_speed_input, "DISTANZA_KM"]
        / (df.loc[valid_speed_input, "DURATA_MIN"] / 60)
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

    valid_coordinates = df[coordinate_columns].notna().all(axis=1)

    df["HAVERSINE_KM"] = np.nan

    df.loc[valid_coordinates, "HAVERSINE_KM"] = haversine_km(
        df.loc[valid_coordinates, "LATITUDINE_INIZIO_CORSA"],
        df.loc[valid_coordinates, "LONGITUTIDE_INIZIO_CORSA"],
        df.loc[valid_coordinates, "LATITUDINE_FINE_CORSA"],
        df.loc[valid_coordinates, "LONGITUTIDE_FINE_CORSA"],
    )

    # --------------------------------------------------------
    # Exact same origin / destination coordinates
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

    return df


# ============================================================
# 8. FLAG SUSPICIOUS RECORDS
#    These are CANDIDATES only.
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
        df[essential_columns].isna().any(axis=1)
    )

    df["FLAG_DISTANCE_NON_POSITIVE"] = (
        df["DISTANZA_KM"].notna()
        & (df["DISTANZA_KM"] <= 0)
    )

    df["FLAG_DURATION_NON_POSITIVE"] = (
        df["DURATA_MIN"].notna()
        & (df["DURATA_MIN"] <= 0)
    )

    df["FLAG_SPEED_OVER_30"] = (
        df["SPEED_KMH"].notna()
        & (df["SPEED_KMH"] > SPEED_CHECK_KMH)
    )

    df["FLAG_REVERSED_TIMESTAMP"] = (
        df["START_TIME"].notna()
        & df["END_TIME_RAW"].notna()
        & (df["END_TIME_RAW"] < df["START_TIME"])
    )

    df["FLAG_SMALL_DISPLACEMENT"] = (
        df["HAVERSINE_KM"].notna()
        & (df["HAVERSINE_KM"] < SMALL_DISPLACEMENT_KM)
    )

    df["FLAG_GPS_JUMP"] = (
        df["HAVERSINE_KM"].notna()
        & (df["HAVERSINE_KM"] > GPS_JUMP_CHECK_KM)
    )

    # Difference of approximately one hour:
    # useful for inspecting possible DST effects.
    df["FLAG_POSSIBLE_DST"] = (
        df["DURATION_DIFFERENCE_MIN"].abs().between(
            55,
            65,
            inclusive="both"
        )
    )

    return df


# ============================================================
# 9. BUILD AUDIT SUMMARY
# ============================================================

def build_audit_summary(df, year):
    raw_columns = EXPECTED_COLUMNS

    exact_duplicates = df.duplicated(
        subset=raw_columns,
        keep=False
    )

    summary = {
        "year": year,
        "raw_rows": len(df),

        "exact_duplicate_rows":
            int(exact_duplicates.sum()),

        "missing_vehicle_id":
            int(df["ID_VEICOLO"].isna().sum()),

        "invalid_start_datetime":
            int(df["START_TIME"].isna().sum()),

        "invalid_end_datetime":
            int(df["END_TIME_RAW"].isna().sum()),

        "missing_start_coordinates":
            int(
                df[
                    [
                        "LATITUDINE_INIZIO_CORSA",
                        "LONGITUTIDE_INIZIO_CORSA",
                    ]
                ].isna().any(axis=1).sum()
            ),

        "missing_end_coordinates":
            int(
                df[
                    [
                        "LATITUDINE_FINE_CORSA",
                        "LONGITUTIDE_FINE_CORSA",
                    ]
                ].isna().any(axis=1).sum()
            ),

        "missing_distance":
            int(df["DISTANZA_KM"].isna().sum()),

        "missing_duration":
            int(df["DURATA_MIN"].isna().sum()),

        "distance_non_positive":
            int(df["FLAG_DISTANCE_NON_POSITIVE"].sum()),

        "duration_non_positive":
            int(df["FLAG_DURATION_NON_POSITIVE"].sum()),

        "speed_over_30_kmh":
            int(df["FLAG_SPEED_OVER_30"].sum()),

        "reversed_timestamp":
            int(df["FLAG_REVERSED_TIMESTAMP"].sum()),

        "same_start_end_coordinates":
            int(df["SAME_START_END_COORDS"].sum()),

        "haversine_under_20m":
            int(df["FLAG_SMALL_DISPLACEMENT"].sum()),

        "haversine_over_30km":
            int(df["FLAG_GPS_JUMP"].sum()),

        "possible_dst_records":
            int(df["FLAG_POSSIBLE_DST"].sum()),

        "unique_vehicles":
            int(df["ID_VEICOLO"].nunique(dropna=True)),
    }

    return pd.DataFrame([summary])


# ============================================================
# 10. EXPORT SUSPICIOUS ROWS FOR MANUAL INSPECTION
# ============================================================

def export_suspicious_rows(df, year):
    flag_columns = [
        "FLAG_MISSING_ESSENTIAL",
        "FLAG_DISTANCE_NON_POSITIVE",
        "FLAG_DURATION_NON_POSITIVE",
        "FLAG_SPEED_OVER_30",
        "FLAG_REVERSED_TIMESTAMP",
        "FLAG_SMALL_DISPLACEMENT",
        "FLAG_GPS_JUMP",
        "FLAG_POSSIBLE_DST",
    ]

    suspicious_mask = df[flag_columns].any(axis=1)

    suspicious = df.loc[suspicious_mask].copy()

    suspicious_path = (
        AUDIT_DIR
        / f"bird_{year}_suspicious_rows.csv"
    )

    suspicious.to_csv(
        suspicious_path,
        index=False
    )

    print(
        f"Suspicious rows exported: "
        f"{len(suspicious):,} -> {suspicious_path}"
    )


# ============================================================
# 11. SAVE INTERIM DATA
# ============================================================

def save_interim(df, year):
    output_path = (
        INTERIM_DIR
        / f"bird_{year}_typed_flagged.parquet"
    )

    df.to_parquet(
        output_path,
        index=False
    )

    print(f"Interim dataset saved -> {output_path}")


# ============================================================
# 12. MAIN PIPELINE
# ============================================================

def main():
    audit_tables = []

    for year, file_path in FILES.items():

        df = load_bird(
            year=year,
            file_path=file_path
        )

        validate_schema(
            df=df,
            year=year
        )

        df = convert_types(df)

        df = add_quality_features(df)

        df = add_audit_flags(df)

        audit = build_audit_summary(
            df=df,
            year=year
        )

        audit_tables.append(audit)

        export_suspicious_rows(
            df=df,
            year=year
        )

        save_interim(
            df=df,
            year=year
        )

        print("\nAudit summary:")
        print(
            audit
            .set_index("year")
            .T
            .to_string()
        )

    # --------------------------------------------------------
    # Combined audit table
    # --------------------------------------------------------
    final_audit = pd.concat(
        audit_tables,
        ignore_index=True
    )

    audit_path = (
        AUDIT_DIR
        / "bird_cleaning_audit_summary.csv"
    )

    final_audit.to_csv(
        audit_path,
        index=False
    )

    print("\n" + "=" * 70)
    print("BIRD INITIAL AUDIT COMPLETED")
    print("=" * 70)

    print("\nCombined summary:")
    print(
        final_audit.to_string(index=False)
    )

    print(
        f"\nAudit table saved -> {audit_path}"
    )

    print(
        "\nIMPORTANT:"
        "\nNo rows have been deleted."
        "\nThis stage only typed, enriched, and flagged the raw data."
    )


if __name__ == "__main__":
    main()