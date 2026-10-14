from __future__ import annotations

from pathlib import Path
import io
import zipfile

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import LineString


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GTFS_BASE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "external"
    / "gtt_gtfs"
)

ZONING_PATH = (
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
    / "exercise_3"
    / "pt_reference"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "pt_reference"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_GPKG = (
    OUTPUT_DIR
    / "gtt_reference_network.gpkg"
)

TARGET_CRS = "EPSG:3003"

# Public-transport network used in the 30/30 example:
# urban bus + tram + metro.
TARGET_AGENCY_ID = "U"

ROUTE_TYPE_MAP = {
    0: "tram",
    1: "metro",
    3: "bus",
}

TARGET_ROUTE_TYPES = set(
    ROUTE_TYPE_MAP.keys()
)

REQUIRED_GTFS_FILES = {
    "agency.txt",
    "routes.txt",
    "stops.txt",
    "stop_attributes.txt",
    "trips.txt",
    "shapes.txt",
    "feed_info.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "stop_times.txt",
}


# =============================================================================
# GTFS SOURCE HANDLING
# =============================================================================

def resolve_gtfs_source():
    """
    Supports either:
      1. extracted .txt files inside data/raw/external/gtt_gtfs/
      2. a GTFS .zip file inside the same directory
      3. gtt_gtfs.zip directly under data/raw/external/
    """

    if GTFS_BASE.exists() and GTFS_BASE.is_dir():

        txt_files = {
            p.name
            for p in GTFS_BASE.glob("*.txt")
        }

        if REQUIRED_GTFS_FILES.issubset(txt_files):

            return {
                "type": "directory",
                "path": GTFS_BASE,
            }

        zip_candidates = sorted(
            GTFS_BASE.glob("*.zip")
        )

        if zip_candidates:

            return {
                "type": "zip",
                "path": zip_candidates[0],
            }

    parent_zip_candidates = sorted(
        (
            PROJECT_ROOT
            / "data"
            / "raw"
            / "external"
        ).glob("gtt_gtfs*.zip")
    )

    if parent_zip_candidates:

        return {
            "type": "zip",
            "path": parent_zip_candidates[0],
        }

    raise FileNotFoundError(
        "\nCould not find the GTT GTFS source.\n"
        "Expected either extracted TXT files under:\n"
        f"{GTFS_BASE}\n"
        "or a gtt_gtfs*.zip file."
    )


class GTFSReader:

    def __init__(self, source):

        self.source_type = source["type"]
        self.path = source["path"]

        if self.source_type == "zip":

            self.zipfile = zipfile.ZipFile(
                self.path,
                "r",
            )

            self.files = set(
                self.zipfile.namelist()
            )

        else:

            self.zipfile = None

            self.files = {
                p.name
                for p in self.path.glob("*.txt")
            }

    def read_csv(
        self,
        filename,
        **kwargs,
    ):

        if self.source_type == "directory":

            return pd.read_csv(
                self.path / filename,
                **kwargs,
            )

        with self.zipfile.open(
            filename
        ) as fh:

            return pd.read_csv(
                fh,
                **kwargs,
            )

    def close(self):

        if self.zipfile is not None:
            self.zipfile.close()


# =============================================================================
# HELPERS
# =============================================================================

def safe_string(series):

    return (
        series
        .astype("string")
        .str.strip()
    )


def unique_join(series):

    values = (
        safe_string(series)
        .dropna()
        .unique()
        .tolist()
    )

    return "|".join(
        sorted(values)
    )


def make_shape_lines(
    shapes,
):

    rows = []

    grouped = shapes.groupby(
        "shape_id",
        sort=False,
    )

    for shape_id, group in grouped:

        group = group.sort_values(
            "shape_pt_sequence"
        )

        coords = list(
            zip(
                group["shape_pt_lon"],
                group["shape_pt_lat"],
            )
        )

        # Remove consecutive duplicate coordinates.
        clean_coords = []

        for coord in coords:

            if (
                not clean_coords
                or coord != clean_coords[-1]
            ):
                clean_coords.append(coord)

        if len(clean_coords) < 2:

            continue

        if len(set(clean_coords)) < 2:

            continue

        rows.append(
            {
                "shape_id": str(shape_id),
                "shape_point_count":
                    len(clean_coords),
                "geometry":
                    LineString(
                        clean_coords
                    ),
            }
        )

    return gpd.GeoDataFrame(
        rows,
        geometry="geometry",
        crs="EPSG:4326",
    )


def write_layer(
    gdf,
    layer_name,
):

    gdf.to_file(
        OUTPUT_GPKG,
        layer=layer_name,
        driver="GPKG",
    )

    print(
        f"Saved layer: {layer_name}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 110
    )

    print(
        "EXERCISE 3 — GTT REFERENCE PUBLIC-TRANSPORT NETWORK"
    )

    print(
        "=" * 110
    )

    # =========================================================================
    # GTFS SOURCE
    # =========================================================================

    source = resolve_gtfs_source()

    print(
        f"\nGTFS source type: "
        f"{source['type']}"
    )

    print(
        f"GTFS source: "
        f"{source['path']}"
    )

    reader = GTFSReader(
        source
    )

    missing_files = (
        REQUIRED_GTFS_FILES
        -
        reader.files
    )

    if missing_files:

        raise RuntimeError(
            "Required GTFS files missing:\n"
            f"{sorted(missing_files)}"
        )

    print(
        "Required-file validation: PASSED"
    )

    # =========================================================================
    # FEED INFO
    # =========================================================================

    feed_info = reader.read_csv(
        "feed_info.txt",
        dtype="string",
    )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "GTFS FEED METADATA"
    )

    print(
        "-" * 110
    )

    print(
        feed_info.to_string(
            index=False
        )
    )

    feed_start = pd.to_datetime(
        feed_info.loc[
            0,
            "feed_start_date",
        ],
        format="%Y%m%d",
        errors="coerce",
    )

    feed_end = pd.to_datetime(
        feed_info.loc[
            0,
            "feed_end_date",
        ],
        format="%Y%m%d",
        errors="coerce",
    )

    feed_version = (
        feed_info.loc[
            0,
            "feed_version",
        ]
        if "feed_version"
        in feed_info.columns
        else pd.NA
    )

    feed_overlaps_2024 = bool(
        (
            pd.notna(feed_start)
            and pd.notna(feed_end)
            and feed_start
            <= pd.Timestamp(
                "2024-12-31"
            )
            and feed_end
            >= pd.Timestamp(
                "2024-01-01"
            )
        )
    )

    print(
        f"\nFeed overlaps 2024: "
        f"{feed_overlaps_2024}"
    )

    if not feed_overlaps_2024:

        print(
            "\nREFERENCE-NETWORK WARNING:"
        )

        print(
            "- GTFS service dates do not overlap "
            "the 2024 scooter observation period."
        )

        print(
            "- GTFS is therefore used only as a "
            "reference SPATIAL network in Exercise 3."
        )

        print(
            "- calendar.txt, calendar_dates.txt and "
            "stop_times.txt will NOT be used to claim "
            "historical 2024 timetable availability."
        )

    # =========================================================================
    # LOAD CORE GTFS TABLES
    # =========================================================================

    agency = reader.read_csv(
        "agency.txt",
        dtype="string",
    )

    routes = reader.read_csv(
        "routes.txt",
        dtype="string",
        low_memory=False,
    )

    trips = reader.read_csv(
        "trips.txt",
        dtype="string",
        low_memory=False,
    )

    stops = reader.read_csv(
        "stops.txt",
        dtype="string",
        low_memory=False,
    )

    stop_attributes = reader.read_csv(
        "stop_attributes.txt",
        dtype="string",
        low_memory=False,
    )

    shapes = reader.read_csv(
        "shapes.txt",
        dtype={
            "shape_id": "string",
            "shape_pt_lat": "float64",
            "shape_pt_lon": "float64",
            "shape_pt_sequence": "int64",
        },
        low_memory=False,
    )

    reader.close()

    # =========================================================================
    # SCHEMA / ID VALIDATION
    # =========================================================================

    agency["agency_id"] = safe_string(
        agency["agency_id"]
    )

    routes["route_id"] = safe_string(
        routes["route_id"]
    )

    routes["agency_id"] = safe_string(
        routes["agency_id"]
    )

    trips["trip_id"] = safe_string(
        trips["trip_id"]
    )

    trips["route_id"] = safe_string(
        trips["route_id"]
    )

    trips["shape_id"] = safe_string(
        trips["shape_id"]
    )

    stops["stop_id"] = safe_string(
        stops["stop_id"]
    )

    stop_attributes["stop_id"] = (
        safe_string(
            stop_attributes[
                "stop_id"
            ]
        )
    )

    shapes["shape_id"] = safe_string(
        shapes["shape_id"]
    )

    if agency["agency_id"].duplicated().any():

        raise RuntimeError(
            "Duplicate agency_id values found."
        )

    if routes["route_id"].duplicated().any():

        raise RuntimeError(
            "Duplicate route_id values found."
        )

    if trips["trip_id"].duplicated().any():

        raise RuntimeError(
            "Duplicate trip_id values found."
        )

    if stops["stop_id"].duplicated().any():

        raise RuntimeError(
            "Duplicate stop_id values found."
        )

    if stop_attributes[
        "stop_id"
    ].duplicated().any():

        raise RuntimeError(
            "Duplicate stop_id values found "
            "in stop_attributes.txt."
        )

    print(
        "\nCore ID validation: PASSED"
    )

    # =========================================================================
    # ROUTE AUDIT
    # =========================================================================

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
        .fillna(
            "other"
        )
    )

    route_agency_check = routes[
        "agency_id"
    ].isin(
        agency[
            "agency_id"
        ]
    )

    if not route_agency_check.all():

        raise RuntimeError(
            "Some routes reference "
            "unknown agency_id values."
        )

    urban_routes = routes.loc[
        (
            routes[
                "agency_id"
            ]
            == TARGET_AGENCY_ID
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
    ].copy()

    route_summary = (
        urban_routes
        .groupby(
            [
                "route_type_num",
                "route_mode",
            ],
            dropna=False,
        )
        .agg(
            routes=(
                "route_id",
                "nunique",
            ),
        )
        .reset_index()
        .sort_values(
            "route_type_num"
        )
    )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "URBAN ROUTE SUMMARY"
    )

    print(
        "-" * 110
    )

    print(
        route_summary.to_string(
            index=False
        )
    )

    # =========================================================================
    # TRIP → ROUTE → SHAPE RELATIONSHIP
    # =========================================================================

    selected_trips = trips.merge(
        urban_routes[
            [
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type_num",
                "route_mode",
            ]
        ],
        on="route_id",
        how="inner",
        validate="many_to_one",
    )

    selected_trips[
        "shape_missing"
    ] = (
        selected_trips[
            "shape_id"
        ]
        .isna()
        |
        (
            selected_trips[
                "shape_id"
            ]
            == ""
        )
    )

    selected_trip_count = len(
        selected_trips
    )

    selected_missing_shape = int(
        selected_trips[
            "shape_missing"
        ].sum()
    )

    shape_route_usage = (
        selected_trips.loc[
            ~selected_trips[
                "shape_missing"
            ],
            [
                "shape_id",
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type_num",
                "route_mode",
            ],
        ]
        .drop_duplicates()
        .copy()
    )

    required_shape_ids = set(
        shape_route_usage[
            "shape_id"
        ]
    )

    available_shape_ids = set(
        shapes[
            "shape_id"
        ]
    )

    missing_shape_geometry_ids = (
        required_shape_ids
        -
        available_shape_ids
    )

    print(
        "\nSelected urban trips: "
        f"{selected_trip_count:,}"
    )

    print(
        "Trips missing shape_id: "
        f"{selected_missing_shape:,}"
    )

    print(
        "Selected unique route shapes: "
        f"{len(required_shape_ids):,}"
    )

    print(
        "Selected shape IDs absent from shapes.txt: "
        f"{len(missing_shape_geometry_ids):,}"
    )

    # =========================================================================
    # STOP ATTRIBUTE JOIN
    # =========================================================================

    stops = stops.merge(
        stop_attributes[
            [
                "stop_id",
                "stop_city",
            ]
        ],
        on="stop_id",
        how="left",
        validate="one_to_one",
    )

    stops[
        "stop_lat_num"
    ] = pd.to_numeric(
        stops["stop_lat"],
        errors="coerce",
    )

    stops[
        "stop_lon_num"
    ] = pd.to_numeric(
        stops["stop_lon"],
        errors="coerce",
    )

    stops[
        "valid_coordinates"
    ] = (
        stops[
            "stop_lat_num"
        ].between(
            -90,
            90,
            inclusive="both",
        )
        &
        stops[
            "stop_lon_num"
        ].between(
            -180,
            180,
            inclusive="both",
        )
    )

    invalid_stop_coordinates = int(
        (
            ~stops[
                "valid_coordinates"
            ]
        ).sum()
    )

    stops_valid = stops.loc[
        stops[
            "valid_coordinates"
        ]
    ].copy()

    stop_gdf = gpd.GeoDataFrame(
        stops_valid,
        geometry=gpd.points_from_xy(
            stops_valid[
                "stop_lon_num"
            ],
            stops_valid[
                "stop_lat_num"
            ],
        ),
        crs="EPSG:4326",
    )

    stop_gdf = stop_gdf.to_crs(
        TARGET_CRS
    )

    stop_gdf[
        "city_attribute_torino"
    ] = (
        stop_gdf[
            "stop_city"
        ]
        .fillna("")
        .str.strip()
        .str.casefold()
        .eq(
            "torino"
        )
    )

    # =========================================================================
    # OFFICIAL TORINO BOUNDARY FROM EXERCISE 2
    # =========================================================================

    if not ZONING_PATH.exists():

        raise FileNotFoundError(
            "Official Torino zoning not found:\n"
            f"{ZONING_PATH}"
        )

    zones = gpd.read_file(
        ZONING_PATH
        layer="zones",
    )

    if zones.crs is None:

        raise RuntimeError(
            "Torino zoning has no CRS."
        )

    zones = zones.to_crs(
        TARGET_CRS
    )

    if hasattr(
        zones.geometry,
        "union_all",
    ):

        torino_union = (
            zones.geometry.union_all()
        )

    else:

        torino_union = (
            zones.geometry.unary_union
        )

    torino_boundary = (
        gpd.GeoDataFrame(
            {
                "boundary_name": [
                    "Torino official municipal footprint"
                ]
            },
            geometry=[
                torino_union
            ],
            crs=TARGET_CRS,
        )
    )

    stop_gdf[
        "inside_official_torino"
    ] = stop_gdf.geometry.apply(
        torino_union.covers
    )

    stop_gdf[
        "scope_match"
    ] = np.select(
        [
            (
                stop_gdf[
                    "city_attribute_torino"
                ]
                &
                stop_gdf[
                    "inside_official_torino"
                ]
            ),
            (
                stop_gdf[
                    "city_attribute_torino"
                ]
                &
                ~stop_gdf[
                    "inside_official_torino"
                ]
            ),
            (
                ~stop_gdf[
                    "city_attribute_torino"
                ]
                &
                stop_gdf[
                    "inside_official_torino"
                ]
            ),
        ],
        [
            "both_torino",
            "city_attr_only",
            "official_polygon_only",
        ],
        default="neither",
    )

    stop_scope_summary = (
        stop_gdf[
            "scope_match"
        ]
        .value_counts()
        .rename_axis(
            "scope_match"
        )
        .reset_index(
            name="stops"
        )
    )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "STOP SCOPE CROSS-CHECK"
    )

    print(
        "-" * 110
    )

    print(
        stop_scope_summary.to_string(
            index=False
        )
    )

    print(
        f"\nTotal stops: "
        f"{len(stops):,}"
    )

    print(
        f"Invalid stop coordinates: "
        f"{invalid_stop_coordinates:,}"
    )

    print(
        "stop_city = Torino: "
        f"{int(stop_gdf['city_attribute_torino'].sum()):,}"
    )

    print(
        "Inside official Torino polygon: "
        f"{int(stop_gdf['inside_official_torino'].sum()):,}"
    )

    # =========================================================================
    # BUILD GTFS SHAPE GEOMETRIES
    # =========================================================================

    selected_shapes = shapes.loc[
        shapes[
            "shape_id"
        ].isin(
            required_shape_ids
        )
    ].copy()

    valid_shape_coordinates = (
        selected_shapes[
            "shape_pt_lat"
        ].between(
            -90,
            90,
            inclusive="both",
        )
        &
        selected_shapes[
            "shape_pt_lon"
        ].between(
            -180,
            180,
            inclusive="both",
        )
    )

    invalid_shape_points = int(
        (
            ~valid_shape_coordinates
        ).sum()
    )

    selected_shapes = (
        selected_shapes.loc[
            valid_shape_coordinates
        ]
        .copy()
    )

    print(
        "\nBuilding urban route shapes..."
    )

    shape_lines = make_shape_lines(
        selected_shapes
    )

    shape_lines = shape_lines.to_crs(
        TARGET_CRS
    )

    print(
        f"Constructed shape geometries: "
        f"{len(shape_lines):,}"
    )

    print(
        f"Invalid selected shape points: "
        f"{invalid_shape_points:,}"
    )

    # =========================================================================
    # ATTACH ROUTE METADATA TO SHAPES
    # =========================================================================

    route_shape_gdf = (
        shape_route_usage.merge(
            shape_lines,
            on="shape_id",
            how="inner",
            validate="many_to_one",
        )
    )

    route_shape_gdf = (
        gpd.GeoDataFrame(
            route_shape_gdf,
            geometry="geometry",
            crs=TARGET_CRS,
        )
    )

    # =========================================================================
    # CLIP NETWORK TO OFFICIAL TORINO FOOTPRINT
    # =========================================================================

    print(
        "\nClipping urban PT network "
        "to official Torino footprint..."
    )

    route_shapes_torino = gpd.clip(
        route_shape_gdf,
        torino_boundary,
        keep_geom_type=True,
    )

    route_shapes_torino = (
        route_shapes_torino.loc[
            ~route_shapes_torino.geometry.is_empty
            &
            route_shapes_torino.geometry.notna()
        ]
        .copy()
    )

    valid_line_types = {
        "LineString",
        "MultiLineString",
    }

    route_shapes_torino = (
        route_shapes_torino.loc[
            route_shapes_torino
            .geometry
            .geom_type
            .isin(
                valid_line_types
            )
        ]
        .copy()
    )

    # Route-level layer for QGIS.
    route_level = (
        route_shapes_torino[
            [
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type_num",
                "route_mode",
                "geometry",
            ]
        ]
        .dissolve(
            by=[
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type_num",
                "route_mode",
            ],
            as_index=False,
        )
    )

    # =========================================================================
    # STOP LAYERS
    # =========================================================================

    stops_city_attribute = (
        stop_gdf.loc[
            stop_gdf[
                "city_attribute_torino"
            ]
        ]
        .copy()
    )

    stops_official_polygon = (
        stop_gdf.loc[
            stop_gdf[
                "inside_official_torino"
            ]
        ]
        .copy()
    )

    stop_scope_mismatches = (
        stop_gdf.loc[
            stop_gdf[
                "scope_match"
            ].isin(
                [
                    "city_attr_only",
                    "official_polygon_only",
                ]
            )
        ]
        .copy()
    )

    # =========================================================================
    # FINAL VALIDATION
    # =========================================================================

    if route_level.empty:

        raise RuntimeError(
            "Urban PT route layer is empty."
        )

    if stops_city_attribute.empty:

        raise RuntimeError(
            "No Torino stops found "
            "using stop_city."
        )

    if stops_official_polygon.empty:

        raise RuntimeError(
            "No stops fall inside the "
            "official Torino footprint."
        )

    if not route_level.geometry.is_valid.all():

        raise RuntimeError(
            "Invalid geometries found "
            "in route-level PT network."
        )

    print(
        "\nSpatial validation: PASSED"
    )

    # =========================================================================
    # WRITE GPKG
    # =========================================================================

    if OUTPUT_GPKG.exists():

        OUTPUT_GPKG.unlink()

        print(
            f"\nRemoved previous file -> "
            f"{OUTPUT_GPKG}"
        )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "WRITING GIS LAYERS"
    )

    print(
        "-" * 110
    )

    write_layer(
        torino_boundary,
        "torino_boundary",
    )

    write_layer(
        stops_city_attribute,
        "pt_stops_torino_city_attr",
    )

    write_layer(
        stops_official_polygon,
        "pt_stops_torino_official",
    )

    write_layer(
        route_shapes_torino,
        "pt_route_shapes_urban",
    )

    write_layer(
        route_level,
        "pt_routes_urban",
    )

    if not stop_scope_mismatches.empty:

        write_layer(
            stop_scope_mismatches,
            "pt_stop_scope_mismatches",
        )

    # =========================================================================
    # AUDIT TABLES
    # =========================================================================

    route_summary.to_csv(
        AUDIT_DIR
        / "urban_route_mode_summary.csv",
        index=False,
    )

    stop_scope_summary.to_csv(
        AUDIT_DIR
        / "stop_scope_crosscheck.csv",
        index=False,
    )

    stop_scope_mismatches.drop(
        columns="geometry",
        errors="ignore",
    ).to_csv(
        AUDIT_DIR
        / "stop_scope_mismatches.csv",
        index=False,
    )

    audit_rows = [
        {
            "metric":
                "feed_start_date",
            "value":
                str(
                    feed_start.date()
                    if pd.notna(feed_start)
                    else pd.NA
                ),
        },
        {
            "metric":
                "feed_end_date",
            "value":
                str(
                    feed_end.date()
                    if pd.notna(feed_end)
                    else pd.NA
                ),
        },
        {
            "metric":
                "feed_version",
            "value":
                str(feed_version),
        },
        {
            "metric":
                "feed_overlaps_2024",
            "value":
                str(feed_overlaps_2024),
        },
        {
            "metric":
                "total_agencies",
            "value":
                len(agency),
        },
        {
            "metric":
                "total_routes",
            "value":
                len(routes),
        },
        {
            "metric":
                "selected_urban_routes",
            "value":
                urban_routes[
                    "route_id"
                ].nunique(),
        },
        {
            "metric":
                "selected_urban_trips",
            "value":
                selected_trip_count,
        },
        {
            "metric":
                "selected_unique_shapes",
            "value":
                len(required_shape_ids),
        },
        {
            "metric":
                "constructed_shape_geometries",
            "value":
                len(shape_lines),
        },
        {
            "metric":
                "urban_routes_intersecting_torino",
            "value":
                route_level[
                    "route_id"
                ].nunique(),
        },
        {
            "metric":
                "total_gtfs_stops",
            "value":
                len(stops),
        },
        {
            "metric":
                "invalid_stop_coordinates",
            "value":
                invalid_stop_coordinates,
        },
        {
            "metric":
                "stop_city_torino",
            "value":
                int(
                    stop_gdf[
                        "city_attribute_torino"
                    ].sum()
                ),
        },
        {
            "metric":
                "stops_inside_official_torino",
            "value":
                int(
                    stop_gdf[
                        "inside_official_torino"
                    ].sum()
                ),
        },
        {
            "metric":
                "stop_scope_mismatches",
            "value":
                len(
                    stop_scope_mismatches
                ),
        },
    ]

    audit_df = pd.DataFrame(
        audit_rows
    )

    audit_df.to_csv(
        AUDIT_DIR
        / "gtfs_reference_network_audit.csv",
        index=False,
    )

    # =========================================================================
    # TERMINAL SUMMARY
    # =========================================================================

    print(
        "\n"
        + "=" * 110
    )

    print(
        "REFERENCE PT NETWORK SUMMARY"
    )

    print(
        "=" * 110
    )

    print(
        f"Feed service period: "
        f"{feed_start.date()} "
        f"→ {feed_end.date()}"
    )

    print(
        f"Feed version: "
        f"{feed_version}"
    )

    print(
        f"Historical 2024 timetable match: "
        f"{feed_overlaps_2024}"
    )

    print(
        f"\nAll GTFS routes: "
        f"{len(routes):,}"
    )

    print(
        f"Selected urban bus/tram/metro routes: "
        f"{urban_routes['route_id'].nunique():,}"
    )

    print(
        "Selected routes intersecting "
        f"official Torino: "
        f"{route_level['route_id'].nunique():,}"
    )

    print(
        f"\nAll GTFS stops: "
        f"{len(stops):,}"
    )

    print(
        f"stop_city = Torino: "
        f"{len(stops_city_attribute):,}"
    )

    print(
        "Inside official Torino footprint: "
        f"{len(stops_official_polygon):,}"
    )

    print(
        f"Scope mismatches: "
        f"{len(stop_scope_mismatches):,}"
    )

    print(
        f"\nGeoPackage -> "
        f"{OUTPUT_GPKG}"
    )

    print(
        f"Audit directory -> "
        f"{AUDIT_DIR}"
    )

    print(
        "\nINTERPRETATION:"
    )

    print(
        "- This dataset defines the spatial "
        "reference PT network for Exercise 3."
    )

    print(
        "- The 2026 service calendar is NOT "
        "treated as a historical 2024 timetable."
    )

    print(
        "- No scooter trips have been classified yet."
    )

    print(
        "- The Torino stop scope remains auditable "
        "through both stop_city and the official "
        "municipal footprint."
    )


if __name__ == "__main__":
    main()