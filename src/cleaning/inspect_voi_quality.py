from pathlib import Path
import re

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "voi"
AUDIT_DIR = PROJECT_ROOT / "audit" / "voi"

AUDIT_DIR.mkdir(parents=True, exist_ok=True)


TRIP_ID = "Identificativo noleggio"

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
# HELPERS
# ============================================================

def title(text):
    print("\n" + "=" * 100)
    print(text)
    print("=" * 100)


def discover_files():

    files = sorted(
        INTERIM_DIR.glob(
            "voi_*_typed_flagged.parquet"
        )
    )

    pattern = re.compile(
        r"voi_(\d{4}-\d{2})_typed_flagged\.parquet"
    )

    output = []

    for path in files:

        match = pattern.fullmatch(path.name)

        if match:
            output.append(
                (
                    match.group(1),
                    path
                )
            )

    if not output:
        raise FileNotFoundError(
            f"No VOI interim files in {INTERIM_DIR}"
        )

    return output


def reservation_string(series):

    values = (
        series
        .astype("string")
        .fillna("<MISSING>")
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return "|".join(
        map(str, values)
    )


# ============================================================
# LOAD ALL INTERIM DATA
# ============================================================

def load_all():

    parts = []

    for period, path in discover_files():

        df = pd.read_parquet(path)

        parts.append(df)

    df = pd.concat(
        parts,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Harmonize string-like columns across monthly files
    #
    # Some VOI Excel files store compact timestamps as integers,
    # while others store them as strings. After concatenation,
    # this creates mixed object dtypes that PyArrow cannot save
    # reliably to a single Parquet file.
    # --------------------------------------------------------

    string_columns = [
        "SOURCE_PERIOD",
        "SOURCE_FILE",
        "Identificativo noleggio",
        "Targa veicolo",
        "Data inizio corsa",
        "Data fine corsa",
        "Prenotazione",
        "START_TIMESTAMP_CODE",
        "END_TIMESTAMP_CODE",
    ]

    for col in string_columns:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
            )
    return df


# ============================================================
# DUPLICATE STRUCTURE + CANONICAL PREVIEW
# ============================================================

def build_canonical_preview(df):

    title("DUPLICATE STRUCTURE")

    group_size = (
        df.groupby(TRIP_ID)
        .size()
        .rename("DUPLICATE_GROUP_SIZE")
    )

    print(
        f"Raw rows: {len(df):,}"
    )

    print(
        f"Unique trip IDs: "
        f"{df[TRIP_ID].nunique():,}"
    )

    print(
        f"Excess rows: "
        f"{len(df) - df[TRIP_ID].nunique():,}"
    )

    print("\nDuplicate group-size distribution:")

    print(
        group_size
        .value_counts()
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # Verify that trip-defining fields do NOT conflict
    # --------------------------------------------------------

    defining_variants = (
        df[
            [TRIP_ID]
            + TRIP_DEFINING_COLUMNS
        ]
        .drop_duplicates()
        .groupby(TRIP_ID)
        .size()
    )

    conflicting_trip_definition = (
        defining_variants > 1
    )

    print(
        "\nTrip IDs with conflicting trip-defining fields: "
        f"{int(conflicting_trip_definition.sum()):,}"
    )

    assert not conflicting_trip_definition.any(), (
        "Unexpected conflict in trip-defining fields."
    )

    # --------------------------------------------------------
    # Reservation conflicts
    # --------------------------------------------------------

    reservation_info = (
        df.groupby(TRIP_ID)["Prenotazione"]
        .agg(
            RESERVATION_VARIANTS=lambda x:
            x.astype("string")
            .fillna("<MISSING>")
            .nunique(),

            RESERVATION_VALUES=reservation_string,
        )
    )

    reservation_info[
        "PRENOTAZIONE_CONFLICT"
    ] = (
        reservation_info[
            "RESERVATION_VARIANTS"
        ] > 1
    )

    conflicts = reservation_info.loc[
        reservation_info[
            "PRENOTAZIONE_CONFLICT"
        ]
    ]

    print(
        f"\nReservation-conflict trip IDs: "
        f"{len(conflicts):,}"
    )

    if not conflicts.empty:

        print(
            "\nReservation conflict combinations:"
        )

        print(
            conflicts[
                "RESERVATION_VALUES"
            ]
            .value_counts()
            .to_string()
        )

    # --------------------------------------------------------
    # Cross-file duplicate groups
    # --------------------------------------------------------

    files_per_trip = (
        df.groupby(TRIP_ID)[
            "SOURCE_FILE"
        ]
        .nunique()
    )

    print(
        "\nDuplicate trip IDs spanning >1 source file: "
        f"{int((files_per_trip > 1).sum()):,}"
    )

    # --------------------------------------------------------
    # Canonical preview
    #
    # This is NOT yet final cleaning.
    # Since all trip-defining fields are identical within ID,
    # one physical/logical trip can safely be represented once.
    # --------------------------------------------------------

    canonical = (
        df.sort_values(
            [
                TRIP_ID,
                "SOURCE_PERIOD",
                "SOURCE_ROW",
            ]
        )
        .drop_duplicates(
            subset=[TRIP_ID],
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
        reservation_info[
            [
                "RESERVATION_VALUES",
                "PRENOTAZIONE_CONFLICT",
            ]
        ],
        left_on=TRIP_ID,
        right_index=True,
        how="left",
    )

    return canonical


# ============================================================
# JANUARY 2024 TEMPORAL DAMAGE
# ============================================================

def inspect_january_2024(canonical):

    title("JANUARY 2024 TEMPORAL DAMAGE")

    jan = canonical.loc[
        canonical[
            "SOURCE_PERIOD"
        ] == "2024-01"
    ].copy()

    print(
        f"Canonical January trips: "
        f"{len(jan):,}"
    )

    print(
        f"Invalid starts: "
        f"{jan['START_TIME_RAW'].isna().sum():,}"
    )

    print(
        f"Invalid ends: "
        f"{jan['END_TIME_RAW'].isna().sum():,}"
    )

    print(
        "\nMost common START timestamp codes:"
    )

    print(
        jan[
            "START_TIMESTAMP_CODE"
        ]
        .value_counts(
            dropna=False
        )
        .head(20)
        .to_string()
    )

    print(
        "\nMost common END timestamp codes:"
    )

    print(
        jan[
            "END_TIMESTAMP_CODE"
        ]
        .value_counts(
            dropna=False
        )
        .head(20)
        .to_string()
    )

    print(
        "\nSTART timestamp prefixes YYYYMM:"
    )

    print(
        jan[
            "START_TIMESTAMP_CODE"
        ]
        .str.slice(0, 6)
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    jan[
        [
            "SOURCE_PERIOD",
            "SOURCE_ROW",
            TRIP_ID,
            "Targa veicolo",
            "START_TIMESTAMP_CODE",
            "END_TIMESTAMP_CODE",
            "Tempo Tot",
            "KM Tot",
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_2024_01_temporal_damage.csv",
        index=False,
    )


# ============================================================
# TIMEZONE HYPOTHESIS
# ============================================================

def inspect_timezone(canonical):

    title("UTC -> EUROPE/ROME TIMEZONE TEST")

    valid = canonical.loc[
        canonical[
            "START_TIME_RAW"
        ].notna()
    ].copy()

    # Candidate interpretation:
    # raw VOI timestamps are UTC.
    valid["START_TIME_LOCAL_CANDIDATE"] = (
        valid[
            "START_TIME_RAW"
        ]
        .dt.tz_localize("UTC")
        .dt.tz_convert("Europe/Rome")
        .dt.tz_localize(None)
    )

    valid["END_TIME_LOCAL_CANDIDATE"] = (
        valid[
            "END_TIME_RAW"
        ]
        .dt.tz_localize("UTC")
        .dt.tz_convert("Europe/Rome")
        .dt.tz_localize(None)
    )

    raw_period = (
        valid[
            "START_TIME_RAW"
        ]
        .dt.to_period("M")
        .astype(str)
    )

    local_period = (
        valid[
            "START_TIME_LOCAL_CANDIDATE"
        ]
        .dt.to_period("M")
        .astype(str)
    )

    raw_mismatch = (
        raw_period
        != valid[
            "SOURCE_PERIOD"
        ]
    )

    local_mismatch = (
        local_period
        != valid[
            "SOURCE_PERIOD"
        ]
    )

    print(
        f"Parsed canonical trips evaluated: "
        f"{len(valid):,}"
    )

    print(
        f"Raw timestamp/source-month mismatch: "
        f"{int(raw_mismatch.sum()):,}"
    )

    print(
        "After assuming UTC and converting to Europe/Rome: "
        f"{int(local_mismatch.sum()):,}"
    )

    mismatch = valid.loc[
        raw_mismatch
    ].copy()

    if not mismatch.empty:

        print(
            "\nRaw mismatches by raw hour:"
        )

        print(
            mismatch[
                "START_TIME_RAW"
            ]
            .dt.hour
            .value_counts()
            .sort_index()
            .to_string()
        )

        print(
            "\nFirst 30 raw period mismatches:"
        )

        print(
            mismatch[
                [
                    "SOURCE_PERIOD",
                    TRIP_ID,
                    "START_TIME_RAW",
                    "START_TIME_LOCAL_CANDIDATE",
                ]
            ]
            .head(30)
            .to_string(
                index=False
            )
        )

    valid.loc[
        raw_mismatch
        | local_mismatch,
        [
            "SOURCE_PERIOD",
            TRIP_ID,
            "START_TIME_RAW",
            "START_TIME_LOCAL_CANDIDATE",
            "END_TIME_RAW",
            "END_TIME_LOCAL_CANDIDATE",
        ]
    ].to_csv(
        AUDIT_DIR
        / "voi_timezone_test_rows.csv",
        index=False,
    )


# ============================================================
# TEMPORAL CONSISTENCY
# ============================================================

def inspect_temporal_consistency(canonical):

    title("TEMPORAL CONSISTENCY")

    valid = canonical.loc[
        canonical[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ].notna()
        &
        canonical[
            "Tempo Tot"
        ].notna()
    ].copy()

    diff = (
        valid[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ]
        - valid[
            "Tempo Tot"
        ]
    )

    abs_diff = diff.abs()

    print(
        f"Trips evaluated: {len(valid):,}"
    )

    print(
        "\nTimestamp duration - Tempo Tot:"
    )

    print(
        diff.describe(
            percentiles=[
                0.01,
                0.50,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    print(
        "\nAbsolute discrepancy:"
    )

    print(
        abs_diff.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    for threshold in [
        0.01,
        0.1,
        0.5,
        1,
        5,
    ]:

        print(
            f"|difference| > {threshold} min: "
            f"{int((abs_diff > threshold).sum()):,}"
        )

    # --------------------------------------------------------
    # Tempo Tot <= 0
    # --------------------------------------------------------

    bad_tempo = canonical.loc[
        canonical[
            "Tempo Tot"
        ].notna()
        &
        (
            canonical[
                "Tempo Tot"
            ] <= 0
        )
    ].copy()

    print(
        f"\nCanonical trips with Tempo Tot <=0: "
        f"{len(bad_tempo):,}"
    )

    if not bad_tempo.empty:

        print(
            bad_tempo[
                [
                    "SOURCE_PERIOD",
                    TRIP_ID,
                    "START_TIME_RAW",
                    "END_TIME_RAW",
                    "Tempo Tot",
                    "DURATION_FROM_TIMESTAMPS_MIN",
                    "KM Tot",
                    "HAVERSINE_KM",
                ]
            ]
            .to_string(
                index=False
            )
        )

    bad_tempo.to_csv(
        AUDIT_DIR
        / "voi_tempo_tot_non_positive_unique_trips.csv",
        index=False,
    )


# ============================================================
# DISTANCE CONSISTENCY
# ============================================================

def inspect_distance(canonical):

    title("DISTANCE QUALITY")

    bad = canonical.loc[
        canonical[
            "KM Tot"
        ].notna()
        &
        (
            canonical[
                "KM Tot"
            ] <= 0
        )
    ].copy()

    print(
        f"Canonical trips with KM Tot <=0: "
        f"{len(bad):,}"
    )

    if not bad.empty:

        print(
            "\nHaversine displacement among KM Tot<=0:"
        )

        print(
            bad[
                "HAVERSINE_KM"
            ]
            .describe(
                percentiles=[
                    0.25,
                    0.50,
                    0.75,
                    0.90,
                    0.95,
                    0.99,
                ]
            )
            .to_string()
        )

        for threshold in [
            0.020,
            0.100,
            0.500,
            1.0,
        ]:

            print(
                f"Haversine > {threshold} km: "
                f"{int((bad['HAVERSINE_KM'] > threshold).sum()):,}"
            )

    bad.to_csv(
        AUDIT_DIR
        / "voi_km_tot_non_positive_unique_trips.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Geometry vs reported distance
    # --------------------------------------------------------

    geo = canonical.loc[
        (canonical["KM Tot"] > 0)
        &
        canonical[
            "HAVERSINE_KM"
        ].notna()
    ].copy()

    geo[
        "GEOMETRY_EXCESS_KM"
    ] = (
        geo[
            "HAVERSINE_KM"
        ]
        - geo[
            "KM Tot"
        ]
    )

    excess = geo[
        "GEOMETRY_EXCESS_KM"
    ]

    print(
        "\nHaversine - KM Tot:"
    )

    print(
        excess.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    for threshold in [
        0,
        0.05,
        0.10,
        0.50,
        1.0,
    ]:

        print(
            f"Haversine exceeds KM Tot by >"
            f"{threshold} km: "
            f"{int((excess > threshold).sum()):,}"
        )

    worst = geo.loc[
        excess > 0.10
    ].sort_values(
        "GEOMETRY_EXCESS_KM",
        ascending=False
    )

    print(
        "\nTop 20 geometry inconsistencies:"
    )

    print(
        worst[
            [
                "SOURCE_PERIOD",
                TRIP_ID,
                "KM Tot",
                "Tempo Tot",
                "HAVERSINE_KM",
                "REPORTED_SPEED_KMH",
                "HAVERSINE_SPEED_KMH",
                "GEOMETRY_EXCESS_KM",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    worst.to_csv(
        AUDIT_DIR
        / "voi_distance_geometry_inconsistency.csv",
        index=False,
    )


# ============================================================
# SPEED + TAILS
# ============================================================

def inspect_speed_and_tails(canonical):

    title("SPEED AND DISTRIBUTION TAILS")

    speed = canonical[
        "REPORTED_SPEED_KMH"
    ].dropna()

    print(
        "\nReported speed:"
    )

    print(
        speed.describe(
            percentiles=[
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    for threshold in [
        30,
        40,
        60,
        100,
    ]:

        print(
            f"Reported speed >{threshold}: "
            f"{int((speed > threshold).sum()):,}"
        )

    fast = canonical.loc[
        canonical[
            "REPORTED_SPEED_KMH"
        ] > 40
    ].sort_values(
        "REPORTED_SPEED_KMH",
        ascending=False
    )

    print(
        "\nTop 20 speed anomalies:"
    )

    print(
        fast[
            [
                "SOURCE_PERIOD",
                TRIP_ID,
                "KM Tot",
                "Tempo Tot",
                "REPORTED_SPEED_KMH",
                "HAVERSINE_KM",
                "HAVERSINE_SPEED_KMH",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    fast.to_csv(
        AUDIT_DIR
        / "voi_speed_over_40_unique_trips.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Duration tail
    # --------------------------------------------------------

    duration = canonical[
        "Tempo Tot"
    ].dropna()

    print(
        "\nTempo Tot distribution:"
    )

    print(
        duration.describe(
            percentiles=[
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    for threshold in [
        60,
        120,
        180,
    ]:

        print(
            f"Tempo Tot >{threshold} min: "
            f"{int((duration > threshold).sum()):,}"
        )

    # --------------------------------------------------------
    # Distance tail
    # --------------------------------------------------------

    distance = canonical[
        "KM Tot"
    ].dropna()

    print(
        "\nKM Tot distribution:"
    )

    print(
        distance.describe(
            percentiles=[
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    for threshold in [
        20,
        30,
        50,
    ]:

        print(
            f"KM Tot >{threshold} km: "
            f"{int((distance > threshold).sum()):,}"
        )


# ============================================================
# SPATIAL QUALITY
# ============================================================

def inspect_spatial(canonical):

    title("SPATIAL QUALITY")

    missing_start = (
        canonical[
            [
                "Lat inizio corsa_coordinate",
                "Lon inizio corsa_coordinate",
            ]
        ]
        .isna()
        .any(axis=1)
    )

    missing_end = (
        canonical[
            [
                "Lat fine corsa_coordinate",
                "Lon fine corsa_coordinate",
            ]
        ]
        .isna()
        .any(axis=1)
    )

    print(
        f"Missing start coordinates: "
        f"{int(missing_start.sum()):,}"
    )

    print(
        f"Missing end coordinates: "
        f"{int(missing_end.sum()):,}"
    )

    print(
        f"Haversine >30 km: "
        f"{int((canonical['HAVERSINE_KM'] > 30).sum()):,}"
    )

    spatial_bad = canonical.loc[
        missing_start
        | missing_end
        | (
            canonical[
                "HAVERSINE_KM"
            ] > 30
        )
    ].copy()

    print(
        f"Unique trips requiring spatial review: "
        f"{len(spatial_bad):,}"
    )

    print(
        "\nTop spatial anomalies:"
    )

    print(
        spatial_bad[
            [
                "SOURCE_PERIOD",
                TRIP_ID,
                "KM Tot",
                "Tempo Tot",
                "HAVERSINE_KM",
                "Lat inizio corsa_coordinate",
                "Lon inizio corsa_coordinate",
                "Lat fine corsa_coordinate",
                "Lon fine corsa_coordinate",
            ]
        ]
        .sort_values(
            "HAVERSINE_KM",
            ascending=False,
            na_position="last"
        )
        .head(30)
        .to_string(
            index=False
        )
    )

    spatial_bad.to_csv(
        AUDIT_DIR
        / "voi_spatial_review_unique_trips.csv",
        index=False,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    title("LOADING VOI INTERIM DATA")

    df = load_all()

    print(
        f"Rows loaded: {len(df):,}"
    )

    canonical = build_canonical_preview(
        df
    )

    print(
        f"\nCanonical preview trips: "
        f"{len(canonical):,}"
    )

    inspect_january_2024(
        canonical
    )

    inspect_timezone(
        canonical
    )

    inspect_temporal_consistency(
        canonical
    )

    inspect_distance(
        canonical
    )

    inspect_speed_and_tails(
        canonical
    )

    inspect_spatial(
        canonical
    )

    # Save preview only for audit.
    # Do NOT treat this as final cleaned data yet.
    canonical.to_parquet(
        AUDIT_DIR
        / "voi_canonical_preview.parquet",
        index=False,
    )

    title(
        "VOI QUALITY INSPECTION COMPLETED"
    )

    print(
        "No final cleaned dataset was created."
    )


if __name__ == "__main__":
    main()