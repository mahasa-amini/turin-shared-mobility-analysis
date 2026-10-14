from pathlib import Path
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "bird"
AUDIT_DIR = PROJECT_ROOT / "audit" / "bird"

AUDIT_DIR.mkdir(parents=True, exist_ok=True)


FILES = {
    2024: INTERIM_DIR / "bird_2024_typed_flagged.parquet",
    2025: INTERIM_DIR / "bird_2025_typed_flagged.parquet",
}


# ============================================================
# HELPERS
# ============================================================

def title(text):
    print("\n")
    print("=" * 90)
    print(text)
    print("=" * 90)


def save_table(df, filename):
    path = AUDIT_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved -> {path}")


# ============================================================
# TEMPORAL INSPECTION
# ============================================================

def inspect_temporal(df, year):

    title(f"{year} — TEMPORAL ANOMALIES")

    reversed_rows = df.loc[
        df["FLAG_REVERSED_TIMESTAMP"],
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "END_TIME_RAW",
            "DURATA_MIN",
            "DURATION_FROM_TIMESTAMPS_MIN",
            "DURATION_DIFFERENCE_MIN",
            "FLAG_POSSIBLE_DST",
        ]
    ].copy()

    print(f"\nReversed timestamps: {len(reversed_rows):,}")

    if not reversed_rows.empty:
        print("\nDates of reversed timestamps:")
        print(
            reversed_rows["START_TIME"]
            .dt.date
            .value_counts()
            .sort_index()
            .to_string()
        )

        print("\nReversed timestamp rows:")
        print(reversed_rows.to_string(index=False))

        save_table(
            reversed_rows,
            f"bird_{year}_reversed_timestamps.csv"
        )

    possible_dst = df.loc[
        df["FLAG_POSSIBLE_DST"],
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "END_TIME_RAW",
            "DURATA_MIN",
            "DURATION_FROM_TIMESTAMPS_MIN",
            "DURATION_DIFFERENCE_MIN",
            "FLAG_REVERSED_TIMESTAMP",
        ]
    ].copy()

    print(f"\nPossible DST records: {len(possible_dst):,}")

    if not possible_dst.empty:

        print("\nPossible DST records by date:")
        print(
            possible_dst["START_TIME"]
            .dt.date
            .value_counts()
            .sort_index()
            .to_string()
        )

        print("\nDuration difference distribution:")
        print(
            possible_dst["DURATION_DIFFERENCE_MIN"]
            .round(2)
            .value_counts()
            .sort_index()
            .to_string()
        )

        save_table(
            possible_dst,
            f"bird_{year}_possible_dst.csv"
        )


# ============================================================
# DISTANCE = 0 / NON-POSITIVE DISTANCE
# ============================================================

def inspect_non_positive_distance(df, year):

    title(f"{year} — NON-POSITIVE DISTANCE")

    bad = df.loc[
        df["FLAG_DISTANCE_NON_POSITIVE"],
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "END_TIME_RAW",
            "DISTANZA_KM",
            "DURATA_MIN",
            "HAVERSINE_KM",
            "SAME_START_END_COORDS",
            "LATITUDINE_INIZIO_CORSA",
            "LONGITUTIDE_INIZIO_CORSA",
            "LATITUDINE_FINE_CORSA",
            "LONGITUTIDE_FINE_CORSA",
        ]
    ].copy()

    print(f"\nRows with distance <= 0: {len(bad):,}")

    if bad.empty:
        return

    print("\nHaversine statistics:")
    print(
        bad["HAVERSINE_KM"]
        .describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95])
        .to_string()
    )

    print(
        "\nSame start/end coordinates:",
        int(bad["SAME_START_END_COORDS"].sum())
    )

    print(
        "Haversine > 20 m:",
        int((bad["HAVERSINE_KM"] > 0.020).sum())
    )

    print(
        "Haversine > 100 m:",
        int((bad["HAVERSINE_KM"] > 0.100).sum())
    )

    print(
        "Haversine > 500 m:",
        int((bad["HAVERSINE_KM"] > 0.500).sum())
    )

    print(
        "Haversine > 1 km:",
        int((bad["HAVERSINE_KM"] > 1).sum())
    )

    print("\nRows sorted by Haversine displacement:")

    print(
        bad.sort_values(
            "HAVERSINE_KM",
            ascending=False
        ).to_string(index=False)
    )

    save_table(
        bad,
        f"bird_{year}_distance_non_positive.csv"
    )


# ============================================================
# SPEED OUTLIERS
# ============================================================

def inspect_speed(df, year):

    title(f"{year} — SPEED > 30 KM/H")

    speed = df.loc[
        df["FLAG_SPEED_OVER_30"],
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "END_TIME_RAW",
            "DISTANZA_KM",
            "DURATA_MIN",
            "SPEED_KMH",
            "HAVERSINE_KM",
            "SAME_START_END_COORDS",
        ]
    ].copy()

    print(f"\nSpeed > 30 km/h: {len(speed):,}")

    if not speed.empty:

        speed = speed.sort_values(
            "SPEED_KMH",
            ascending=False
        )

        print(speed.to_string(index=False))

        save_table(
            speed,
            f"bird_{year}_speed_over_30.csv"
        )


# ============================================================
# GPS JUMPS
# ============================================================

def inspect_gps_jump(df, year):

    title(f"{year} — HAVERSINE > 30 KM")

    gps = df.loc[
        df["FLAG_GPS_JUMP"],
        [
            "SOURCE_ROW",
            "ID_VEICOLO",
            "START_TIME",
            "DISTANZA_KM",
            "DURATA_MIN",
            "SPEED_KMH",
            "HAVERSINE_KM",
            "LATITUDINE_INIZIO_CORSA",
            "LONGITUTIDE_INIZIO_CORSA",
            "LATITUDINE_FINE_CORSA",
            "LONGITUTIDE_FINE_CORSA",
        ]
    ].copy()

    print(f"\nGPS jump candidates: {len(gps):,}")

    if gps.empty:
        return

    gps["HAVERSINE_TO_REPORTED_RATIO"] = (
        gps["HAVERSINE_KM"]
        / gps["DISTANZA_KM"].replace(0, pd.NA)
    )

    gps = gps.sort_values(
        "HAVERSINE_KM",
        ascending=False
    )

    print(gps.to_string(index=False))

    save_table(
        gps,
        f"bird_{year}_gps_jump_candidates.csv"
    )


# ============================================================
# SMALL DISPLACEMENT PROFILE
# ============================================================

def inspect_small_displacement(df, year):

    title(f"{year} — HAVERSINE < 20 METERS")

    small = df.loc[
        df["FLAG_SMALL_DISPLACEMENT"]
    ].copy()

    print(
        f"\nTrips with Haversine <20 m: "
        f"{len(small):,}"
    )

    if small.empty:
        return

    print("\nReported distance distribution:")

    print(
        small["DISTANZA_KM"]
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

    print("\nTrip duration distribution:")

    print(
        small["DURATA_MIN"]
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

    thresholds = {
        "reported_distance_gt_0_1km":
            (small["DISTANZA_KM"] > 0.1),

        "reported_distance_gt_0_5km":
            (small["DISTANZA_KM"] > 0.5),

        "reported_distance_gt_1km":
            (small["DISTANZA_KM"] > 1),

        "reported_distance_gt_2km":
            (small["DISTANZA_KM"] > 2),

        "reported_distance_gt_5km":
            (small["DISTANZA_KM"] > 5),
    }

    print("\nReported-distance thresholds:")

    for name, mask in thresholds.items():

        count = int(mask.sum())

        share = (
            count / len(small) * 100
            if len(small) > 0
            else 0
        )

        print(
            f"{name}: "
            f"{count:,} "
            f"({share:.2f}%)"
        )

    same_coords = int(
        small["SAME_START_END_COORDS"].sum()
    )

    print(
        f"\nExact same start/end coordinates: "
        f"{same_coords:,} "
        f"({same_coords / len(small) * 100:.2f}%)"
    )

    summary = pd.DataFrame(
        {
            "year": [year],
            "small_displacement_rows": [len(small)],
            "same_coordinates": [same_coords],
            "distance_gt_0_1km": [
                int((small["DISTANZA_KM"] > 0.1).sum())
            ],
            "distance_gt_0_5km": [
                int((small["DISTANZA_KM"] > 0.5).sum())
            ],
            "distance_gt_1km": [
                int((small["DISTANZA_KM"] > 1).sum())
            ],
            "distance_gt_2km": [
                int((small["DISTANZA_KM"] > 2).sum())
            ],
            "distance_gt_5km": [
                int((small["DISTANZA_KM"] > 5).sum())
            ],
        }
    )

    save_table(
        summary,
        f"bird_{year}_small_displacement_summary.csv"
    )


# ============================================================
# FLAG OVERLAP
# ============================================================

def inspect_flag_overlap(df, year):

    title(f"{year} — FLAG OVERLAP")

    flags = [
        "FLAG_DISTANCE_NON_POSITIVE",
        "FLAG_DURATION_NON_POSITIVE",
        "FLAG_SPEED_OVER_30",
        "FLAG_REVERSED_TIMESTAMP",
        "FLAG_SMALL_DISPLACEMENT",
        "FLAG_GPS_JUMP",
        "FLAG_POSSIBLE_DST",
    ]

    overlap = pd.DataFrame(
        index=flags,
        columns=flags,
        dtype=int
    )

    for flag_a in flags:
        for flag_b in flags:

            overlap.loc[flag_a, flag_b] = int(
                (
                    df[flag_a]
                    & df[flag_b]
                ).sum()
            )

    print(
        "\nPairwise number of overlapping flags:"
    )

    print(overlap.to_string())

    overlap.to_csv(
        AUDIT_DIR
        / f"bird_{year}_flag_overlap.csv"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    for year, path in FILES.items():

        title(f"LOADING BIRD {year}")

        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_parquet(path)

        print(
            f"Rows loaded: {len(df):,}"
        )

        inspect_temporal(df, year)

        inspect_non_positive_distance(df, year)

        inspect_speed(df, year)

        inspect_gps_jump(df, year)

        inspect_small_displacement(df, year)

        inspect_flag_overlap(df, year)

    title("BIRD FLAG INSPECTION COMPLETED")

    print(
        "No records were deleted or modified."
    )


if __name__ == "__main__":
    main()