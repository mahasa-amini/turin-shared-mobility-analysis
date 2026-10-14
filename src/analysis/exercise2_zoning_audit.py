from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_ZONE_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "external"
    / "torino_zones"
)

ZONE_FILE = (
    RAW_ZONE_DIR
    / "zone_statistiche_geo.shp"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "zoning"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_2"
    / "zoning"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "zoning"
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


OUTPUT_GPKG = (
    OUTPUT_DIR
    / "torino_statistical_zones.gpkg"
)


# ============================================================
# EXPECTED STRUCTURE
# ============================================================

EXPECTED_CRS_EPSG = 3003

EXPECTED_ZONE_COUNT = 94

REQUIRED_COLUMNS = {
    "ZONASTAT",
    "DENOM",
    "geometry",
}


# ============================================================
# LOAD
# ============================================================

def load_zoning():

    if not ZONE_FILE.exists():

        raise FileNotFoundError(
            f"Zoning file not found:\n{ZONE_FILE}"
        )

    gdf = gpd.read_file(
        ZONE_FILE
    )

    print(
        f"Loaded zoning: {len(gdf):,} polygons"
    )

    print(
        f"Columns: {list(gdf.columns)}"
    )

    print(
        f"CRS: {gdf.crs}"
    )

    return gdf


# ============================================================
# SCHEMA VALIDATION
# ============================================================

def validate_schema(gdf):

    missing = (
        REQUIRED_COLUMNS
        -
        set(gdf.columns)
    )

    if missing:

        raise ValueError(
            "Missing required zoning columns: "
            f"{sorted(missing)}"
        )

    if gdf.crs is None:

        raise ValueError(
            "Zoning CRS is missing."
        )

    epsg = gdf.crs.to_epsg()

    if epsg != EXPECTED_CRS_EPSG:

        raise ValueError(
            f"Unexpected zoning CRS: {gdf.crs}. "
            f"Expected EPSG:{EXPECTED_CRS_EPSG}."
        )

    if len(gdf) != EXPECTED_ZONE_COUNT:

        raise ValueError(
            f"Unexpected number of zones: {len(gdf)}. "
            f"Expected {EXPECTED_ZONE_COUNT}."
        )

    print(
        "Schema validation: PASSED"
    )


# ============================================================
# STANDARDIZE ATTRIBUTES
#
# IMPORTANT:
# ZONASTAT remains STRING because values such as
# 09bis and 17bis exist.
# ============================================================

def standardize_attributes(gdf):

    data = gdf.copy()

    data["ZONASTAT"] = (
        data["ZONASTAT"]
        .astype("string")
        .str.strip()
    )

    data["DENOM"] = (
        data["DENOM"]
        .astype("string")
        .str.strip()
    )

    data = data.rename(
        columns={
            "ZONASTAT":
                "zone_id",

            "DENOM":
                "zone_name",
        }
    )

    return data


# ============================================================
# ATTRIBUTE AUDIT
# ============================================================

def audit_attributes(gdf):

    result = {
        "zones":
            len(gdf),

        "missing_zone_id":
            int(
                gdf[
                    "zone_id"
                ]
                .isna()
                .sum()
            ),

        "missing_zone_name":
            int(
                gdf[
                    "zone_name"
                ]
                .isna()
                .sum()
            ),

        "duplicate_zone_id":
            int(
                gdf[
                    "zone_id"
                ]
                .duplicated()
                .sum()
            ),

        "duplicate_zone_name":
            int(
                gdf[
                    "zone_name"
                ]
                .duplicated()
                .sum()
            ),

        "unique_zone_ids":
            int(
                gdf[
                    "zone_id"
                ]
                .nunique()
            ),

        "unique_zone_names":
            int(
                gdf[
                    "zone_name"
                ]
                .nunique()
            ),
    }

    if (
        result[
            "missing_zone_id"
        ] > 0
    ):

        raise ValueError(
            "Missing zone IDs detected."
        )

    if (
        result[
            "duplicate_zone_id"
        ] > 0
    ):

        raise ValueError(
            "Duplicate ZONASTAT values detected."
        )

    if (
        result[
            "unique_zone_ids"
        ]
        != EXPECTED_ZONE_COUNT
    ):

        raise ValueError(
            "Zone IDs are not one-to-one with polygons."
        )

    print(
        "Attribute validation: PASSED"
    )

    return result


# ============================================================
# GEOMETRY AUDIT
# ============================================================

def audit_geometry(gdf):

    geom_types = (
        gdf[
            "geometry"
        ]
        .geom_type
        .value_counts()
        .to_dict()
    )

    null_geometry = int(
        gdf[
            "geometry"
        ]
        .isna()
        .sum()
    )

    empty_geometry = int(
        gdf[
            "geometry"
        ]
        .is_empty
        .sum()
    )

    invalid_geometry = int(
        (
            ~gdf[
                "geometry"
            ]
            .is_valid
        )
        .sum()
    )

    if null_geometry > 0:

        raise ValueError(
            "Null zoning geometries detected."
        )

    if empty_geometry > 0:

        raise ValueError(
            "Empty zoning geometries detected."
        )

    if invalid_geometry > 0:

        invalid = gdf.loc[
            ~gdf[
                "geometry"
            ]
            .is_valid
        ].copy()

        invalid.to_file(
            AUDIT_DIR
            / "invalid_zoning_geometries.gpkg",
            layer="invalid_zones",
            driver="GPKG",
        )

        raise ValueError(
            f"{invalid_geometry} invalid zoning "
            "geometries detected."
        )

    allowed_types = {
        "Polygon",
        "MultiPolygon",
    }

    unexpected_types = (
        set(
            geom_types.keys()
        )
        -
        allowed_types
    )

    if unexpected_types:

        raise ValueError(
            "Unexpected geometry types: "
            f"{sorted(unexpected_types)}"
        )

    print(
        "Geometry validation: PASSED"
    )

    return {
        "geometry_types":
            str(geom_types),

        "null_geometry":
            null_geometry,

        "empty_geometry":
            empty_geometry,

        "invalid_geometry":
            invalid_geometry,
    }


# ============================================================
# OVERLAP AUDIT
#
# Statistical zones should partition the municipality.
# Boundary touching is allowed.
# Positive-area overlap is not.
# ============================================================

def audit_polygon_overlaps(gdf):

    overlaps = []

    spatial_index = (
        gdf.sindex
    )

    for idx, row in (
        gdf.iterrows()
    ):

        geometry = (
            row.geometry
        )

        candidate_indices = (
            list(
                spatial_index.intersection(
                    geometry.bounds
                )
            )
        )

        for other_idx in candidate_indices:

            if other_idx <= idx:
                continue

            other = (
                gdf.loc[
                    other_idx
                ]
            )

            intersection = (
                geometry.intersection(
                    other.geometry
                )
            )

            if intersection.is_empty:
                continue

            overlap_area = (
                intersection.area
            )

            # Ignore normal shared borders.
            if overlap_area <= 1.0:
                continue

            overlaps.append(
                {
                    "zone_id_1":
                        row[
                            "zone_id"
                        ],

                    "zone_id_2":
                        other[
                            "zone_id"
                        ],

                    "overlap_area_m2":
                        overlap_area,
                }
            )

    overlap_df = (
        pd.DataFrame(
            overlaps
        )
    )

    if not overlap_df.empty:

        overlap_df.to_csv(
            AUDIT_DIR
            / "zoning_polygon_overlaps.csv",
            index=False,
        )

        raise ValueError(
            f"{len(overlap_df)} positive-area "
            "zone overlaps detected."
        )

    print(
        "Polygon overlap validation: PASSED"
    )

    return 0


# ============================================================
# SPATIAL ATTRIBUTES
# ============================================================

def add_spatial_attributes(gdf):

    data = gdf.copy()

    # --------------------------------------------------------
    # Polygon area
    #
    # EPSG:3003 is projected in metres.
    # --------------------------------------------------------

    data[
        "area_m2"
    ] = (
        data.geometry.area
    )

    data[
        "area_km2"
    ] = (
        data[
            "area_m2"
        ]
        / 1_000_000
    )

    # --------------------------------------------------------
    # Geometric centroid
    #
    # The exercise explicitly discusses centroid-based
    # zone representation, so centroid coordinates are
    # retained.
    # --------------------------------------------------------

    centroids = (
        data.geometry.centroid
    )

    data[
        "centroid_x"
    ] = (
        centroids.x
    )

    data[
        "centroid_y"
    ] = (
        centroids.y
    )

    # --------------------------------------------------------
    # Representative point
    #
    # Guaranteed to lie within each polygon.
    # Kept as a safer alternative for cartography.
    # --------------------------------------------------------

    representative = (
        data.geometry
        .representative_point()
    )

    data[
        "representative_x"
    ] = (
        representative.x
    )

    data[
        "representative_y"
    ] = (
        representative.y
    )

    # --------------------------------------------------------
    # Check whether centroid lies inside polygon
    # --------------------------------------------------------

    data[
        "centroid_inside"
    ] = [
        geom.covers(
            centroid
        )
        for geom, centroid
        in zip(
            data.geometry,
            centroids,
        )
    ]

    return (
        data,
        centroids,
        representative,
    )


# ============================================================
# MUNICIPAL FOOTPRINT SUMMARY
# ============================================================

def build_spatial_summary(gdf):

    total_area_km2 = (
        gdf[
            "area_km2"
        ]
        .sum()
    )

    union_geometry = (
        gdf.geometry.union_all()
    )

    union_area_km2 = (
        union_geometry.area
        / 1_000_000
    )

    minx, miny, maxx, maxy = (
        gdf.total_bounds
    )

    summary = {
        "zone_count":
            len(gdf),

        "crs":
            str(gdf.crs),

        "epsg":
            gdf.crs.to_epsg(),

        "total_polygon_area_km2":
            total_area_km2,

        "union_area_km2":
            union_area_km2,

        "mean_zone_area_km2":
            gdf[
                "area_km2"
            ].mean(),

        "median_zone_area_km2":
            gdf[
                "area_km2"
            ].median(),

        "min_zone_area_km2":
            gdf[
                "area_km2"
            ].min(),

        "max_zone_area_km2":
            gdf[
                "area_km2"
            ].max(),

        "centroids_inside":
            int(
                gdf[
                    "centroid_inside"
                ]
                .sum()
            ),

        "centroids_outside":
            int(
                (
                    ~gdf[
                        "centroid_inside"
                    ]
                )
                .sum()
            ),

        "bbox_min_x":
            minx,

        "bbox_min_y":
            miny,

        "bbox_max_x":
            maxx,

        "bbox_max_y":
            maxy,
    }

    return summary


# ============================================================
# CREATE POINT LAYERS
# ============================================================

def build_point_layers(
    zones,
    centroids,
    representative,
):

    attributes = [
        "zone_id",
        "zone_name",
        "area_km2",
    ]

    centroid_points = (
        zones[
            attributes
        ]
        .copy()
    )

    centroid_points = (
        gpd.GeoDataFrame(
            centroid_points,
            geometry=centroids,
            crs=zones.crs,
        )
    )

    representative_points = (
        zones[
            attributes
        ]
        .copy()
    )

    representative_points = (
        gpd.GeoDataFrame(
            representative_points,
            geometry=representative,
            crs=zones.crs,
        )
    )

    return (
        centroid_points,
        representative_points,
    )


# ============================================================
# SAVE CANONICAL ZONING
# ============================================================

def save_outputs(
    zones,
    centroid_points,
    representative_points,
    audit_summary,
):

    # Remove previous output so reruns cannot leave stale layers.
    if OUTPUT_GPKG.exists():

        OUTPUT_GPKG.unlink()

        print(
            f"Removed previous GeoPackage -> "
            f"{OUTPUT_GPKG}"
        )

    zones.to_file(
        OUTPUT_GPKG,
        layer="zones",
        driver="GPKG",
    )

    centroid_points.to_file(
        OUTPUT_GPKG,
        layer="zone_centroids",
        driver="GPKG",
    )

    representative_points.to_file(
        OUTPUT_GPKG,
        layer="zone_representative_points",
        driver="GPKG",
    )

    # --------------------------------------------------------
    # Human-readable zone dictionary
    # --------------------------------------------------------

    zone_dictionary = (
        zones[
            [
                "zone_id",
                "zone_name",
                "area_km2",
                "centroid_x",
                "centroid_y",
                "representative_x",
                "representative_y",
                "centroid_inside",
            ]
        ]
        .sort_values(
            "zone_id"
        )
    )

    zone_dictionary.to_csv(
        TABLE_DIR
        / "torino_zone_dictionary.csv",
        index=False,
    )

    pd.DataFrame(
        [
            audit_summary
        ]
    ).to_csv(
        AUDIT_DIR
        / "torino_zoning_audit_summary.csv",
        index=False,
    )

    print(
        f"Canonical zoning saved -> "
        f"{OUTPUT_GPKG}"
    )


# ============================================================
# READ-BACK VALIDATION
# ============================================================

def validate_saved_output():

    zones = gpd.read_file(
        OUTPUT_GPKG,
        layer="zones",
    )

    centroids = gpd.read_file(
        OUTPUT_GPKG,
        layer="zone_centroids",
    )

    representative = gpd.read_file(
        OUTPUT_GPKG,
        layer="zone_representative_points",
    )

    assert len(zones) == EXPECTED_ZONE_COUNT

    assert len(centroids) == EXPECTED_ZONE_COUNT

    assert len(representative) == EXPECTED_ZONE_COUNT

    assert (
        zones[
            "zone_id"
        ]
        .nunique()
        == EXPECTED_ZONE_COUNT
    )

    assert (
        zones.crs.to_epsg()
        == EXPECTED_CRS_EPSG
    )

    assert (
        centroids.crs.to_epsg()
        == EXPECTED_CRS_EPSG
    )

    assert (
        representative.crs.to_epsg()
        == EXPECTED_CRS_EPSG
    )

    print(
        "GeoPackage read-back validation: PASSED"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 105
    )

    print(
        "EXERCISE 2 — TORINO STATISTICAL ZONING AUDIT"
    )

    print(
        "=" * 105
    )

    raw = load_zoning()

    validate_schema(
        raw
    )

    zones = (
        standardize_attributes(
            raw
        )
    )

    attribute_audit = (
        audit_attributes(
            zones
        )
    )

    geometry_audit = (
        audit_geometry(
            zones
        )
    )

    overlap_count = (
        audit_polygon_overlaps(
            zones
        )
    )

    (
        zones,
        centroids,
        representative,
    ) = (
        add_spatial_attributes(
            zones
        )
    )

    spatial_summary = (
        build_spatial_summary(
            zones
        )
    )

    (
        centroid_points,
        representative_points,
    ) = (
        build_point_layers(
            zones,
            centroids,
            representative,
        )
    )

    audit_summary = {
        **attribute_audit,
        **geometry_audit,
        **spatial_summary,

        "positive_area_overlaps":
            overlap_count,

        "source_file":
            ZONE_FILE.name,
    }

    save_outputs(
        zones,
        centroid_points,
        representative_points,
        audit_summary,
    )

    validate_saved_output()

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print(
        "\n"
        + "-" * 105
    )

    print(
        "CANONICAL ZONING SUMMARY"
    )

    print(
        "-" * 105
    )

    print(
        f"Zones: "
        f"{len(zones)}"
    )

    print(
        f"CRS: "
        f"{zones.crs}"
    )

    print(
        f"EPSG: "
        f"{zones.crs.to_epsg()}"
    )

    print(
        "\nGeometry types:"
    )

    print(
        zones[
            "geometry"
        ]
        .geom_type
        .value_counts()
        .to_string()
    )

    print(
        "\nArea statistics [km²]:"
    )

    print(
        zones[
            "area_km2"
        ]
        .describe()
        .round(4)
        .to_string()
    )

    print(
        "\nMunicipal footprint:"
    )

    print(
        f"Sum polygon area: "
        f"{spatial_summary['total_polygon_area_km2']:.4f} km²"
    )

    print(
        f"Union area: "
        f"{spatial_summary['union_area_km2']:.4f} km²"
    )

    print(
        "\nCentroid validation:"
    )

    print(
        f"Inside/covers polygon: "
        f"{spatial_summary['centroids_inside']}"
    )

    print(
        f"Outside polygon: "
        f"{spatial_summary['centroids_outside']}"
    )

    print(
        "\nSpecial alphanumeric zone IDs:"
    )

    special_ids = zones.loc[
        zones[
            "zone_id"
        ].str.contains(
            r"[^0-9]",
            regex=True,
            na=False,
        ),
        [
            "zone_id",
            "zone_name",
        ],
    ]

    if special_ids.empty:

        print(
            "None"
        )

    else:

        print(
            special_ids.to_string(
                index=False
            )
        )

    print(
        "\nSmallest zones:"
    )

    print(
        zones[
            [
                "zone_id",
                "zone_name",
                "area_km2",
            ]
        ]
        .nsmallest(
            5,
            "area_km2",
        )
        .to_string(
            index=False
        )
    )

    print(
        "\nLargest zones:"
    )

    print(
        zones[
            [
                "zone_id",
                "zone_name",
                "area_km2",
            ]
        ]
        .nlargest(
            5,
            "area_km2",
        )
        .to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION:"
        "\n- Official statistical-zone IDs preserved as strings."
        "\n- No geometry repair was silently performed."
        "\n- Polygon validity checked."
        "\n- Positive-area overlaps checked."
        "\n- Areas calculated in native projected CRS."
        "\n- Both centroids and representative points retained."
        "\n- Canonical GeoPackage is ready for trip zoning."
    )


if __name__ == "__main__":
    main()