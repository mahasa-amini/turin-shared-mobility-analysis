from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ZONED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "trips_zoned"
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
    / "od"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "od"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_2"
    / "od"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


FILES = {
    "bird":
        ZONED_DIR
        / "bird_2024_zoned.parquet",

    "lime":
        ZONED_DIR
        / "lime_2024_zoned.parquet",

    "voi":
        ZONED_DIR
        / "voi_2024_zoned.parquet",
}


EXPECTED_VALID_OD = {
    "bird": 382533,
    "lime": 1193572,
    "voi": 105822,
}


EXPECTED_SYSTEM_VALID_OD = (
    sum(
        EXPECTED_VALID_OD.values()
    )
)


OPERATORS = [
    "bird",
    "lime",
    "voi",
]


# ============================================================
# LOAD ZONES
#
# Canonical zone order is taken from the official layer.
# This avoids lexicographic problems such as:
# 01, 02, ..., 09bis, ..., 17bis
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

    zones[
        "zone_id"
    ] = (
        zones[
            "zone_id"
        ]
        .astype("string")
    )

    assert len(zones) == 94

    assert (
        zones[
            "zone_id"
        ]
        .nunique()
        == 94
    )

    zone_order = (
        zones[
            "zone_id"
        ]
        .tolist()
    )

    zone_lookup = (
        zones[
            [
                "zone_id",
                "zone_name",
                "area_km2",
                "centroid_x",
                "centroid_y",
                "representative_x",
                "representative_y",
            ]
        ]
        .copy()
    )

    return (
        zones,
        zone_order,
        zone_lookup,
    )


# ============================================================
# LOAD VALID OD TRIPS
# ============================================================

def load_valid_od_trips(
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
        "origin_zone_id",
        "destination_zone_id",
        "valid_od_zone",
        "intra_zonal",
        "inter_zonal",
    ]

    df = pd.read_parquet(
        path,
        columns=columns,
    )

    df = df.loc[
        df[
            "valid_od_zone"
        ]
    ].copy()

    assert (
        len(df)
        ==
        EXPECTED_VALID_OD[
            operator
        ]
    )

    assert (
        df[
            "trip_uid"
        ]
        .is_unique
    )

    df[
        "origin_zone_id"
    ] = (
        df[
            "origin_zone_id"
        ]
        .astype("string")
    )

    df[
        "destination_zone_id"
    ] = (
        df[
            "destination_zone_id"
        ]
        .astype("string")
    )

    return df


# ============================================================
# VALIDATE ZONE REFERENCES
# ============================================================

def validate_zone_references(
    df,
    zone_order,
    operator,
):

    valid_zones = set(
        zone_order
    )

    origin_values = set(
        df[
            "origin_zone_id"
        ]
        .dropna()
        .unique()
    )

    destination_values = set(
        df[
            "destination_zone_id"
        ]
        .dropna()
        .unique()
    )

    invalid_origins = (
        origin_values
        -
        valid_zones
    )

    invalid_destinations = (
        destination_values
        -
        valid_zones
    )

    if invalid_origins:

        raise ValueError(
            f"{operator}: unknown origin zones: "
            f"{sorted(invalid_origins)}"
        )

    if invalid_destinations:

        raise ValueError(
            f"{operator}: unknown destination zones: "
            f"{sorted(invalid_destinations)}"
        )


# ============================================================
# OPERATOR LONG OD TABLE
# ============================================================

def build_operator_od(
    df,
    operator,
    zone_lookup,
):

    od = (
        df.groupby(
            [
                "origin_zone_id",
                "destination_zone_id",
            ],
            as_index=False,
        )
        .agg(
            trips=(
                "trip_uid",
                "count",
            )
        )
    )

    od[
        "operator"
    ] = operator

    od[
        "year"
    ] = 2024

    od[
        "intra_zonal"
    ] = (
        od[
            "origin_zone_id"
        ]
        ==
        od[
            "destination_zone_id"
        ]
    )

    total_trips = (
        od[
            "trips"
        ]
        .sum()
    )

    od[
        "od_share_pct"
    ] = (
        od[
            "trips"
        ]
        /
        total_trips
        * 100
    )

    # --------------------------------------------------------
    # Origin and destination names
    # --------------------------------------------------------

    origin_lookup = (
        zone_lookup[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .rename(
            columns={
                "zone_id":
                    "origin_zone_id",

                "zone_name":
                    "origin_zone_name",
            }
        )
    )

    destination_lookup = (
        zone_lookup[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .rename(
            columns={
                "zone_id":
                    "destination_zone_id",

                "zone_name":
                    "destination_zone_name",
            }
        )
    )

    od = (
        od.merge(
            origin_lookup,
            on="origin_zone_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            destination_lookup,
            on="destination_zone_id",
            how="left",
            validate="many_to_one",
        )
    )

    # --------------------------------------------------------
    # Within-origin flow share
    #
    # Useful later for understanding where trips from each
    # origin are distributed.
    # --------------------------------------------------------

    origin_totals = (
        od.groupby(
            "origin_zone_id"
        )[
            "trips"
        ]
        .transform(
            "sum"
        )
    )

    od[
        "share_of_origin_production_pct"
    ] = (
        od[
            "trips"
        ]
        /
        origin_totals
        * 100
    )

    # --------------------------------------------------------
    # Within-destination flow share
    # --------------------------------------------------------

    destination_totals = (
        od.groupby(
            "destination_zone_id"
        )[
            "trips"
        ]
        .transform(
            "sum"
        )
    )

    od[
        "share_of_destination_attraction_pct"
    ] = (
        od[
            "trips"
        ]
        /
        destination_totals
        * 100
    )

    return od


# ============================================================
# SYSTEM LONG OD TABLE WITH OPERATOR BREAKDOWN
# ============================================================

def build_system_od(
    operator_od_tables,
    zone_lookup,
):

    stacked = pd.concat(
        operator_od_tables,
        ignore_index=True,
    )

    pivot = (
        stacked.pivot_table(
            index=[
                "origin_zone_id",
                "destination_zone_id",
            ],
            columns="operator",
            values="trips",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    pivot.columns.name = None

    for operator in OPERATORS:

        if operator not in pivot.columns:

            pivot[
                operator
            ] = 0

    pivot = pivot.rename(
        columns={
            "bird":
                "bird_trips",

            "lime":
                "lime_trips",

            "voi":
                "voi_trips",
        }
    )

    for col in [
        "bird_trips",
        "lime_trips",
        "voi_trips",
    ]:

        pivot[
            col
        ] = (
            pivot[
                col
            ]
            .astype("int64")
        )

    pivot[
        "system_trips"
    ] = (
        pivot[
            [
                "bird_trips",
                "lime_trips",
                "voi_trips",
            ]
        ]
        .sum(
            axis=1
        )
    )

    pivot[
        "operators_present"
    ] = (
        (
            pivot[
                [
                    "bird_trips",
                    "lime_trips",
                    "voi_trips",
                ]
            ]
            > 0
        )
        .sum(
            axis=1
        )
    )

    pivot[
        "intra_zonal"
    ] = (
        pivot[
            "origin_zone_id"
        ]
        ==
        pivot[
            "destination_zone_id"
        ]
    )

    pivot[
        "system_od_share_pct"
    ] = (
        pivot[
            "system_trips"
        ]
        /
        pivot[
            "system_trips"
        ].sum()
        * 100
    )

    # --------------------------------------------------------
    # Operator contribution within each OD pair
    # --------------------------------------------------------

    for operator in OPERATORS:

        col = (
            f"{operator}_trips"
        )

        pivot[
            f"{operator}_share_of_od_pct"
        ] = np.where(
            pivot[
                "system_trips"
            ] > 0,

            pivot[
                col
            ]
            /
            pivot[
                "system_trips"
            ]
            * 100,

            np.nan,
        )

    # --------------------------------------------------------
    # Names
    # --------------------------------------------------------

    origin_lookup = (
        zone_lookup[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .rename(
            columns={
                "zone_id":
                    "origin_zone_id",

                "zone_name":
                    "origin_zone_name",
            }
        )
    )

    destination_lookup = (
        zone_lookup[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .rename(
            columns={
                "zone_id":
                    "destination_zone_id",

                "zone_name":
                    "destination_zone_name",
            }
        )
    )

    pivot = (
        pivot.merge(
            origin_lookup,
            on="origin_zone_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            destination_lookup,
            on="destination_zone_id",
            how="left",
            validate="many_to_one",
        )
    )

    # --------------------------------------------------------
    # Origin production shares
    # --------------------------------------------------------

    origin_total = (
        pivot.groupby(
            "origin_zone_id"
        )[
            "system_trips"
        ]
        .transform(
            "sum"
        )
    )

    pivot[
        "share_of_origin_production_pct"
    ] = (
        pivot[
            "system_trips"
        ]
        /
        origin_total
        * 100
    )

    return pivot


# ============================================================
# SQUARE OD MATRIX
#
# Includes all 94 official zones as rows and columns,
# even when a zone has zero observed trips.
# ============================================================

def build_square_matrix(
    od,
    value_col,
    zone_order,
):

    matrix = (
        od.pivot_table(
            index="origin_zone_id",
            columns="destination_zone_id",
            values=value_col,
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(
            index=zone_order,
            columns=zone_order,
            fill_value=0,
        )
    )

    matrix.index.name = (
        "origin_zone_id"
    )

    matrix.columns.name = (
        "destination_zone_id"
    )

    matrix = matrix.astype(
        "int64"
    )

    return matrix


# ============================================================
# PRODUCTION / ATTRACTION
# ============================================================

def build_zone_intensity(
    od,
    value_col,
    zone_lookup,
    label,
):

    production = (
        od.groupby(
            "origin_zone_id"
        )[
            value_col
        ]
        .sum()
        .rename(
            "production_trips"
        )
    )

    attraction = (
        od.groupby(
            "destination_zone_id"
        )[
            value_col
        ]
        .sum()
        .rename(
            "attraction_trips"
        )
    )

    result = (
        zone_lookup[
            [
                "zone_id",
                "zone_name",
                "area_km2",
                "centroid_x",
                "centroid_y",
                "representative_x",
                "representative_y",
            ]
        ]
        .copy()
    )

    result = result.merge(
        production,
        left_on="zone_id",
        right_index=True,
        how="left",
    )

    result = result.merge(
        attraction,
        left_on="zone_id",
        right_index=True,
        how="left",
    )

    result[
        "production_trips"
    ] = (
        result[
            "production_trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    result[
        "attraction_trips"
    ] = (
        result[
            "attraction_trips"
        ]
        .fillna(0)
        .astype("int64")
    )

    total_trips = (
        result[
            "production_trips"
        ]
        .sum()
    )

    assert (
        total_trips
        ==
        result[
            "attraction_trips"
        ]
        .sum()
    )

    result[
        "production_share_pct"
    ] = (
        result[
            "production_trips"
        ]
        /
        total_trips
        * 100
    )

    result[
        "attraction_share_pct"
    ] = (
        result[
            "attraction_trips"
        ]
        /
        total_trips
        * 100
    )

    # Positive:
    # more trip destinations than origins.
    result[
        "net_attraction_trips"
    ] = (
        result[
            "attraction_trips"
        ]
        -
        result[
            "production_trips"
        ]
    )

    result[
        "production_density_trips_per_km2"
    ] = (
        result[
            "production_trips"
        ]
        /
        result[
            "area_km2"
        ]
    )

    result[
        "attraction_density_trips_per_km2"
    ] = (
        result[
            "attraction_trips"
        ]
        /
        result[
            "area_km2"
        ]
    )

    result[
        "analysis_scope"
    ] = label

    return result


# ============================================================
# CONCENTRATION
# ============================================================

def concentration_statistics(
    od,
    value_col,
    scope,
):

    records = []

    subsets = {
        "all_od_pairs":
            od.copy(),

        "inter_zonal_only":
            od.loc[
                ~od[
                    "intra_zonal"
                ]
            ].copy(),
    }

    for pair_scope, data in (
        subsets.items()
    ):

        data = (
            data.loc[
                data[
                    value_col
                ] > 0
            ]
            .sort_values(
                value_col,
                ascending=False,
            )
            .copy()
        )

        total = (
            data[
                value_col
            ]
            .sum()
        )

        shares = (
            data[
                value_col
            ]
            /
            total
        )

        hhi = (
            shares.pow(2)
            .sum()
        )

        row = {
            "analysis_scope":
                scope,

            "pair_scope":
                pair_scope,

            "total_trips":
                int(total),

            "active_od_pairs":
                len(data),

            "hhi_od_pair":
                hhi,
        }

        for k in [
            1,
            5,
            10,
            20,
            50,
            100,
        ]:

            top_k = (
                data.head(k)[
                    value_col
                ]
                .sum()
            )

            row[
                f"top_{k}_pair_share_pct"
            ] = (
                top_k
                /
                total
                * 100
            )

        records.append(
            row
        )

    return records


# ============================================================
# STRUCTURAL SUMMARY
# ============================================================

def build_structural_summary(
    od,
    value_col,
    scope,
    zone_count=94,
):

    total = int(
        od[
            value_col
        ].sum()
    )

    intra = int(
        od.loc[
            od[
                "intra_zonal"
            ],
            value_col,
        ].sum()
    )

    inter = (
        total - intra
    )

    active_origin = (
        od.loc[
            od[
                value_col
            ] > 0,
            "origin_zone_id",
        ]
        .nunique()
    )

    active_destination = (
        od.loc[
            od[
                value_col
            ] > 0,
            "destination_zone_id",
        ]
        .nunique()
    )

    active_pairs = int(
        (
            od[
                value_col
            ] > 0
        )
        .sum()
    )

    active_inter_pairs = int(
        (
            (
                od[
                    value_col
                ] > 0
            )
            &
            (
                ~od[
                    "intra_zonal"
                ]
            )
        )
        .sum()
    )

    all_possible_pairs = (
        zone_count
        *
        zone_count
    )

    all_possible_inter_pairs = (
        zone_count
        *
        (
            zone_count
            - 1
        )
    )

    return {
        "analysis_scope":
            scope,

        "total_valid_od_trips":
            total,

        "intra_zonal_trips":
            intra,

        "inter_zonal_trips":
            inter,

        "intra_zonal_share_pct":
            (
                intra
                /
                total
                * 100
            ),

        "active_origin_zones":
            int(
                active_origin
            ),

        "active_destination_zones":
            int(
                active_destination
            ),

        "active_od_pairs":
            active_pairs,

        "active_interzonal_pairs":
            active_inter_pairs,

        "od_matrix_density_pct":
            (
                active_pairs
                /
                all_possible_pairs
                * 100
            ),

        "interzonal_matrix_density_pct":
            (
                active_inter_pairs
                /
                all_possible_inter_pairs
                * 100
            ),
    }


# ============================================================
# TOP FLOW TABLE
# ============================================================

def build_top_flows(
    od,
    value_col,
    scope,
    n=50,
):

    result = (
        od.loc[
            ~od[
                "intra_zonal"
            ]
        ]
        .sort_values(
            value_col,
            ascending=False,
        )
        .head(
            n
        )
        .copy()
    )

    result.insert(
        0,
        "rank",
        np.arange(
            1,
            len(result) + 1,
        )
    )

    result[
        "analysis_scope"
    ] = scope

    return result


# ============================================================
# TOP INTRA-ZONAL TABLE
# ============================================================

def build_top_intrazonal(
    od,
    value_col,
    scope,
):

    result = (
        od.loc[
            od[
                "intra_zonal"
            ]
        ]
        .sort_values(
            value_col,
            ascending=False,
        )
        .copy()
    )

    result.insert(
        0,
        "rank",
        np.arange(
            1,
            len(result) + 1,
        )
    )

    result[
        "analysis_scope"
    ] = scope

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 115
    )

    print(
        "EXERCISE 2 — 2024 ORIGIN-DESTINATION MATRICES"
    )

    print(
        "=" * 115
    )

    (
        zones,
        zone_order,
        zone_lookup,
    ) = load_zones()

    operator_trip_tables = {}

    operator_od_tables = {}

    # ========================================================
    # OPERATOR OD
    # ========================================================

    for operator in OPERATORS:

        print(
            f"\nBuilding {operator.upper()} OD..."
        )

        trips = (
            load_valid_od_trips(
                operator
            )
        )

        validate_zone_references(
            trips,
            zone_order,
            operator,
        )

        od = (
            build_operator_od(
                trips,
                operator,
                zone_lookup,
            )
        )

        assert (
            int(
                od[
                    "trips"
                ].sum()
            )
            ==
            EXPECTED_VALID_OD[
                operator
            ]
        )

        operator_trip_tables[
            operator
        ] = trips

        operator_od_tables[
            operator
        ] = od

        # ----------------------------------------------------
        # Save long format
        # ----------------------------------------------------

        od.to_csv(
            TABLE_DIR
            / f"od_{operator}_2024_long.csv",
            index=False,
        )

        od.to_parquet(
            OUTPUT_DIR
            / f"od_{operator}_2024_long.parquet",
            index=False,
        )

        # ----------------------------------------------------
        # Square 94 × 94
        # ----------------------------------------------------

        matrix = (
            build_square_matrix(
                od,
                value_col="trips",
                zone_order=zone_order,
            )
        )

        assert (
            matrix.shape
            ==
            (
                94,
                94,
            )
        )

        assert (
            int(
                matrix.to_numpy()
                .sum()
            )
            ==
            EXPECTED_VALID_OD[
                operator
            ]
        )

        matrix.to_csv(
            TABLE_DIR
            / f"od_matrix_{operator}_2024.csv"
        )

    # ========================================================
    # SYSTEM OD
    # ========================================================

    print(
        "\nBuilding pooled SYSTEM OD..."
    )

    system_od = (
        build_system_od(
            list(
                operator_od_tables.values()
            ),
            zone_lookup,
        )
    )

    assert (
        int(
            system_od[
                "system_trips"
            ].sum()
        )
        ==
        EXPECTED_SYSTEM_VALID_OD
    )

    system_od.to_csv(
        TABLE_DIR
        / "od_system_2024_long.csv",
        index=False,
    )

    system_od.to_parquet(
        OUTPUT_DIR
        / "od_system_2024_long.parquet",
        index=False,
    )

    system_matrix = (
        build_square_matrix(
            system_od,
            value_col="system_trips",
            zone_order=zone_order,
        )
    )

    assert (
        system_matrix.shape
        ==
        (
            94,
            94,
        )
    )

    assert (
        int(
            system_matrix
            .to_numpy()
            .sum()
        )
        ==
        EXPECTED_SYSTEM_VALID_OD
    )

    system_matrix.to_csv(
        TABLE_DIR
        / "od_matrix_system_2024.csv"
    )

    # ========================================================
    # PRODUCTION / ATTRACTION
    # ========================================================

    intensity_tables = []

    for operator in OPERATORS:

        intensity = (
            build_zone_intensity(
                operator_od_tables[
                    operator
                ],
                value_col="trips",
                zone_lookup=zone_lookup,
                label=operator,
            )
        )

        intensity_tables.append(
            intensity
        )

        intensity.to_csv(
            TABLE_DIR
            / f"zone_production_attraction_{operator}_2024.csv",
            index=False,
        )

    system_intensity = (
        build_zone_intensity(
            system_od,
            value_col="system_trips",
            zone_lookup=zone_lookup,
            label="system",
        )
    )

    system_intensity.to_csv(
        TABLE_DIR
        / "zone_production_attraction_system_2024.csv",
        index=False,
    )

    # ========================================================
    # STRUCTURAL SUMMARY
    # ========================================================

    structural_records = []

    concentration_records = []

    top_flow_tables = []

    top_intra_tables = []

    for operator in OPERATORS:

        od = (
            operator_od_tables[
                operator
            ]
        )

        structural_records.append(
            build_structural_summary(
                od,
                value_col="trips",
                scope=operator,
            )
        )

        concentration_records.extend(
            concentration_statistics(
                od,
                value_col="trips",
                scope=operator,
            )
        )

        top_flow_tables.append(
            build_top_flows(
                od,
                value_col="trips",
                scope=operator,
                n=50,
            )
        )

        top_intra_tables.append(
            build_top_intrazonal(
                od,
                value_col="trips",
                scope=operator,
            )
        )

    # SYSTEM
    structural_records.append(
        build_structural_summary(
            system_od,
            value_col="system_trips",
            scope="system",
        )
    )

    concentration_records.extend(
        concentration_statistics(
            system_od,
            value_col="system_trips",
            scope="system",
        )
    )

    top_flow_tables.append(
        build_top_flows(
            system_od,
            value_col="system_trips",
            scope="system",
            n=50,
        )
    )

    top_intra_tables.append(
        build_top_intrazonal(
            system_od,
            value_col="system_trips",
            scope="system",
        )
    )

    structural = pd.DataFrame(
        structural_records
    )

    concentration = pd.DataFrame(
        concentration_records
    )

    top_flows = pd.concat(
        top_flow_tables,
        ignore_index=True,
    )

    top_intra = pd.concat(
        top_intra_tables,
        ignore_index=True,
    )

    structural.to_csv(
        TABLE_DIR
        / "od_structural_summary_2024.csv",
        index=False,
    )

    concentration.to_csv(
        TABLE_DIR
        / "od_concentration_summary_2024.csv",
        index=False,
    )

    top_flows.to_csv(
        TABLE_DIR
        / "top_50_interzonal_od_flows_2024.csv",
        index=False,
    )

    top_intra.to_csv(
        TABLE_DIR
        / "intra_zonal_flows_2024.csv",
        index=False,
    )

    # ========================================================
    # SYSTEM TOP PRODUCTION / ATTRACTION
    # ========================================================

    system_top_production = (
        system_intensity
        .sort_values(
            "production_trips",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    system_top_attraction = (
        system_intensity
        .sort_values(
            "attraction_trips",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    system_top_production.to_csv(
        TABLE_DIR
        / "top_15_system_origin_zones_2024.csv",
        index=False,
    )

    system_top_attraction.to_csv(
        TABLE_DIR
        / "top_15_system_destination_zones_2024.csv",
        index=False,
    )

    # ========================================================
    # TERMINAL
    # ========================================================

    pd.set_option(
        "display.max_columns",
        None
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "OD STRUCTURAL SUMMARY"
    )

    print(
        "=" * 115
    )

    display_structural = (
        structural.copy()
    )

    for col in [
        "intra_zonal_share_pct",
        "od_matrix_density_pct",
        "interzonal_matrix_density_pct",
    ]:

        display_structural[
            col
        ] = (
            display_structural[
                col
            ]
            .round(2)
        )

    print(
        display_structural.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "OD CONCENTRATION"
    )

    print(
        "=" * 115
    )

    display_concentration = (
        concentration.copy()
    )

    percentage_cols = [
        c
        for c in display_concentration.columns
        if c.endswith(
            "_pct"
        )
    ]

    for col in percentage_cols:

        display_concentration[
            col
        ] = (
            display_concentration[
                col
            ]
            .round(2)
        )

    display_concentration[
        "hhi_od_pair"
    ] = (
        display_concentration[
            "hhi_od_pair"
        ]
        .round(5)
    )

    print(
        display_concentration.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP 15 SYSTEM INTER-ZONAL FLOWS"
    )

    print(
        "=" * 115
    )

    system_top_flows = (
        top_flows.loc[
            top_flows[
                "analysis_scope"
            ] == "system"
        ]
        .head(15)
        .copy()
    )

    display_cols = [
        "rank",
        "origin_zone_id",
        "origin_zone_name",
        "destination_zone_id",
        "destination_zone_name",
        "system_trips",
        "bird_trips",
        "lime_trips",
        "voi_trips",
        "operators_present",
    ]

    print(
        system_top_flows[
            display_cols
        ].to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP 10 SYSTEM ORIGIN ZONES"
    )

    print(
        "=" * 115
    )

    print(
        system_top_production[
            [
                "zone_id",
                "zone_name",
                "production_trips",
                "production_share_pct",
                "production_density_trips_per_km2",
            ]
        ]
        .head(10)
        .round(
            {
                "production_share_pct":
                    2,

                "production_density_trips_per_km2":
                    1,
            }
        )
        .to_string(
            index=False
        )
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP 10 SYSTEM DESTINATION ZONES"
    )

    print(
        "=" * 115
    )

    print(
        system_top_attraction[
            [
                "zone_id",
                "zone_name",
                "attraction_trips",
                "attraction_share_pct",
                "attraction_density_trips_per_km2",
            ]
        ]
        .head(10)
        .round(
            {
                "attraction_share_pct":
                    2,

                "attraction_density_trips_per_km2":
                    1,
            }
        )
        .to_string(
            index=False
        )
    )

    print(
        "\nVALIDATION:"
        "\n- All matrices use the 94 official statistical zones."
        "\n- Matrix rows = origins; columns = destinations."
        "\n- Zero-flow zones/pairs remain represented in square matrices."
        "\n- Operator matrices reconcile exactly with valid zoned-trip counts."
        "\n- System matrix equals Bird + Lime + VOI."
        "\n- Intra-zonal trips remain on the matrix diagonal."
        "\n- Long-format OD tables are ready for GIS flow construction."
        "\n- Production and attraction are calculated independently."
        "\n- Top-flow ranking shown in terminal excludes intra-zonal trips."
    )

    print(
        "\nSaved outputs -> "
        f"{TABLE_DIR}"
    )


if __name__ == "__main__":
    main()