from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pyarrow.parquet as pq


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GTFS_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "external"
    / "gtt_gtfs"
)

PT_REFERENCE_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "pt_reference"
    / "gtt_reference_network.gpkg"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "proximity"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "proximity"
)

BY_OPERATOR_DIR = (
    OUTPUT_DIR
    / "by_operator"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BY_OPERATOR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PARQUET = (
    OUTPUT_DIR
    / "pt_proximity_february_july_2024.parquet"
)

OUTPUT_GPKG = (
    OUTPUT_DIR
    / "exercise3_proximity_layers.gpkg"
)

TARGET_CRS = "EPSG:3003"

TARGET_AGENCY = "U"

ROUTE_TYPE_MAP = {
    0: "tram",
    1: "metro",
    3: "bus",
}

TARGET_ROUTE_TYPES = set(
    ROUTE_TYPE_MAP.keys()
)

EXPECTED_CANONICAL_STOP_COUNT = 2197

THRESHOLDS_M = [
    250,
    400,
    600,
]

BASELINE_THRESHOLD_M = 400

TARGET_MONTHS = {
    2: "winter_february",
    7: "summer_july",
}

OPERATORS = [
    "bird",
    "lime",
    "voi",
]


# -------------------------------------------------------------------------
# Optional manual input paths.
#
# Leave as None to auto-discover the harmonized 2024 operator parquet.
# If auto-discovery ever selects the wrong file, specify it here.
# -------------------------------------------------------------------------

INPUT_FILES = {
     "bird": (
        "data/processed/harmonized/"
        "bird_2024_harmonized.parquet"
    ),
    "lime": (
        "data/processed/harmonized/"
        "lime_2024_harmonized.parquet"
    ),
    "voi": (
        "data/processed/harmonized/"
        "voi_2024_harmonized.parquet"
    ),
}


# =============================================================================
# COLUMN ALIASES
# =============================================================================

ALIASES = {

    "trip_uid": [
        "trip_uid",
        "trip_id",
        "rental_id",
        "id_noleggio",
    ],

    "start_time": [
         "start_time_local",
         "start_time",
         "start_datetime",
         "start_timestamp",
         "start_date_time",
    ],

    "start_lat": [
        "start_lat",
        "start_latitude",
        "origin_lat",
    ],

    "start_lon": [
        "start_lon",
        "start_longitude",
        "origin_lon",
    ],

    "end_lat": [
        "end_lat",
        "end_latitude",
        "destination_lat",
    ],

    "end_lon": [
        "end_lon",
        "end_longitude",
        "destination_lon",
    ],
}


# =============================================================================
# HELPERS
# =============================================================================

def clean_string(series: pd.Series) -> pd.Series:

    return (
        series
        .astype("string")
        .str.strip()
    )


def unique_pipe(series: pd.Series) -> str:

    values = (
        clean_string(series)
        .dropna()
        .loc[lambda x: x != ""]
        .unique()
        .tolist()
    )

    return "|".join(
        sorted(values)
    )


def resolve_column(
    available_columns,
    aliases,
    required=True,
):

    lower_map = {
        str(col).casefold(): str(col)
        for col in available_columns
    }

    for alias in aliases:

        key = alias.casefold()

        if key in lower_map:

            return lower_map[key]

    if required:

        raise KeyError(
            "Could not resolve required column.\n"
            f"Aliases tried: {aliases}\n"
            f"Available columns: {available_columns}"
        )

    return None


def get_parquet_columns(path: Path):

    schema = pq.read_schema(
        path
    )

    return schema.names


# =============================================================================
# DISCOVER CANONICAL / HARMONIZED INPUT PARQUETS
# =============================================================================

def score_candidate(
    path: Path,
    operator: str,
):

    text = str(path).casefold()

    score = 0

    if operator in text:
        score += 50

    if "2024" in text:
        score += 30

    if "harmon" in text:
        score += 120

    if "canonical" in text:
        score += 80

    if "processed" in text:
        score += 30

    if "cleaned" in text:
        score += 10

    if "interim" in text:
        score -= 80

    if "audit" in text:
        score -= 100

    if "exercise_2" in text:
        score -= 100

    if "exercise_3" in text:
        score -= 100

    if "2025" in text:
        score -= 150

    return score


def parquet_has_required_columns(
    path: Path,
):

    try:

        columns = get_parquet_columns(
            path
        )

        resolve_column(
            columns,
            ALIASES["start_time"],
        )

        resolve_column(
            columns,
            ALIASES["start_lat"],
        )

        resolve_column(
            columns,
            ALIASES["start_lon"],
        )

        resolve_column(
            columns,
            ALIASES["end_lat"],
        )

        resolve_column(
            columns,
            ALIASES["end_lon"],
        )

        return True

    except Exception:

        return False


def discover_operator_parquet(
    operator: str,
):

    manual = INPUT_FILES.get(
        operator
    )

    if manual is not None:

        path = Path(manual)

        if not path.is_absolute():

            path = (
                PROJECT_ROOT
                / path
            )

        if not path.exists():

            raise FileNotFoundError(
                f"Manual input path does not exist:\n{path}"
            )

        return path

    candidates = []

    data_root = (
        PROJECT_ROOT
        / "data"
    )

    for path in data_root.rglob(
        "*.parquet"
    ):

        text = str(path).casefold()

        if operator not in text:
            continue

        if "2024" not in text:
            continue

        if not parquet_has_required_columns(
            path
        ):
            continue

        candidates.append(
            (
                score_candidate(
                    path,
                    operator,
                ),
                path,
            )
        )

    if not candidates:

        raise FileNotFoundError(
            f"\nCould not automatically locate a "
            f"2024 parquet for {operator.upper()}.\n"
            "Set its path manually in INPUT_FILES."
        )

    candidates.sort(
        key=lambda x: (
            x[0],
            str(x[1]),
        ),
        reverse=True,
    )

    best_score = candidates[0][0]

    best = [
        path
        for score, path
        in candidates
        if score == best_score
    ]

    if len(best) > 1:

        print(
            f"\nWARNING: multiple equally scored "
            f"{operator.upper()} candidates:"
        )

        for path in best:

            print(
                f"  {path}"
            )

        print(
            f"Using: {best[0]}"
        )

    return best[0]


# =============================================================================
# BUILD CANONICAL URBAN PT STOPS
# =============================================================================

def build_canonical_pt_stops():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "BUILDING CANONICAL URBAN PT STOP POPULATION"
    )

    print(
        "=" * 110
    )

    routes = pd.read_csv(
        GTFS_DIR
        / "routes.txt",
        dtype="string",
        low_memory=False,
    )

    trips = pd.read_csv(
        GTFS_DIR
        / "trips.txt",
        dtype="string",
        usecols=[
            "trip_id",
            "route_id",
        ],
        low_memory=False,
    )

    stop_times = pd.read_csv(
        GTFS_DIR
        / "stop_times.txt",
        dtype="string",
        usecols=[
            "trip_id",
            "stop_id",
        ],
        low_memory=False,
    )

    routes["route_id"] = clean_string(
        routes["route_id"]
    )

    routes["agency_id"] = clean_string(
        routes["agency_id"]
    )

    trips["trip_id"] = clean_string(
        trips["trip_id"]
    )

    trips["route_id"] = clean_string(
        trips["route_id"]
    )

    stop_times["trip_id"] = clean_string(
        stop_times["trip_id"]
    )

    stop_times["stop_id"] = clean_string(
        stop_times["stop_id"]
    )

    routes[
        "route_type_num"
    ] = pd.to_numeric(
        routes["route_type"],
        errors="coerce",
    )

    routes[
        "route_mode"
    ] = (
        routes[
            "route_type_num"
        ]
        .map(
            ROUTE_TYPE_MAP
        )
    )

    selected_routes = (
        routes.loc[
            (
                routes[
                    "agency_id"
                ]
                == TARGET_AGENCY
            )
            &
            (
                routes[
                    "route_type_num"
                ]
                .isin(
                    TARGET_ROUTE_TYPES
                )
            )
        ]
        .copy()
    )

    trip_route = (
        trips.loc[
            trips[
                "route_id"
            ].isin(
                selected_routes[
                    "route_id"
                ]
            )
        ]
        .merge(
            selected_routes[
                [
                    "route_id",
                    "route_short_name",
                    "route_type_num",
                    "route_mode",
                ]
            ],
            on="route_id",
            how="left",
            validate="many_to_one",
        )
    )

    selected_stop_times = (
        stop_times.loc[
            stop_times[
                "trip_id"
            ].isin(
                trip_route[
                    "trip_id"
                ]
            )
        ]
        .merge(
            trip_route,
            on="trip_id",
            how="left",
            validate="many_to_one",
        )
    )

    used_stop_ids = set(
        selected_stop_times[
            "stop_id"
        ].dropna()
    )

    official_stops = gpd.read_file(
        PT_REFERENCE_GPKG,
        layer="pt_stops_torino_official",
    ).to_crs(
        TARGET_CRS
    )

    official_stops[
        "stop_id"
    ] = clean_string(
        official_stops[
            "stop_id"
        ]
    )

    stop_service = (
        selected_stop_times
        .groupby(
            "stop_id",
            dropna=False,
        )
        .agg(
            urban_route_count=(
                "route_id",
                "nunique",
            ),
            served_route_ids=(
                "route_id",
                unique_pipe,
            ),
            served_route_names=(
                "route_short_name",
                unique_pipe,
            ),
            served_modes=(
                "route_mode",
                unique_pipe,
            ),
        )
        .reset_index()
    )

    canonical = (
        official_stops.loc[
            official_stops[
                "stop_id"
            ].isin(
                used_stop_ids
            )
        ]
        .merge(
            stop_service,
            on="stop_id",
            how="left",
            validate="one_to_one",
        )
    )

    canonical = gpd.GeoDataFrame(
        canonical,
        geometry="geometry",
        crs=TARGET_CRS,
    )

    print(
        f"Selected urban routes: "
        f"{selected_routes['route_id'].nunique():,}"
    )

    print(
        f"Selected urban trips: "
        f"{trip_route['trip_id'].nunique():,}"
    )

    print(
        f"Stops used by selected urban network: "
        f"{len(used_stop_ids):,}"
    )

    print(
        f"Stops inside official Torino before "
        f"network-use filter: "
        f"{len(official_stops):,}"
    )

    print(
        f"Canonical urban PT stops: "
        f"{len(canonical):,}"
    )

    if len(canonical) != EXPECTED_CANONICAL_STOP_COUNT:

        raise RuntimeError(
            "\nCanonical stop count differs from "
            "the independently audited result.\n"
            f"Expected: {EXPECTED_CANONICAL_STOP_COUNT:,}\n"
            f"Observed: {len(canonical):,}"
        )

    stop_ids = set(
        canonical[
            "stop_id"
        ]
    )

    checks = {
        "1361": True,
        "116589": False,
        "116590": False,
    }

    for stop_id, expected in checks.items():

        observed = (
            stop_id
            in stop_ids
        )

        if observed != expected:

            raise RuntimeError(
                f"Canonical-stop audit failed "
                f"for stop_id={stop_id}: "
                f"expected retained={expected}, "
                f"observed={observed}"
            )

    print(
        "Canonical-stop audit: PASSED"
    )

    return canonical


# =============================================================================
# LOAD OFFICIAL TORINO BOUNDARY
# =============================================================================

def load_torino_boundary():

    boundary = gpd.read_file(
        PT_REFERENCE_GPKG,
        layer="torino_boundary",
    ).to_crs(
        TARGET_CRS
    )

    if len(boundary) != 1:

        boundary = (
            boundary
            .dissolve()
            .reset_index(
                drop=True
            )
        )

    return boundary


# =============================================================================
# PARQUET LOADING
# =============================================================================

def load_operator_2024(
    operator: str,
    path: Path,
):

    columns = get_parquet_columns(
        path
    )

    resolved = {}

    for canonical in [
        "start_time",
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
    ]:

        resolved[
            canonical
        ] = resolve_column(
            columns,
            ALIASES[
                canonical
            ],
        )

    resolved[
        "trip_uid"
    ] = resolve_column(
        columns,
        ALIASES[
            "trip_uid"
        ],
        required=False,
    )

    read_columns = list(
        dict.fromkeys(
            col
            for col
            in resolved.values()
            if col is not None
        )
    )

    df = pd.read_parquet(
        path,
        columns=read_columns,
    )

    rename_map = {
        actual: canonical
        for canonical, actual
        in resolved.items()
        if actual is not None
    }

    df = df.rename(
        columns=rename_map
    )

    df[
        "operator"
    ] = operator

    if "trip_uid" not in df.columns:

        df[
            "trip_uid"
        ] = (
            operator
            + "_row_"
            + df.index
            .astype(str)
        )

    df[
        "trip_uid"
    ] = clean_string(
        df[
            "trip_uid"
        ]
    )

    if df[
        "trip_uid"
    ].duplicated().any():

        duplicate_count = int(
            df[
                "trip_uid"
            ]
            .duplicated(
                keep=False
            )
            .sum()
        )

        raise RuntimeError(
            f"{operator.upper()}: trip_uid is not unique. "
            f"Rows involved in duplicates: "
            f"{duplicate_count:,}"
        )

    df[
        "start_time"
    ] = pd.to_datetime(
        df[
            "start_time"
        ],
        errors="coerce",
    )

    for col in [
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    return df


# =============================================================================
# SPATIAL SCOPE
# =============================================================================

def valid_coordinate_mask(
    df: pd.DataFrame,
):

    return (
        df[
            "start_lat"
        ].between(
            -90,
            90,
            inclusive="both",
        )
        &
        df[
            "start_lon"
        ].between(
            -180,
            180,
            inclusive="both",
        )
        &
        df[
            "end_lat"
        ].between(
            -90,
            90,
            inclusive="both",
        )
        &
        df[
            "end_lon"
        ].between(
            -180,
            180,
            inclusive="both",
        )
    )


def create_endpoint_points(
    df: pd.DataFrame,
    endpoint: str,
):

    if endpoint == "origin":

        lon_col = "start_lon"
        lat_col = "start_lat"

    elif endpoint == "destination":

        lon_col = "end_lon"
        lat_col = "end_lat"

    else:

        raise ValueError(
            "endpoint must be "
            "'origin' or 'destination'"
        )

    gdf = gpd.GeoDataFrame(
        df[
            [
                "analysis_trip_id",
            ]
        ].copy(),
        geometry=gpd.points_from_xy(
            df[
                lon_col
            ],
            df[
                lat_col
            ],
        ),
        crs="EPSG:4326",
    )

    return gdf.to_crs(
        TARGET_CRS
    )


def mark_points_inside_torino(
    points: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
):

    valid_predicates = (
        points
        .sindex
        .valid_query_predicates
    )

    if "covered_by" in valid_predicates:

        predicate = "covered_by"

    else:

        predicate = "within"

    joined = gpd.sjoin(
        points,
        boundary[
            [
                "geometry",
            ]
        ],
        how="left",
        predicate=predicate,
    )

    inside_ids = set(
        joined.loc[
            joined[
                "index_right"
            ].notna(),
            "analysis_trip_id",
        ]
    )

    return points[
        "analysis_trip_id"
    ].isin(
        inside_ids
    )


# =============================================================================
# NEAREST PT STOP
# =============================================================================

def nearest_stop(
    points: gpd.GeoDataFrame,
    canonical_stops: gpd.GeoDataFrame,
    endpoint: str,
):

    stop_cols = [
        "stop_id",
        "stop_name",
        "served_modes",
        "urban_route_count",
        "geometry",
    ]

    joined = gpd.sjoin_nearest(
        points,
        canonical_stops[
            stop_cols
        ],
        how="left",
        distance_col=(
            f"{endpoint}_nearest_stop_distance_m"
        ),
    )

    joined[
        "stop_id"
    ] = clean_string(
        joined[
            "stop_id"
        ]
    )

    # sjoin_nearest can return multiple rows when
    # two stops are exactly equidistant.
    # Resolve ties deterministically.
    joined = (
        joined
        .sort_values(
            [
                "analysis_trip_id",
                f"{endpoint}_nearest_stop_distance_m",
                "stop_id",
            ],
            kind="mergesort",
        )
        .drop_duplicates(
            subset=[
                "analysis_trip_id",
            ],
            keep="first",
        )
    )

    result = (
        joined[
            [
                "analysis_trip_id",
                "stop_id",
                "stop_name",
                "served_modes",
                "urban_route_count",
                f"{endpoint}_nearest_stop_distance_m",
            ]
        ]
        .rename(
            columns={
                "stop_id":
                    f"{endpoint}_nearest_stop_id",

                "stop_name":
                    f"{endpoint}_nearest_stop_name",

                "served_modes":
                    f"{endpoint}_nearest_stop_modes",

                "urban_route_count":
                    f"{endpoint}_nearest_stop_route_count",
            }
        )
    )

    return result


# =============================================================================
# PROCESS ONE OPERATOR × MONTH
# =============================================================================

def process_operator_month(
    operator: str,
    annual_df: pd.DataFrame,
    month: int,
    season_label: str,
    boundary: gpd.GeoDataFrame,
    canonical_stops: gpd.GeoDataFrame,
):

    valid_timestamp = (
        annual_df[
            "start_time"
        ].notna()
    )

    month_mask = (
        valid_timestamp
        &
        (
            annual_df[
                "start_time"
            ].dt.year
            == 2024
        )
        &
        (
            annual_df[
                "start_time"
            ].dt.month
            == month
        )
    )

    month_df = (
        annual_df.loc[
            month_mask
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    if month_df.empty:

        raise RuntimeError(
            f"No {operator.upper()} trips found "
            f"for 2024-{month:02d}."
        )

    month_df[
        "season"
    ] = season_label

    month_df[
        "month"
    ] = month

    month_df[
        "analysis_trip_id"
    ] = (
        operator
        + "::"
        + month_df[
            "trip_uid"
        ].astype(str)
    )

    input_rows = len(
        month_df
    )

    complete_coords = (
        valid_coordinate_mask(
            month_df
        )
    )

    coordinate_valid_rows = int(
        complete_coords.sum()
    )

    spatial_df = (
        month_df.loc[
            complete_coords
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    origins = create_endpoint_points(
        spatial_df,
        "origin",
    )

    destinations = create_endpoint_points(
        spatial_df,
        "destination",
    )

    origin_inside = (
        mark_points_inside_torino(
            origins,
            boundary,
        )
    )

    destination_inside = (
        mark_points_inside_torino(
            destinations,
            boundary,
        )
    )

    both_inside = (
        origin_inside.to_numpy()
        &
        destination_inside.to_numpy()
    )

    scope_df = (
        spatial_df.loc[
            both_inside
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    origins_scope = (
        origins.loc[
            both_inside
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    destinations_scope = (
        destinations.loc[
            both_inside
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    if scope_df.empty:

        raise RuntimeError(
            f"{operator.upper()} "
            f"2024-{month:02d}: "
            "no trips remain inside "
            "official Torino."
        )

    origin_nearest = nearest_stop(
        origins_scope,
        canonical_stops,
        "origin",
    )

    destination_nearest = nearest_stop(
        destinations_scope,
        canonical_stops,
        "destination",
    )

    result = (
        scope_df
        .merge(
            origin_nearest,
            on="analysis_trip_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            destination_nearest,
            on="analysis_trip_id",
            how="left",
            validate="one_to_one",
        )
    )

    if (
        result[
            "origin_nearest_stop_distance_m"
        ].isna().any()
        or
        result[
            "destination_nearest_stop_distance_m"
        ].isna().any()
    ):

        raise RuntimeError(
            f"{operator.upper()} "
            f"2024-{month:02d}: "
            "missing nearest-stop result."
        )

    for threshold in THRESHOLDS_M:

        origin_near_col = (
            f"origin_within_{threshold}m"
        )

        destination_near_col = (
            f"destination_within_{threshold}m"
        )

        class_col = (
            f"interaction_class_{threshold}m"
        )

        result[
            origin_near_col
        ] = (
            result[
                "origin_nearest_stop_distance_m"
            ]
            <= threshold
        )

        result[
            destination_near_col
        ] = (
            result[
                "destination_nearest_stop_distance_m"
            ]
            <= threshold
        )

        o = result[
            origin_near_col
        ]

        d = result[
            destination_near_col
        ]

        result[
            class_col
        ] = np.select(
            [
                o & d,
                (~o) & d,
                o & (~d),
                (~o) & (~d),
            ],
            [
                "PT-overlap candidate",
                "Potential access / first-mile",
                "Potential egress / last-mile",
                "Potential independent / spatial-gap",
            ],
            default="Unclassified",
        )

    retained_rows = len(
        result
    )

    scope_summary = {
        "operator": operator,
        "season": season_label,
        "year": 2024,
        "month": month,
        "calendar_dates_with_trips":
            result[
                "start_time"
            ]
            .dt.normalize()
            .nunique(),
        "month_trips_input":
            input_rows,
        "valid_coordinate_trips":
            coordinate_valid_rows,
        "both_endpoints_inside_torino":
            retained_rows,
        "excluded_invalid_coordinates":
            input_rows
            - coordinate_valid_rows,
        "excluded_outside_torino_scope":
            coordinate_valid_rows
            - retained_rows,
        "retained_scope_pct":
            (
                100
                * retained_rows
                / input_rows
            ),
    }

    print(
        f"\n{operator.upper()} "
        f"2024-{month:02d} "
        f"({season_label})"
    )

    print(
        f"Input trips: "
        f"{input_rows:,}"
    )

    print(
        f"Valid coordinates: "
        f"{coordinate_valid_rows:,}"
    )

    print(
        f"Both endpoints inside Torino: "
        f"{retained_rows:,} "
        f"({scope_summary['retained_scope_pct']:.2f}%)"
    )

    return (
        result,
        scope_summary,
    )


# =============================================================================
# SUMMARIES
# =============================================================================

def add_system_scope(
    df: pd.DataFrame,
):

    system = df.copy()

    system[
        "operator"
    ] = "system"

    return pd.concat(
        [
            df,
            system,
        ],
        ignore_index=True,
    )


def build_distance_summary(
    analysis_df: pd.DataFrame,
):

    working = add_system_scope(
        analysis_df
    )

    rows = []

    for (
        operator,
        season,
        month,
    ), group in working.groupby(
        [
            "operator",
            "season",
            "month",
        ],
        sort=False,
    ):

        for endpoint in [
            "origin",
            "destination",
        ]:

            col = (
                f"{endpoint}_nearest_stop_distance_m"
            )

            values = (
                group[col]
                .dropna()
                .astype(float)
            )

            rows.append(
                {
                    "operator":
                        operator,

                    "season":
                        season,

                    "month":
                        month,

                    "endpoint":
                        endpoint,

                    "trips":
                        len(values),

                    "mean_distance_m":
                        values.mean(),

                    "median_distance_m":
                        values.median(),

                    "p25_distance_m":
                        values.quantile(
                            0.25
                        ),

                    "p75_distance_m":
                        values.quantile(
                            0.75
                        ),

                    "p90_distance_m":
                        values.quantile(
                            0.90
                        ),

                    "p95_distance_m":
                        values.quantile(
                            0.95
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


def build_classification_summary(
    analysis_df: pd.DataFrame,
):

    working = add_system_scope(
        analysis_df
    )

    rows = []

    for (
        operator,
        season,
        month,
    ), group in working.groupby(
        [
            "operator",
            "season",
            "month",
        ],
        sort=False,
    ):

        total = len(
            group
        )

        for threshold in THRESHOLDS_M:

            class_col = (
                f"interaction_class_{threshold}m"
            )

            origin_col = (
                f"origin_within_{threshold}m"
            )

            destination_col = (
                f"destination_within_{threshold}m"
            )

            origin_near_pct = (
                100
                * group[
                    origin_col
                ].mean()
            )

            destination_near_pct = (
                100
                * group[
                    destination_col
                ].mean()
            )

            counts = (
                group[
                    class_col
                ]
                .value_counts()
            )

            for interaction_class, count in counts.items():

                rows.append(
                    {
                        "operator":
                            operator,

                        "season":
                            season,

                        "month":
                            month,

                        "threshold_m":
                            threshold,

                        "interaction_class":
                            interaction_class,

                        "trips":
                            int(
                                count
                            ),

                        "share_pct":
                            (
                                100
                                * count
                                / total
                            ),

                        "origin_within_threshold_pct":
                            origin_near_pct,

                        "destination_within_threshold_pct":
                            destination_near_pct,

                        "total_scope_trips":
                            total,
                    }
                )

    return pd.DataFrame(
        rows
    )


def build_baseline_seasonal_comparison(
    classification_summary,
):

    baseline = (
        classification_summary.loc[
            classification_summary[
                "threshold_m"
            ]
            == BASELINE_THRESHOLD_M
        ]
        .copy()
    )

    pivot = (
        baseline.pivot_table(
            index=[
                "operator",
                "interaction_class",
            ],
            columns="season",
            values="share_pct",
            aggfunc="first",
        )
        .reset_index()
    )

    winter_col = (
        "winter_february"
    )

    summer_col = (
        "summer_july"
    )

    if (
        winter_col in pivot.columns
        and summer_col in pivot.columns
    ):

        pivot[
            "summer_minus_winter_pp"
        ] = (
            pivot[
                summer_col
            ]
            -
            pivot[
                winter_col
            ]
        )

    return pivot


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 110
    )

    print(
        "EXERCISE 3 — SCOOTER × PUBLIC TRANSPORT PROXIMITY"
    )

    print(
        "=" * 110
    )

    # =========================================================================
    # CANONICAL PT STOPS
    # =========================================================================

    canonical_stops = (
        build_canonical_pt_stops()
    )

    boundary = (
        load_torino_boundary()
    )

    # =========================================================================
    # SAVE CANONICAL GIS LAYER
    # =========================================================================

    if OUTPUT_GPKG.exists():

        OUTPUT_GPKG.unlink()

    boundary.to_file(
        OUTPUT_GPKG,
        layer="torino_boundary",
        driver="GPKG",
    )

    canonical_stops.to_file(
        OUTPUT_GPKG,
        layer="pt_stops_canonical",
        driver="GPKG",
    )

    print(
        f"\nSaved canonical PT stops -> "
        f"{OUTPUT_GPKG}"
    )

    # =========================================================================
    # DISCOVER INPUT DATA
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "DISCOVERING 2024 SCOOTER PARQUETS"
    )

    print(
        "=" * 110
    )

    input_paths = {}

    for operator in OPERATORS:

        path = discover_operator_parquet(
            operator
        )

        input_paths[
            operator
        ] = path

        print(
            f"{operator.upper():5s} -> "
            f"{path}"
        )

    # =========================================================================
    # PROCESS MONTHS
    # =========================================================================

    results = []

    scope_rows = []

    for operator in OPERATORS:

        print(
            "\n"
            + "-" * 110
        )

        print(
            f"LOADING {operator.upper()} 2024"
        )

        print(
            "-" * 110
        )

        annual_df = (
            load_operator_2024(
                operator,
                input_paths[
                    operator
                ],
            )
        )

        print(
            f"Rows loaded: "
            f"{len(annual_df):,}"
        )

        print(
            f"Start-time coverage: "
            f"{annual_df['start_time'].min()} "
            f"→ "
            f"{annual_df['start_time'].max()}"
        )

        for (
            month,
            season_label,
        ) in TARGET_MONTHS.items():

            result, scope_summary = (
                process_operator_month(
                    operator=operator,
                    annual_df=annual_df,
                    month=month,
                    season_label=season_label,
                    boundary=boundary,
                    canonical_stops=canonical_stops,
                )
            )

            results.append(
                result
            )

            scope_rows.append(
                scope_summary
            )

    analysis_df = pd.concat(
        results,
        ignore_index=True,
    )

    scope_summary_df = pd.DataFrame(
        scope_rows
    )

    # =========================================================================
    # FINAL VALIDATION
    # =========================================================================

    if analysis_df[
        "analysis_trip_id"
    ].duplicated().any():

        raise RuntimeError(
            "analysis_trip_id is not unique "
            "in final Exercise 3 dataset."
        )

    expected_combinations = (
        len(OPERATORS)
        *
        len(TARGET_MONTHS)
    )

    observed_combinations = (
        analysis_df[
            [
                "operator",
                "month",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    if (
        observed_combinations
        != expected_combinations
    ):

        raise RuntimeError(
            "Missing operator-month combination "
            "in final proximity dataset."
        )

    print(
        "\nFinal trip-ID validation: PASSED"
    )

    # =========================================================================
    # SUMMARIES
    # =========================================================================

    distance_summary = (
        build_distance_summary(
            analysis_df
        )
    )

    classification_summary = (
        build_classification_summary(
            analysis_df
        )
    )

    seasonal_comparison = (
        build_baseline_seasonal_comparison(
            classification_summary
        )
    )

    # =========================================================================
    # SAVE PER-TRIP OUTPUT
    # =========================================================================

    analysis_df.to_parquet(
        OUTPUT_PARQUET,
        index=False,
    )

    for (
        operator,
        season,
        month,
    ), group in analysis_df.groupby(
        [
            "operator",
            "season",
            "month",
        ],
        sort=False,
    ):

        out_path = (
            BY_OPERATOR_DIR
            / (
                f"{operator}_2024_"
                f"{month:02d}_"
                f"pt_proximity.parquet"
            )
        )

        group.to_parquet(
            out_path,
            index=False,
        )

    # =========================================================================
    # SAVE AUDITS
    # =========================================================================

    scope_summary_df.to_csv(
        AUDIT_DIR
        / "spatial_scope_summary.csv",
        index=False,
    )

    distance_summary.to_csv(
        AUDIT_DIR
        / "nearest_pt_stop_distance_summary.csv",
        index=False,
    )

    classification_summary.to_csv(
        AUDIT_DIR
        / "pt_interaction_sensitivity_summary.csv",
        index=False,
    )

    seasonal_comparison.to_csv(
        AUDIT_DIR
        / "baseline_400m_seasonal_comparison.csv",
        index=False,
    )

    canonical_stops.drop(
        columns="geometry",
        errors="ignore",
    ).to_csv(
        AUDIT_DIR
        / "canonical_pt_stops.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL OUTPUT
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "SPATIAL SCOPE SUMMARY"
    )

    print(
        "=" * 110
    )

    print(
        scope_summary_df.to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "NEAREST PT STOP DISTANCE — MEDIANS"
    )

    print(
        "=" * 110
    )

    median_table = (
        distance_summary[
            [
                "operator",
                "season",
                "endpoint",
                "trips",
                "median_distance_m",
                "p90_distance_m",
            ]
        ]
        .copy()
    )

    print(
        median_table.to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        f"BASELINE INTERACTION CLASSIFICATION "
        f"— {BASELINE_THRESHOLD_M} m"
    )

    print(
        "=" * 110
    )

    baseline = (
        classification_summary.loc[
            classification_summary[
                "threshold_m"
            ]
            == BASELINE_THRESHOLD_M
        ]
        .sort_values(
            [
                "season",
                "operator",
                "share_pct",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
    )

    print(
        baseline[
            [
                "operator",
                "season",
                "interaction_class",
                "trips",
                "share_pct",
                "total_scope_trips",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "400 m — SUMMER MINUS WINTER"
    )

    print(
        "=" * 110
    )

    print(
        seasonal_comparison.to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "OUTPUTS"
    )

    print(
        "=" * 110
    )

    print(
        f"Per-trip proximity dataset -> "
        f"{OUTPUT_PARQUET}"
    )

    print(
        f"GIS layers -> "
        f"{OUTPUT_GPKG}"
    )

    print(
        f"Audit tables -> "
        f"{AUDIT_DIR}"
    )

    print(
        "\nIMPORTANT INTERPRETATION:"
    )

    print(
        "- Distances are measured to the "
        "2,197 canonical urban PT stops."
    )

    print(
        "- Scooter trips are restricted to "
        "those with BOTH endpoints inside "
        "the official Torino footprint."
    )

    print(
        "- 400 m is the baseline accessibility "
        "threshold; 250 m and 600 m are "
        "sensitivity tests."
    )

    print(
        "- 'PT-overlap candidate' is NOT yet "
        "treated as proven modal competition."
    )

    print(
        "- Timetable-specific 2024 claims "
        "are intentionally avoided."
    )


if __name__ == "__main__":

    main()