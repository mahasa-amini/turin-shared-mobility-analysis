from pathlib import Path
import re

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "lime"
AUDIT_DIR = PROJECT_ROOT / "audit" / "lime"

AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def discover_files():
    files = sorted(
        INTERIM_DIR.glob("lime_*_typed_flagged.parquet")
    )

    pattern = re.compile(
        r"lime_(\d{4}-\d{2})_typed_flagged\.parquet"
    )

    output = []

    for path in files:
        match = pattern.fullmatch(path.name)

        if match:
            output.append(
                (match.group(1), path)
            )

    return output


def main():

    monthly_summary = []
    distance_tail_records = []
    zero_time_records = []

    for period, path in discover_files():

        df = pd.read_parquet(path)

        # ====================================================
        # DISTANCE DISTRIBUTION
        # ====================================================

        distance = df["DISTANZA_KM"].dropna()

        duration_exact = (
            df["DURATION_FROM_TIMESTAMPS_MIN"]
        )

        row = {
            "period": period,
            "rows": len(df),

            "distance_min":
                distance.min(),

            "distance_median":
                distance.median(),

            "distance_p95":
                distance.quantile(0.95),

            "distance_p99":
                distance.quantile(0.99),

            "distance_p999":
                distance.quantile(0.999),

            "distance_max":
                distance.max(),

            "distance_eq_0":
                int((distance == 0).sum()),

            "distance_ge_20":
                int((distance >= 20).sum()),

            "distance_ge_30":
                int((distance >= 30).sum()),

            "distance_ge_50":
                int((distance >= 50).sum()),

            "distance_eq_100":
                int((distance == 100).sum()),

            "exact_duration_eq_0":
                int((duration_exact == 0).sum()),

            "exact_duration_lt_0":
                int((duration_exact < 0).sum()),

            "exact_duration_gt_60":
                int((duration_exact > 60).sum()),

            "exact_duration_gt_120":
                int((duration_exact > 120).sum()),

            "exact_duration_gt_180":
                int((duration_exact > 180).sum()),

            "exact_duration_max":
                duration_exact.max(),

            "haversine_speed_gt40":
                int(
                    (
                        df["HAVERSINE_SPEED_TS_KMH"]
                        > 40
                    ).sum()
                ),

            "haversine_speed_gt100":
                int(
                    (
                        df["HAVERSINE_SPEED_TS_KMH"]
                        > 100
                    ).sum()
                ),
        }

        monthly_summary.append(row)

        # ====================================================
        # LARGE DISTANCES
        # ====================================================

        tail = df.loc[
            df["DISTANZA_KM"] >= 20,
            [
                "SOURCE_PERIOD",
                "SOURCE_ROW",
                "ID_VEICOLO",
                "START_TIME",
                "END_TIME_RAW",
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
        ].copy()

        distance_tail_records.append(tail)

        # ====================================================
        # EXACT ZERO-DURATION TIMESTAMPS
        # ====================================================

        zero_time = df.loc[
            df["DURATION_FROM_TIMESTAMPS_MIN"] == 0,
            [
                "SOURCE_PERIOD",
                "SOURCE_ROW",
                "ID_VEICOLO",
                "START_TIME",
                "END_TIME_RAW",
                "DISTANZA_KM",
                "DURATA_MIN",
                "HAVERSINE_KM",
                "SAME_START_END_COORDS",
            ]
        ].copy()

        zero_time_records.append(zero_time)

    # ========================================================
    # SAVE OUTPUTS
    # ========================================================

    monthly = pd.DataFrame(monthly_summary)

    monthly.to_csv(
        AUDIT_DIR / "lime_tail_summary.csv",
        index=False
    )

    distance_tail = pd.concat(
        distance_tail_records,
        ignore_index=True
    )

    distance_tail.to_csv(
        AUDIT_DIR / "lime_large_distance_records.csv",
        index=False
    )

    zero_time = pd.concat(
        zero_time_records,
        ignore_index=True
    )

    zero_time.to_csv(
        AUDIT_DIR / "lime_exact_zero_duration_records.csv",
        index=False
    )

    # ========================================================
    # COMPACT TERMINAL OUTPUT
    # ========================================================

    print("\n" + "=" * 100)
    print("LIME TAIL INSPECTION")
    print("=" * 100)

    print("\nMonthly summary:")

    print(
        monthly.to_string(
            index=False
        )
    )

    print("\n" + "=" * 100)

    print(
        f"Trips with DISTANZA_KM >=20: "
        f"{len(distance_tail):,}"
    )

    print(
        f"Trips with exact timestamp duration =0: "
        f"{len(zero_time):,}"
    )

    print("\nTop 30 largest reported distances:")

    print(
        distance_tail
        .sort_values(
            "DISTANZA_KM",
            ascending=False
        )
        .head(30)
        .to_string(index=False)
    )

    print("\nExact zero-duration records:")

    print(
        zero_time.to_string(
            index=False
        )
    )

    print("\nFiles saved:")
    print(
        AUDIT_DIR / "lime_tail_summary.csv"
    )
    print(
        AUDIT_DIR / "lime_large_distance_records.csv"
    )
    print(
        AUDIT_DIR / "lime_exact_zero_duration_records.csv"
    )


if __name__ == "__main__":
    main()