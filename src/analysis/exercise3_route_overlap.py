from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd


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

PROXIMITY_PARQUET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "proximity"
    / "pt_proximity_february_july_2024.parquet"
)

PROXIMITY_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "proximity"
    / "exercise3_proximity_layers.gpkg"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_3"
    / "route_overlap"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "route_overlap"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PARQUET = (
    OUTPUT_DIR
    / "scooter_pt_route_overlap_february_july_2024.parquet"
)

TARGET_CRS = "EPSG:3003"

TARGET_AGENCY = "U"

TARGET_ROUTE_TYPES = {
    0,  # tram
    1,  # metro
    3,  # bus
}

# Main methodological thresholds:
# 50 m  = strict
# 100 m = baseline
# 150 m = relaxed
THRESHOLDS_M = [
    50,
    100,
    150,
]

BASELINE_THRESHOLD_M = 100

EXPECTED_CANONICAL_STOPS = 2197


# =============================================================================
# BASIC HELPERS
# =============================================================================

def clean_string(
    series: pd.Series,
) -> pd.Series:
    """
    Convert identifiers to stripped pandas strings.
    """
    return (
        series
        .astype("string")
        .str.strip()
    )


def tuple_to_pipe(
    values,
) -> str:
    """
    Serialize tuple/list-like values for final Parquet storage.
    """
    if values is None:
        return ""

    try:
        if len(values) == 0:
            return ""
    except TypeError:
        return str(values)

    return "|".join(
        str(v)
        for v in values
    )


def route_names_from_ids(
    route_ids,
    route_name_map,
):
    """
    Convert route IDs to unique sorted route short names.
    """
    if not route_ids:
        return tuple()

    names = []

    for route_id in route_ids:

        name = route_name_map.get(
            route_id,
            route_id,
        )

        if pd.isna(name):
            name = route_id

        names.append(
            str(name)
        )

    return tuple(
        sorted(
            set(names)
        )
    )


# =============================================================================
# BUILD REFERENCE PT TOPOLOGY
# =============================================================================

def build_pt_topology(
    canonical_stop_ids,
):
    """
    Build a purely spatial/topological representation of the selected
    GTT urban bus/tram/metro network.

    IMPORTANT:
    - GTFS timetable dates do NOT correspond to 2024.
    - stop_times is therefore used only to reconstruct ordered stop patterns.
    - frequencies, departure times and historical availability are NOT used.
    """

    print(
        "\n"
        + "=" * 110
    )

    print(
        "BUILDING REFERENCE PT ROUTE TOPOLOGY"
    )

    print(
        "=" * 110
    )

    # -------------------------------------------------------------------------
    # Load GTFS core files
    # -------------------------------------------------------------------------

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
            "direction_id",
        ],
        low_memory=False,
    )

    stop_times = pd.read_csv(
        GTFS_DIR
        / "stop_times.txt",
        dtype={
            "trip_id": "string",
            "stop_id": "string",
            "stop_sequence": "Int64",
        },
        usecols=[
            "trip_id",
            "stop_id",
            "stop_sequence",
        ],
        low_memory=False,
    )

    # -------------------------------------------------------------------------
    # Clean identifiers
    # -------------------------------------------------------------------------

    routes[
        "route_id"
    ] = clean_string(
        routes[
            "route_id"
        ]
    )

    routes[
        "agency_id"
    ] = clean_string(
        routes[
            "agency_id"
        ]
    )

    routes[
        "route_short_name"
    ] = clean_string(
        routes[
            "route_short_name"
        ]
    )

    trips[
        "trip_id"
    ] = clean_string(
        trips[
            "trip_id"
        ]
    )

    trips[
        "route_id"
    ] = clean_string(
        trips[
            "route_id"
        ]
    )

    trips[
        "direction_id"
    ] = clean_string(
        trips[
            "direction_id"
        ]
    )

    stop_times[
        "trip_id"
    ] = clean_string(
        stop_times[
            "trip_id"
        ]
    )

    stop_times[
        "stop_id"
    ] = clean_string(
        stop_times[
            "stop_id"
        ]
    )

    routes[
        "route_type_num"
    ] = pd.to_numeric(
        routes[
            "route_type"
        ],
        errors="coerce",
    )

    # -------------------------------------------------------------------------
    # Select urban GTT bus/tram/metro
    # -------------------------------------------------------------------------

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

    selected_route_ids = set(
        selected_routes[
            "route_id"
        ]
        .dropna()
    )

    route_name_map = dict(
        zip(
            selected_routes[
                "route_id"
            ],
            selected_routes[
                "route_short_name"
            ],
        )
    )

    selected_trips = (
        trips.loc[
            trips[
                "route_id"
            ].isin(
                selected_route_ids
            )
        ]
        .copy()
    )

    selected_trip_ids = set(
        selected_trips[
            "trip_id"
        ]
        .dropna()
    )

    print(
        f"Selected urban routes: "
        f"{len(selected_route_ids):,}"
    )

    print(
        f"Selected urban GTFS trips: "
        f"{len(selected_trip_ids):,}"
    )

    # -------------------------------------------------------------------------
    # Attach route metadata to stop_times
    # -------------------------------------------------------------------------

    selected_stop_times = (
        stop_times.loc[
            stop_times[
                "trip_id"
            ].isin(
                selected_trip_ids
            )
        ]
        .merge(
            selected_trips[
                [
                    "trip_id",
                    "route_id",
                    "direction_id",
                ]
            ],
            on="trip_id",
            how="left",
            validate="many_to_one",
        )
    )

    # Only canonical urban stops inside official Torino boundary
    selected_stop_times = (
        selected_stop_times.loc[
            selected_stop_times[
                "stop_id"
            ].isin(
                canonical_stop_ids
            )
        ]
        .copy()
    )

    # stop_sequence is essential for directional topology
    selected_stop_times = (
        selected_stop_times.loc[
            selected_stop_times[
                "stop_sequence"
            ].notna()
        ]
        .copy()
    )

    selected_stop_times[
        "stop_sequence"
    ] = (
        selected_stop_times[
            "stop_sequence"
        ]
        .astype(int)
    )

    if selected_stop_times.empty:

        raise RuntimeError(
            "No canonical stop_times remain "
            "after GTFS filtering."
        )

    # -------------------------------------------------------------------------
    # Stop -> route lookup
    # -------------------------------------------------------------------------

    stop_route_pairs = (
        selected_stop_times[
            [
                "stop_id",
                "route_id",
            ]
        ]
        .drop_duplicates()
    )

    stop_route_map = (
        stop_route_pairs
        .groupby(
            "stop_id"
        )[
            "route_id"
        ]
        .agg(
            lambda values: tuple(
                sorted(
                    set(values)
                )
            )
        )
        .to_dict()
    )

    print(
        f"Canonical stops represented in "
        f"urban topology: "
        f"{len(stop_route_map):,}"
    )

    # -------------------------------------------------------------------------
    # Construct ordered trip-level stop sequences
    # -------------------------------------------------------------------------

    ordered = (
        selected_stop_times
        .sort_values(
            [
                "trip_id",
                "stop_sequence",
            ],
            kind="mergesort",
        )
        .copy()
    )

    # =========================================================================
    # IMPORTANT PYARROW FIX
    # =========================================================================
    #
    # Recent pandas/pyarrow combinations may return Arrow list arrays after
    # groupby aggregation. DataFrame.drop_duplicates() cannot factorize
    # list<item:string>, producing:
    #
    # ArrowNotImplementedError:
    # dictionary_encode has no kernel matching list<item:string>
    #
    # Therefore:
    # 1) aggregate temporarily to list
    # 2) explicitly convert every sequence to an ordinary Python tuple
    # 3) construct a scalar hashable sequence key
    # 4) deduplicate using the scalar key
    #
    # Stop order remains completely unchanged.
    # =========================================================================

    sequences = (
        ordered
        .groupby(
            [
                "trip_id",
                "route_id",
                "direction_id",
            ],
            dropna=False,
            sort=False,
        )[
            "stop_id"
        ]
        .agg(list)
        .reset_index(
            name="stop_sequence_raw"
        )
    )

    sequences[
        "stop_sequence_tuple"
    ] = pd.Series(
        [
            tuple(seq)
            for seq
            in sequences[
                "stop_sequence_raw"
            ].tolist()
        ],
        index=sequences.index,
        dtype="object",
    )

    # Hashable representation used ONLY for pattern deduplication.
    sequences[
        "stop_sequence_key"
    ] = [
        "\x1f".join(
            str(stop_id)
            for stop_id
            in seq
        )
        for seq
        in sequences[
            "stop_sequence_tuple"
        ]
    ]

    # -------------------------------------------------------------------------
    # Unique route-direction ordered patterns
    # -------------------------------------------------------------------------

    patterns = (
        sequences
        .drop_duplicates(
            subset=[
                "route_id",
                "direction_id",
                "stop_sequence_key",
            ]
        )
        [
            [
                "route_id",
                "direction_id",
                "stop_sequence_tuple",
            ]
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    print(
        f"Unique trip-level stop sequences: "
        f"{len(sequences):,}"
    )

    print(
        f"Unique route/direction stop patterns: "
        f"{len(patterns):,}"
    )

    # Explicit validation of Python tuple normalization.
    if not all(
        isinstance(
            sequence,
            tuple,
        )
        for sequence
        in patterns[
            "stop_sequence_tuple"
        ]
    ):

        raise RuntimeError(
            "Stop-pattern sequences were not "
            "normalized to Python tuples."
        )

    patterns[
        "stop_count"
    ] = patterns[
        "stop_sequence_tuple"
    ].map(len)

    # Routes with fewer than two retained canonical stops cannot
    # provide an origin -> destination PT alternative.
    patterns = (
        patterns.loc[
            patterns[
                "stop_count"
            ]
            >= 2
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    print(
        f"Usable ordered route patterns "
        f"(>=2 canonical stops): "
        f"{len(patterns):,}"
    )

    # -------------------------------------------------------------------------
    # Build directed stop-pair -> route lookup
    # -------------------------------------------------------------------------
    #
    # Example:
    #
    # A -> B -> C -> D
    #
    # generates:
    # A->B, A->C, A->D
    # B->C, B->D
    # C->D
    #
    # Reverse combinations are NOT added unless a real GTFS pattern
    # contains them in reverse order.
    # -------------------------------------------------------------------------

    direct_pair_routes = defaultdict(
        set
    )

    for row in patterns.itertuples(
        index=False
    ):

        route_id = (
            row.route_id
        )

        sequence = (
            row.stop_sequence_tuple
        )

        n = len(
            sequence
        )

        for i in range(
            n - 1
        ):

            origin_stop = (
                sequence[i]
            )

            for j in range(
                i + 1,
                n,
            ):

                destination_stop = (
                    sequence[j]
                )

                if (
                    origin_stop
                    == destination_stop
                ):
                    continue

                direct_pair_routes[
                    (
                        origin_stop,
                        destination_stop,
                    )
                ].add(
                    route_id
                )

    # Convert mutable sets to stable sorted tuples.
    direct_pair_routes = {
        key: tuple(
            sorted(
                route_ids
            )
        )
        for key, route_ids
        in direct_pair_routes.items()
    }

    print(
        f"Directed stop pairs with "
        f"direct-route compatibility: "
        f"{len(direct_pair_routes):,}"
    )

    if not direct_pair_routes:

        raise RuntimeError(
            "No directed PT stop pairs "
            "were constructed."
        )

    print(
        "Reference PT topology audit: PASSED"
    )

    return (
        stop_route_map,
        direct_pair_routes,
        route_name_map,
        selected_routes,
    )


# =============================================================================
# BUILD SCOOTER ENDPOINT GEOMETRIES
# =============================================================================

def build_endpoint_points(
    df: pd.DataFrame,
    endpoint: str,
) -> gpd.GeoDataFrame:
    """
    Construct projected origin or destination points.
    """

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

    points = gpd.GeoDataFrame(
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

    points = points.to_crs(
        TARGET_CRS
    )

    return points


# =============================================================================
# FIND ALL CANONICAL PT STOPS WITHIN ENDPOINT THRESHOLD
# =============================================================================

def endpoint_access_sets(
    points: gpd.GeoDataFrame,
    canonical_stops: gpd.GeoDataFrame,
    stop_route_map,
    endpoint: str,
    threshold: int,
) -> pd.DataFrame:
    """
    For every scooter endpoint:
    - find ALL canonical PT stops within threshold
    - collect their route IDs

    This intentionally does not rely only on the nearest stop, because a
    slightly farther nearby stop may provide a direct route compatible
    with the scooter OD.
    """

    # -------------------------------------------------------------------------
    # Buffer canonical PT stops
    # -------------------------------------------------------------------------

    stop_buffers = (
        canonical_stops[
            [
                "stop_id",
                "geometry",
            ]
        ]
        .copy()
    )

    stop_buffers[
        "geometry"
    ] = (
        stop_buffers
        .geometry
        .buffer(
            threshold
        )
    )

    # -------------------------------------------------------------------------
    # Point-in-buffer spatial join
    # -------------------------------------------------------------------------

    joined = gpd.sjoin(
        points,
        stop_buffers,
        how="left",
        predicate="within",
    )

    matched = (
        joined.loc[
            joined[
                "stop_id"
            ].notna(),
            [
                "analysis_trip_id",
                "stop_id",
            ],
        ]
        .copy()
    )

    matched[
        "stop_id"
    ] = clean_string(
        matched[
            "stop_id"
        ]
    )

    # -------------------------------------------------------------------------
    # Build trip -> nearby stops lookup
    # -------------------------------------------------------------------------

    if matched.empty:

        stop_groups = {}

    else:

        stop_groups = (
            matched
            .groupby(
                "analysis_trip_id"
            )[
                "stop_id"
            ]
            .agg(
                lambda values: tuple(
                    sorted(
                        set(values)
                    )
                )
            )
            .to_dict()
        )

    all_trip_ids = (
        points[
            "analysis_trip_id"
        ]
        .tolist()
    )

    stop_sets = []

    route_sets = []

    stop_counts = []

    route_counts = []

    for trip_id in all_trip_ids:

        stop_ids = (
            stop_groups.get(
                trip_id,
                tuple(),
            )
        )

        route_ids = set()

        for stop_id in stop_ids:

            route_ids.update(
                stop_route_map.get(
                    stop_id,
                    tuple(),
                )
            )

        route_ids = tuple(
            sorted(
                route_ids
            )
        )

        stop_sets.append(
            stop_ids
        )

        route_sets.append(
            route_ids
        )

        stop_counts.append(
            len(
                stop_ids
            )
        )

        route_counts.append(
            len(
                route_ids
            )
        )

    result = pd.DataFrame(
        {
            "analysis_trip_id":
                all_trip_ids,

            f"{endpoint}_stop_ids_{threshold}m":
                stop_sets,

            f"{endpoint}_route_ids_{threshold}m":
                route_sets,

            f"{endpoint}_stop_count_{threshold}m":
                stop_counts,

            f"{endpoint}_route_count_{threshold}m":
                route_counts,
        }
    )

    return result


# =============================================================================
# ROUTE-COMPATIBILITY HELPERS
# =============================================================================

def shared_routes(
    origin_routes,
    destination_routes,
):
    """
    Routes appearing near both scooter endpoints,
    without testing stop order.
    """

    if (
        not origin_routes
        or not destination_routes
    ):
        return tuple()

    return tuple(
        sorted(
            set(
                origin_routes
            )
            &
            set(
                destination_routes
            )
        )
    )


def direct_routes_between(
    origin_stops,
    destination_stops,
    direct_pair_routes,
):
    """
    Find routes for which at least one origin-near stop appears before
    at least one destination-near stop in a real GTFS route pattern.
    """

    if (
        not origin_stops
        or not destination_stops
    ):
        return tuple()

    direct_routes = set()

    for origin_stop in origin_stops:

        for destination_stop in destination_stops:

            direct_routes.update(
                direct_pair_routes.get(
                    (
                        origin_stop,
                        destination_stop,
                    ),
                    tuple(),
                )
            )

    return tuple(
        sorted(
            direct_routes
        )
    )


def classify_trip(
    origin_stops,
    destination_stops,
    direct_routes,
):
    """
    Route-aware interaction classification.
    """

    origin_near = bool(
        origin_stops
    )

    destination_near = bool(
        destination_stops
    )

    # Strongest competition candidate:
    # both endpoints near PT and direct ordered route exists.
    if (
        origin_near
        and destination_near
        and direct_routes
    ):
        return (
            "Direct PT-route overlap candidate"
        )

    # Both endpoints near PT, but no one-seat route could be established.
    if (
        origin_near
        and destination_near
    ):
        return (
            "PT-network overlap / no direct route"
        )

    # Scooter starts away from PT and terminates near PT.
    if (
        (not origin_near)
        and destination_near
    ):
        return (
            "Potential access / first-mile"
        )

    # Scooter starts near PT and terminates away from PT.
    if (
        origin_near
        and (not destination_near)
    ):
        return (
            "Potential egress / last-mile"
        )

    return (
        "Potential independent / spatial-gap"
    )


# =============================================================================
# SYSTEM-SCOPE HELPER
# =============================================================================

def add_system_scope(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add pooled system rows while retaining operator-specific observations.
    """

    system = (
        df.copy()
    )

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


# =============================================================================
# CLASSIFICATION SUMMARY
# =============================================================================

def build_classification_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:

    working = add_system_scope(
        df
    )

    rows = []

    for (
        operator,
        season,
    ), group in working.groupby(
        [
            "operator",
            "season",
        ],
        sort=False,
    ):

        total = len(
            group
        )

        for threshold in THRESHOLDS_M:

            class_col = (
                f"route_interaction_class_"
                f"{threshold}m"
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

                        "total_trips":
                            total,
                    }
                )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# ROUTE-OVERLAP DIAGNOSTIC SUMMARY
# =============================================================================

def build_route_diagnostic_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:

    working = add_system_scope(
        df
    )

    rows = []

    for (
        operator,
        season,
    ), group in working.groupby(
        [
            "operator",
            "season",
        ],
        sort=False,
    ):

        total = len(
            group
        )

        for threshold in THRESHOLDS_M:

            origin_near = (
                group[
                    f"origin_stop_count_"
                    f"{threshold}m"
                ]
                > 0
            )

            destination_near = (
                group[
                    f"destination_stop_count_"
                    f"{threshold}m"
                ]
                > 0
            )

            both_near = (
                origin_near
                &
                destination_near
            )

            shared_route = (
                group[
                    f"shared_route_count_"
                    f"{threshold}m"
                ]
                > 0
            )

            direct_route = (
                group[
                    f"direct_route_count_"
                    f"{threshold}m"
                ]
                > 0
            )

            both_near_n = int(
                both_near.sum()
            )

            rows.append(
                {
                    "operator":
                        operator,

                    "season":
                        season,

                    "threshold_m":
                        threshold,

                    "trips":
                        total,

                    "origin_near_pt_pct":
                        (
                            100
                            * origin_near.mean()
                        ),

                    "destination_near_pt_pct":
                        (
                            100
                            * destination_near.mean()
                        ),

                    "both_endpoints_near_pt_pct":
                        (
                            100
                            * both_near.mean()
                        ),

                    "shared_route_any_direction_pct":
                        (
                            100
                            * shared_route.mean()
                        ),

                    "ordered_direct_route_pct":
                        (
                            100
                            * direct_route.mean()
                        ),

                    "ordered_direct_given_both_near_pct":
                        (
                            100
                            * direct_route.sum()
                            / both_near_n
                            if both_near_n
                            else np.nan
                        ),

                    "shared_route_but_no_order_pct":
                        (
                            100
                            * (
                                shared_route
                                &
                                ~direct_route
                            ).mean()
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# 100 m SEASONAL COMPARISON
# =============================================================================

def build_baseline_seasonal_comparison(
    classification_summary: pd.DataFrame,
) -> pd.DataFrame:

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
        baseline
        .pivot_table(
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

    if (
        "winter_february"
        in pivot.columns
        and
        "summer_july"
        in pivot.columns
    ):

        pivot[
            "summer_minus_winter_pp"
        ] = (
            pivot[
                "summer_july"
            ]
            -
            pivot[
                "winter_february"
            ]
        )

    return pivot


# =============================================================================
# DIRECT-ROUTE FREQUENCY
# =============================================================================

def build_direct_route_frequency(
    df: pd.DataFrame,
    route_name_map,
) -> pd.DataFrame:

    threshold = (
        BASELINE_THRESHOLD_M
    )

    working = add_system_scope(
        df
    )

    rows = []

    route_col = (
        f"direct_route_ids_"
        f"{threshold}m"
    )

    count_col = (
        f"direct_route_count_"
        f"{threshold}m"
    )

    for (
        operator,
        season,
    ), group in working.groupby(
        [
            "operator",
            "season",
        ],
        sort=False,
    ):

        candidate_trips = (
            group.loc[
                group[
                    count_col
                ]
                > 0
            ]
        )

        route_counts = defaultdict(
            int
        )

        for route_ids in candidate_trips[
            route_col
        ]:

            for route_id in route_ids:

                route_counts[
                    route_id
                ] += 1

        denominator = len(
            candidate_trips
        )

        for route_id, count in route_counts.items():

            route_name = (
                route_name_map.get(
                    route_id,
                    route_id,
                )
            )

            if pd.isna(
                route_name
            ):
                route_name = (
                    route_id
                )

            rows.append(
                {
                    "operator":
                        operator,

                    "season":
                        season,

                    "route_id":
                        route_id,

                    "route_short_name":
                        route_name,

                    "candidate_trip_mentions":
                        count,

                    "share_of_direct_candidate_trips_pct":
                        (
                            100
                            * count
                            / denominator
                            if denominator
                            else np.nan
                        ),
                }
            )

    out = pd.DataFrame(
        rows
    )

    if not out.empty:

        out = (
            out
            .sort_values(
                [
                    "operator",
                    "season",
                    "candidate_trip_mentions",
                ],
                ascending=[
                    True,
                    True,
                    False,
                ],
            )
            .reset_index(
                drop=True
            )
        )

    return out


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 110
    )

    print(
        "EXERCISE 3 — DIRECT PT ROUTE / SCOOTER OD OVERLAP"
    )

    print(
        "=" * 110
    )

    # =========================================================================
    # LOAD STAGE 2 SCOOTER PROXIMITY DATA
    # =========================================================================

    if not PROXIMITY_PARQUET.exists():

        raise FileNotFoundError(
            "Missing Stage 2 output:\n"
            f"{PROXIMITY_PARQUET}"
        )

    df = pd.read_parquet(
        PROXIMITY_PARQUET
    )

    print(
        f"\nScooter trips loaded: "
        f"{len(df):,}"
    )

    required_columns = [
        "analysis_trip_id",
        "operator",
        "season",
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        raise RuntimeError(
            "Stage 2 proximity dataset "
            "is missing required columns:\n"
            f"{missing_columns}"
        )

    if (
        df[
            "analysis_trip_id"
        ]
        .isna()
        .any()
    ):

        raise RuntimeError(
            "analysis_trip_id contains "
            "missing values."
        )

    if (
        df[
            "analysis_trip_id"
        ]
        .duplicated()
        .any()
    ):

        duplicate_count = int(
            df[
                "analysis_trip_id"
            ]
            .duplicated(
                keep=False
            )
            .sum()
        )

        raise RuntimeError(
            "analysis_trip_id is not unique. "
            f"Rows involved: "
            f"{duplicate_count:,}"
        )

    # =========================================================================
    # LOAD CANONICAL PT STOPS
    # =========================================================================

    if not PROXIMITY_GPKG.exists():

        raise FileNotFoundError(
            "Missing Stage 2 GeoPackage:\n"
            f"{PROXIMITY_GPKG}"
        )

    canonical_stops = gpd.read_file(
        PROXIMITY_GPKG,
        layer="pt_stops_canonical",
    ).to_crs(
        TARGET_CRS
    )

    canonical_stops[
        "stop_id"
    ] = clean_string(
        canonical_stops[
            "stop_id"
        ]
    )

    if (
        len(
            canonical_stops
        )
        != EXPECTED_CANONICAL_STOPS
    ):

        raise RuntimeError(
            "Canonical PT stop count mismatch.\n"
            f"Expected: "
            f"{EXPECTED_CANONICAL_STOPS:,}\n"
            f"Observed: "
            f"{len(canonical_stops):,}"
        )

    if (
        canonical_stops[
            "stop_id"
        ]
        .duplicated()
        .any()
    ):

        raise RuntimeError(
            "Canonical PT stop IDs "
            "are not unique."
        )

    canonical_stop_ids = set(
        canonical_stops[
            "stop_id"
        ]
        .dropna()
    )

    print(
        f"Canonical PT stops: "
        f"{len(canonical_stops):,}"
    )

    # =========================================================================
    # BUILD REFERENCE PT TOPOLOGY
    # =========================================================================

    (
        stop_route_map,
        direct_pair_routes,
        route_name_map,
        selected_routes,
    ) = build_pt_topology(
        canonical_stop_ids
    )

    # =========================================================================
    # BUILD SCOOTER ENDPOINT POINTS
    # =========================================================================

    origins = build_endpoint_points(
        df,
        "origin",
    )

    destinations = build_endpoint_points(
        df,
        "destination",
    )

    # =========================================================================
    # THRESHOLD ANALYSIS
    # =========================================================================

    for threshold in THRESHOLDS_M:

        print(
            "\n"
            + "-" * 110
        )

        print(
            f"PROCESSING {threshold} m THRESHOLD"
        )

        print(
            "-" * 110
        )

        # ---------------------------------------------------------------------
        # All stops and routes near origin
        # ---------------------------------------------------------------------

        origin_access = endpoint_access_sets(
            points=origins,
            canonical_stops=canonical_stops,
            stop_route_map=stop_route_map,
            endpoint="origin",
            threshold=threshold,
        )

        # ---------------------------------------------------------------------
        # All stops and routes near destination
        # ---------------------------------------------------------------------

        destination_access = endpoint_access_sets(
            points=destinations,
            canonical_stops=canonical_stops,
            stop_route_map=stop_route_map,
            endpoint="destination",
            threshold=threshold,
        )

        # ---------------------------------------------------------------------
        # Merge endpoint PT access information
        # ---------------------------------------------------------------------

        df = (
            df
            .merge(
                origin_access,
                on="analysis_trip_id",
                how="left",
                validate="one_to_one",
            )
            .merge(
                destination_access,
                on="analysis_trip_id",
                how="left",
                validate="one_to_one",
            )
        )

        origin_route_col = (
            f"origin_route_ids_"
            f"{threshold}m"
        )

        destination_route_col = (
            f"destination_route_ids_"
            f"{threshold}m"
        )

        origin_stop_col = (
            f"origin_stop_ids_"
            f"{threshold}m"
        )

        destination_stop_col = (
            f"destination_stop_ids_"
            f"{threshold}m"
        )

        # ---------------------------------------------------------------------
        # Same route exists near both endpoints,
        # ignoring route direction/order.
        # ---------------------------------------------------------------------

        shared = [
            shared_routes(
                origin_routes,
                destination_routes,
            )
            for (
                origin_routes,
                destination_routes,
            )
            in zip(
                df[
                    origin_route_col
                ],
                df[
                    destination_route_col
                ],
            )
        ]

        df[
            f"shared_route_ids_"
            f"{threshold}m"
        ] = shared

        df[
            f"shared_route_count_"
            f"{threshold}m"
        ] = [
            len(
                route_ids
            )
            for route_ids
            in shared
        ]

        # ---------------------------------------------------------------------
        # Stronger test:
        # ordered direct route from origin-side stop to destination-side stop.
        # ---------------------------------------------------------------------

        direct = [
            direct_routes_between(
                origin_stops,
                destination_stops,
                direct_pair_routes,
            )
            for (
                origin_stops,
                destination_stops,
            )
            in zip(
                df[
                    origin_stop_col
                ],
                df[
                    destination_stop_col
                ],
            )
        ]

        df[
            f"direct_route_ids_"
            f"{threshold}m"
        ] = direct

        df[
            f"direct_route_count_"
            f"{threshold}m"
        ] = [
            len(
                route_ids
            )
            for route_ids
            in direct
        ]

        df[
            f"direct_route_names_"
            f"{threshold}m"
        ] = [
            route_names_from_ids(
                route_ids,
                route_name_map,
            )
            for route_ids
            in direct
        ]

        # ---------------------------------------------------------------------
        # Final route-aware classification
        # ---------------------------------------------------------------------

        df[
            f"route_interaction_class_"
            f"{threshold}m"
        ] = [
            classify_trip(
                origin_stops,
                destination_stops,
                direct_routes,
            )
            for (
                origin_stops,
                destination_stops,
                direct_routes,
            )
            in zip(
                df[
                    origin_stop_col
                ],
                df[
                    destination_stop_col
                ],
                df[
                    f"direct_route_ids_"
                    f"{threshold}m"
                ],
            )
        ]

        # ---------------------------------------------------------------------
        # Threshold validation
        # ---------------------------------------------------------------------

        if (
            df[
                f"route_interaction_class_"
                f"{threshold}m"
            ]
            .isna()
            .any()
        ):

            raise RuntimeError(
                f"Missing classifications "
                f"at {threshold} m."
            )

        direct_route_mask = (
            df[
                f"direct_route_count_"
                f"{threshold}m"
            ]
            > 0
        )

        both_near_mask = (
            (
                df[
                    f"origin_stop_count_"
                    f"{threshold}m"
                ]
                > 0
            )
            &
            (
                df[
                    f"destination_stop_count_"
                    f"{threshold}m"
                ]
                > 0
            )
        )

        # Direct route must logically imply both endpoints are near PT.
        impossible = (
            direct_route_mask
            &
            ~both_near_mask
        )

        if impossible.any():

            raise RuntimeError(
                f"Logical validation failed "
                f"at {threshold} m: "
                "direct route detected without "
                "both endpoints near PT."
            )

        print(
            f"{threshold} m analysis: PASSED"
        )

    # =========================================================================
    # FINAL VALIDATION
    # =========================================================================

    if (
        df[
            "analysis_trip_id"
        ]
        .duplicated()
        .any()
    ):

        raise RuntimeError(
            "Trip duplication was introduced "
            "during route-overlap processing."
        )

    if (
        len(df)
        != 268590
    ):

        print(
            "\nWARNING:"
        )

        print(
            f"Final trip count is "
            f"{len(df):,}; "
            "Stage 2 previously contained "
            "268,590 trips."
        )

    print(
        "\nFinal route-overlap validation: PASSED"
    )

    # =========================================================================
    # BUILD SUMMARY TABLES
    # =========================================================================

    classification_summary = (
        build_classification_summary(
            df
        )
    )

    diagnostic_summary = (
        build_route_diagnostic_summary(
            df
        )
    )

    seasonal_comparison = (
        build_baseline_seasonal_comparison(
            classification_summary
        )
    )

    route_frequency = (
        build_direct_route_frequency(
            df,
            route_name_map,
        )
    )

    # =========================================================================
    # SERIALIZE COLLECTION COLUMNS BEFORE PARQUET
    # =========================================================================
    #
    # Keeping Python tuple/list objects in final Parquet can again trigger
    # Arrow nested-list behaviour. The analytical calculations are already
    # finished, so collection attributes are stored as pipe-delimited strings.
    # =========================================================================

    tuple_columns = []

    for threshold in THRESHOLDS_M:

        tuple_columns.extend(
            [
                f"origin_stop_ids_{threshold}m",
                f"destination_stop_ids_{threshold}m",
                f"origin_route_ids_{threshold}m",
                f"destination_route_ids_{threshold}m",
                f"shared_route_ids_{threshold}m",
                f"direct_route_ids_{threshold}m",
                f"direct_route_names_{threshold}m",
            ]
        )

    output_df = (
        df.copy()
    )

    for col in tuple_columns:

        output_df[
            col
        ] = (
            output_df[
                col
            ]
            .map(
                tuple_to_pipe
            )
        )

    # =========================================================================
    # SAVE PER-TRIP RESULT
    # =========================================================================

    if OUTPUT_PARQUET.exists():

        OUTPUT_PARQUET.unlink()

    output_df.to_parquet(
        OUTPUT_PARQUET,
        index=False,
    )

    # Read-back validation
    readback = pd.read_parquet(
        OUTPUT_PARQUET
    )

    if (
        len(readback)
        != len(output_df)
    ):

        raise RuntimeError(
            "Route-overlap Parquet "
            "read-back row count mismatch."
        )

    if (
        readback[
            "analysis_trip_id"
        ]
        .duplicated()
        .any()
    ):

        raise RuntimeError(
            "Route-overlap Parquet "
            "read-back trip IDs are not unique."
        )

    print(
        "Per-trip Parquet read-back validation: PASSED"
    )

    # =========================================================================
    # SAVE AUDIT TABLES
    # =========================================================================

    classification_summary.to_csv(
        AUDIT_DIR
        / "route_aware_classification_summary.csv",
        index=False,
    )

    diagnostic_summary.to_csv(
        AUDIT_DIR
        / "route_overlap_diagnostic_summary.csv",
        index=False,
    )

    seasonal_comparison.to_csv(
        AUDIT_DIR
        / "route_aware_100m_seasonal_comparison.csv",
        index=False,
    )

    route_frequency.to_csv(
        AUDIT_DIR
        / "direct_route_frequency_100m.csv",
        index=False,
    )

    route_audit_columns = [
        col
        for col in [
            "route_id",
            "route_short_name",
            "route_long_name",
            "route_type",
            "route_type_num",
        ]
        if col in selected_routes.columns
    ]

    selected_routes[
        route_audit_columns
    ].to_csv(
        AUDIT_DIR
        / "selected_reference_routes.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL OUTPUT 1
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "ROUTE-OVERLAP DIAGNOSTIC SUMMARY"
    )

    print(
        "=" * 110
    )

    print(
        diagnostic_summary.to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    # =========================================================================
    # TERMINAL OUTPUT 2
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "100 m — ROUTE-AWARE INTERACTION CLASSIFICATION"
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
                "total_trips",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    # =========================================================================
    # TERMINAL OUTPUT 3
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "100 m — SUMMER MINUS WINTER"
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

    # =========================================================================
    # TERMINAL OUTPUT 4
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "TOP DIRECT-ROUTE CANDIDATES — SYSTEM / 100 m"
    )

    print(
        "=" * 110
    )

    if route_frequency.empty:

        print(
            "No direct-route candidates detected."
        )

    else:

        system_routes = (
            route_frequency.loc[
                route_frequency[
                    "operator"
                ]
                == "system"
            ]
            .groupby(
                "season",
                sort=False,
                group_keys=False,
            )
            .head(15)
        )

        print(
            system_routes.to_string(
                index=False,
                float_format=lambda x: (
                    f"{x:.2f}"
                ),
            )
        )

    # =========================================================================
    # OUTPUT LOCATIONS
    # =========================================================================

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
        f"Per-trip route-overlap dataset -> "
        f"{OUTPUT_PARQUET}"
    )

    print(
        f"Audit tables -> "
        f"{AUDIT_DIR}"
    )

    # =========================================================================
    # METHODOLOGICAL INTERPRETATION
    # =========================================================================

    print(
        "\nINTERPRETATION RULES:"
    )

    print(
        "- The analysis uses the 2,197 canonical "
        "GTT urban bus/tram/metro stops inside "
        "the official Torino footprint."
    )

    print(
        "- 100 m is the primary endpoint-to-stop "
        "proximity threshold."
    )

    print(
        "- 50 m is a strict sensitivity test; "
        "150 m is a relaxed sensitivity test."
    )

    print(
        "- Direct PT-route overlap means at least "
        "one reference urban route serves a stop "
        "near the scooter origin and subsequently "
        "a stop near its destination in the correct "
        "GTFS stop order."
    )

    print(
        "- A direct-route overlap is stronger "
        "evidence of potential modal competition "
        "than simple stop proximity."
    )

    print(
        "- It still does NOT prove that a scooter "
        "trip replaced a public-transport trip."
    )

    print(
        "- Access and egress classes are interpreted "
        "as potential first/last-mile evidence, not "
        "confirmed intermodal transfers."
    )

    print(
        "- The available GTFS feed is temporally "
        "non-contemporaneous with the 2024 scooter data."
    )

    print(
        "- GTFS stop order and route topology are used "
        "as a reference spatial network only."
    )

    print(
        "- 2026 GTFS frequencies, departure times, "
        "calendar service and waiting times are NOT "
        "used to make historical 2024 claims."
    )


if __name__ == "__main__":

    main()