from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


# ==================================================================================================
# PATHS
# ==================================================================================================

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
    / "temporal_od"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "temporal_od"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "audit"
    / "exercise_2"
    / "temporal_od"
)

for directory in [
    OUTPUT_DIR,
    TABLE_DIR,
    AUDIT_DIR,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


FILES = {
    "bird": ZONED_DIR / "bird_2024_zoned.parquet",
    "lime": ZONED_DIR / "lime_2024_zoned.parquet",
    "voi": ZONED_DIR / "voi_2024_zoned.parquet",
}


OPERATORS = [
    "bird",
    "lime",
    "voi",
]


# ==================================================================================================
# COMMON TEMPORAL WINDOW
# ==================================================================================================

START_DATE = pd.Timestamp("2024-02-01")
END_DATE = pd.Timestamp("2024-12-31")

# Feb 1-Dec 31, 2024
CALENDAR_DAYS = 335


# ==================================================================================================
# TEMPORAL PERIOD DEFINITIONS
#
# Conventional transport periods:
# AM peak     = 07:00-09:59
# PM peak     = 16:00-19:59
#
# Empirical scooter peak:
# 15:00-20:59, obtained from Exercise 1.
# ==================================================================================================

ALL_HOURS = set(range(24))


CONVENTIONAL_PERIOD_HOURS = {
    "AM peak": {
        7,
        8,
        9,
    },

    "PM peak": {
        16,
        17,
        18,
        19,
    },

    "Off-peak": (
        ALL_HOURS
        - {
            7,
            8,
            9,
            16,
            17,
            18,
            19,
        }
    ),
}


CONVENTIONAL_HOURS_PER_DAY = {
    period: len(hours)
    for period, hours
    in CONVENTIONAL_PERIOD_HOURS.items()
}


EMPIRICAL_PERIOD_HOURS = {
    "Empirical peak": {
        15,
        16,
        17,
        18,
        19,
        20,
    },

    "Empirical off-peak": (
        ALL_HOURS
        - {
            15,
            16,
            17,
            18,
            19,
            20,
        }
    ),
}


EMPIRICAL_HOURS_PER_DAY = {
    period: len(hours)
    for period, hours
    in EMPIRICAL_PERIOD_HOURS.items()
}


# ==================================================================================================
# LOAD OFFICIAL ZONE ORDER
# ==================================================================================================

def load_zone_order():

    zones = gpd.read_file(
        ZONE_GPKG,
        layer="zones",
    )

    assert len(zones) == 94, (
        f"Expected 94 official zones, found {len(zones)}."
    )

    zones["zone_id"] = (
        zones["zone_id"]
        .astype("string")
    )

    assert zones["zone_id"].nunique() == 94

    return (
        zones["zone_id"]
        .tolist()
    )


# ==================================================================================================
# TIMESTAMP NORMALIZATION
#
# start_time_local is already local Torino time.
# If timezone information is retained in Parquet, we remove
# timezone metadata while preserving local wall-clock time.
# ==================================================================================================

def local_timestamp_without_timezone(
    series,
):

    ts = pd.to_datetime(
        series,
        errors="coerce",
    )

    try:

        timezone = ts.dt.tz

    except AttributeError:

        timezone = None

    if timezone is not None:

        ts = ts.dt.tz_localize(
            None
        )

    return ts


# ==================================================================================================
# LOAD OPERATOR
# ==================================================================================================

def load_operator(
    operator,
):

    path = FILES[
        operator
    ]

    if not path.exists():

        raise FileNotFoundError(
            f"Missing zoned dataset: {path}"
        )

    columns = [
        "operator",
        "trip_uid",
        "source_period",
        "start_time_local",
        "valid_temporal_detail",
        "valid_od_zone",
        "origin_zone_id",
        "destination_zone_id",
    ]

    df = pd.read_parquet(
        path,
        columns=columns,
    )

    # ----------------------------------------------------------------------------------------------
    # Timestamp
    # ----------------------------------------------------------------------------------------------

    ts = (
        local_timestamp_without_timezone(
            df["start_time_local"]
        )
    )

    df["local_timestamp"] = ts

    df["local_date"] = (
        ts.dt.normalize()
    )

    df["hour"] = (
        ts.dt.hour
    )

    # ----------------------------------------------------------------------------------------------
    # Common detailed-time analysis population
    # ----------------------------------------------------------------------------------------------

    keep = (
        df["valid_od_zone"]
        &
        df["valid_temporal_detail"]
        &
        df["local_date"].between(
            START_DATE,
            END_DATE,
            inclusive="both",
        )
    )

    data = (
        df.loc[
            keep
        ]
        .copy()
    )

    # ----------------------------------------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------------------------------------

    assert (
        data["local_timestamp"]
        .notna()
        .all()
    )

    assert (
        data["origin_zone_id"]
        .notna()
        .all()
    )

    assert (
        data["destination_zone_id"]
        .notna()
        .all()
    )

    assert (
        data["trip_uid"]
        .notna()
        .all()
    )

    assert (
        data["trip_uid"]
        .is_unique
    )

    assert (
        data["hour"]
        .between(
            0,
            23,
        )
        .all()
    )

    data["origin_zone_id"] = (
        data["origin_zone_id"]
        .astype("string")
    )

    data["destination_zone_id"] = (
        data["destination_zone_id"]
        .astype("string")
    )

    # ==============================================================================================
    # CONVENTIONAL PERIOD CLASSIFICATION
    # ==============================================================================================

    data["conventional_period"] = (
        "Off-peak"
    )

    data.loc[
        data["hour"].isin(
            CONVENTIONAL_PERIOD_HOURS[
                "AM peak"
            ]
        ),
        "conventional_period",
    ] = "AM peak"

    data.loc[
        data["hour"].isin(
            CONVENTIONAL_PERIOD_HOURS[
                "PM peak"
            ]
        ),
        "conventional_period",
    ] = "PM peak"

    # ==============================================================================================
    # EMPIRICAL PERIOD CLASSIFICATION
    # ==============================================================================================

    data["empirical_period"] = np.where(
        data["hour"].isin(
            EMPIRICAL_PERIOD_HOURS[
                "Empirical peak"
            ]
        ),
        "Empirical peak",
        "Empirical off-peak",
    )

    return data


# ==================================================================================================
# OPERATOR LONG-FORM OD
# ==================================================================================================

def build_long_od(
    data,
    period_col,
):

    od = (
        data.groupby(
            [
                "operator",
                period_col,
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

    od["intra_zonal"] = (
        od["origin_zone_id"]
        ==
        od["destination_zone_id"]
    )

    return od


# ==================================================================================================
# SYSTEM LONG-FORM OD
# ==================================================================================================

def build_system_od(
    data,
    period_col,
):

    od = (
        data.groupby(
            [
                period_col,
                "origin_zone_id",
                "destination_zone_id",
            ],
            as_index=False,
        )
        .agg(
            system_trips=(
                "trip_uid",
                "count",
            )
        )
    )

    od["intra_zonal"] = (
        od["origin_zone_id"]
        ==
        od["destination_zone_id"]
    )

    return od


# ==================================================================================================
# PERIOD SUMMARY
#
# IMPORTANT:
# od_density_pct is PERIOD-AGGREGATED density.
#
# AM, PM, and off-peak contain different numbers of clock hours,
# therefore this density must NOT be interpreted directly as a
# normalized comparison of network breadth.
#
# mean_active_od_pairs_per_clock_hour below provides the
# exposure-aware comparison.
# ==================================================================================================

def summarize_periods(
    data,
    period_col,
    hours_per_day,
    analysis_family,
):

    rows = []

    scopes = (
        [
            (
                operator,
                data.loc[
                    data["operator"]
                    == operator
                ],
            )
            for operator
            in OPERATORS
        ]
        +
        [
            (
                "system",
                data,
            )
        ]
    )

    for scope, scope_data in scopes:

        for period, period_data in (
            scope_data.groupby(
                period_col
            )
        ):

            hours = (
                hours_per_day[
                    period
                ]
            )

            trips = len(
                period_data
            )

            intra = int(
                (
                    period_data["origin_zone_id"]
                    ==
                    period_data["destination_zone_id"]
                )
                .sum()
            )

            active_pairs = (
                period_data[
                    [
                        "origin_zone_id",
                        "destination_zone_id",
                    ]
                ]
                .drop_duplicates()
                .shape[0]
            )

            rows.append(
                {
                    "analysis_family":
                        analysis_family,

                    "scope":
                        scope,

                    "period":
                        period,

                    "hours_per_day":
                        hours,

                    "calendar_days":
                        CALENDAR_DAYS,

                    "available_clock_hours":
                        (
                            hours
                            *
                            CALENDAR_DAYS
                        ),

                    "trips":
                        trips,

                    "mean_trips_per_day":
                        (
                            trips
                            /
                            CALENDAR_DAYS
                        ),

                    "mean_trips_per_clock_hour":
                        (
                            trips
                            /
                            (
                                hours
                                *
                                CALENDAR_DAYS
                            )
                        ),

                    "intra_zonal_trips":
                        intra,

                    "intra_zonal_share_pct":
                        (
                            intra
                            /
                            trips
                            * 100
                            if trips > 0
                            else np.nan
                        ),

                    "active_od_pairs":
                        active_pairs,

                    "od_density_pct":
                        (
                            active_pairs
                            /
                            (
                                94
                                *
                                94
                            )
                            * 100
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


# ==================================================================================================
# HOUR-NORMALIZED NETWORK BREADTH
#
# Raw period-level active OD pairs are affected by the number
# of constituent hours.
#
# Example:
# Off-peak contains 17 hours while AM peak contains 3 hours.
#
# Therefore we calculate the number of distinct OD pairs
# separately for each clock-hour and average across the hours
# belonging to each temporal period.
# ==================================================================================================

def build_hour_normalized_breadth(
    data,
    period_col,
    period_hour_map,
    analysis_family,
):

    rows = []

    scopes = (
        [
            (
                operator,
                data.loc[
                    data["operator"]
                    == operator
                ],
            )
            for operator
            in OPERATORS
        ]
        +
        [
            (
                "system",
                data,
            )
        ]
    )

    for scope, scope_data in scopes:

        hourly_pair_counts = (
            scope_data.groupby(
                [
                    period_col,
                    "hour",
                ]
            )
            .apply(
                lambda x:
                x[
                    [
                        "origin_zone_id",
                        "destination_zone_id",
                    ]
                ]
                .drop_duplicates()
                .shape[0],
                include_groups=False,
            )
            .rename(
                "active_od_pairs"
            )
            .reset_index()
        )

        for period, hours in (
            period_hour_map.items()
        ):

            expected_hours = sorted(
                hours
            )

            current = (
                hourly_pair_counts.loc[
                    hourly_pair_counts[
                        period_col
                    ] == period,
                    [
                        "hour",
                        "active_od_pairs",
                    ],
                ]
                .set_index(
                    "hour"
                )
                .reindex(
                    expected_hours,
                    fill_value=0,
                )
            )

            values = (
                current[
                    "active_od_pairs"
                ]
                .to_numpy(
                    dtype="float64"
                )
            )

            rows.append(
                {
                    "analysis_family":
                        analysis_family,

                    "scope":
                        scope,

                    "period":
                        period,

                    "constituent_clock_hours":
                        len(
                            expected_hours
                        ),

                    "mean_active_od_pairs_per_clock_hour":
                        values.mean(),

                    "median_active_od_pairs_per_clock_hour":
                        np.median(
                            values
                        ),

                    "min_active_od_pairs_per_clock_hour":
                        values.min(),

                    "max_active_od_pairs_per_clock_hour":
                        values.max(),
                }
            )

    return pd.DataFrame(
        rows
    )


# ==================================================================================================
# FLOW CONCENTRATION BY PERIOD
# ==================================================================================================

def concentration_by_period(
    system_od,
    period_col,
    value_col,
    analysis_family,
):

    records = []

    for period, group in (
        system_od.groupby(
            period_col
        )
    ):

        for pair_scope in [
            "all_od_pairs",
            "inter_zonal_only",
        ]:

            if (
                pair_scope
                ==
                "inter_zonal_only"
            ):

                data = (
                    group.loc[
                        ~group[
                            "intra_zonal"
                        ]
                    ]
                    .copy()
                )

            else:

                data = (
                    group.copy()
                )

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
            )

            total = (
                data[
                    value_col
                ]
                .sum()
            )

            if total == 0:

                continue

            shares = (
                data[
                    value_col
                ]
                /
                total
            )

            row = {
                "analysis_family":
                    analysis_family,

                "period":
                    period,

                "pair_scope":
                    pair_scope,

                "trips":
                    int(
                        total
                    ),

                "active_od_pairs":
                    len(
                        data
                    ),

                "hhi":
                    shares.pow(
                        2
                    ).sum(),
            }

            for k in [
                10,
                20,
                50,
                100,
                200,
            ]:

                row[
                    f"top_{k}_share_pct"
                ] = (
                    data.head(
                        k
                    )[
                        value_col
                    ]
                    .sum()
                    /
                    total
                    * 100
                )

            records.append(
                row
            )

    return pd.DataFrame(
        records
    )


# ==================================================================================================
# TOP FLOWS BY PERIOD
# ==================================================================================================

def top_flows_by_period(
    system_od,
    period_col,
    value_col,
    analysis_family,
    n=50,
):

    outputs = []

    for period, group in (
        system_od.groupby(
            period_col
        )
    ):

        top = (
            group.loc[
                ~group[
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

        top.insert(
            0,
            "rank",
            np.arange(
                1,
                len(top) + 1,
            )
        )

        top[
            "analysis_family"
        ] = (
            analysis_family
        )

        outputs.append(
            top
        )

    return pd.concat(
        outputs,
        ignore_index=True,
    )


# ==================================================================================================
# HOURLY SYSTEM OD
#
# Provides 24 separate system-wide OD structures.
# ==================================================================================================

def build_hourly_system_od(
    data,
):

    hourly = (
        data.groupby(
            [
                "hour",
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

    hourly[
        "intra_zonal"
    ] = (
        hourly[
            "origin_zone_id"
        ]
        ==
        hourly[
            "destination_zone_id"
        ]
    )

    return hourly


# ==================================================================================================
# HOURLY STRUCTURAL SUMMARY
# ==================================================================================================

def summarize_hourly_od(
    hourly,
):

    rows = []

    for hour, group in (
        hourly.groupby(
            "hour"
        )
    ):

        total = int(
            group[
                "trips"
            ].sum()
        )

        intra = int(
            group.loc[
                group[
                    "intra_zonal"
                ],
                "trips",
            ].sum()
        )

        active_pairs = (
            group.shape[
                0
            ]
        )

        sorted_group = (
            group.sort_values(
                "trips",
                ascending=False,
            )
        )

        rows.append(
            {
                "hour":
                    int(
                        hour
                    ),

                "trips":
                    total,

                "mean_system_trips_per_clock_hour":
                    (
                        total
                        /
                        CALENDAR_DAYS
                    ),

                "intra_zonal_trips":
                    intra,

                "intra_zonal_share_pct":
                    (
                        intra
                        /
                        total
                        * 100
                        if total > 0
                        else np.nan
                    ),

                "active_od_pairs":
                    active_pairs,

                "od_density_pct":
                    (
                        active_pairs
                        /
                        (
                            94
                            *
                            94
                        )
                        * 100
                    ),

                "top_20_flow_share_pct":
                    (
                        sorted_group
                        .head(
                            20
                        )[
                            "trips"
                        ]
                        .sum()
                        /
                        total
                        * 100
                        if total > 0
                        else np.nan
                    ),

                "top_100_flow_share_pct":
                    (
                        sorted_group
                        .head(
                            100
                        )[
                            "trips"
                        ]
                        .sum()
                        /
                        total
                        * 100
                        if total > 0
                        else np.nan
                    ),
            }
        )

    return (
        pd.DataFrame(
            rows
        )
        .sort_values(
            "hour"
        )
        .reset_index(
            drop=True
        )
    )


# ==================================================================================================
# DISTRIBUTION VECTOR
# ==================================================================================================

def build_distribution_vector(
    group,
    value_col,
    zone_order,
):

    index = pd.MultiIndex.from_product(
        [
            zone_order,
            zone_order,
        ],
        names=[
            "origin_zone_id",
            "destination_zone_id",
        ],
    )

    vector = (
        group.set_index(
            [
                "origin_zone_id",
                "destination_zone_id",
            ]
        )[
            value_col
        ]
        .reindex(
            index,
            fill_value=0,
        )
        .to_numpy(
            dtype="float64"
        )
    )

    total = (
        vector.sum()
    )

    if total > 0:

        vector = (
            vector
            /
            total
        )

    return vector


# ==================================================================================================
# COSINE SIMILARITY
#
# 1 = identical normalized OD distribution
# 0 = completely different vectors
#
# This compares spatial structure rather than raw trip volume.
# ==================================================================================================

def cosine_similarity(
    a,
    b,
):

    denominator = (
        np.linalg.norm(
            a
        )
        *
        np.linalg.norm(
            b
        )
    )

    if denominator == 0:

        return np.nan

    return float(
        np.dot(
            a,
            b,
        )
        /
        denominator
    )


# ==================================================================================================
# HOURLY COSINE SIMILARITY MATRIX
# ==================================================================================================

def build_hourly_similarity(
    hourly,
    zone_order,
):

    vectors = {}

    for hour in range(
        24
    ):

        group = (
            hourly.loc[
                hourly[
                    "hour"
                ] == hour
            ]
            .copy()
        )

        vectors[
            hour
        ] = (
            build_distribution_vector(
                group,
                "trips",
                zone_order,
            )
        )

    matrix = pd.DataFrame(
        index=range(
            24
        ),
        columns=range(
            24
        ),
        dtype="float64",
    )

    for hour_1 in range(
        24
    ):

        for hour_2 in range(
            24
        ):

            matrix.loc[
                hour_1,
                hour_2,
            ] = cosine_similarity(
                vectors[
                    hour_1
                ],
                vectors[
                    hour_2
                ],
            )

    matrix.index.name = (
        "hour"
    )

    matrix.columns.name = (
        "comparison_hour"
    )

    return matrix


# ==================================================================================================
# PERIOD-LEVEL COSINE SIMILARITY
#
# Calculates both:
#
# 1. all OD pairs
# 2. inter-zonal pairs only
# ==================================================================================================

def build_period_cosine_similarity(
    system_od,
    period_col,
    value_col,
    periods,
    zone_order,
    pair_scope,
    analysis_family,
):

    vectors = {}

    for period in periods:

        group = (
            system_od.loc[
                system_od[
                    period_col
                ] == period
            ]
            .copy()
        )

        if (
            pair_scope
            ==
            "inter_zonal_only"
        ):

            group = (
                group.loc[
                    ~group[
                        "intra_zonal"
                    ]
                ]
                .copy()
            )

        vectors[
            period
        ] = (
            build_distribution_vector(
                group,
                value_col,
                zone_order,
            )
        )

    rows = []

    for i, period_1 in enumerate(
        periods
    ):

        for period_2 in periods[
            i + 1:
        ]:

            similarity = (
                cosine_similarity(
                    vectors[
                        period_1
                    ],
                    vectors[
                        period_2
                    ],
                )
            )

            rows.append(
                {
                    "analysis_family":
                        analysis_family,

                    "pair_scope":
                        pair_scope,

                    "period_1":
                        period_1,

                    "period_2":
                        period_2,

                    "cosine_similarity":
                        similarity,
                }
            )

    return pd.DataFrame(
        rows
    )


# ==================================================================================================
# TOP-N OD PAIR SET
# ==================================================================================================

def top_pair_set(
    group,
    period_col,
    period,
    value_col,
    n,
):

    data = (
        group.loc[
            (
                group[
                    period_col
                ]
                == period
            )
            &
            (
                ~group[
                    "intra_zonal"
                ]
            )
        ]
        .sort_values(
            value_col,
            ascending=False,
        )
        .head(
            n
        )
    )

    return set(
        zip(
            data[
                "origin_zone_id"
            ],
            data[
                "destination_zone_id"
            ],
        )
    )


# ==================================================================================================
# TOP-N PERIOD OVERLAP
#
# Jaccard similarity =
#
# intersection / union
#
# This evaluates persistence of strongest corridors.
# ==================================================================================================

def build_period_overlap(
    system_od,
    period_col,
    value_col,
    periods,
    analysis_family,
    n=50,
):

    rows = []

    for i, period_1 in enumerate(
        periods
    ):

        for period_2 in periods[
            i + 1:
        ]:

            set_1 = (
                top_pair_set(
                    system_od,
                    period_col,
                    period_1,
                    value_col,
                    n,
                )
            )

            set_2 = (
                top_pair_set(
                    system_od,
                    period_col,
                    period_2,
                    value_col,
                    n,
                )
            )

            intersection = len(
                set_1
                &
                set_2
            )

            union = len(
                set_1
                |
                set_2
            )

            rows.append(
                {
                    "analysis_family":
                        analysis_family,

                    "period_1":
                        period_1,

                    "period_2":
                        period_2,

                    "top_n":
                        n,

                    "common_top_pairs":
                        intersection,

                    "jaccard_similarity":
                        (
                            intersection
                            /
                            union
                            if union > 0
                            else np.nan
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


# ==================================================================================================
# PERIOD RECONCILIATION VALIDATION
# ==================================================================================================

def validate_period_reconciliation(
    system,
):

    total = len(
        system
    )

    conventional_total = (
        system[
            "conventional_period"
        ]
        .notna()
        .sum()
    )

    empirical_total = (
        system[
            "empirical_period"
        ]
        .notna()
        .sum()
    )

    assert (
        conventional_total
        ==
        total
    )

    assert (
        empirical_total
        ==
        total
    )

    conventional_counts = (
        system[
            "conventional_period"
        ]
        .value_counts()
        .sum()
    )

    empirical_counts = (
        system[
            "empirical_period"
        ]
        .value_counts()
        .sum()
    )

    assert (
        conventional_counts
        ==
        total
    )

    assert (
        empirical_counts
        ==
        total
    )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    pd.set_option(
        "display.max_columns",
        None,
    )

    pd.set_option(
        "display.width",
        240,
    )

    pd.set_option(
        "display.max_colwidth",
        50,
    )

    print(
        "\n"
        + "=" * 115
    )

    print(
        "EXERCISE 2 — TEMPORAL ORIGIN-DESTINATION STRUCTURE"
    )

    print(
        "=" * 115
    )

    # ==============================================================================================
    # OFFICIAL ZONES
    # ==============================================================================================

    zone_order = (
        load_zone_order()
    )

    operator_tables = []

    coverage_rows = []

    # ==============================================================================================
    # LOAD OPERATORS
    # ==============================================================================================

    for operator in OPERATORS:

        print(
            f"Loading {operator.upper()}..."
        )

        data = (
            load_operator(
                operator
            )
        )

        operator_tables.append(
            data
        )

        coverage_rows.append(
            {
                "operator":
                    operator,

                "trips":
                    len(
                        data
                    ),

                "first_date":
                    data[
                        "local_date"
                    ].min(),

                "last_date":
                    data[
                        "local_date"
                    ].max(),

                "calendar_dates_with_trips":
                    data[
                        "local_date"
                    ].nunique(),
            }
        )

    system = pd.concat(
        operator_tables,
        ignore_index=True,
    )

    coverage = pd.DataFrame(
        coverage_rows
    )

    # ----------------------------------------------------------------------------------------------
    # Coverage validation
    # ----------------------------------------------------------------------------------------------

    assert (
        coverage[
            "calendar_dates_with_trips"
        ]
        ==
        CALENDAR_DAYS
    ).all()

    validate_period_reconciliation(
        system
    )

    coverage.to_csv(
        AUDIT_DIR
        / "temporal_od_coverage_2024.csv",
        index=False,
    )

    # ==============================================================================================
    # CONVENTIONAL PERIOD OD
    # ==============================================================================================

    conventional_operator_od = (
        build_long_od(
            system,
            "conventional_period",
        )
    )

    conventional_system_od = (
        build_system_od(
            system,
            "conventional_period",
        )
    )

    conventional_summary = (
        summarize_periods(
            system,
            period_col="conventional_period",
            hours_per_day=CONVENTIONAL_HOURS_PER_DAY,
            analysis_family="conventional",
        )
    )

    conventional_breadth = (
        build_hour_normalized_breadth(
            system,
            period_col="conventional_period",
            period_hour_map=CONVENTIONAL_PERIOD_HOURS,
            analysis_family="conventional",
        )
    )

    conventional_summary = (
        conventional_summary.merge(
            conventional_breadth,
            on=[
                "analysis_family",
                "scope",
                "period",
            ],
            how="left",
            validate="one_to_one",
        )
    )

    conventional_concentration = (
        concentration_by_period(
            conventional_system_od,
            period_col="conventional_period",
            value_col="system_trips",
            analysis_family="conventional",
        )
    )

    conventional_top = (
        top_flows_by_period(
            conventional_system_od,
            period_col="conventional_period",
            value_col="system_trips",
            analysis_family="conventional",
            n=50,
        )
    )

    conventional_overlap = (
        build_period_overlap(
            conventional_system_od,
            period_col="conventional_period",
            value_col="system_trips",
            periods=[
                "AM peak",
                "PM peak",
                "Off-peak",
            ],
            analysis_family="conventional",
            n=50,
        )
    )

    # ==============================================================================================
    # EMPIRICAL PERIOD OD
    # ==============================================================================================

    empirical_operator_od = (
        build_long_od(
            system,
            "empirical_period",
        )
    )

    empirical_system_od = (
        build_system_od(
            system,
            "empirical_period",
        )
    )

    empirical_summary = (
        summarize_periods(
            system,
            period_col="empirical_period",
            hours_per_day=EMPIRICAL_HOURS_PER_DAY,
            analysis_family="empirical",
        )
    )

    empirical_breadth = (
        build_hour_normalized_breadth(
            system,
            period_col="empirical_period",
            period_hour_map=EMPIRICAL_PERIOD_HOURS,
            analysis_family="empirical",
        )
    )

    empirical_summary = (
        empirical_summary.merge(
            empirical_breadth,
            on=[
                "analysis_family",
                "scope",
                "period",
            ],
            how="left",
            validate="one_to_one",
        )
    )

    empirical_concentration = (
        concentration_by_period(
            empirical_system_od,
            period_col="empirical_period",
            value_col="system_trips",
            analysis_family="empirical",
        )
    )

    empirical_top = (
        top_flows_by_period(
            empirical_system_od,
            period_col="empirical_period",
            value_col="system_trips",
            analysis_family="empirical",
            n=50,
        )
    )

    empirical_overlap = (
        build_period_overlap(
            empirical_system_od,
            period_col="empirical_period",
            value_col="system_trips",
            periods=[
                "Empirical peak",
                "Empirical off-peak",
            ],
            analysis_family="empirical",
            n=50,
        )
    )

    # ==============================================================================================
    # HOURLY SYSTEM OD
    # ==============================================================================================

    hourly = (
        build_hourly_system_od(
            system
        )
    )

    hourly_summary = (
        summarize_hourly_od(
            hourly
        )
    )

    hourly_similarity = (
        build_hourly_similarity(
            hourly,
            zone_order,
        )
    )

    # ==============================================================================================
    # PERIOD COSINE SIMILARITY
    # ==============================================================================================

    conventional_cosine_all = (
        build_period_cosine_similarity(
            conventional_system_od,
            period_col="conventional_period",
            value_col="system_trips",
            periods=[
                "AM peak",
                "PM peak",
                "Off-peak",
            ],
            zone_order=zone_order,
            pair_scope="all_od_pairs",
            analysis_family="conventional",
        )
    )

    conventional_cosine_inter = (
        build_period_cosine_similarity(
            conventional_system_od,
            period_col="conventional_period",
            value_col="system_trips",
            periods=[
                "AM peak",
                "PM peak",
                "Off-peak",
            ],
            zone_order=zone_order,
            pair_scope="inter_zonal_only",
            analysis_family="conventional",
        )
    )

    empirical_cosine_all = (
        build_period_cosine_similarity(
            empirical_system_od,
            period_col="empirical_period",
            value_col="system_trips",
            periods=[
                "Empirical peak",
                "Empirical off-peak",
            ],
            zone_order=zone_order,
            pair_scope="all_od_pairs",
            analysis_family="empirical",
        )
    )

    empirical_cosine_inter = (
        build_period_cosine_similarity(
            empirical_system_od,
            period_col="empirical_period",
            value_col="system_trips",
            periods=[
                "Empirical peak",
                "Empirical off-peak",
            ],
            zone_order=zone_order,
            pair_scope="inter_zonal_only",
            analysis_family="empirical",
        )
    )

    period_cosine = pd.concat(
        [
            conventional_cosine_all,
            conventional_cosine_inter,
            empirical_cosine_all,
            empirical_cosine_inter,
        ],
        ignore_index=True,
    )

    # ==============================================================================================
    # FINAL RECONCILIATION CHECKS
    # ==============================================================================================

    assert (
        conventional_system_od[
            "system_trips"
        ].sum()
        ==
        len(
            system
        )
    )

    assert (
        empirical_system_od[
            "system_trips"
        ].sum()
        ==
        len(
            system
        )
    )

    assert (
        hourly[
            "trips"
        ].sum()
        ==
        len(
            system
        )
    )

    assert (
        hourly[
            "hour"
        ].nunique()
        ==
        24
    )

    # ==============================================================================================
    # SAVE PARQUET OUTPUTS
    # ==============================================================================================

    conventional_operator_od.to_parquet(
        OUTPUT_DIR
        / "operator_conventional_period_od_2024.parquet",
        index=False,
    )

    conventional_system_od.to_parquet(
        OUTPUT_DIR
        / "system_conventional_period_od_2024.parquet",
        index=False,
    )

    empirical_operator_od.to_parquet(
        OUTPUT_DIR
        / "operator_empirical_period_od_2024.parquet",
        index=False,
    )

    empirical_system_od.to_parquet(
        OUTPUT_DIR
        / "system_empirical_period_od_2024.parquet",
        index=False,
    )

    hourly.to_parquet(
        OUTPUT_DIR
        / "system_hourly_od_2024.parquet",
        index=False,
    )

    # ==============================================================================================
    # SAVE TABLES
    # ==============================================================================================

    conventional_summary.to_csv(
        TABLE_DIR
        / "conventional_period_summary_2024.csv",
        index=False,
    )

    conventional_concentration.to_csv(
        TABLE_DIR
        / "conventional_period_concentration_2024.csv",
        index=False,
    )

    conventional_top.to_csv(
        TABLE_DIR
        / "top_50_conventional_period_flows_2024.csv",
        index=False,
    )

    conventional_overlap.to_csv(
        TABLE_DIR
        / "top_50_conventional_period_overlap_2024.csv",
        index=False,
    )

    empirical_summary.to_csv(
        TABLE_DIR
        / "empirical_period_summary_2024.csv",
        index=False,
    )

    empirical_concentration.to_csv(
        TABLE_DIR
        / "empirical_period_concentration_2024.csv",
        index=False,
    )

    empirical_top.to_csv(
        TABLE_DIR
        / "top_50_empirical_period_flows_2024.csv",
        index=False,
    )

    empirical_overlap.to_csv(
        TABLE_DIR
        / "top_50_empirical_period_overlap_2024.csv",
        index=False,
    )

    hourly_summary.to_csv(
        TABLE_DIR
        / "hourly_od_structural_summary_2024.csv",
        index=False,
    )

    hourly_similarity.to_csv(
        TABLE_DIR
        / "hourly_od_cosine_similarity_2024.csv",
    )

    period_cosine.to_csv(
        TABLE_DIR
        / "period_od_cosine_similarity_2024.csv",
        index=False,
    )

    # ==============================================================================================
    # TERMINAL OUTPUT
    # ==============================================================================================

    print(
        "\n"
        + "=" * 115
    )

    print(
        "COMMON DETAILED-TIME OD COVERAGE"
    )

    print(
        "=" * 115
    )

    print(
        coverage.to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Conventional summary
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "CONVENTIONAL PERIOD SUMMARY"
    )

    print(
        "=" * 115
    )

    conventional_display = (
        conventional_summary.copy()
    )

    round_cols = [
        "mean_trips_per_day",
        "mean_trips_per_clock_hour",
        "intra_zonal_share_pct",
        "od_density_pct",
        "mean_active_od_pairs_per_clock_hour",
        "median_active_od_pairs_per_clock_hour",
        "min_active_od_pairs_per_clock_hour",
        "max_active_od_pairs_per_clock_hour",
    ]

    for col in round_cols:

        conventional_display[
            col
        ] = (
            conventional_display[
                col
            ]
            .round(
                2
            )
        )

    print(
        conventional_display.to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Conventional concentration
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "SYSTEM CONVENTIONAL FLOW CONCENTRATION"
    )

    print(
        "=" * 115
    )

    conventional_concentration_display = (
        conventional_concentration.copy()
    )

    concentration_round_cols = (
        [
            col
            for col
            in conventional_concentration_display.columns
            if col.endswith(
                "_pct"
            )
        ]
        +
        [
            "hhi"
        ]
    )

    for col in concentration_round_cols:

        conventional_concentration_display[
            col
        ] = (
            conventional_concentration_display[
                col
            ]
            .round(
                4
            )
        )

    print(
        conventional_concentration_display.to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Conventional top-flow overlap
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP-50 FLOW OVERLAP — CONVENTIONAL PERIODS"
    )

    print(
        "=" * 115
    )

    print(
        conventional_overlap.round(
            {
                "jaccard_similarity":
                    3,
            }
        ).to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Empirical summary
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "EMPIRICAL PEAK/OFF-PEAK SUMMARY"
    )

    print(
        "=" * 115
    )

    empirical_display = (
        empirical_summary.copy()
    )

    for col in round_cols:

        empirical_display[
            col
        ] = (
            empirical_display[
                col
            ]
            .round(
                2
            )
        )

    print(
        empirical_display.to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Empirical top-flow overlap
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "TOP-50 FLOW OVERLAP — EMPIRICAL PEAK/OFF-PEAK"
    )

    print(
        "=" * 115
    )

    print(
        empirical_overlap.round(
            {
                "jaccard_similarity":
                    3,
            }
        ).to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Period cosine similarity
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "PERIOD OD COSINE SIMILARITY"
    )

    print(
        "=" * 115
    )

    print(
        period_cosine.round(
            {
                "cosine_similarity":
                    4,
            }
        ).to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Hourly OD structure
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "HOURLY SYSTEM OD STRUCTURE"
    )

    print(
        "=" * 115
    )

    print(
        hourly_summary.round(
            {
                "mean_system_trips_per_clock_hour":
                    2,

                "intra_zonal_share_pct":
                    2,

                "od_density_pct":
                    2,

                "top_20_flow_share_pct":
                    2,

                "top_100_flow_share_pct":
                    2,
            }
        ).to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Validation / interpretation
    # ----------------------------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 115
    )

    print(
        "VALIDATION / INTERPRETATION"
    )

    print(
        "=" * 115
    )

    print(
        "- Temporal OD analysis uses only trips with valid official OD zones."
    )

    print(
        "- Common detailed-time window is 1 Feb-31 Dec 2024."
    )

    print(
        "- VOI January is excluded because detailed timestamps are unavailable."
    )

    print(
        "- Bird and Lime January are also excluded so all three operators use the same temporal comparison window."
    )

    print(
        "- Conventional AM peak = 07:00-09:59."
    )

    print(
        "- Conventional PM peak = 16:00-19:59."
    )

    print(
        "- Conventional off-peak contains the remaining 17 hours."
    )

    print(
        "- Empirical scooter peak is fixed at 15:00-20:59 from Exercise 1."
    )

    print(
        "- Peak/off-peak intensity is compared using mean trips per clock-hour because period durations differ."
    )

    print(
        "- Raw period-level active OD pair counts and OD density are exposure-dependent and should not be directly compared across periods of unequal duration."
    )

    print(
        "- mean_active_od_pairs_per_clock_hour provides the hour-normalized comparison of spatial network breadth."
    )

    print(
        "- Hourly OD tables provide 24 separate spatial flow structures."
    )

    print(
        "- Top-50 Jaccard overlap evaluates persistence of the strongest inter-zonal corridors."
    )

    print(
        "- Cosine similarity evaluates the complete normalized OD distribution rather than raw volume."
    )

    print(
        "- Cosine similarity is calculated both with all OD pairs and with inter-zonal pairs only."
    )

    print(
        "- No behavioral trip purpose is inferred directly from temporal OD patterns."
    )

    print(
        "- All temporal OD totals reconcile exactly with the filtered common-window trip population."
    )

    print(
        "\nSaved temporal OD outputs ->"
    )

    print(
        OUTPUT_DIR
    )

    print(
        "Saved temporal OD tables ->"
    )

    print(
        TABLE_DIR
    )


# ==================================================================================================
# ENTRY POINT
# ==================================================================================================

if __name__ == "__main__":
    main()