from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HARMONIZED_DIR = PROJECT_ROOT / "data" / "processed" / "harmonized"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "parking"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_4"
    / "parking"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


OPERATORS = ["bird", "lime", "voi"]

# Common detailed-time comparison window.
# VOI January 2024 is excluded because exact timestamps are unavailable.
ANALYSIS_START = pd.Timestamp("2024-02-01 00:00:00")
ANALYSIS_END_EXCLUSIVE = pd.Timestamp("2025-01-01 00:00:00")

ROME_TZ = "Europe/Rome"


CORE_COLUMNS = [
    "operator",
    "trip_uid",
    "vehicle_uid",
    "start_time_local",
    "end_time_local",
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
]

OPTIONAL_COLUMNS = [
    "year",
    "source_period",
    "source_row",
    "temporal_detail_available",
    "valid_spatial_prezone",
]


# =============================================================================
# HELPERS
# =============================================================================

def read_available_columns(path: Path) -> list[str]:
    schema = pq.ParquetFile(path).schema
    return schema.names


def load_operator_year(operator: str, year: int) -> pd.DataFrame:
    path = HARMONIZED_DIR / f"{operator}_{year}_harmonized.parquet"

    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    available = read_available_columns(path)

    missing_core = [c for c in CORE_COLUMNS if c not in available]

    if missing_core:
        raise ValueError(
            f"{path.name} is missing required columns: {missing_core}"
        )

    columns = CORE_COLUMNS + [
        c for c in OPTIONAL_COLUMNS
        if c in available and c not in CORE_COLUMNS
    ]

    df = pd.read_parquet(path, columns=columns)

    print(
        f"Loaded {operator.upper()} {year}: "
        f"{len(df):,} rows"
    )

    return df


def normalize_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def local_wallclock_to_utc(
    series: pd.Series,
) -> pd.Series:
    """
    Convert Europe/Rome local-clock timestamps to UTC.

    Ambiguous autumn-DST timestamps and nonexistent spring-DST
    timestamps are deliberately returned as NaT rather than guessed.
    """

    s = pd.to_datetime(series, errors="coerce")

    # If timestamps are already timezone-aware.
    if isinstance(s.dtype, pd.DatetimeTZDtype):
        return (
            s.dt
            .tz_convert("UTC")
            .dt
            .tz_localize(None)
        )

    localized = s.dt.tz_localize(
        ROME_TZ,
        ambiguous="NaT",
        nonexistent="NaT",
    )

    return (
        localized.dt
        .tz_convert("UTC")
        .dt
        .tz_localize(None)
    )


def haversine_m(
    lat1,
    lon1,
    lat2,
    lon2,
):
    """
    Vectorized great-circle distance in metres.
    """

    lat1 = np.asarray(lat1, dtype="float64")
    lon1 = np.asarray(lon1, dtype="float64")
    lat2 = np.asarray(lat2, dtype="float64")
    lon2 = np.asarray(lon2, dtype="float64")

    valid = (
        np.isfinite(lat1)
        & np.isfinite(lon1)
        & np.isfinite(lat2)
        & np.isfinite(lon2)
        & (lat1 >= -90)
        & (lat1 <= 90)
        & (lat2 >= -90)
        & (lat2 <= 90)
        & (lon1 >= -180)
        & (lon1 <= 180)
        & (lon2 >= -180)
        & (lon2 <= 180)
    )

    result = np.full(len(lat1), np.nan, dtype="float64")

    if not valid.any():
        return result

    r = 6_371_008.8

    lat1r = np.radians(lat1[valid])
    lon1r = np.radians(lon1[valid])
    lat2r = np.radians(lat2[valid])
    lon2r = np.radians(lon2[valid])

    dlat = lat2r - lat1r
    dlon = lon2r - lon1r

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1r)
        * np.cos(lat2r)
        * np.sin(dlon / 2.0) ** 2
    )

    c = 2.0 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1.0 - a),
    )

    result[valid] = r * c

    return result


def duration_bin(series: pd.Series) -> pd.Categorical:
    bins = [
        -np.inf,
        0,
        5,
        15,
        30,
        60,
        180,
        360,
        720,
        1440,
        2880,
        10080,
        np.inf,
    ]

    labels = [
        "<=0 min",
        "0-5 min",
        "5-15 min",
        "15-30 min",
        "30-60 min",
        "1-3 h",
        "3-6 h",
        "6-12 h",
        "12-24 h",
        "1-2 d",
        "2-7 d",
        ">7 d",
    ]

    return pd.cut(
        series,
        bins=bins,
        labels=labels,
        right=True,
    )


def relocation_bin(series: pd.Series) -> pd.Categorical:
    bins = [
        -np.inf,
        20,
        50,
        100,
        200,
        500,
        1000,
        2000,
        5000,
        20000,
        np.inf,
    ]

    labels = [
        "0-20 m",
        "20-50 m",
        "50-100 m",
        "100-200 m",
        "200-500 m",
        "0.5-1 km",
        "1-2 km",
        "2-5 km",
        "5-20 km",
        ">20 km",
    ]

    return pd.cut(
        series,
        bins=bins,
        labels=labels,
        right=True,
    )


def quantile_table(
    df: pd.DataFrame,
    column: str,
    metric_name: str,
) -> pd.DataFrame:

    quantiles = [
        0.01,
        0.05,
        0.10,
        0.25,
        0.50,
        0.75,
        0.90,
        0.95,
        0.99,
        0.995,
        0.999,
    ]

    records = []

    for operator, group in df.groupby("operator"):

        values = (
            group[column]
            .dropna()
            .astype(float)
        )

        if values.empty:
            continue

        record = {
            "operator": operator,
            "metric": metric_name,
            "count": len(values),
            "mean": values.mean(),
            "min": values.min(),
            "max": values.max(),
        }

        for q in quantiles:
            record[f"p{q * 100:g}"] = values.quantile(q)

        records.append(record)

    return pd.DataFrame(records)


# =============================================================================
# BUILD PARKING-INTERVAL CANDIDATES
# =============================================================================

def build_operator_intervals(
    operator: str,
) -> tuple[pd.DataFrame, dict]:

    print("\n" + "=" * 100)
    print(f"PROCESSING {operator.upper()}")
    print("=" * 100)

    df_2024 = load_operator_year(operator, 2024)
    df_2025 = load_operator_year(operator, 2025)

    rows_2024 = len(df_2024)
    rows_2025 = len(df_2025)

    df = pd.concat(
        [df_2024, df_2025],
        ignore_index=True,
    )

    del df_2024
    del df_2025

    # -------------------------------------------------------------------------
    # Standardize timestamps
    # -------------------------------------------------------------------------

    df["start_time_local"] = normalize_datetime(
        df["start_time_local"]
    )

    df["end_time_local"] = normalize_datetime(
        df["end_time_local"]
    )

    # Temporal detail must actually exist.
    has_timestamp_pair = (
        df["start_time_local"].notna()
        & df["end_time_local"].notna()
    )

    if "temporal_detail_available" in df.columns:
        has_timestamp_pair &= (
            df["temporal_detail_available"]
            .fillna(False)
            .astype(bool)
        )

    df = df.loc[has_timestamp_pair].copy()

    temporal_rows = len(df)

    # -------------------------------------------------------------------------
    # Sequence trips by globally safe vehicle identifier
    # -------------------------------------------------------------------------

    sort_columns = [
        "vehicle_uid",
        "start_time_local",
        "end_time_local",
    ]

    if "source_row" in df.columns:
        sort_columns.append("source_row")

    sort_columns.append("trip_uid")

    df = df.sort_values(
        sort_columns,
        kind="mergesort",
    ).reset_index(drop=True)

    grouped = df.groupby(
        "vehicle_uid",
        sort=False,
        observed=True,
    )

    # Next trip information for the SAME vehicle.
    df["next_trip_uid"] = grouped["trip_uid"].shift(-1)

    df["next_start_time_local"] = grouped[
        "start_time_local"
    ].shift(-1)

    df["next_start_lat"] = grouped[
        "start_lat"
    ].shift(-1)

    df["next_start_lon"] = grouped[
        "start_lon"
    ].shift(-1)

    if "valid_spatial_prezone" in df.columns:
        df["next_valid_spatial_prezone"] = grouped[
            "valid_spatial_prezone"
        ].shift(-1)

    # -------------------------------------------------------------------------
    # Restrict CURRENT parking-start events to Feb-Dec 2024.
    #
    # 2025 records were loaded only to allow a 31-Dec-2024 parking event
    # to be closed by the next observed 2025 trip.
    # -------------------------------------------------------------------------

    events = df.loc[
        (df["end_time_local"] >= ANALYSIS_START)
        & (df["end_time_local"] < ANALYSIS_END_EXCLUSIVE)
    ].copy()

    events["has_next_trip"] = (
        events["next_start_time_local"].notna()
    )

    # -------------------------------------------------------------------------
    # Local-clock gap
    # -------------------------------------------------------------------------

    events["parking_gap_clock_min"] = (
        (
            events["next_start_time_local"]
            - events["end_time_local"]
        )
        .dt.total_seconds()
        / 60.0
    )

    # -------------------------------------------------------------------------
    # DST-aware elapsed gap
    #
    # Do not guess ambiguous 02:xx timestamps during autumn clock change.
    # -------------------------------------------------------------------------

    events["parking_end_utc"] = local_wallclock_to_utc(
        events["end_time_local"]
    )

    events["next_start_utc"] = local_wallclock_to_utc(
        events["next_start_time_local"]
    )

    events["parking_gap_elapsed_min"] = (
        (
            events["next_start_utc"]
            - events["parking_end_utc"]
        )
        .dt.total_seconds()
        / 60.0
    )

    events["dst_elapsed_resolved"] = (
        events["parking_end_utc"].notna()
        & events["next_start_utc"].notna()
    )

    events["dst_endpoint_unresolved"] = (
        events["has_next_trip"]
        & ~events["dst_elapsed_resolved"]
    )

    # -------------------------------------------------------------------------
    # Destination of current trip -> origin of next trip
    # -------------------------------------------------------------------------

    relocation = haversine_m(
        events["end_lat"],
        events["end_lon"],
        events["next_start_lat"],
        events["next_start_lon"],
    )

    events["relocation_distance_m_raw"] = relocation

    # A common spatial validity check is preferable where available.
    if "valid_spatial_prezone" in events.columns:

        spatial_pair_valid = (
            events["valid_spatial_prezone"]
            .fillna(False)
            .astype(bool)
            &
            events["next_valid_spatial_prezone"]
            .fillna(False)
            .astype(bool)
        )

        events["spatial_pair_valid_prezone"] = (
            spatial_pair_valid
        )

        events["relocation_distance_m"] = (
            events[
                "relocation_distance_m_raw"
            ]
            .where(spatial_pair_valid)
        )

    else:

        events["spatial_pair_valid_prezone"] = (
            events[
                "relocation_distance_m_raw"
            ]
            .notna()
        )

        events["relocation_distance_m"] = (
            events["relocation_distance_m_raw"]
        )

    # -------------------------------------------------------------------------
    # Diagnostic flags ONLY — no filtering
    # -------------------------------------------------------------------------

    gap = events["parking_gap_elapsed_min"]

    events["gap_negative"] = gap < 0
    events["gap_zero"] = gap == 0
    events["gap_positive"] = gap > 0

    events["gap_over_6h"] = gap > 360
    events["gap_over_12h"] = gap > 720
    events["gap_over_24h"] = gap > 1440
    events["gap_over_48h"] = gap > 2880
    events["gap_over_7d"] = gap > 10080

    d = events["relocation_distance_m"]

    for threshold in [
        20,
        50,
        100,
        200,
        500,
        1000,
        2000,
        5000,
    ]:
        events[
            f"relocation_le_{threshold}m"
        ] = d <= threshold

    events["relocation_gt_1km"] = d > 1000
    events["relocation_gt_5km"] = d > 5000

    events["parking_duration_bin"] = duration_bin(
        events["parking_gap_elapsed_min"]
    )

    events["relocation_distance_bin"] = relocation_bin(
        events["relocation_distance_m"]
    )

    # Parking starts at the end of the current trip.
    events["parking_start_date"] = (
        events["end_time_local"].dt.date
    )

    events["parking_start_hour"] = (
        events["end_time_local"].dt.hour
    )

    # -------------------------------------------------------------------------
    # Audit summary
    # -------------------------------------------------------------------------

    resolved = events["parking_gap_elapsed_min"].notna()

    positive = (
        events["parking_gap_elapsed_min"] > 0
    )

    relocation_available = (
        events["relocation_distance_m"].notna()
    )

    summary = {
        "operator": operator,

        "source_rows_2024": rows_2024,
        "source_rows_2025": rows_2025,

        "rows_with_detailed_timestamps_for_sequence":
            temporal_rows,

        "candidate_parking_events_feb_dec_2024":
            len(events),

        "events_with_next_trip":
            int(events["has_next_trip"].sum()),

        "right_censored_no_next_trip":
            int((~events["has_next_trip"]).sum()),

        "elapsed_gap_resolved":
            int(resolved.sum()),

        "dst_or_timezone_unresolved":
            int(events["dst_endpoint_unresolved"].sum()),

        "negative_gap":
            int(events["gap_negative"].sum()),

        "zero_gap":
            int(events["gap_zero"].sum()),

        "positive_gap":
            int(events["gap_positive"].sum()),

        "positive_gap_over_6h":
            int((positive & events["gap_over_6h"]).sum()),

        "positive_gap_over_12h":
            int((positive & events["gap_over_12h"]).sum()),

        "positive_gap_over_24h":
            int((positive & events["gap_over_24h"]).sum()),

        "positive_gap_over_48h":
            int((positive & events["gap_over_48h"]).sum()),

        "positive_gap_over_7d":
            int((positive & events["gap_over_7d"]).sum()),

        "spatial_pair_valid_prezone":
            int(
                events[
                    "spatial_pair_valid_prezone"
                ].sum()
            ),

        "relocation_distance_available":
            int(relocation_available.sum()),

        "relocation_le_20m":
            int((relocation_available & (d <= 20)).sum()),

        "relocation_le_50m":
            int((relocation_available & (d <= 50)).sum()),

        "relocation_le_100m":
            int((relocation_available & (d <= 100)).sum()),

        "relocation_le_200m":
            int((relocation_available & (d <= 200)).sum()),

        "relocation_le_500m":
            int((relocation_available & (d <= 500)).sum()),

        "relocation_gt_1km":
            int((relocation_available & (d > 1000)).sum()),

        "relocation_gt_5km":
            int((relocation_available & (d > 5000)).sum()),
    }

    # -------------------------------------------------------------------------
    # Save operator candidate intervals
    # -------------------------------------------------------------------------

    output_path = (
        OUTPUT_DIR
        / f"{operator}_parking_interval_candidates_2024.parquet"
    )

    events.to_parquet(
        output_path,
        index=False,
    )

    print(f"\nSaved candidate intervals -> {output_path}")

    # Suspicious examples for manual inspection.
    events.loc[
        events["gap_negative"]
    ].to_csv(
        AUDIT_DIR
        / f"{operator}_negative_gap_examples.csv",
        index=False,
    )

    events.loc[
        events["relocation_distance_m"] > 1000
    ].sort_values(
        "relocation_distance_m",
        ascending=False,
    ).head(1000).to_csv(
        AUDIT_DIR
        / f"{operator}_large_relocation_examples.csv",
        index=False,
    )

    events.loc[
        events["parking_gap_elapsed_min"] > 10080
    ].sort_values(
        "parking_gap_elapsed_min",
        ascending=False,
    ).head(1000).to_csv(
        AUDIT_DIR
        / f"{operator}_long_gap_examples.csv",
        index=False,
    )

    return events, summary


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 110)
    print("EXERCISE 4 — PARKING INTERVAL AUDIT")
    print("=" * 110)

    print(
        f"\nAnalysis window for parking starts: "
        f"{ANALYSIS_START} -> "
        f"{ANALYSIS_END_EXCLUSIVE}"
    )

    print(
        "\nIMPORTANT:"
        "\n- 2025 trips are used only to close the next-trip sequence"
        " for parking events starting at the end of 2024."
        "\n- No parking-duration threshold is applied."
        "\n- No relocation threshold is applied."
        "\n- No records are classified as valid parking yet."
    )

    all_events = []
    summaries = []

    for operator in OPERATORS:

        events, summary = build_operator_intervals(
            operator
        )

        all_events.append(events)
        summaries.append(summary)

    combined = pd.concat(
        all_events,
        ignore_index=True,
    )

    summary_df = pd.DataFrame(summaries)

    # -------------------------------------------------------------------------
    # Duration quantiles — only positive, resolved gaps
    # -------------------------------------------------------------------------

    positive = combined.loc[
        combined["parking_gap_elapsed_min"] > 0
    ].copy()

    duration_quantiles = quantile_table(
        positive,
        "parking_gap_elapsed_min",
        "positive_parking_gap_minutes",
    )

    relocation_quantiles = quantile_table(
        positive.loc[
            positive[
                "relocation_distance_m"
            ].notna()
        ],
        "relocation_distance_m",
        "end_to_next_start_distance_m",
    )

    # -------------------------------------------------------------------------
    # Bin distributions
    # -------------------------------------------------------------------------

    duration_bins = (
        combined
        .groupby(
            [
                "operator",
                "parking_duration_bin",
            ],
            observed=False,
        )
        .size()
        .reset_index(name="count")
    )

    relocation_bins = (
        combined
        .groupby(
            [
                "operator",
                "relocation_distance_bin",
            ],
            observed=False,
        )
        .size()
        .reset_index(name="count")
    )

    # Cross-tab: useful for deciding whether long idle times are associated
    # with large spatial relocations.
    cross_tab = (
        combined
        .groupby(
            [
                "operator",
                "parking_duration_bin",
                "relocation_distance_bin",
            ],
            observed=False,
        )
        .size()
        .reset_index(name="count")
    )

    # -------------------------------------------------------------------------
    # SAVE AUDITS
    # -------------------------------------------------------------------------

    summary_path = (
        AUDIT_DIR
        / "parking_interval_audit_summary_2024.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
    )

    duration_quantiles.to_csv(
        AUDIT_DIR
        / "parking_duration_quantiles_2024.csv",
        index=False,
    )

    relocation_quantiles.to_csv(
        AUDIT_DIR
        / "relocation_distance_quantiles_2024.csv",
        index=False,
    )

    duration_bins.to_csv(
        AUDIT_DIR
        / "parking_duration_bins_2024.csv",
        index=False,
    )

    relocation_bins.to_csv(
        AUDIT_DIR
        / "relocation_distance_bins_2024.csv",
        index=False,
    )

    cross_tab.to_csv(
        AUDIT_DIR
        / "parking_duration_x_relocation_2024.csv",
        index=False,
    )

    # -------------------------------------------------------------------------
    # TERMINAL OUTPUT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 110)
    print("PARKING INTERVAL AUDIT SUMMARY")
    print("=" * 110)

    print(
        summary_df.to_string(
            index=False
        )
    )

    print("\n" + "-" * 110)
    print("POSITIVE PARKING-GAP QUANTILES [MINUTES]")
    print("-" * 110)

    print(
        duration_quantiles.to_string(
            index=False
        )
    )

    print("\n" + "-" * 110)
    print("END -> NEXT-START DISPLACEMENT QUANTILES [METRES]")
    print("-" * 110)

    print(
        relocation_quantiles.to_string(
            index=False
        )
    )

    print("\n" + "-" * 110)
    print("PARKING-DURATION BINS")
    print("-" * 110)

    print(
        duration_bins.to_string(
            index=False
        )
    )

    print("\n" + "-" * 110)
    print("RELOCATION-DISTANCE BINS")
    print("-" * 110)

    print(
        relocation_bins.to_string(
            index=False
        )
    )

    print("\n" + "=" * 110)
    print("AUDIT COMPLETED")
    print("=" * 110)

    print(
        "\nNo parking observations were removed."
    )

    print(
        "No stationary-parking threshold has been chosen."
    )

    print(
        "No upper parking-duration cutoff has been chosen."
    )

    print(
        f"\nSummary -> {summary_path}"
    )


if __name__ == "__main__":
    main()