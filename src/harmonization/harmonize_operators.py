from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEANED_DIR = (
    PROJECT_ROOT
    / "data"
    / "cleaned"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "harmonized"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "harmonization"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# INPUT FILES
# ============================================================

FILES = {
    ("bird", 2024):
        CLEANED_DIR
        / "bird"
        / "bird_2024_clean.parquet",

    ("bird", 2025):
        CLEANED_DIR
        / "bird"
        / "bird_2025_clean.parquet",

    ("lime", 2024):
        CLEANED_DIR
        / "lime"
        / "lime_2024_clean.parquet",

    ("lime", 2025):
        CLEANED_DIR
        / "lime"
        / "lime_2025_clean.parquet",

    ("voi", 2024):
        CLEANED_DIR
        / "voi"
        / "voi_2024_clean.parquet",

    ("voi", 2025):
        CLEANED_DIR
        / "voi"
        / "voi_2025_clean.parquet",
}


# ============================================================
# COMMON SCHEMA
# ============================================================

COMMON_COLUMNS = [
    # Identity
    "operator",
    "vehicle_type",
    "trip_uid",
    "source_trip_id",
    "vehicle_id",
    "vehicle_uid",

    # Temporal
    "start_time_local",
    "end_time_local",
    "start_time_utc",
    "end_time_utc",
    "duration_min_clean",
    "duration_source",
    "timestamp_source_timezone",
    "timestamp_precision",

    # Spatial
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
    "endpoint_displacement_km",
    "valid_endpoint_displacement",

    # Operator-specific distance
    "distance_value_km",
    "distance_measure_type",
    "distance_precision",

    # Operator-specific speed
    "speed_value_kmh",
    "speed_measure_type",

    # Provenance
    "source_period",
    "year",
    "source_file",
    "source_row",

    # Validity
    "valid_trip_record",
    "valid_monthly_period",
    "valid_temporal_detail",
    "valid_duration",
    "temporal_clock_ambiguous",
    "valid_spatial_prezone",
    "valid_distance_measurement",
    "valid_speed_measurement",

    # Common comparable kinematic diagnostic
    "endpoint_speed_kmh",
    "endpoint_speed_warning_40",

    # Reservation
    "reservation_status",
    "reservation_conflict",

    # Battery
    "battery_start_pct",
    "battery_end_pct",
    "battery_available",
    "valid_battery",
]


# ============================================================
# CANONICAL ARROW SCHEMA
#
# IMPORTANT:
# This schema is the authoritative physical schema of all
# harmonized Parquet files.
#
# It avoids operator-specific Arrow inference differences,
# particularly for:
# - all-null source_trip_id columns
# - nullable strings
# - timezone-aware UTC timestamps
# - nullable integer fields
# ============================================================

CANONICAL_ARROW_SCHEMA = pa.schema([
    # Identity
    pa.field(
        "operator",
        pa.string()
    ),

    pa.field(
        "vehicle_type",
        pa.string()
    ),

    pa.field(
        "trip_uid",
        pa.string()
    ),

    pa.field(
        "source_trip_id",
        pa.string()
    ),

    pa.field(
        "vehicle_id",
        pa.string()
    ),

    pa.field(
        "vehicle_uid",
        pa.string()
    ),

    # Temporal
    pa.field(
        "start_time_local",
        pa.timestamp("ns")
    ),

    pa.field(
        "end_time_local",
        pa.timestamp("ns")
    ),

    pa.field(
        "start_time_utc",
        pa.timestamp(
            "ns",
            tz="UTC"
        )
    ),

    pa.field(
        "end_time_utc",
        pa.timestamp(
            "ns",
            tz="UTC"
        )
    ),

    pa.field(
        "duration_min_clean",
        pa.float64()
    ),

    pa.field(
        "duration_source",
        pa.string()
    ),

    pa.field(
        "timestamp_source_timezone",
        pa.string()
    ),

    pa.field(
        "timestamp_precision",
        pa.string()
    ),

    # Spatial
    pa.field(
        "start_lat",
        pa.float64()
    ),

    pa.field(
        "start_lon",
        pa.float64()
    ),

    pa.field(
        "end_lat",
        pa.float64()
    ),

    pa.field(
        "end_lon",
        pa.float64()
    ),

    pa.field(
        "endpoint_displacement_km",
        pa.float64()
    ),

    pa.field(
        "valid_endpoint_displacement",
        pa.bool_()
    ),

    # Operator-specific distance
    pa.field(
        "distance_value_km",
        pa.float64()
    ),

    pa.field(
        "distance_measure_type",
        pa.string()
    ),

    pa.field(
        "distance_precision",
        pa.string()
    ),

    # Operator-specific speed
    pa.field(
        "speed_value_kmh",
        pa.float64()
    ),

    pa.field(
        "speed_measure_type",
        pa.string()
    ),

    # Provenance
    pa.field(
        "source_period",
        pa.string()
    ),

    pa.field(
        "year",
        pa.int64()
    ),

    pa.field(
        "source_file",
        pa.string()
    ),

    pa.field(
        "source_row",
        pa.int64()
    ),

    # Validity
    pa.field(
        "valid_trip_record",
        pa.bool_()
    ),

    pa.field(
        "valid_monthly_period",
        pa.bool_()
    ),

    pa.field(
        "valid_temporal_detail",
        pa.bool_()
    ),

    pa.field(
        "valid_duration",
        pa.bool_()
    ),

    pa.field(
        "temporal_clock_ambiguous",
        pa.bool_()
    ),

    pa.field(
        "valid_spatial_prezone",
        pa.bool_()
    ),

    pa.field(
        "valid_distance_measurement",
        pa.bool_()
    ),

    pa.field(
        "valid_speed_measurement",
        pa.bool_()
    ),

    # Common endpoint kinematic diagnostic
    pa.field(
        "endpoint_speed_kmh",
        pa.float64()
    ),

    pa.field(
        "endpoint_speed_warning_40",
        pa.bool_()
    ),

    # Reservation
    pa.field(
        "reservation_status",
        pa.string()
    ),

    pa.field(
        "reservation_conflict",
        pa.bool_()
    ),

    # Battery
    pa.field(
        "battery_start_pct",
        pa.float64()
    ),

    pa.field(
        "battery_end_pct",
        pa.float64()
    ),

    pa.field(
        "battery_available",
        pa.bool_()
    ),

    pa.field(
        "valid_battery",
        pa.bool_()
    ),
])


# ============================================================
# BASIC HELPERS
# ============================================================

def nullable_utc(index):

    return pd.Series(
        pd.NaT,
        index=index,
        dtype="datetime64[ns, UTC]",
    )


def nullable_string(index):

    return pd.Series(
        pd.NA,
        index=index,
        dtype="string",
    )


def nullable_float(index):

    return pd.Series(
        np.nan,
        index=index,
        dtype="float64",
    )


def normalize_reservation(series):

    values = (
        series
        .astype("string")
        .str.strip()
        .str.lower()
    )

    result = pd.Series(
        pd.NA,
        index=series.index,
        dtype="string",
    )

    yes_values = {
        "sì",
        "si",
        "yes",
        "y",
        "1",
        "true",
    }

    no_values = {
        "no",
        "n",
        "0",
        "false",
    }

    result.loc[
        values.isin(
            yes_values
        )
    ] = "yes"

    result.loc[
        values.isin(
            no_values
        )
    ] = "no"

    return result


def source_file_series(
    df,
    fallback_name
):

    if (
        "SOURCE_FILE"
        in df.columns
    ):

        return (
            df["SOURCE_FILE"]
            .astype("string")
        )

    return pd.Series(
        fallback_name,
        index=df.index,
        dtype="string",
    )


def source_row_series(df):

    if (
        "SOURCE_ROW"
        not in df.columns
    ):

        raise ValueError(
            "SOURCE_ROW is required "
            "for harmonization traceability."
        )

    result = pd.to_numeric(
        df["SOURCE_ROW"],
        errors="coerce"
    )

    if result.isna().any():

        raise ValueError(
            "SOURCE_ROW contains missing or "
            "non-numeric values."
        )

    return (
        result
        .astype("Int64")
    )


def derive_source_period(
    df,
    start_time
):

    if (
        "SOURCE_PERIOD"
        in df.columns
    ):

        return (
            df["SOURCE_PERIOD"]
            .astype("string")
        )

    return (
        pd.to_datetime(
            start_time,
            errors="coerce"
        )
        .dt.to_period("M")
        .astype("string")
    )


# ============================================================
# BIRD HARMONIZATION
# ============================================================

def harmonize_bird(
    df,
    year,
    input_path
):

    h = pd.DataFrame(
        index=df.index
    )

    source_row = (
        source_row_series(
            df
        )
    )

    start_local = pd.to_datetime(
        df["START_TIME"],
        errors="coerce",
    )

    end_local = pd.to_datetime(
        df["END_TIME_RAW"],
        errors="coerce",
    )

    source_period = (
        derive_source_period(
            df,
            start_local
        )
    )

    # ========================================================
    # IDENTITY
    # ========================================================

    h["operator"] = (
        "bird"
    )

    h["vehicle_type"] = (
        "e_scooter"
    )

    # Bird has no provider-level trip ID.
    h["source_trip_id"] = (
        nullable_string(
            df.index
        )
    )

    h["trip_uid"] = (
        "bird:"
        + str(year)
        + ":"
        + source_row.astype(
            "string"
        )
    )

    h["vehicle_id"] = (
        df["ID_VEICOLO"]
        .astype("string")
    )

    h["vehicle_uid"] = (
        "bird:"
        + h["vehicle_id"]
    )

    # ========================================================
    # TEMPORAL
    # ========================================================

    h["start_time_local"] = (
        start_local
    )

    h["end_time_local"] = (
        end_local
    )

    # Bird provides local clock timestamps.
    # Exact UTC instants are not reconstructed here because
    # the autumn DST repeated-hour records are ambiguous.
    h["start_time_utc"] = (
        nullable_utc(
            df.index
        )
    )

    h["end_time_utc"] = (
        nullable_utc(
            df.index
        )
    )

    h["duration_min_clean"] = (
        pd.to_numeric(
            df["DURATA_MIN"],
            errors="coerce"
        )
    )

    h["duration_source"] = (
        "provider_duration"
    )

    h[
        "timestamp_source_timezone"
    ] = (
        "Europe/Rome_local_clock"
    )

    h["timestamp_precision"] = (
        "minute"
    )

    # ========================================================
    # SPATIAL
    # ========================================================

    h["start_lat"] = (
        pd.to_numeric(
            df[
                "LATITUDINE_INIZIO_CORSA"
            ],
            errors="coerce"
        )
    )

    h["start_lon"] = (
        pd.to_numeric(
            df[
                "LONGITUTIDE_INIZIO_CORSA"
            ],
            errors="coerce"
        )
    )

    h["end_lat"] = (
        pd.to_numeric(
            df[
                "LATITUDINE_FINE_CORSA"
            ],
            errors="coerce"
        )
    )

    h["end_lon"] = (
        pd.to_numeric(
            df[
                "LONGITUTIDE_FINE_CORSA"
            ],
            errors="coerce"
        )
    )

    h[
        "endpoint_displacement_km"
    ] = (
        pd.to_numeric(
            df["HAVERSINE_KM"],
            errors="coerce"
        )
    )

    # ========================================================
    # OPERATOR DISTANCE
    # ========================================================

    h["distance_value_km"] = (
        pd.to_numeric(
            df["DISTANCE_KM_CLEAN"],
            errors="coerce"
        )
    )

    h[
        "distance_measure_type"
    ] = (
        "provider_reported_trip_distance"
    )

    h["distance_precision"] = (
        "continuous_decimal_km"
    )

    # ========================================================
    # OPERATOR SPEED
    # ========================================================

    h["speed_value_kmh"] = (
        pd.to_numeric(
            df["SPEED_KMH_CLEAN"],
            errors="coerce"
        )
    )

    h["speed_measure_type"] = (
        "reported_distance_over_provider_duration"
    )

    # ========================================================
    # PROVENANCE
    # ========================================================

    h["source_period"] = (
        source_period
    )

    h["year"] = (
        year
    )

    h["source_file"] = (
        source_file_series(
            df,
            input_path.name
        )
    )

    h["source_row"] = (
        source_row
    )

    # ========================================================
    # VALIDITY
    # ========================================================

    h["valid_trip_record"] = (
        df[
            "VALID_TRIP_RECORD"
        ]
    )

    h["valid_monthly_period"] = (
        source_period.notna()
    )

    h[
        "valid_temporal_detail"
    ] = (
        start_local.notna()
        & end_local.notna()
    )

    h["valid_duration"] = (
        h[
            "duration_min_clean"
        ].notna()
        &
        (
            h[
                "duration_min_clean"
            ] > 0
        )
    )

    h[
        "temporal_clock_ambiguous"
    ] = (
        df[
            "TEMPORAL_DST_AMBIGUOUS"
        ]
    )

    h[
        "valid_spatial_prezone"
    ] = (
        df[
            "VALID_SPATIAL_PREZONE"
        ]
    )

    h[
        "valid_distance_measurement"
    ] = (
        df[
            "VALID_DISTANCE"
        ]
    )

    h[
        "valid_speed_measurement"
    ] = (
        df[
            "VALID_SPEED"
        ]
    )

    # ========================================================
    # RESERVATION
    # ========================================================

    if (
        "RISERVATO"
        in df.columns
    ):

        h[
            "reservation_status"
        ] = (
            normalize_reservation(
                df["RISERVATO"]
            )
        )

    else:

        h[
            "reservation_status"
        ] = (
            nullable_string(
                df.index
            )
        )

    h[
        "reservation_conflict"
    ] = False

    # ========================================================
    # BATTERY
    #
    # Bird dataset has no usable common battery variables.
    # ========================================================

    h["battery_start_pct"] = (
        nullable_float(
            df.index
        )
    )

    h["battery_end_pct"] = (
        nullable_float(
            df.index
        )
    )

    h["battery_available"] = (
        False
    )

    h["valid_battery"] = (
        False
    )

    return h


# ============================================================
# LIME HARMONIZATION
# ============================================================

def harmonize_lime(
    df,
    year,
    input_path
):

    h = pd.DataFrame(
        index=df.index
    )

    source_row = (
        source_row_series(
            df
        )
    )

    start_local = pd.to_datetime(
        df["START_TIME"],
        errors="coerce",
    )

    end_local = pd.to_datetime(
        df["END_TIME_RAW"],
        errors="coerce",
    )

    source_period = (
        df["SOURCE_PERIOD"]
        .astype("string")
    )

    # ========================================================
    # IDENTITY
    # ========================================================

    h["operator"] = (
        "lime"
    )

    h["vehicle_type"] = (
        "e_scooter"
    )

    # Lime dataset has no provider-level trip identifier.
    h["source_trip_id"] = (
        nullable_string(
            df.index
        )
    )

    # SOURCE_ROW restarts in each monthly file,
    # therefore SOURCE_PERIOD must be part of trip_uid.
    h["trip_uid"] = (
        "lime:"
        + source_period
        + ":"
        + source_row.astype(
            "string"
        )
    )

    h["vehicle_id"] = (
        df["ID_VEICOLO"]
        .astype("string")
    )

    h["vehicle_uid"] = (
        "lime:"
        + h["vehicle_id"]
    )

    # ========================================================
    # TEMPORAL
    # ========================================================

    h["start_time_local"] = (
        start_local
    )

    h["end_time_local"] = (
        end_local
    )

    h["start_time_utc"] = (
        nullable_utc(
            df.index
        )
    )

    h["end_time_utc"] = (
        nullable_utc(
            df.index
        )
    )

    h["duration_min_clean"] = (
        pd.to_numeric(
            df[
                "DURATION_MIN_CLEAN"
            ],
            errors="coerce"
        )
    )

    h["duration_source"] = (
        "timestamp_elapsed_dst_corrected"
    )

    h[
        "timestamp_source_timezone"
    ] = (
        "Europe/Rome_local_clock"
    )

    h["timestamp_precision"] = (
        "second"
    )

    # ========================================================
    # SPATIAL
    # ========================================================

    h["start_lat"] = (
        pd.to_numeric(
            df[
                "LATITUDINE_INIZIO_CORSA"
            ],
            errors="coerce"
        )
    )

    h["start_lon"] = (
        pd.to_numeric(
            df[
                "LONGITUTIDE_INIZIO_CORSA"
            ],
            errors="coerce"
        )
    )

    h["end_lat"] = (
        pd.to_numeric(
            df[
                "LATITUDINE_FINE_CORSA"
            ],
            errors="coerce"
        )
    )

    h["end_lon"] = (
        pd.to_numeric(
            df[
                "LONGITUTIDE_FINE_CORSA"
            ],
            errors="coerce"
        )
    )

    h[
        "endpoint_displacement_km"
    ] = (
        pd.to_numeric(
            df["HAVERSINE_KM"],
            errors="coerce"
        )
    )

    # ========================================================
    # OPERATOR DISTANCE
    # ========================================================

    h["distance_value_km"] = (
        pd.to_numeric(
            df["DISTANCE_KM_CLEAN"],
            errors="coerce"
        )
    )

    h[
        "distance_measure_type"
    ] = (
        "provider_reported_distance"
    )

    h["distance_precision"] = (
        "integer_km_rounded"
    )

    # ========================================================
    # OPERATOR SPEED
    # ========================================================

    h["speed_value_kmh"] = (
        pd.to_numeric(
            df["SPEED_KMH_APPROX"],
            errors="coerce"
        )
    )

    h["speed_measure_type"] = (
        "rounded_reported_distance_over_clean_duration"
    )

    # ========================================================
    # PROVENANCE
    # ========================================================

    h["source_period"] = (
        source_period
    )

    h["year"] = (
        year
    )

    h["source_file"] = (
        source_file_series(
            df,
            input_path.name
        )
    )

    h["source_row"] = (
        source_row
    )

    # ========================================================
    # VALIDITY
    # ========================================================

    h["valid_trip_record"] = (
        df[
            "VALID_TRIP_RECORD"
        ]
    )

    h["valid_monthly_period"] = (
        source_period.notna()
    )

    h[
        "valid_temporal_detail"
    ] = (
        start_local.notna()
        & end_local.notna()
    )

    h["valid_duration"] = (
        h[
            "duration_min_clean"
        ].notna()
        &
        (
            h[
                "duration_min_clean"
            ] > 0
        )
    )

    h[
        "temporal_clock_ambiguous"
    ] = (
        df["FLAG_DST"]
    )

    h[
        "valid_spatial_prezone"
    ] = (
        df[
            "VALID_SPATIAL_PREZONE"
        ]
    )

    h[
        "valid_distance_measurement"
    ] = (
        df[
            "VALID_DISTANCE"
        ]
    )

    h[
        "valid_speed_measurement"
    ] = (
        df[
            "VALID_SPEED_APPROX"
        ]
    )

    # ========================================================
    # RESERVATION
    # ========================================================

    if (
        "RISERVATO"
        in df.columns
    ):

        h[
            "reservation_status"
        ] = (
            normalize_reservation(
                df["RISERVATO"]
            )
        )

    else:

        h[
            "reservation_status"
        ] = (
            nullable_string(
                df.index
            )
        )

    h[
        "reservation_conflict"
    ] = False

    # ========================================================
    # BATTERY
    # ========================================================

    h["battery_start_pct"] = (
        pd.to_numeric(
            df[
                "BATTERIA_INIZIO_CORSA"
            ],
            errors="coerce"
        )
    )

    h["battery_end_pct"] = (
        pd.to_numeric(
            df[
                "BATTERIA_FINE_CORSA"
            ],
            errors="coerce"
        )
    )

    h["battery_available"] = (
        h[
            "battery_start_pct"
        ].notna()
        &
        h[
            "battery_end_pct"
        ].notna()
    )

    h["valid_battery"] = (
        df["VALID_BATTERY"]
    )

    return h


# ============================================================
# VOI HARMONIZATION
# ============================================================

def harmonize_voi(
    df,
    year,
    input_path
):

    h = pd.DataFrame(
        index=df.index
    )

    source_row = (
        source_row_series(
            df
        )
    )

    source_period = (
        df["SOURCE_PERIOD"]
        .astype("string")
    )

    source_trip_id = (
        df[
            "Identificativo noleggio"
        ]
        .astype("string")
    )

    # ========================================================
    # IDENTITY
    # ========================================================

    h["operator"] = (
        "voi"
    )

    h["vehicle_type"] = (
        "e_scooter"
    )

    h["source_trip_id"] = (
        source_trip_id
    )

    h["trip_uid"] = (
        "voi:"
        + source_trip_id
    )

    h["vehicle_id"] = (
        df["Targa veicolo"]
        .astype("string")
    )

    h["vehicle_uid"] = (
        "voi:"
        + h["vehicle_id"]
    )

    # ========================================================
    # TEMPORAL
    # ========================================================

    h["start_time_local"] = (
        pd.to_datetime(
            df["START_TIME_LOCAL"],
            errors="coerce",
        )
    )

    h["end_time_local"] = (
        pd.to_datetime(
            df["END_TIME_LOCAL"],
            errors="coerce",
        )
    )

    h["start_time_utc"] = (
        pd.to_datetime(
            df["START_TIME_UTC"],
            errors="coerce",
            utc=True,
        )
    )

    h["end_time_utc"] = (
        pd.to_datetime(
            df["END_TIME_UTC"],
            errors="coerce",
            utc=True,
        )
    )

    h["duration_min_clean"] = (
        pd.to_numeric(
            df[
                "DURATION_MIN_CLEAN"
            ],
            errors="coerce"
        )
    )

    h["duration_source"] = (
        df["DURATION_SOURCE"]
        .astype("string")
    )

    h[
        "timestamp_source_timezone"
    ] = (
        "UTC_converted_to_Europe/Rome"
    )

    h["timestamp_precision"] = (
        "second"
    )

    # ========================================================
    # SPATIAL
    # ========================================================

    h["start_lat"] = (
        pd.to_numeric(
            df[
                "Lat inizio corsa_coordinate"
            ],
            errors="coerce"
        )
    )

    h["start_lon"] = (
        pd.to_numeric(
            df[
                "Lon inizio corsa_coordinate"
            ],
            errors="coerce"
        )
    )

    h["end_lat"] = (
        pd.to_numeric(
            df[
                "Lat fine corsa_coordinate"
            ],
            errors="coerce"
        )
    )

    h["end_lon"] = (
        pd.to_numeric(
            df[
                "Lon fine corsa_coordinate"
            ],
            errors="coerce"
        )
    )

    h[
        "endpoint_displacement_km"
    ] = (
        pd.to_numeric(
            df["HAVERSINE_KM"],
            errors="coerce"
        )
    )

    # ========================================================
    # OPERATOR DISTANCE
    # ========================================================

    h["distance_value_km"] = (
        pd.to_numeric(
            df["DISTANCE_KM_CLEAN"],
            errors="coerce"
        )
    )

    h[
        "distance_measure_type"
    ] = (
        "endpoint_displacement"
    )

    h["distance_precision"] = (
        "continuous_decimal_km"
    )

    # ========================================================
    # OPERATOR SPEED
    # ========================================================

    h["speed_value_kmh"] = (
        pd.to_numeric(
            df["SPEED_KMH_CLEAN"],
            errors="coerce"
        )
    )

    h["speed_measure_type"] = (
        "endpoint_displacement_over_clean_duration"
    )

    # ========================================================
    # PROVENANCE
    # ========================================================

    h["source_period"] = (
        source_period
    )

    h["year"] = (
        year
    )

    h["source_file"] = (
        source_file_series(
            df,
            input_path.name
        )
    )

    h["source_row"] = (
        source_row
    )

    # ========================================================
    # VALIDITY
    # ========================================================

    h["valid_trip_record"] = (
        df[
            "VALID_TRIP_RECORD"
        ]
    )

    h["valid_monthly_period"] = (
        df[
            "VALID_MONTHLY_PERIOD"
        ]
    )

    h[
        "valid_temporal_detail"
    ] = (
        df[
            "HAS_TEMPORAL_DETAIL"
        ]
    )

    h["valid_duration"] = (
        df["VALID_DURATION"]
    )

    # VOI raw timestamps are UTC.
    # Once converted to local time, DST ambiguity is resolved.
    h[
        "temporal_clock_ambiguous"
    ] = False

    h[
        "valid_spatial_prezone"
    ] = (
        df[
            "VALID_SPATIAL_PREZONE"
        ]
    )

    h[
        "valid_distance_measurement"
    ] = (
        df[
            "VALID_DISTANCE"
        ]
    )

    h[
        "valid_speed_measurement"
    ] = (
        df[
            "VALID_SPEED"
        ]
    )

    # ========================================================
    # RESERVATION
    # ========================================================

    h["reservation_status"] = (
        normalize_reservation(
            df[
                "PRENOTAZIONE_CLEAN"
            ]
        )
    )

    h[
        "reservation_conflict"
    ] = (
        df[
            "PRENOTAZIONE_CONFLICT"
        ]
    )

    # ========================================================
    # BATTERY
    # ========================================================

    h["battery_start_pct"] = (
        pd.to_numeric(
            df[
                "Batteria inizio"
            ],
            errors="coerce"
        )
    )

    h["battery_end_pct"] = (
        pd.to_numeric(
            df[
                "Batteria fine"
            ],
            errors="coerce"
        )
    )

    h["battery_available"] = (
        h[
            "battery_start_pct"
        ].notna()
        &
        h[
            "battery_end_pct"
        ].notna()
    )

    h["valid_battery"] = (
        df["VALID_BATTERY"]
    )

    return h


# ============================================================
# COMMON DERIVED FIELDS
# ============================================================

def add_common_fields(h):

    h = h.copy()

    # ========================================================
    # COMMON ENDPOINT DISPLACEMENT VALIDITY
    #
    # endpoint_displacement_km is calculated using the same
    # Haversine concept for all operators.
    # ========================================================

    h[
        "valid_endpoint_displacement"
    ] = (
        h[
            "valid_spatial_prezone"
        ]
        &
        h[
            "endpoint_displacement_km"
        ].notna()
        &
        (
            h[
                "endpoint_displacement_km"
            ] >= 0
        )
    )

    # ========================================================
    # COMMON ENDPOINT SPEED
    #
    # IMPORTANT:
    # This is NOT route/travelled speed.
    #
    # It is:
    # straight-line endpoint displacement / trip duration
    #
    # It is useful as a consistent cross-operator kinematic
    # diagnostic.
    # ========================================================

    h["endpoint_speed_kmh"] = (
        np.nan
    )

    valid_endpoint_speed = (
        h[
            "valid_endpoint_displacement"
        ]
        &
        h[
            "valid_duration"
        ]
        &
        (
            h[
                "duration_min_clean"
            ] > 0
        )
    )

    h.loc[
        valid_endpoint_speed,
        "endpoint_speed_kmh"
    ] = (
        h.loc[
            valid_endpoint_speed,
            "endpoint_displacement_km"
        ]
        /
        (
            h.loc[
                valid_endpoint_speed,
                "duration_min_clean"
            ]
            / 60
        )
    )

    h[
        "endpoint_speed_warning_40"
    ] = (
        h[
            "endpoint_speed_kmh"
        ].notna()
        &
        (
            h[
                "endpoint_speed_kmh"
            ] > 40
        )
    )

    return h


# ============================================================
# PANDAS DTYPE STANDARDIZATION
# ============================================================

STRING_COLUMNS = [
    "operator",
    "vehicle_type",
    "trip_uid",
    "source_trip_id",
    "vehicle_id",
    "vehicle_uid",
    "duration_source",
    "timestamp_source_timezone",
    "timestamp_precision",
    "distance_measure_type",
    "distance_precision",
    "speed_measure_type",
    "source_period",
    "source_file",
    "reservation_status",
]


FLOAT_COLUMNS = [
    "duration_min_clean",
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
    "endpoint_displacement_km",
    "distance_value_km",
    "speed_value_kmh",
    "endpoint_speed_kmh",
    "battery_start_pct",
    "battery_end_pct",
]


BOOLEAN_COLUMNS = [
    "valid_endpoint_displacement",
    "valid_trip_record",
    "valid_monthly_period",
    "valid_temporal_detail",
    "valid_duration",
    "temporal_clock_ambiguous",
    "valid_spatial_prezone",
    "valid_distance_measurement",
    "valid_speed_measurement",
    "endpoint_speed_warning_40",
    "reservation_conflict",
    "battery_available",
    "valid_battery",
]


def standardize_dtypes(h):

    h = h.copy()

    missing_columns = [
        col
        for col in COMMON_COLUMNS
        if col not in h.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing common harmonization columns: "
            f"{missing_columns}"
        )

    # --------------------------------------------------------
    # Strings
    # --------------------------------------------------------

    for col in STRING_COLUMNS:

        h[col] = (
            h[col]
            .astype("string")
        )

    # --------------------------------------------------------
    # Floats
    # --------------------------------------------------------

    for col in FLOAT_COLUMNS:

        h[col] = (
            pd.to_numeric(
                h[col],
                errors="coerce"
            )
            .astype("float64")
        )

    # --------------------------------------------------------
    # Booleans
    # --------------------------------------------------------

    for col in BOOLEAN_COLUMNS:

        h[col] = (
            h[col]
            .astype("boolean")
        )

    # --------------------------------------------------------
    # Integers
    # --------------------------------------------------------

    h["source_row"] = (
        pd.to_numeric(
            h["source_row"],
            errors="coerce"
        )
        .astype("Int64")
    )

    h["year"] = (
        pd.to_numeric(
            h["year"],
            errors="coerce"
        )
        .astype("Int64")
    )

    # --------------------------------------------------------
    # Local timestamps
    # --------------------------------------------------------

    h["start_time_local"] = (
        pd.to_datetime(
            h["start_time_local"],
            errors="coerce",
        )
    )

    h["end_time_local"] = (
        pd.to_datetime(
            h["end_time_local"],
            errors="coerce",
        )
    )

    # --------------------------------------------------------
    # UTC timestamps
    # --------------------------------------------------------

    h["start_time_utc"] = (
        pd.to_datetime(
            h["start_time_utc"],
            errors="coerce",
            utc=True,
        )
    )

    h["end_time_utc"] = (
        pd.to_datetime(
            h["end_time_utc"],
            errors="coerce",
            utc=True,
        )
    )

    # --------------------------------------------------------
    # Final column order
    # --------------------------------------------------------

    h = h[
        COMMON_COLUMNS
    ].copy()

    return h


# ============================================================
# ARROW CONVERSION
# ============================================================

def to_canonical_arrow_table(h):

    # Explicit schema prevents PyArrow from inferring
    # different physical types between operators.
    table = pa.Table.from_pandas(
        h,
        schema=CANONICAL_ARROW_SCHEMA,
        preserve_index=False,
        safe=True,
    )

    # Remove pandas-specific metadata so that the same
    # canonical Arrow schema is stored in all files.
    table = (
        table
        .replace_schema_metadata()
    )

    return table


# ============================================================
# HARMONIZED DATA VALIDATION
# ============================================================

def validate_harmonized(
    source_df,
    h,
    operator,
    year,
):

    print(
        "\nValidation:"
    )

    # --------------------------------------------------------
    # No rows may disappear during harmonization
    # --------------------------------------------------------

    assert (
        len(source_df)
        ==
        len(h)
    ), (
        f"{operator} {year}: "
        "row count changed during harmonization."
    )

    # --------------------------------------------------------
    # Globally unique analytical trip key
    # --------------------------------------------------------

    assert (
        h["trip_uid"]
        .notna()
        .all()
    ), (
        f"{operator} {year}: "
        "missing trip_uid."
    )

    assert (
        h["trip_uid"]
        .is_unique
    ), (
        f"{operator} {year}: "
        "trip_uid is not unique."
    )

    # --------------------------------------------------------
    # Vehicle key
    # --------------------------------------------------------

    assert (
        h["vehicle_uid"]
        .notna()
        .all()
    ), (
        f"{operator} {year}: "
        "missing vehicle_uid."
    )

    # --------------------------------------------------------
    # Operator and year fixed
    # --------------------------------------------------------

    assert (
        h["operator"]
        == operator
    ).all()

    assert (
        h["year"]
        == year
    ).all()

    # --------------------------------------------------------
    # Month attribution required for Exercise 1
    # --------------------------------------------------------

    assert (
        h["valid_monthly_period"]
        .fillna(False)
        .all()
    ), (
        f"{operator} {year}: "
        "invalid source-month attribution."
    )

    # --------------------------------------------------------
    # Where detailed local time exists, local month must
    # agree with source period.
    #
    # This also validates VOI's UTC -> Europe/Rome conversion.
    # --------------------------------------------------------

    timestamp_available = (
        h[
            "start_time_local"
        ].notna()
    )

    timestamp_period = (
        h.loc[
            timestamp_available,
            "start_time_local"
        ]
        .dt.to_period("M")
        .astype(str)
    )

    expected_period = (
        h.loc[
            timestamp_available,
            "source_period"
        ]
        .astype(str)
    )

    assert (
        timestamp_period.values
        ==
        expected_period.values
    ).all(), (
        f"{operator} {year}: "
        "local timestamp/source-period mismatch."
    )

    # --------------------------------------------------------
    # Valid durations must be positive
    # --------------------------------------------------------

    valid_duration_mask = (
        h[
            "valid_duration"
        ]
        .fillna(False)
    )

    assert (
        h.loc[
            valid_duration_mask,
            "duration_min_clean"
        ]
        > 0
    ).all(), (
        f"{operator} {year}: "
        "non-positive clean duration marked valid."
    )

    # --------------------------------------------------------
    # Valid endpoint displacement cannot be negative
    # --------------------------------------------------------

    valid_endpoint_mask = (
        h[
            "valid_endpoint_displacement"
        ]
        .fillna(False)
    )

    assert (
        h.loc[
            valid_endpoint_mask,
            "endpoint_displacement_km"
        ]
        >= 0
    ).all(), (
        f"{operator} {year}: "
        "negative endpoint displacement marked valid."
    )

    # --------------------------------------------------------
    # Valid operator-specific distance cannot be negative
    # --------------------------------------------------------

    valid_distance_mask = (
        h[
            "valid_distance_measurement"
        ]
        .fillna(False)
    )

    assert (
        h.loc[
            valid_distance_mask,
            "distance_value_km"
        ]
        .notna()
        .all()
    ), (
        f"{operator} {year}: "
        "valid distance measurement has missing value."
    )

    assert (
        h.loc[
            valid_distance_mask,
            "distance_value_km"
        ]
        >= 0
    ).all(), (
        f"{operator} {year}: "
        "negative distance marked valid."
    )

    # --------------------------------------------------------
    # Final common column order
    # --------------------------------------------------------

    assert (
        list(h.columns)
        ==
        COMMON_COLUMNS
    ), (
        f"{operator} {year}: "
        "common schema column order mismatch."
    )

    print(
        "Validation checks: PASSED"
    )


# ============================================================
# ARROW SCHEMA VALIDATION
# ============================================================

def validate_arrow_schema(
    path,
    operator,
    year,
):

    schema = (
        pq.read_schema(
            path
        )
        .remove_metadata()
    )

    expected = (
        CANONICAL_ARROW_SCHEMA
        .remove_metadata()
    )

    if not schema.equals(
        expected
    ):

        print(
            "\nObserved schema:"
        )

        print(
            schema
        )

        print(
            "\nExpected schema:"
        )

        print(
            expected
        )

        raise ValueError(
            f"{operator} {year}: "
            "canonical Arrow schema validation failed."
        )

    print(
        "Arrow schema validation: PASSED"
    )


# ============================================================
# OPERATOR-YEAR SUMMARY
# ============================================================

def build_summary(h):

    return {
        "operator":
            h[
                "operator"
            ].iloc[0],

        "year":
            int(
                h[
                    "year"
                ].iloc[0]
            ),

        "rows":
            len(h),

        "unique_trips":
            h[
                "trip_uid"
            ].nunique(),

        "unique_vehicles":
            h[
                "vehicle_uid"
            ].nunique(),

        "min_source_period":
            h[
                "source_period"
            ].min(),

        "max_source_period":
            h[
                "source_period"
            ].max(),

        "months_present":
            h[
                "source_period"
            ].nunique(),

        "observed_start_min":
            h[
                "start_time_local"
            ].min(),

        "observed_start_max":
            h[
                "start_time_local"
            ].max(),

        "temporal_detail_available":
            int(
                h[
                    "valid_temporal_detail"
                ]
                .fillna(False)
                .sum()
            ),

        "valid_duration":
            int(
                h[
                    "valid_duration"
                ]
                .fillna(False)
                .sum()
            ),

        "valid_spatial_prezone":
            int(
                h[
                    "valid_spatial_prezone"
                ]
                .fillna(False)
                .sum()
            ),

        "valid_distance_measurement":
            int(
                h[
                    "valid_distance_measurement"
                ]
                .fillna(False)
                .sum()
            ),

        "valid_endpoint_displacement":
            int(
                h[
                    "valid_endpoint_displacement"
                ]
                .fillna(False)
                .sum()
            ),

        "valid_speed_measurement":
            int(
                h[
                    "valid_speed_measurement"
                ]
                .fillna(False)
                .sum()
            ),

        "endpoint_speed_warning_40":
            int(
                h[
                    "endpoint_speed_warning_40"
                ]
                .fillna(False)
                .sum()
            ),

        "distance_measure_type":
            h[
                "distance_measure_type"
            ].iloc[0],

        "distance_precision":
            h[
                "distance_precision"
            ].iloc[0],
    }


# ============================================================
# DATA DICTIONARY
# ============================================================

DATA_DICTIONARY = {
    "operator":
        "Micromobility operator: bird, lime, or voi.",

    "vehicle_type":
        "Common vehicle category used in the project.",

    "trip_uid":
        "Globally unique analytical trip identifier across all operators.",

    "source_trip_id":
        "Original provider trip identifier where available; VOI provides one, Bird and Lime do not.",

    "vehicle_id":
        "Original provider-level vehicle identifier.",

    "vehicle_uid":
        "Operator-prefixed vehicle identifier suitable for pooled multi-operator analysis.",

    "start_time_local":
        "Trip start time expressed in Europe/Rome local clock when detailed temporal information is available.",

    "end_time_local":
        "Trip end time expressed in Europe/Rome local clock when detailed temporal information is available.",

    "start_time_utc":
        "Exact UTC trip start when recoverable from the source; currently available for VOI.",

    "end_time_utc":
        "Exact UTC trip end when recoverable from the source; currently available for VOI.",

    "duration_min_clean":
        "Best validated trip duration according to the operator-specific cleaning methodology.",

    "duration_source":
        "Source used to define duration_min_clean.",

    "timestamp_source_timezone":
        "Interpretation of the provider timestamp system.",

    "timestamp_precision":
        "Temporal precision of the provider timestamps.",

    "start_lat":
        "Trip origin latitude in WGS84 coordinates.",

    "start_lon":
        "Trip origin longitude in WGS84 coordinates.",

    "end_lat":
        "Trip destination latitude in WGS84 coordinates.",

    "end_lon":
        "Trip destination longitude in WGS84 coordinates.",

    "endpoint_displacement_km":
        "Haversine straight-line distance between trip origin and destination, conceptually standardized across all operators.",

    "valid_endpoint_displacement":
        "Whether the common endpoint displacement is valid for analysis.",

    "distance_value_km":
        "Clean operator-specific distance measurement. Semantic meaning differs between providers.",

    "distance_measure_type":
        "Semantic definition of distance_value_km.",

    "distance_precision":
        "Precision and rounding characteristics of the provider-specific distance.",

    "speed_value_kmh":
        "Clean operator-specific speed measure. It is not necessarily directly comparable across providers.",

    "speed_measure_type":
        "Definition used to calculate speed_value_kmh.",

    "source_period":
        "Reliable source reporting month in YYYY-MM format.",

    "year":
        "Calendar year associated with source_period.",

    "source_file":
        "Original source file for traceability.",

    "source_row":
        "Original source-row identifier preserved for traceability.",

    "valid_trip_record":
        "Whether the record satisfies the operator-specific core trip definition.",

    "valid_monthly_period":
        "Whether reliable month-level attribution is available.",

    "valid_temporal_detail":
        "Whether detailed trip timestamps are available for day/hour-level analysis.",

    "valid_duration":
        "Whether duration_min_clean is analytically valid.",

    "temporal_clock_ambiguous":
        "Whether the original local clock time is affected by DST ambiguity.",

    "valid_spatial_prezone":
        "Spatial validity before official Torino statistical-zone assignment.",

    "valid_distance_measurement":
        "Whether distance_value_km is valid according to operator-specific semantics.",

    "valid_speed_measurement":
        "Whether speed_value_kmh is valid according to operator-specific methodology.",

    "endpoint_speed_kmh":
        "Straight-line endpoint displacement divided by cleaned trip duration; comparable only as a kinematic diagnostic, not route speed.",

    "endpoint_speed_warning_40":
        "Diagnostic flag indicating endpoint displacement divided by duration exceeds 40 km/h.",

    "reservation_status":
        "Standardized provider reservation indicator when available.",

    "reservation_conflict":
        "Whether duplicated source records disagreed on reservation status; primarily relevant for VOI.",

    "battery_start_pct":
        "Battery percentage at trip start when provided.",

    "battery_end_pct":
        "Battery percentage at trip end when provided.",

    "battery_available":
        "Whether both start and end battery measurements are available.",

    "valid_battery":
        "Whether battery measurements satisfy provider-specific quality rules.",
}


def save_data_dictionary():

    dictionary = pd.DataFrame(
        [
            {
                "column": key,
                "definition": value,
            }
            for key, value
            in DATA_DICTIONARY.items()
        ]
    )

    path = (
        AUDIT_DIR
        / "harmonization_data_dictionary.csv"
    )

    dictionary.to_csv(
        path,
        index=False
    )

    return path


# ============================================================
# COMBINE ONE YEAR
#
# IMPORTANT CHANGE:
# Uses an explicit canonical Arrow schema instead of using
# Bird's inferred Parquet schema as the reference.
# ============================================================

def combine_year(
    year,
    harmonized_paths
):

    output = (
        OUTPUT_DIR
        / f"all_operators_{year}_harmonized.parquet"
    )

    if output.exists():

        output.unlink()

        print(
            f"Removed previous partial file -> "
            f"{output}"
        )

    writer = pq.ParquetWriter(
        output,
        CANONICAL_ARROW_SCHEMA,
        compression="snappy",
    )

    total_rows = 0

    operator_counts = {}

    try:

        for path in harmonized_paths:

            table = pq.read_table(
                path
            )

            table = (
                table
                .replace_schema_metadata()
            )

            # Explicitly cast every operator file to the
            # canonical physical Arrow schema.
            table = table.cast(
                CANONICAL_ARROW_SCHEMA,
                safe=True,
            )

            writer.write_table(
                table
            )

            rows = (
                table.num_rows
            )

            total_rows += (
                rows
            )

            operator_name = (
                path.name
                .split("_")[0]
            )

            operator_counts[
                operator_name
            ] = rows

            print(
                f"  Added {path.name}: "
                f"{rows:,} rows"
            )

    finally:

        writer.close()

    # ========================================================
    # COMBINED READ-BACK VALIDATION
    # ========================================================

    combined_schema = (
        pq.read_schema(
            output
        )
        .remove_metadata()
    )

    expected_schema = (
        CANONICAL_ARROW_SCHEMA
        .remove_metadata()
    )

    assert (
        combined_schema.equals(
            expected_schema
        )
    ), (
        f"{year}: combined Arrow schema mismatch."
    )

    check = (
        pq.read_table(
            output,
            columns=[
                "trip_uid",
                "operator",
                "year",
            ],
        )
        .to_pandas()
    )

    assert (
        len(check)
        ==
        total_rows
    ), (
        f"{year}: combined row count mismatch."
    )

    assert (
        check[
            "trip_uid"
        ].is_unique
    ), (
        f"{year}: duplicate trip_uid "
        "after operator combination."
    )

    assert (
        check[
            "year"
        ]
        == year
    ).all(), (
        f"{year}: incorrect year "
        "inside combined dataset."
    )

    observed_operator_counts = (
        check[
            "operator"
        ]
        .value_counts()
        .to_dict()
    )

    for (
        operator,
        expected_count
    ) in operator_counts.items():

        observed_count = int(
            observed_operator_counts.get(
                operator,
                0
            )
        )

        assert (
            observed_count
            ==
            expected_count
        ), (
            f"{year} {operator}: "
            "operator count changed during combine."
        )

    print(
        f"Combined read-back validation "
        f"{year}: PASSED"
    )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    summaries = []

    harmonized_paths_by_year = {
        2024: [],
        2025: [],
    }

    print(
        "\n"
        + "=" * 100
    )

    print(
        "HARMONIZING BIRD + LIME + VOI"
    )

    print(
        "=" * 100
    )

    # ========================================================
    # PROCESS EACH OPERATOR-YEAR DATASET
    # ========================================================

    for (
        operator,
        year
    ), path in FILES.items():

        print(
            "\n"
            + "-" * 100
        )

        print(
            f"Processing "
            f"{operator.upper()} {year}"
        )

        print(
            "-" * 100
        )

        if not path.exists():

            raise FileNotFoundError(
                f"Missing cleaned input file:\n"
                f"{path}"
            )

        source = pd.read_parquet(
            path
        )

        print(
            f"Source rows: "
            f"{len(source):,}"
        )

        # ----------------------------------------------------
        # Operator-specific harmonization
        # ----------------------------------------------------

        if operator == "bird":

            h = harmonize_bird(
                source,
                year,
                path,
            )

        elif operator == "lime":

            h = harmonize_lime(
                source,
                year,
                path,
            )

        elif operator == "voi":

            h = harmonize_voi(
                source,
                year,
                path,
            )

        else:

            raise ValueError(
                f"Unsupported operator: "
                f"{operator}"
            )

        # ----------------------------------------------------
        # Common cross-operator metrics
        # ----------------------------------------------------

        h = add_common_fields(
            h
        )

        # ----------------------------------------------------
        # Standardized pandas dtypes
        # ----------------------------------------------------

        h = standardize_dtypes(
            h
        )

        # ----------------------------------------------------
        # Analytical validation
        # ----------------------------------------------------

        validate_harmonized(
            source,
            h,
            operator,
            year,
        )

        # ----------------------------------------------------
        # Output path
        # ----------------------------------------------------

        output_path = (
            OUTPUT_DIR
            / (
                f"{operator}_"
                f"{year}_harmonized.parquet"
            )
        )

        if output_path.exists():

            output_path.unlink()

            print(
                f"Removed previous file -> "
                f"{output_path}"
            )

        # ----------------------------------------------------
        # Explicit canonical Arrow serialization
        # ----------------------------------------------------

        table = (
            to_canonical_arrow_table(
                h
            )
        )

        pq.write_table(
            table,
            output_path,
            compression="snappy",
        )

        # ----------------------------------------------------
        # Arrow schema validation
        # ----------------------------------------------------

        validate_arrow_schema(
            output_path,
            operator,
            year,
        )

        # ----------------------------------------------------
        # Read-back validation
        # ----------------------------------------------------

        check = pd.read_parquet(
            output_path
        )

        assert (
            len(check)
            ==
            len(h)
        )

        assert (
            check[
                "trip_uid"
            ].is_unique
        )

        assert (
            check[
                "operator"
            ]
            == operator
        ).all()

        assert (
            check[
                "year"
            ]
            == year
        ).all()

        print(
            f"Saved -> "
            f"{output_path}"
        )

        print(
            "Read-back validation: PASSED"
        )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summaries.append(
            build_summary(
                h
            )
        )

        harmonized_paths_by_year[
            year
        ].append(
            output_path
        )

    # ========================================================
    # COMBINE OPERATORS BY YEAR
    # ========================================================

    combined_paths = {}

    for year in [
        2024,
        2025,
    ]:

        print(
            "\n"
            + "-" * 100
        )

        print(
            f"Combining operators "
            f"for {year}..."
        )

        print(
            "-" * 100
        )

        output = combine_year(
            year,
            harmonized_paths_by_year[
                year
            ],
        )

        combined_paths[
            year
        ] = (
            output
        )

        total_rows = (
            pq.ParquetFile(
                output
            )
            .metadata
            .num_rows
        )

        print(
            f"Combined {year}: "
            f"{total_rows:,} trips"
        )

        print(
            f"Saved -> "
            f"{output}"
        )

    # ========================================================
    # OPERATOR-YEAR SUMMARY
    # ========================================================

    summary = pd.DataFrame(
        summaries
    )

    summary = (
        summary
        .sort_values(
            [
                "year",
                "operator",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    summary_path = (
        AUDIT_DIR
        / "harmonization_summary.csv"
    )

    summary.to_csv(
        summary_path,
        index=False
    )

    # ========================================================
    # TEMPORAL COVERAGE TABLE
    # ========================================================

    coverage = summary[
        [
            "operator",
            "year",
            "rows",
            "unique_vehicles",
            "min_source_period",
            "max_source_period",
            "months_present",
            "observed_start_min",
            "observed_start_max",
            "temporal_detail_available",
        ]
    ].copy()

    coverage_path = (
        AUDIT_DIR
        / "harmonization_coverage.csv"
    )

    coverage.to_csv(
        coverage_path,
        index=False
    )

    # ========================================================
    # DATA DICTIONARY
    # ========================================================

    dictionary_path = (
        save_data_dictionary()
    )

    # ========================================================
    # GLOBAL CROSS-YEAR VALIDATION
    # ========================================================

    expected_2024 = (
        summary.loc[
            summary["year"] == 2024,
            "rows"
        ]
        .sum()
    )

    expected_2025 = (
        summary.loc[
            summary["year"] == 2025,
            "rows"
        ]
        .sum()
    )

    observed_2024 = (
        pq.ParquetFile(
            combined_paths[2024]
        )
        .metadata
        .num_rows
    )

    observed_2025 = (
        pq.ParquetFile(
            combined_paths[2025]
        )
        .metadata
        .num_rows
    )

    assert (
        expected_2024
        ==
        observed_2024
    )

    assert (
        expected_2025
        ==
        observed_2025
    )

    # ========================================================
    # FINAL OUTPUT
    # ========================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "HARMONIZATION COMPLETED"
    )

    print(
        "=" * 110
    )

    print(
        "\nOperator-year summary:"
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print(
        "\nCombined dataset row counts:"
    )

    total_all_years = 0

    for (
        year,
        path
    ) in combined_paths.items():

        count = (
            pq.ParquetFile(
                path
            )
            .metadata
            .num_rows
        )

        total_all_years += (
            count
        )

        print(
            f"{year}: "
            f"{count:,}"
        )

    print(
        f"\nTotal harmonized observations: "
        f"{total_all_years:,}"
    )

    print(
        f"\nSummary -> "
        f"{summary_path}"
    )

    print(
        f"Coverage -> "
        f"{coverage_path}"
    )

    print(
        f"Data dictionary -> "
        f"{dictionary_path}"
    )

    print(
        "\nIMPORTANT:"
        "\n- Harmonization did not delete any cleaned trips."
        "\n- Original cleaned operator datasets remain the source of truth."
        "\n- All harmonized Parquet files use one explicit canonical Arrow schema."
        "\n- trip_uid is globally unique across operators."
        "\n- vehicle_uid must be used for pooled vehicle analysis."
        "\n- distance_value_km is NOT semantically identical across operators."
        "\n- endpoint_displacement_km is the common geometric distance metric."
        "\n- endpoint_speed_kmh is a common kinematic diagnostic, not travelled route speed."
        "\n- 2025 operator coverage periods differ and must not be interpreted as comparable full-year totals."
    )


if __name__ == "__main__":
    main()