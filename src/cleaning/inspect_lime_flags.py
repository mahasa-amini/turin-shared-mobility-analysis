from pathlib import Path
import re

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "lime"
AUDIT_DIR = PROJECT_ROOT / "audit" / "lime"

AUDIT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FILE DISCOVERY
# ============================================================

def discover_files():

    files = sorted(
        INTERIM_DIR.glob(
            "lime_*_typed_flagged.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No Lime interim files found in {INTERIM_DIR}"
        )

    pattern = re.compile(
        r"lime_(\d{4}-\d{2})_typed_flagged\.parquet"
    )

    output = []

    for path in files:

        match = pattern.fullmatch(
            path.name
        )

        if match:
            output.append(
                (
                    match.group(1),
                    path
                )
            )

    return output


# ============================================================
# HELPERS
# ============================================================

def title(text):

    print("\n")
    print("=" * 100)
    print(text)
    print("=" * 100)


def pct(count, total):

    if total == 0:
        return 0

    return count / total * 100


# ============================================================
# 1. DURATION ROUNDING
# ============================================================

def inspect_duration_rounding(df, period):

    title(
        f"{period} — DURATION ROUNDING"
    )

    valid = df.loc[
        df["DURATION_FROM_TIMESTAMPS_MIN"]
        .notna()
        &
        (
            df["DURATION_FROM_TIMESTAMPS_MIN"]
            >= 0
        )
        &
        ~df["FLAG_DURATION_DIFFERENCE_GT1"]
    ].copy()

    exact = (
        valid[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ]
    )

    reported = (
        valid["DURATA_MIN"]
    )

    # Standard half-up rounding
    nearest = np.floor(
        exact + 0.5
    )

    floored = np.floor(
        exact
    )

    ceiled = np.ceil(
        exact
    )

    nearest_match = int(
        np.isclose(
            reported,
            nearest
        ).sum()
    )

    floor_match = int(
        np.isclose(
            reported,
            floored
        ).sum()
    )

    ceil_match = int(
        np.isclose(
            reported,
            ceiled
        ).sum()
    )

    print(
        f"Rows evaluated: {len(valid):,}"
    )

    print(
        f"Matches nearest-minute rounding: "
        f"{nearest_match:,} "
        f"({pct(nearest_match, len(valid)):.2f}%)"
    )

    print(
        f"Matches floor(): "
        f"{floor_match:,} "
        f"({pct(floor_match, len(valid)):.2f}%)"
    )

    print(
        f"Matches ceil(): "
        f"{ceil_match:,} "
        f"({pct(ceil_match, len(valid)):.2f}%)"
    )

    residual = (
        exact
        - reported
    )

    print(
        "\nExact timestamp duration minus "
        "reported DURATA_MIN:"
    )

    print(
        residual.describe(
            percentiles=[
                0.01,
                0.05,
                0.25,
                0.50,
                0.75,
                0.95,
                0.99,
            ]
        ).to_string()
    )


# ============================================================
# 2. REPORTED DURATION = 0
# ============================================================

def inspect_zero_duration(df, period):

    title(
        f"{period} — REPORTED DURATION <= 0"
    )

    zero = df.loc[
        df["DURATA_MIN"] <= 0
    ].copy()

    print(
        f"Rows with DURATA_MIN <= 0: "
        f"{len(zero):,}"
    )

    if zero.empty:
        return

    print(
        f"Negative DURATA_MIN: "
        f"{int((zero['DURATA_MIN'] < 0).sum()):,}"
    )

    print(
        f"Exactly zero DURATA_MIN: "
        f"{int((zero['DURATA_MIN'] == 0).sum()):,}"
    )

    exact = (
        zero[
            "DURATION_FROM_TIMESTAMPS_MIN"
        ]
    )

    print(
        "\nExact timestamp-derived duration:"
    )

    print(
        exact.describe(
            percentiles=[
                0.01,
                0.05,
                0.25,
                0.50,
                0.75,
                0.90,
                0.95,
                0.99,
            ]
        ).to_string()
    )

    print(
        "\nTimestamp-derived duration:"
    )

    for threshold in [
        0,
        0.1,
        0.25,
        0.5,
        1,
        2,
    ]:

        count = int(
            (exact > threshold).sum()
        )

        print(
            f"> {threshold} min: "
            f"{count:,}"
        )

    print(
        f"\nExact duration == 0: "
        f"{int((exact == 0).sum()):,}"
    )

    print(
        f"Exact duration < 0: "
        f"{int((exact < 0).sum()):,}"
    )


# ============================================================
# 3. ZERO REPORTED DISTANCE
# ============================================================

def inspect_zero_distance(df, period):

    title(
        f"{period} — DISTANZA_KM = 0"
    )

    zero = df.loc[
        df["DISTANZA_KM"] == 0
    ].copy()

    print(
        f"Zero-distance rows: "
        f"{len(zero):,}"
    )

    if zero.empty:
        return

    h = zero["HAVERSINE_KM"]

    print(
        "\nHaversine displacement:"
    )

    print(
        h.describe(
            percentiles=[
                0.25,
                0.50,
                0.75,
                0.90,
                0.95,
                0.99,
            ]
        ).to_string()
    )

    for threshold in [
        0.020,
        0.100,
        0.500,
        1.0,
        2.0,
        5.0,
    ]:

        count = int(
            (h > threshold).sum()
        )

        print(
            f"Haversine > {threshold} km: "
            f"{count:,} "
            f"({pct(count, len(zero)):.2f}%)"
        )

    same = int(
        zero[
            "SAME_START_END_COORDS"
        ].sum()
    )

    print(
        f"\nExact same coordinates: "
        f"{same:,} "
        f"({pct(same, len(zero)):.2f}%)"
    )

    print(
        "\nTimestamp-derived duration "
        "for zero-distance trips:"
    )

    print(
        zero[
            "DURATION_FROM_TIMESTAMPS_MIN"
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


# ============================================================
# 4. TEMPORAL ANOMALIES / DST
# ============================================================

def inspect_temporal(df, period):

    temporal = df.loc[
        df["FLAG_REVERSED_TIMESTAMP"]
        |
        df["FLAG_DURATION_DIFFERENCE_GT1"]
    ].copy()

    if temporal.empty:
        return

    title(
        f"{period} — TEMPORAL ANOMALIES"
    )

    print(
        f"Rows: {len(temporal):,}"
    )

    print(
        "\nBy start date:"
    )

    print(
        temporal[
            "START_TIME"
        ]
        .dt.date
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nDuration difference:"
    )

    print(
        temporal[
            "DURATION_DIFFERENCE_MIN"
        ]
        .round(2)
        .value_counts()
        .sort_index()
        .to_string()
    )

    cols = [
        "SOURCE_ROW",
        "ID_VEICOLO",
        "START_TIME",
        "END_TIME_RAW",
        "DURATA_MIN",
        "DURATION_FROM_TIMESTAMPS_MIN",
        "DURATION_DIFFERENCE_MIN",
        "FLAG_REVERSED_TIMESTAMP",
    ]

    print(
        "\nRows:"
    )

    print(
        temporal[
            cols
        ]
        .to_string(
            index=False
        )
    )

    temporal[
        cols
    ].to_csv(
        AUDIT_DIR
        / f"lime_{period}_temporal_anomalies.csv",
        index=False,
    )


# ============================================================
# 5. HAVERSINE SPEED
# ============================================================

def inspect_spatial_speed(df, period):

    suspicious = df.loc[
        df["HAVERSINE_SPEED_TS_KMH"] > 40
    ].copy()

    if suspicious.empty:
        return

    title(
        f"{period} — HAVERSINE SPEED > 40 KM/H"
    )

    s = (
        df[
            "HAVERSINE_SPEED_TS_KMH"
        ]
        .dropna()
    )

    print(
        "\nOverall distribution:"
    )

    print(
        s.describe(
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
        30,
        40,
        60,
        100,
    ]:

        print(
            f"Haversine speed > {threshold}: "
            f"{int((s > threshold).sum()):,}"
        )

    cols = [
        "SOURCE_ROW",
        "ID_VEICOLO",
        "START_TIME",
        "DISTANZA_KM",
        "DURATA_MIN",
        "DURATION_FROM_TIMESTAMPS_MIN",
        "HAVERSINE_KM",
        "HAVERSINE_SPEED_TS_KMH",
        "LATITUDINE_INIZIO_CORSA",
        "LONGITUTIDE_INIZIO_CORSA",
        "LATITUDINE_FINE_CORSA",
        "LONGITUTIDE_FINE_CORSA",
    ]

    print(
        "\nTop 20:"
    )

    print(
        suspicious[
            cols
        ]
        .sort_values(
            "HAVERSINE_SPEED_TS_KMH",
            ascending=False
        )
        .head(20)
        .to_string(
            index=False
        )
    )


# ============================================================
# 6. DISTANCE / GEOMETRY CONSISTENCY
# ============================================================

def inspect_distance_geometry(df, period):

    title(
        f"{period} — INTEGER DISTANCE VS GEOMETRY"
    )

    valid = df.loc[
        df["DISTANZA_KM"].notna()
        &
        df["HAVERSINE_KM"].notna()
    ].copy()

    valid[
        "GEOMETRY_MINUS_REPORTED_KM"
    ] = (
        valid["HAVERSINE_KM"]
        - valid["DISTANZA_KM"]
    )

    d = (
        valid[
            "GEOMETRY_MINUS_REPORTED_KM"
        ]
    )

    print(
        "\nHaversine - reported distance:"
    )

    print(
        d.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string()
    )

    # Because DISTANZA_KM is integer-valued,
    # use tolerance bands instead of Bird-style ratios.

    for excess in [
        0,
        0.5,
        1.0,
        2.0,
        5.0,
    ]:

        count = int(
            (d > excess).sum()
        )

        print(
            f"Haversine exceeds reported by "
            f">{excess} km: "
            f"{count:,} "
            f"({pct(count, len(valid)):.3f}%)"
        )

    worst = valid.loc[
        d > 1
    ].copy()

    cols = [
        "SOURCE_ROW",
        "ID_VEICOLO",
        "START_TIME",
        "DISTANZA_KM",
        "DURATA_MIN",
        "DURATION_FROM_TIMESTAMPS_MIN",
        "HAVERSINE_KM",
        "HAVERSINE_SPEED_TS_KMH",
        "GEOMETRY_MINUS_REPORTED_KM",
    ]

    print(
        "\nTop 20 largest geometry excess:"
    )

    print(
        worst[
            cols
        ]
        .sort_values(
            "GEOMETRY_MINUS_REPORTED_KM",
            ascending=False
        )
        .head(20)
        .to_string(
            index=False
        )
    )


# ============================================================
# 7. SAME START / END COORDINATES
# ============================================================

def inspect_same_coordinates(df, period):

    same = df.loc[
        df["SAME_START_END_COORDS"]
    ].copy()

    if same.empty:
        return

    title(
        f"{period} — SAME START/END COORDINATES"
    )

    print(
        f"Rows: {len(same):,}"
    )

    print(
        "\nReported distance:"
    )

    print(
        same[
            "DISTANZA_KM"
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

    positive_distance = int(
        (
            same["DISTANZA_KM"] > 0
        ).sum()
    )

    print(
        f"\nSame coordinates but "
        f"reported distance >0: "
        f"{positive_distance:,} "
        f"({pct(positive_distance, len(same)):.2f}%)"
    )

    print(
        "\nTimestamp-derived duration:"
    )

    print(
        same[
            "DURATION_FROM_TIMESTAMPS_MIN"
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


# ============================================================
# MAIN
# ============================================================

def main():

    files = discover_files()

    print(
        f"Found {len(files)} Lime interim files."
    )

    for period, path in files:

        print("\n")
        print("#" * 100)
        print(f"LOADING LIME {period}")
        print("#" * 100)

        df = pd.read_parquet(
            path
        )

        print(
            f"Rows: {len(df):,}"
        )

        inspect_duration_rounding(
            df,
            period
        )

        inspect_zero_duration(
            df,
            period
        )

        inspect_zero_distance(
            df,
            period
        )

        inspect_temporal(
            df,
            period
        )

        inspect_spatial_speed(
            df,
            period
        )

        inspect_distance_geometry(
            df,
            period
        )

        inspect_same_coordinates(
            df,
            period
        )

    title(
        "LIME FLAG INSPECTION COMPLETED"
    )

    print(
        "No records were deleted or modified."
    )


if __name__ == "__main__":
    main()