from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HARMONIZED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "harmonized"
)

ZONE_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "zoning"
    / "torino_statistical_zones.gpkg"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "trips_zoned"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_2"
    / "spatial_assignment"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "spatial_assignment"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# INPUT FILES
#
# Exercise 2 baseline:
# complete common calendar year 2024.
# ============================================================

FILES = {
    "bird":
        HARMONIZED_DIR
        / "bird_2024_harmonized.parquet",

    "lime":
        HARMONIZED_DIR
        / "lime_2024_harmonized.parquet",

    "voi":
        HARMONIZED_DIR
        / "voi_2024_harmonized.parquet",
}


EXPECTED_ROWS = {
    "bird": 390844,
    "lime": 1196200,
    "voi": 106115,
}


# ============================================================
# CRS
#
# Trip coordinates are canonical geographic lon/lat.
# Zoning is EPSG:3003.
# ============================================================

TRIP_SOURCE_CRS = "EPSG:4326"


# ============================================================
# LOAD ZONES
# ============================================================

def load_zones():

    if not ZONE_GPKG.exists():

        raise FileNotFoundError(
            ZONE_GPKG
        )

    zones = gpd.read_file(
        ZONE_GPKG,
        layer="zones",
    )

    required = {
        "zone_id",
        "zone_name",
        "geometry",
    }

    missing = (
        required
        -
        set(zones.columns)
    )

    if missing:

        raise ValueError(
            f"Missing canonical zoning fields: "
            f"{sorted(missing)}"
        )

    assert len(zones) == 94

    assert (
        zones[
            "zone_id"
        ]
        .nunique()
        == 94
    )

    assert (
        zones.crs.to_epsg()
        == 3003
    )

    zones[
        "zone_id"
    ] = (
        zones[
            "zone_id"
        ]
        .astype("string")
    )

    return zones[
        [
            "zone_id",
            "zone_name",
            "geometry",
        ]
    ].copy()


# ============================================================
# LOAD TRIPS
# ============================================================

def load_trips(
    operator,
):

    path = FILES[
        operator
    ]

    if not path.exists():

        raise FileNotFoundError(
            path
        )

    columns = [
        "operator",
        "year",
        "trip_uid",
        "vehicle_uid",
        "source_period",
        "start_time_local",
        "valid_temporal_detail",
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
        "valid_spatial_prezone",
    ]

    df = pd.read_parquet(
        path,
        columns=columns,
    )

    assert (
        len(df)
        ==
        EXPECTED_ROWS[
            operator
        ]
    )

    assert (
        df[
            "trip_uid"
        ]
        .is_unique
    )

    assert (
        df[
            "operator"
        ]
        .eq(
            operator
        )
        .all()
    )

    assert (
        df[
            "year"
        ]
        .eq(2024)
        .all()
    )

    df[
        "analysis_row_id"
    ] = np.arange(
        len(df),
        dtype="int64",
    )

    return df


# ============================================================
# COORDINATE VALIDITY
# ============================================================

def valid_coordinate_mask(
    df,
    lat_col,
    lon_col,
):

    lat = pd.to_numeric(
        df[
            lat_col
        ],
        errors="coerce",
    )

    lon = pd.to_numeric(
        df[
            lon_col
        ],
        errors="coerce",
    )

    finite = (
        np.isfinite(lat)
        &
        np.isfinite(lon)
    )

    world_range = (
        lat.between(
            -90,
            90,
            inclusive="both",
        )
        &
        lon.between(
            -180,
            180,
            inclusive="both",
        )
    )

    return (
        finite
        &
        world_range
    )


# ============================================================
# ASSIGN ONE ENDPOINT
#
# Strategy:
#
# 1. Strict polygon interior:
#       predicate = "within"
#
# 2. Only unmatched valid points are tested using
#       predicate = "intersects"
#    to identify points exactly on polygon boundaries.
#
# 3. A unique boundary match is retained.
#
# 4. A point touching multiple zones is NOT assigned
#    arbitrarily; it is flagged ambiguous_boundary.
#
# No nearest-zone snapping is performed.
# ============================================================

def assign_endpoint(
    df,
    zones,
    lat_col,
    lon_col,
    prefix,
):

    result = pd.DataFrame(
        {
            "analysis_row_id":
                df[
                    "analysis_row_id"
                ].to_numpy()
        }
    )

    result[
        f"{prefix}_zone_id"
    ] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="string",
    )

    result[
        f"{prefix}_zone_name"
    ] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="string",
    )

    result[
        f"{prefix}_assignment_status"
    ] = "invalid_coordinates"

    coord_valid = (
        valid_coordinate_mask(
            df,
            lat_col,
            lon_col,
        )
    )

    valid_df = df.loc[
        coord_valid,
        [
            "analysis_row_id",
            lat_col,
            lon_col,
        ],
    ].copy()

    if valid_df.empty:

        return result

    # --------------------------------------------------------
    # Convert lon/lat → projected zoning CRS
    # --------------------------------------------------------

    points = gpd.GeoDataFrame(
        valid_df[
            [
                "analysis_row_id",
            ]
        ].copy(),
        geometry=gpd.points_from_xy(
            valid_df[
                lon_col
            ],
            valid_df[
                lat_col
            ],
        ),
        crs=TRIP_SOURCE_CRS,
    )

    points = points.to_crs(
        zones.crs
    )

    # --------------------------------------------------------
    # PASS 1 — strict interior
    # --------------------------------------------------------

    interior = gpd.sjoin(
        points,
        zones,
        how="left",
        predicate="within",
    )

    # With non-overlapping zone interiors each point
    # should have at most one match.
    duplicate_interior = (
        interior[
            "analysis_row_id"
        ]
        .duplicated(
            keep=False
        )
    )

    if duplicate_interior.any():

        raise ValueError(
            f"{prefix}: unexpected multiple "
            "strict-interior zone matches."
        )

    interior_assigned = (
        interior[
            "zone_id"
        ]
        .notna()
    )

    interior_rows = interior.loc[
        interior_assigned,
        [
            "analysis_row_id",
            "zone_id",
            "zone_name",
        ],
    ].copy()

    # --------------------------------------------------------
    # Store strict-interior results
    # --------------------------------------------------------

    lookup_position = pd.Series(
        result.index.to_numpy(),
        index=result[
            "analysis_row_id"
        ],
    )

    positions = lookup_position.loc[
        interior_rows["analysis_row_id"]
    ].to_numpy()

    result.loc[positions, f"{prefix}_zone_id"] = (
        interior_rows["zone_id"].to_numpy()
    )
    result.loc[positions, f"{prefix}_zone_name"] = (
        interior_rows["zone_name"].to_numpy()
    )
    result.loc[positions, f"{prefix}_assignment_status"] = "assigned_interior"

    # --------------------------------------------------------
    # Valid-coordinate points still unmatched
    # --------------------------------------------------------

    assigned_ids = set(
        interior_rows[
            "analysis_row_id"
        ]
        .tolist()
    )

    unmatched_points = points.loc[
        ~points[
            "analysis_row_id"
        ].isin(
            assigned_ids
        )
    ].copy()

    if unmatched_points.empty:

        return result

    # --------------------------------------------------------
    # PASS 2 — boundary / intersection check
    # --------------------------------------------------------

    boundary = gpd.sjoin(
        unmatched_points,
        zones,
        how="left",
        predicate="intersects",
    )

    matched_boundary = boundary.loc[
        boundary[
            "zone_id"
        ]
        .notna()
    ].copy()

    if not matched_boundary.empty:

        counts = (
            matched_boundary.groupby(
                "analysis_row_id"
            )
            .size()
        )

        unique_ids = (
            counts.loc[
                counts == 1
            ]
            .index
        )

        ambiguous_ids = (
            counts.loc[
                counts > 1
            ]
            .index
        )

        # ----------------------------------------------------
        # Unique boundary match
        # ----------------------------------------------------

        unique_matches = (
            matched_boundary.loc[
                matched_boundary[
                    "analysis_row_id"
                ].isin(
                    unique_ids
                ),
                [
                    "analysis_row_id",
                    "zone_id",
                    "zone_name",
                ],
            ]
            .drop_duplicates(
                "analysis_row_id"
            )
        )

        for row in (
            unique_matches.itertuples(
                index=False
            )
        ):

            pos = lookup_position.loc[
                row.analysis_row_id
            ]

            result.at[
                pos,
                f"{prefix}_zone_id",
            ] = row.zone_id

            result.at[
                pos,
                f"{prefix}_zone_name",
            ] = row.zone_name

            result.at[
                pos,
                f"{prefix}_assignment_status",
            ] = "assigned_boundary_unique"

        # ----------------------------------------------------
        # Multiple polygons touched
        #
        # Do not resolve arbitrarily.
        # ----------------------------------------------------

        for row_id in ambiguous_ids:

            pos = lookup_position.loc[
                row_id
            ]

            result.at[
                pos,
                f"{prefix}_assignment_status",
            ] = "ambiguous_boundary"

    # --------------------------------------------------------
    # Remaining valid-coordinate points:
    # outside/no official zone
    # --------------------------------------------------------

    current_status = (
        result[
            f"{prefix}_assignment_status"
        ]
    )

    valid_row_ids = set(
        valid_df[
            "analysis_row_id"
        ]
        .tolist()
    )

    for row_id in valid_row_ids:

        pos = lookup_position.loc[
            row_id
        ]

        if (
            current_status.iloc[
                pos
            ]
            ==
            "invalid_coordinates"
        ):

            result.at[
                pos,
                f"{prefix}_assignment_status",
            ] = "unassigned_no_zone"

    return result


# ============================================================
# PROCESS OPERATOR
# ============================================================

def process_operator(
    operator,
    zones,
):

    print(
        "\n"
        + "=" * 100
    )

    print(
        f"ZONING {operator.upper()} 2024"
    )

    print(
        "=" * 100
    )

    df = load_trips(
        operator
    )

    print(
        f"Input trips: "
        f"{len(df):,}"
    )

    # ========================================================
    # ORIGIN
    # ========================================================

    print(
        "\nAssigning origins..."
    )

    origins = assign_endpoint(
        df=df,
        zones=zones,
        lat_col="start_lat",
        lon_col="start_lon",
        prefix="origin",
    )

    # ========================================================
    # DESTINATION
    # ========================================================

    print(
        "Assigning destinations..."
    )

    destinations = assign_endpoint(
        df=df,
        zones=zones,
        lat_col="end_lat",
        lon_col="end_lon",
        prefix="destination",
    )

    # ========================================================
    # MERGE ASSIGNMENTS
    # ========================================================

    zoned = (
        df.merge(
            origins,
            on="analysis_row_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            destinations,
            on="analysis_row_id",
            how="left",
            validate="one_to_one",
        )
    )

    assert (
        len(zoned)
        ==
        len(df)
    )

    assert (
        zoned[
            "trip_uid"
        ]
        .is_unique
    )

    # ========================================================
    # FINAL OFFICIAL-ZONE VALIDITY
    # ========================================================

    zoned[
        "origin_zone_assigned"
    ] = (
        zoned[
            "origin_zone_id"
        ]
        .notna()
    )

    zoned[
        "destination_zone_assigned"
    ] = (
        zoned[
            "destination_zone_id"
        ]
        .notna()
    )

    zoned[
        "valid_od_zone"
    ] = (
        zoned[
            "origin_zone_assigned"
        ]
        &
        zoned[
            "destination_zone_assigned"
        ]
    )

    zoned[
        "intra_zonal"
    ] = (
        zoned[
            "valid_od_zone"
        ]
        &
        (
            zoned[
                "origin_zone_id"
            ]
            ==
            zoned[
                "destination_zone_id"
            ]
        )
    )

    zoned[
        "inter_zonal"
    ] = (
        zoned[
            "valid_od_zone"
        ]
        &
        ~zoned[
            "intra_zonal"
        ]
    )

    zoned[
        "od_pair"
    ] = pd.Series(
        pd.NA,
        index=zoned.index,
        dtype="string",
    )

    valid = (
        zoned[
            "valid_od_zone"
        ]
    )

    zoned.loc[
        valid,
        "od_pair",
    ] = (
        zoned.loc[
            valid,
            "origin_zone_id",
        ].astype("string")
        +
        "→"
        +
        zoned.loc[
            valid,
            "destination_zone_id",
        ].astype("string")
    )

    # ========================================================
    # PREZONE vs OFFICIAL ZONING COMPARISON
    # ========================================================

    zoned[
        "prezone_valid_and_official_valid"
    ] = (
        zoned[
            "valid_spatial_prezone"
        ]
        &
        zoned[
            "valid_od_zone"
        ]
    )

    zoned[
        "prezone_valid_but_official_invalid"
    ] = (
        zoned[
            "valid_spatial_prezone"
        ]
        &
        ~zoned[
            "valid_od_zone"
        ]
    )

    zoned[
        "prezone_invalid_but_official_valid"
    ] = (
        ~zoned[
            "valid_spatial_prezone"
        ]
        &
        zoned[
            "valid_od_zone"
        ]
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    origin_counts = (
        zoned[
            "origin_assignment_status"
        ]
        .value_counts()
        .to_dict()
    )

    destination_counts = (
        zoned[
            "destination_assignment_status"
        ]
        .value_counts()
        .to_dict()
    )

    valid_od_count = int(
        zoned[
            "valid_od_zone"
        ]
        .sum()
    )

    intra_count = int(
        zoned[
            "intra_zonal"
        ]
        .sum()
    )

    inter_count = int(
        zoned[
            "inter_zonal"
        ]
        .sum()
    )

    summary = {
        "operator":
            operator,

        "year":
            2024,

        "input_trips":
            len(zoned),

        "origin_assigned":
            int(
                zoned[
                    "origin_zone_assigned"
                ]
                .sum()
            ),

        "destination_assigned":
            int(
                zoned[
                    "destination_zone_assigned"
                ]
                .sum()
            ),

        "valid_od_trips":
            valid_od_count,

        "valid_od_rate_pct":
            (
                valid_od_count
                /
                len(zoned)
                * 100
            ),

        "intra_zonal_trips":
            intra_count,

        "inter_zonal_trips":
            inter_count,

        "intra_zonal_share_of_valid_od_pct":
            (
                intra_count
                /
                valid_od_count
                * 100
                if valid_od_count > 0
                else np.nan
            ),

        "active_origin_zones":
            int(
                zoned.loc[
                    zoned[
                        "origin_zone_assigned"
                    ],
                    "origin_zone_id",
                ]
                .nunique()
            ),

        "active_destination_zones":
            int(
                zoned.loc[
                    zoned[
                        "destination_zone_assigned"
                    ],
                    "destination_zone_id",
                ]
                .nunique()
            ),

        "active_od_pairs":
            int(
                zoned.loc[
                    zoned[
                        "valid_od_zone"
                    ],
                    "od_pair",
                ]
                .nunique()
            ),

        "prezone_valid":
            int(
                zoned[
                    "valid_spatial_prezone"
                ]
                .sum()
            ),

        "prezone_valid_and_official_valid":
            int(
                zoned[
                    "prezone_valid_and_official_valid"
                ]
                .sum()
            ),

        "prezone_valid_but_official_invalid":
            int(
                zoned[
                    "prezone_valid_but_official_invalid"
                ]
                .sum()
            ),

        "prezone_invalid_but_official_valid":
            int(
                zoned[
                    "prezone_invalid_but_official_valid"
                ]
                .sum()
            ),
    }

    # Add assignment-status counts.
    for status, count in (
        origin_counts.items()
    ):

        summary[
            f"origin_{status}"
        ] = int(
            count
        )

    for status, count in (
        destination_counts.items()
    ):

        summary[
            f"destination_{status}"
        ] = int(
            count
        )

    # ========================================================
    # SAVE ZONED DATA
    # ========================================================

    output_file = (
        OUTPUT_DIR
        / f"{operator}_2024_zoned.parquet"
    )

    if output_file.exists():

        output_file.unlink()

    zoned.to_parquet(
        output_file,
        index=False,
    )

    print(
        f"\nSaved zoned trips -> "
        f"{output_file}"
    )

    # ========================================================
    # SAVE UNASSIGNED / AMBIGUOUS AUDIT
    # ========================================================

    problem = zoned.loc[
        (
            ~zoned[
                "origin_zone_assigned"
            ]
        )
        |
        (
            ~zoned[
                "destination_zone_assigned"
            ]
        ),
        [
            "operator",
            "year",
            "trip_uid",
            "source_period",
            "start_lat",
            "start_lon",
            "end_lat",
            "end_lon",
            "valid_spatial_prezone",
            "origin_assignment_status",
            "destination_assignment_status",
            "origin_zone_id",
            "destination_zone_id",
        ],
    ].copy()

    problem_file = (
        AUDIT_DIR
        / f"{operator}_2024_unassigned_endpoints.csv"
    )

    problem.to_csv(
        problem_file,
        index=False,
    )

    print(
        f"Spatial-assignment audit -> "
        f"{problem_file}"
    )

    # ========================================================
    # READ-BACK VALIDATION
    # ========================================================

    readback = pd.read_parquet(
        output_file,
        columns=[
            "trip_uid",
            "origin_zone_id",
            "destination_zone_id",
            "valid_od_zone",
        ],
    )

    assert len(readback) == len(zoned)

    assert (
        readback[
            "trip_uid"
        ]
        .is_unique
    )

    assert (
        int(
            readback[
                "valid_od_zone"
            ].sum()
        )
        ==
        valid_od_count
    )

    print(
        "Read-back validation: PASSED"
    )

    # ========================================================
    # TERMINAL
    # ========================================================

    print(
        "\nOrigin assignment:"
    )

    print(
        zoned[
            "origin_assignment_status"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nDestination assignment:"
    )

    print(
        zoned[
            "destination_assignment_status"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nOfficial-zone OD validity:"
    )

    print(
        f"Valid OD trips: "
        f"{valid_od_count:,} "
        f"({summary['valid_od_rate_pct']:.3f}%)"
    )

    print(
        f"Intra-zonal: "
        f"{intra_count:,} "
        f"({summary['intra_zonal_share_of_valid_od_pct']:.2f}% "
        f"of valid OD)"
    )

    print(
        f"Inter-zonal: "
        f"{inter_count:,}"
    )

    print(
        f"Active origin zones: "
        f"{summary['active_origin_zones']}"
    )

    print(
        f"Active destination zones: "
        f"{summary['active_destination_zones']}"
    )

    print(
        f"Active OD pairs: "
        f"{summary['active_od_pairs']:,}"
    )

    print(
        "\nPre-zone vs official zoning:"
    )

    print(
        f"Pre-zone valid: "
        f"{summary['prezone_valid']:,}"
    )

    print(
        "Pre-zone valid AND official OD valid: "
        f"{summary['prezone_valid_and_official_valid']:,}"
    )

    print(
        "Pre-zone valid BUT official OD invalid: "
        f"{summary['prezone_valid_but_official_invalid']:,}"
    )

    print(
        "Pre-zone invalid BUT official OD valid: "
        f"{summary['prezone_invalid_but_official_valid']:,}"
    )

    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 2 — OFFICIAL ZONE ASSIGNMENT"
    )

    print(
        "=" * 110
    )

    zones = load_zones()

    summaries = []

    for operator in [
        "bird",
        "lime",
        "voi",
    ]:

        summary = process_operator(
            operator,
            zones,
        )

        summaries.append(
            summary
        )

    summary_df = pd.DataFrame(
        summaries
    )

    summary_file = (
        AUDIT_DIR
        / "spatial_assignment_summary_2024.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False,
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "2024 SPATIAL ASSIGNMENT SUMMARY"
    )

    print(
        "=" * 110
    )

    display = (
        summary_df[
            [
                "operator",
                "input_trips",
                "origin_assigned",
                "destination_assigned",
                "valid_od_trips",
                "valid_od_rate_pct",
                "intra_zonal_trips",
                "intra_zonal_share_of_valid_od_pct",
                "inter_zonal_trips",
                "active_origin_zones",
                "active_destination_zones",
                "active_od_pairs",
                "prezone_valid_but_official_invalid",
                "prezone_invalid_but_official_valid",
            ]
        ]
        .copy()
    )

    display[
        "valid_od_rate_pct"
    ] = (
        display[
            "valid_od_rate_pct"
        ]
        .round(3)
    )

    display[
        "intra_zonal_share_of_valid_od_pct"
    ] = (
        display[
            "intra_zonal_share_of_valid_od_pct"
        ]
        .round(2)
    )

    print(
        display.to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
        "\n- All harmonized 2024 trips were retained during zoning."
        "\n- Raw lon/lat coordinates were interpreted as EPSG:4326 "
        "and reprojected to the official EPSG:3003 zoning."
        "\n- Strict polygon interiors were assigned first."
        "\n- Boundary points were inspected separately."
        "\n- Multi-zone boundary matches were never resolved arbitrarily."
        "\n- No nearest-zone snapping was used."
        "\n- valid_od_zone requires both origin and destination to have "
        "an unambiguous official zone."
        "\n- valid_spatial_prezone is retained as an audit field, "
        "but official zoning provides the final OD spatial criterion."
        "\n- Intra-zonal trips are retained in the OD population."
    )

    print(
        f"\nSummary saved -> "
        f"{summary_file}"
    )


if __name__ == "__main__":
    main()