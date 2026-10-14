from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "bird"
AUDIT_DIR = PROJECT_ROOT / "audit" / "bird"

FILES = {
    2024: INTERIM_DIR / "bird_2024_typed_flagged.parquet",
    2025: INTERIM_DIR / "bird_2025_typed_flagged.parquet",
}


def title(text):
    print("\n" + "=" * 90)
    print(text)
    print("=" * 90)


def save(df, filename):
    path = AUDIT_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved -> {path}")


# ============================================================
# ADD CONSISTENCY METRICS
# ============================================================

def add_consistency_metrics(df):

    df = df.copy()

    # Straight-line displacement speed
    valid_duration = df["DURATA_MIN"] > 0

    df["HAVERSINE_SPEED_KMH"] = np.nan

    df.loc[valid_duration, "HAVERSINE_SPEED_KMH"] = (
        df.loc[valid_duration, "HAVERSINE_KM"]
        /
        (df.loc[valid_duration, "DURATA_MIN"] / 60)
    )

    # Compare geometric displacement with Bird's reported route distance
    valid_reported_distance = df["DISTANZA_KM"] > 0

    df["HAVERSINE_TO_REPORTED_RATIO"] = np.nan

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

    df["REPORTED_MINUS_HAVERSINE_KM"] = (
        df["DISTANZA_KM"]
        - df["HAVERSINE_KM"]
    )

    return df


# ============================================================
# HAVERSINE SPEED
# ============================================================

def inspect_haversine_speed(df, year):

    title(f"{year} — HAVERSINE SPEED CONSISTENCY")

    s = df["HAVERSINE_SPEED_KMH"].dropna()

    print("\nDistribution:")
    print(
        s.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999
            ]
        ).to_string()
    )

    for threshold in [30, 40, 60, 100]:

        count = int((s > threshold).sum())

        print(
            f"Haversine speed > {threshold} km/h: "
            f"{count:,}"
        )

    suspicious = df.loc[
        df["HAVERSINE_SPEED_KMH"] > 30,
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "DISTANZA_KM",
            "DURATA_MIN",
            "SPEED_KMH",
            "HAVERSINE_KM",
            "HAVERSINE_SPEED_KMH",
            "LATITUDINE_INIZIO_CORSA",
            "LONGITUTIDE_INIZIO_CORSA",
            "LATITUDINE_FINE_CORSA",
            "LONGITUTIDE_FINE_CORSA",
        ]
    ].sort_values(
        "HAVERSINE_SPEED_KMH",
        ascending=False
    )

    print(
        f"\nRows with Haversine speed >30: "
        f"{len(suspicious):,}"
    )

    print("\nTop 30:")
    print(
        suspicious
        .head(30)
        .to_string(index=False)
    )

    save(
        suspicious,
        f"bird_{year}_haversine_speed_over_30.csv"
    )


# ============================================================
# REPORTED DISTANCE VS HAVERSINE
# ============================================================

def inspect_distance_consistency(df, year):

    title(f"{year} — REPORTED VS HAVERSINE CONSISTENCY")

    ratio = df[
        "HAVERSINE_TO_REPORTED_RATIO"
    ].dropna()

    print("\nRatio distribution:")
    print(
        ratio.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999
            ]
        ).to_string()
    )

    thresholds = [
        1.0,
        1.1,
        1.5,
        2,
        5,
        10
    ]

    print("\nHaversine / reported-distance thresholds:")

    for threshold in thresholds:

        count = int(
            (ratio > threshold).sum()
        )

        print(
            f"ratio > {threshold}: "
            f"{count:,}"
        )

    suspicious = df.loc[
        df["HAVERSINE_TO_REPORTED_RATIO"] > 1.1,
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "DISTANZA_KM",
            "DURATA_MIN",
            "SPEED_KMH",
            "HAVERSINE_KM",
            "HAVERSINE_SPEED_KMH",
            "HAVERSINE_TO_REPORTED_RATIO",
        ]
    ].sort_values(
        "HAVERSINE_TO_REPORTED_RATIO",
        ascending=False
    )

    print(
        "\nTop 30 largest Haversine/reported ratios:"
    )

    print(
        suspicious
        .head(30)
        .to_string(index=False)
    )

    save(
        suspicious,
        f"bird_{year}_distance_geometry_inconsistency.csv"
    )


# ============================================================
# ZERO DISTANCE + HAVERSINE SPEED
# ============================================================

def inspect_zero_distance(df, year):

    title(f"{year} — ZERO DISTANCE CROSS-CHECK")

    zero = df.loc[
        df["DISTANZA_KM"] <= 0,
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "DISTANZA_KM",
            "DURATA_MIN",
            "HAVERSINE_KM",
            "HAVERSINE_SPEED_KMH",
        ]
    ].copy()

    print(
        f"\nZero/non-positive distance rows: "
        f"{len(zero):,}"
    )

    for threshold in [20, 30, 40, 60]:

        count = int(
            (
                zero["HAVERSINE_SPEED_KMH"]
                > threshold
            ).sum()
        )

        print(
            f"Haversine speed >{threshold}: "
            f"{count:,}"
        )

    print(
        "\nAll zero-distance records sorted "
        "by Haversine speed:"
    )

    print(
        zero.sort_values(
            "HAVERSINE_SPEED_KMH",
            ascending=False
        ).to_string(index=False)
    )

    save(
        zero,
        f"bird_{year}_zero_distance_crosscheck.csv"
    )


# ============================================================
# TEMPORAL CONSISTENCY EXCLUDING DST
# ============================================================

def inspect_temporal_residual(df, year):

    title(f"{year} — TEMPORAL CONSISTENCY EXCLUDING DST")

    normal = df.loc[
        ~df["FLAG_POSSIBLE_DST"]
        &
        df["DURATION_DIFFERENCE_MIN"].notna()
    ].copy()

    diff = (
        normal["DURATION_DIFFERENCE_MIN"]
        .abs()
    )

    print("\nAbsolute duration difference:")
    print(
        diff.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999
            ]
        ).to_string()
    )

    for threshold in [1, 2, 5]:

        print(
            f"|difference| > {threshold} min: "
            f"{int((diff > threshold).sum()):,}"
        )

    bad = normal.loc[
        diff > 2,
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "END_TIME_RAW",
            "DURATA_MIN",
            "DURATION_FROM_TIMESTAMPS_MIN",
            "DURATION_DIFFERENCE_MIN",
        ]
    ].copy()

    if not bad.empty:

        print("\nRows with >2 min discrepancy:")
        print(
            bad.sort_values(
                "DURATION_DIFFERENCE_MIN",
                key=lambda x: x.abs(),
                ascending=False
            )
            .head(30)
            .to_string(index=False)
        )

    save(
        bad,
        f"bird_{year}_non_dst_temporal_inconsistency.csv"
    )


# ============================================================
# REPORTED DISTANCE / DURATION TAILS
# ============================================================

def inspect_tails(df, year):

    title(f"{year} — DISTANCE AND DURATION TAILS")

    print("\nReported distance:")
    print(
        df["DISTANZA_KM"]
        .describe(
            percentiles=[
                0.90,
                0.95,
                0.99,
                0.999
            ]
        )
        .to_string()
    )

    for threshold in [10, 20, 30, 40]:

        print(
            f"Distance > {threshold} km: "
            f"{int((df['DISTANZA_KM'] > threshold).sum()):,}"
        )

    print("\nTrip duration:")
    print(
        df["DURATA_MIN"]
        .describe(
            percentiles=[
                0.90,
                0.95,
                0.99,
                0.999
            ]
        )
        .to_string()
    )

    for threshold in [60, 120, 180]:

        print(
            f"Duration > {threshold} min: "
            f"{int((df['DURATA_MIN'] > threshold).sum()):,}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    for year, path in FILES.items():

        title(f"LOADING BIRD {year}")

        df = pd.read_parquet(path)

        print(f"Rows: {len(df):,}")

        df = add_consistency_metrics(df)

        inspect_haversine_speed(df, year)

        inspect_distance_consistency(df, year)

        inspect_zero_distance(df, year)

        inspect_temporal_residual(df, year)

        inspect_tails(df, year)

    title("BIRD CONSISTENCY INSPECTION COMPLETED")

    print(
        "No rows were deleted or modified."
    )


if __name__ == "__main__":
    main()