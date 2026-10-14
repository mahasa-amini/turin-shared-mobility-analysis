from __future__ import annotations

# =============================================================================
# EXERCISE 4 — PARKING DURATION MAPS
# Q1 FINAL CARTOGRAPHIC VERSION
#
# Output:
#   Bird
#   Lime
#   VOI
#   System-wide event-weighted pooled estimate
#
# Analytical parking definition:
#   - parking starts at the end of a trip
#   - next trip of the same vehicle must exist
#   - positive resolved inter-trip gap
#   - end -> next-start relocation distance <= 100 m
#   - parking duration <= 7 days
#   - parking location must have a valid official Torino statistical zone
#
# Cartographic rules:
#   - same fixed duration classes for every map
#   - <30 events = low-sample hatch
#   - no observations = grey
#   - representative-point zone labels
#   - labels selected objectively from highest/lowest mean zones + low samples
#   - automatic label/label collision suppression
#   - automatic legend/label overlap suppression
#   - fully opaque legend with very high z-order
#
# IMPORTANT:
#   This script first looks for an already-created complete zone-level parking
#   summary. If one is found, it uses that table directly.
#   Otherwise it rebuilds the zone summary from the candidate interval Parquets.
# =============================================================================


from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

from matplotlib.patches import Patch
from matplotlib.transforms import Bbox

import pyarrow.parquet as pq


# =============================================================================
# 1. PROJECT PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

ZONING_PATH = (
    ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "zoning"
    / "torino_statistical_zones.gpkg"
)

PARKING_DIR = (
    ROOT
    / "data"
    / "processed"
    / "exercise_4"
    / "parking"
)

TABLE_SEARCH_DIRS = [
    ROOT / "outputs" / "tables" / "exercise_4",
    ROOT / "data" / "processed" / "exercise_4",
    ROOT / "audit" / "exercise_4",
]

FIGURE_DIR = (
    ROOT
    / "outputs"
    / "figures"
    / "exercise_4"
    / "parking"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# 2. ANALYTICAL CONSTANTS
# =============================================================================

OPERATORS = [
    "bird",
    "lime",
    "voi",
]

SCOPES = [
    "bird",
    "lime",
    "voi",
    "system_pooled",
]

RELOCATION_THRESHOLD_M = 100.0

MAX_PARKING_MIN = (
    7
    * 24
    * 60
)

LOW_SAMPLE_THRESHOLD = 30


# Expected counts from the validated Exercise 4 pipeline.
# These are used as an integrity check, not to generate the results.

EXPECTED_VALID_EVENTS = {
    "bird": 310_300,
    "lime": 1_063_020,
    "voi": 85_507,
}

EXPECTED_SYSTEM_EVENTS = sum(
    EXPECTED_VALID_EVENTS.values()
)


# =============================================================================
# 3. MAP CLASSIFICATION
# =============================================================================

# Fixed classes across ALL maps.
#
# 0-6 h
# 6-12 h
# 12-18 h
# 18-24 h
# 24-30 h
# >30 h

DURATION_CLASSES = [
    (0.0, 6.0, "0–6 h", "#ffffcc"),
    (6.0, 12.0, "6–12 h", "#ffeda0"),
    (12.0, 18.0, "12–18 h", "#feb24c"),
    (18.0, 24.0, "18–24 h", "#fc4e2a"),
    (24.0, 30.0, "24–30 h", "#e31a1c"),
    (30.0, np.inf, ">30 h", "#800026"),
]

NO_DATA_COLOR = "#d9d9d9"

ZONE_EDGE_COLOR = "#8a8a8a"

OUTER_BOUNDARY_COLOR = "#4c4c4c"

LOW_SAMPLE_HATCH = "///"


# =============================================================================
# 4. FIGURE STYLE
# =============================================================================

FIGSIZE = (
    8.5,
    9.5,
)

DPI = 300

TITLE_SIZE = 15.5

ZONE_LABEL_SIZE = 7.2

LEGEND_FONT_SIZE = 8.5

LEGEND_TITLE_SIZE = 9.5

# We inspect at most the 10 highest and 10 lowest zones for labels.
# Actual displayed labels may be fewer because overlapping labels are suppressed.

N_EXTREME_LABELS = 10

# Collision padding in DISPLAY pixels.
LABEL_COLLISION_PAD_PX = 2.5

LEGEND_COLLISION_PAD_PX = 6.0


# =============================================================================
# 5. TITLES / OUTPUT NAMES
# =============================================================================

MAP_CONFIG = {
    "bird": {
        "title": (
            "Bird — Mean E-scooter Parking Duration by Statistical Zone\n"
            "Turin, Feb–Dec 2024"
        ),
        "filename": "parking_duration_by_zone_bird_2024.png",
    },
    "lime": {
        "title": (
            "Lime — Mean E-scooter Parking Duration by Statistical Zone\n"
            "Turin, Feb–Dec 2024"
        ),
        "filename": "parking_duration_by_zone_lime_2024.png",
    },
    "voi": {
        "title": (
            "VOI — Mean E-scooter Parking Duration by Statistical Zone\n"
            "Turin, Feb–Dec 2024"
        ),
        "filename": "parking_duration_by_zone_voi_2024.png",
    },
    "system_pooled": {
        "title": (
            "System-wide Mean E-scooter Parking Duration by Statistical Zone\n"
            "Event-weighted pooled estimate — Turin, Feb–Dec 2024"
        ),
        "filename": "parking_duration_by_zone_system_pooled_2024.png",
    },
}


# =============================================================================
# 6. GENERAL HELPERS
# =============================================================================


def canonical_zone_id(
    value,
) -> str | None:
    """
    Preserve official alphanumeric IDs while displaying numeric IDs as 2 digits.
    Examples:
        1       -> 01
        "7"     -> 07
        "09bis" -> 09bis
        "17bis" -> 17bis
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    # Handle values accidentally read as 1.0, 2.0, etc.
    try:
        numeric = float(value)

        if numeric.is_integer():
            return str(
                int(numeric)
            ).zfill(2)

    except (
        TypeError,
        ValueError,
    ):
        pass

    if value.isdigit():
        return value.zfill(2)

    return value


def normalize_scope(
    value,
) -> str:
    value = (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    replacements = {
        "system": "system_pooled",
        "pooled": "system_pooled",
        "systemwide": "system_pooled",
        "system_wide": "system_pooled",
        "system_pooled": "system_pooled",
        "pooled_system": "system_pooled",
    }

    return replacements.get(
        value,
        value,
    )


def first_existing_column(
    columns,
    aliases,
):
    """
    Case-insensitive column resolver.
    """

    lookup = {
        str(column).strip().lower(): column
        for column in columns
    }

    for alias in aliases:

        key = (
            str(alias)
            .strip()
            .lower()
        )

        if key in lookup:
            return lookup[key]

    return None


# =============================================================================
# 7. LOAD OFFICIAL ZONING
# =============================================================================


def load_zoning() -> gpd.GeoDataFrame:

    if not ZONING_PATH.exists():
        raise FileNotFoundError(
            f"Official zoning not found:\n{ZONING_PATH}"
        )

    zones = gpd.read_file(
        ZONING_PATH
    ).copy()

    zone_id_col = first_existing_column(
        zones.columns,
        [
            "zone_id",
            "ZONASTAT",
            "zonastat",
        ],
    )

    zone_name_col = first_existing_column(
        zones.columns,
        [
            "zone_name",
            "DENOM",
            "denom",
        ],
    )

    if zone_id_col is None:
        raise KeyError(
            "Could not identify official zone-ID field."
        )

    if zone_name_col is None:
        raise KeyError(
            "Could not identify official zone-name field."
        )

    zones["zone_id"] = (
        zones[zone_id_col]
        .map(
            canonical_zone_id
        )
    )

    zones["zone_name"] = (
        zones[zone_name_col]
        .astype(str)
        .str.strip()
    )

    zones = (
        zones[
            [
                "zone_id",
                "zone_name",
                "geometry",
            ]
        ]
        .copy()
    )

    if zones.crs is None:
        raise ValueError(
            "Official zoning has no CRS."
        )

    # Exercise 2 canonical zoning is EPSG:3003.
    epsg = zones.crs.to_epsg()

    if epsg != 3003:
        warnings.warn(
            f"Zoning CRS is {zones.crs}; "
            "reprojecting to EPSG:3003 for metric cartography."
        )

        zones = zones.to_crs(
            epsg=3003
        )

    if zones["zone_id"].duplicated().any():
        duplicates = (
            zones.loc[
                zones["zone_id"].duplicated(
                    keep=False
                ),
                "zone_id",
            ]
            .tolist()
        )

        raise ValueError(
            "Duplicate zone IDs in zoning: "
            f"{duplicates}"
        )

    if len(zones) != 94:
        raise ValueError(
            "Expected 94 official Torino statistical zones; "
            f"found {len(zones)}."
        )

    # Representative points are guaranteed to be inside polygons
    # and are therefore preferable to centroids for labels.

    representative = (
        zones.geometry
        .representative_point()
    )

    zones["label_x"] = representative.x

    zones["label_y"] = representative.y

    return zones


# =============================================================================
# 8. FIND PRE-COMPUTED ZONE SUMMARY
# =============================================================================


def standardize_zone_summary(
    frame: pd.DataFrame,
    inferred_scope: str | None = None,
) -> pd.DataFrame | None:

    frame = frame.copy()

    zone_col = first_existing_column(
        frame.columns,
        [
            "zone_id",
            "parking_zone_id",
            "destination_zone_id",
        ],
    )

    event_col = first_existing_column(
        frame.columns,
        [
            "parking_events",
            "valid_parking_events",
            "n_parking_events",
            "event_count",
            "events",
        ],
    )

    mean_h_col = first_existing_column(
        frame.columns,
        [
            "mean_parking_h",
            "mean_parking_hours",
        ],
    )

    mean_min_col = first_existing_column(
        frame.columns,
        [
            "mean_parking_min",
            "mean_parking_minutes",
        ],
    )

    scope_col = first_existing_column(
        frame.columns,
        [
            "analysis_scope",
            "scope",
            "operator",
        ],
    )

    if zone_col is None:
        return None

    if event_col is None:
        return None

    if (
        mean_h_col is None
        and mean_min_col is None
    ):
        return None

    out = pd.DataFrame()

    out["zone_id"] = (
        frame[zone_col]
        .map(
            canonical_zone_id
        )
    )

    out["parking_events"] = pd.to_numeric(
        frame[event_col],
        errors="coerce",
    )

    if mean_h_col is not None:

        out["mean_parking_h"] = pd.to_numeric(
            frame[mean_h_col],
            errors="coerce",
        )

    else:

        out["mean_parking_h"] = (
            pd.to_numeric(
                frame[mean_min_col],
                errors="coerce",
            )
            / 60.0
        )

    if scope_col is not None:

        out["analysis_scope"] = (
            frame[scope_col]
            .map(
                normalize_scope
            )
        )

    elif inferred_scope is not None:

        out["analysis_scope"] = (
            normalize_scope(
                inferred_scope
            )
        )

    else:
        return None

    out = out.dropna(
        subset=[
            "zone_id",
            "analysis_scope",
        ]
    )

    return out


def infer_scope_from_filename(
    path: Path,
) -> str | None:

    name = path.stem.lower()

    if "bird" in name:
        return "bird"

    if "lime" in name:
        return "lime"

    if "voi" in name:
        return "voi"

    if (
        "system" in name
        or "pooled" in name
    ):
        return "system_pooled"

    return None


def find_precomputed_zone_summary() -> pd.DataFrame | None:
    """
    Search Exercise 4 CSV outputs for a complete zone-level parking table.

    A table is accepted only if:
      - it contains mean parking duration,
      - it contains parking-event counts,
      - each real operator has broad zonal coverage.

    This prevents accidentally reading a Top-10-only diagnostic table.
    """

    # Prefer the analytical pipeline's complete, full-period outputs. Recursive
    # discovery also finds period-specific tables with conflicting zone rows.
    canonical_dir = ROOT / "outputs/tables/exercise_4/parking_by_zone"
    canonical_paths = [
        canonical_dir / f"parking_by_zone_{scope}_2024.csv"
        for scope in SCOPES
    ]
    if all(path.exists() for path in canonical_paths):
        tables = [
            standardize_zone_summary(pd.read_csv(path), inferred_scope=scope)
            for scope, path in zip(SCOPES, canonical_paths)
        ]
        if any(table is None for table in tables):
            raise ValueError("Invalid canonical zone parking summary schema.")
        print("Using canonical full-period zone parking summaries:")
        for path in canonical_paths:
            print(path)
        return pd.concat(tables, ignore_index=True)

    csv_paths = []

    for directory in TABLE_SEARCH_DIRS:

        if not directory.exists():
            continue

        csv_paths.extend(
            sorted(
                directory.rglob(
                    "*.csv"
                )
            )
        )

    if not csv_paths:
        return None

    # -------------------------------------------------------------------------
    # First preference:
    # one table that already contains all scopes.
    # -------------------------------------------------------------------------

    for path in csv_paths:

        try:
            raw = pd.read_csv(
                path
            )

        except Exception:
            continue

        table = standardize_zone_summary(
            raw
        )

        if table is None:
            continue

        present = set(
            table[
                "analysis_scope"
            ].unique()
        )

        if not set(
            SCOPES
        ).issubset(
            present
        ):
            continue

        counts = (
            table.groupby(
                "analysis_scope"
            )[
                "zone_id"
            ]
            .nunique()
        )

        # Full table must have many zones per operator.
        if all(
            counts.get(
                scope,
                0,
            ) >= 70
            for scope in SCOPES
        ):

            print(
                "\nUsing pre-computed zone parking summary:"
            )

            print(
                path
            )

            return (
                table[
                    table[
                        "analysis_scope"
                    ].isin(
                        SCOPES
                    )
                ]
                .copy()
            )

    # -------------------------------------------------------------------------
    # Second preference:
    # combine separate operator-specific tables.
    # -------------------------------------------------------------------------

    collected = []

    for path in csv_paths:

        scope = infer_scope_from_filename(
            path
        )

        if scope is None:
            continue

        try:
            raw = pd.read_csv(
                path
            )

        except Exception:
            continue

        table = standardize_zone_summary(
            raw,
            inferred_scope=scope,
        )

        if table is None:
            continue

        if (
            table["zone_id"]
            .nunique()
            < 70
        ):
            continue

        collected.append(
            table
        )

    if not collected:
        return None

    combined = pd.concat(
        collected,
        ignore_index=True,
    )

    # If several full tables for the same scope were found,
    # select the one with the greatest number of represented zones.

    selected = []

    for scope in SCOPES:

        candidates = combined[
            combined[
                "analysis_scope"
            ]
            == scope
        ].copy()

        if candidates.empty:
            continue

        # Remove exact duplicates first.
        candidates = candidates.drop_duplicates()

        # If multiple values exist for the same zone because several files
        # were found, we cannot safely guess which table is canonical.
        # In that case we abort precomputed-table mode and rebuild instead.

        duplicate_zone_values = (
            candidates.groupby(
                "zone_id"
            )
            .size()
        )

        if (
            duplicate_zone_values
            > 1
        ).any():
            return None

        selected.append(
            candidates
        )

    if len(selected) == len(
        SCOPES
    ):
        return pd.concat(
            selected,
            ignore_index=True,
        )

    return None


# =============================================================================
# 9. REBUILD FROM PARKING CANDIDATE PARQUETS — FALLBACK
# =============================================================================


GAP_ALIASES = [
    "parking_gap_min",
    "parking_gap_minutes",
    "parking_duration_min",
    "parking_duration_minutes",
    "elapsed_gap_min",
    "elapsed_gap_minutes",
    "gap_min",
    "gap_minutes",
]

RELOCATION_ALIASES = [
    "end_to_next_start_distance_m",
    "relocation_distance_m",
    "relocation_m",
    "end_next_distance_m",
]

ZONE_ALIASES = [
    "destination_zone_id",
    "destination_zone",
    "dest_zone_id",
    "end_zone_id",
    "parking_zone_id",
    "zone_id",
]


def parquet_columns(
    path: Path,
) -> list[str]:

    parquet = pq.ParquetFile(
        path
    )

    return list(
        parquet.schema.names
    )


def build_valid_parking_events(
    operator: str,
) -> pd.DataFrame:

    path = (
        PARKING_DIR
        / f"{operator}_parking_interval_candidates_2024.parquet"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Parking candidate file not found:\n{path}"
        )

    columns = parquet_columns(
        path
    )

    gap_col = first_existing_column(
        columns,
        GAP_ALIASES,
    )

    relocation_col = first_existing_column(
        columns,
        RELOCATION_ALIASES,
    )

    zone_col = first_existing_column(
        columns,
        ZONE_ALIASES,
    )

    missing = []

    if gap_col is None:
        missing.append(
            "parking-gap column"
        )

    if relocation_col is None:
        missing.append(
            "relocation-distance column"
        )

    if zone_col is None:
        missing.append(
            "destination/parking-zone column"
        )

    if missing:
        raise KeyError(
            f"\nCould not rebuild {operator.upper()} parking events.\n"
            f"Missing: {', '.join(missing)}\n\n"
            f"Available columns:\n{columns}\n"
        )

    usecols = list(
        dict.fromkeys(
            [
                gap_col,
                relocation_col,
                zone_col,
            ]
        )
    )

    df = pd.read_parquet(
        path,
        columns=usecols,
    )

    df["_parking_min"] = pd.to_numeric(
        df[gap_col],
        errors="coerce",
    )

    df["_relocation_m"] = pd.to_numeric(
        df[relocation_col],
        errors="coerce",
    )

    df["_zone_id"] = (
        df[zone_col]
        .map(
            canonical_zone_id
        )
    )

    # -------------------------------------------------------------------------
    # FINAL PARKING VALIDITY RULE
    # -------------------------------------------------------------------------
    #
    # This simultaneously handles:
    #   no next trip / unresolved gap       -> parking min = NaN
    #   non-positive gap                    -> <= 0
    #   missing relocation                  -> relocation = NaN
    #   relocation >100 m                   -> > threshold
    #   parking >7 days                     -> > duration cap
    #   destination zone unassigned         -> zone = NaN
    #
    # -------------------------------------------------------------------------

    valid = (
        df["_parking_min"].notna()
        & (
            df["_parking_min"]
            > 0
        )
        & (
            df["_parking_min"]
            <= MAX_PARKING_MIN
        )
        & df["_relocation_m"].notna()
        & (
            df["_relocation_m"]
            <= RELOCATION_THRESHOLD_M
        )
        & df["_zone_id"].notna()
    )

    valid_events = (
        df.loc[
            valid,
            [
                "_zone_id",
                "_parking_min",
            ],
        ]
        .rename(
            columns={
                "_zone_id": "zone_id",
                "_parking_min": "parking_min",
            }
        )
        .copy()
    )

    valid_events[
        "analysis_scope"
    ] = operator

    observed = len(
        valid_events
    )

    expected = EXPECTED_VALID_EVENTS[
        operator
    ]

    if observed != expected:

        raise RuntimeError(
            "\n"
            + "=" * 90
            + "\nPARKING VALIDATION COUNT MISMATCH\n"
            + "=" * 90
            + "\n"
            + f"Operator: {operator}\n"
            + f"Observed valid events from candidate file: {observed:,}\n"
            + f"Expected validated count: {expected:,}\n\n"
            + "Do NOT generate final maps until this is reconciled.\n"
            + "Most likely the candidate Parquet uses a different zone/status "
            + "field than the alias automatically selected.\n"
        )

    print(
        f"{operator.upper()}: "
        f"{observed:,} valid parking events"
    )

    return valid_events


def aggregate_zone_parking(
    events: pd.DataFrame,
    scope: str,
) -> pd.DataFrame:

    summary = (
        events.groupby(
            "zone_id",
            as_index=False,
        )
        .agg(
            parking_events=(
                "parking_min",
                "size",
            ),
            mean_parking_min=(
                "parking_min",
                "mean",
            ),
        )
    )

    summary[
        "mean_parking_h"
    ] = (
        summary[
            "mean_parking_min"
        ]
        / 60.0
    )

    summary[
        "analysis_scope"
    ] = scope

    return summary[
        [
            "analysis_scope",
            "zone_id",
            "parking_events",
            "mean_parking_h",
        ]
    ]


def rebuild_zone_summary_from_candidates() -> pd.DataFrame:

    print(
        "\nNo complete pre-computed zone summary found."
    )

    print(
        "Rebuilding zone summaries from validated candidate intervals...\n"
    )

    event_frames = []

    zone_summaries = []

    for operator in OPERATORS:

        events = build_valid_parking_events(
            operator
        )

        event_frames.append(
            events
        )

        zone_summaries.append(
            aggregate_zone_parking(
                events,
                operator,
            )
        )

    pooled_events = pd.concat(
        event_frames,
        ignore_index=True,
    )

    if len(
        pooled_events
    ) != EXPECTED_SYSTEM_EVENTS:

        raise RuntimeError(
            "System pooled event count mismatch: "
            f"{len(pooled_events):,} vs "
            f"{EXPECTED_SYSTEM_EVENTS:,}."
        )

    pooled_summary = (
        aggregate_zone_parking(
            pooled_events,
            "system_pooled",
        )
    )

    zone_summaries.append(
        pooled_summary
    )

    return pd.concat(
        zone_summaries,
        ignore_index=True,
    )


# =============================================================================
# 10. SUMMARY VALIDATION
# =============================================================================


def validate_zone_summary(
    zone_summary: pd.DataFrame,
):

    required = {
        "analysis_scope",
        "zone_id",
        "parking_events",
        "mean_parking_h",
    }

    missing = (
        required
        - set(
            zone_summary.columns
        )
    )

    if missing:
        raise KeyError(
            "Zone summary missing fields: "
            f"{sorted(missing)}"
        )

    zone_summary[
        "analysis_scope"
    ] = (
        zone_summary[
            "analysis_scope"
        ]
        .map(
            normalize_scope
        )
    )

    zone_summary[
        "zone_id"
    ] = (
        zone_summary[
            "zone_id"
        ]
        .map(
            canonical_zone_id
        )
    )

    zone_summary[
        "parking_events"
    ] = pd.to_numeric(
        zone_summary[
            "parking_events"
        ],
        errors="coerce",
    )

    zone_summary[
        "mean_parking_h"
    ] = pd.to_numeric(
        zone_summary[
            "mean_parking_h"
        ],
        errors="coerce",
    )

    for scope in SCOPES:

        part = zone_summary[
            zone_summary[
                "analysis_scope"
            ]
            == scope
        ]

        if part.empty:
            raise ValueError(
                f"No zone summary found for {scope}."
            )

        if part[
            "zone_id"
        ].duplicated().any():
            raise ValueError(
                f"Duplicate zone IDs in {scope} zone summary."
            )

    # -------------------------------------------------------------------------
    # Validate total event counts when possible.
    # -------------------------------------------------------------------------

    for operator in OPERATORS:

        observed = int(
            round(
                zone_summary.loc[
                    zone_summary[
                        "analysis_scope"
                    ]
                    == operator,
                    "parking_events",
                ].sum()
            )
        )

        expected = EXPECTED_VALID_EVENTS[
            operator
        ]

        if observed != expected:

            raise RuntimeError(
                f"{operator.upper()} zone event total mismatch: "
                f"{observed:,} != {expected:,}"
            )

    pooled_observed = int(
        round(
            zone_summary.loc[
                zone_summary[
                    "analysis_scope"
                ]
                == "system_pooled",
                "parking_events",
            ].sum()
        )
    )

    if pooled_observed != EXPECTED_SYSTEM_EVENTS:

        raise RuntimeError(
            "System pooled zone event total mismatch: "
            f"{pooled_observed:,} != "
            f"{EXPECTED_SYSTEM_EVENTS:,}"
        )

    print(
        "\nZone-level parking summary validation: PASSED"
    )


# =============================================================================
# 11. CLASSIFICATION HELPERS
# =============================================================================


def duration_class(
    value,
) -> str | None:

    if pd.isna(
        value
    ):
        return None

    value = float(
        value
    )

    for (
        low,
        high,
        label,
        _,
    ) in DURATION_CLASSES:

        if (
            value >= low
            and value < high
        ):
            return label

    return DURATION_CLASSES[
        -1
    ][2]


CLASS_COLOR = {
    label: color
    for (
        _,
        _,
        label,
        color,
    ) in DURATION_CLASSES
}


# =============================================================================
# 12. CARTOGRAPHIC HELPERS
# =============================================================================


def add_north_arrow(
    ax,
):
    """
    North arrow in axes coordinates.
    """

    ax.annotate(
        "",
        xy=(
            0.925,
            0.885,
        ),
        xytext=(
            0.925,
            0.805,
        ),
        xycoords="axes fraction",
        arrowprops={
            "arrowstyle": "-|>",
            "linewidth": 1.8,
            "edgecolor": "black",
            "facecolor": "white",
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=500,
    )

    ax.text(
        0.925,
        0.785,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        zorder=500,
    )


def add_scale_bar(
    ax,
    bounds,
    length_m=2000,
):
    """
    Metric scale bar.

    EPSG:3003 uses metres, so a 2000-unit bar = 2 km.
    """

    minx, miny, maxx, maxy = bounds

    width = (
        maxx
        - minx
    )

    height = (
        maxy
        - miny
    )

    x1 = (
        maxx
        - 0.035
        * width
    )

    x0 = (
        x1
        - length_m
    )

    y = (
        miny
        + 0.035
        * height
    )

    tick = (
        0.010
        * height
    )

    ax.plot(
        [
            x0,
            x1,
        ],
        [
            y,
            y,
        ],
        color="black",
        linewidth=2.0,
        solid_capstyle="butt",
        zorder=400,
    )

    ax.plot(
        [
            x0,
            x0,
        ],
        [
            y - tick,
            y + tick,
        ],
        color="black",
        linewidth=2.0,
        zorder=400,
    )

    ax.plot(
        [
            x1,
            x1,
        ],
        [
            y - tick,
            y + tick,
        ],
        color="black",
        linewidth=2.0,
        zorder=400,
    )

    ax.text(
        (
            x0
            + x1
        )
        / 2.0,
        y
        + 0.018
        * height,
        f"{length_m / 1000:g} km",
        ha="center",
        va="bottom",
        fontsize=8.5,
        zorder=400,
    )


def build_legend_handles():
    """
    Explicit handles guarantee exactly the same legend on every map.
    """

    handles = []

    for (
        _,
        _,
        label,
        color,
    ) in DURATION_CLASSES:

        handles.append(
            Patch(
                facecolor=color,
                edgecolor="#666666",
                linewidth=0.7,
                label=label,
            )
        )

    handles.append(
        Patch(
            facecolor="white",
            edgecolor="black",
            hatch=LOW_SAMPLE_HATCH,
            linewidth=0.9,
            label=(
                f"Low sample "
                f"(<{LOW_SAMPLE_THRESHOLD} events)"
            ),
        )
    )

    handles.append(
        Patch(
            facecolor=NO_DATA_COLOR,
            edgecolor="#888888",
            linewidth=0.9,
            label="No valid parking observations",
        )
    )

    return handles


def expanded_bbox(
    bbox: Bbox,
    pad_px: float,
) -> Bbox:

    return Bbox.from_extents(
        bbox.x0 - pad_px,
        bbox.y0 - pad_px,
        bbox.x1 + pad_px,
        bbox.y1 + pad_px,
    )


def bbox_overlaps_any(
    bbox: Bbox,
    other_bboxes: list[Bbox],
) -> bool:

    return any(
        bbox.overlaps(
            other
        )
        for other in other_bboxes
    )


# =============================================================================
# 13. OBJECTIVE LABEL SELECTION
# =============================================================================


def select_label_zones(
    map_data: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Labels are selected objectively:

      1. every low-sample zone;
      2. N highest mean-parking zones;
      3. N lowest mean-parking zones.

    A priority field is retained so the most analytically important labels
    survive collision filtering first.
    """

    valid = (
        map_data[
            map_data[
                "mean_parking_h"
            ].notna()
        ]
        .copy()
    )

    if valid.empty:
        return valid

    high = (
        valid.nlargest(
            N_EXTREME_LABELS,
            "mean_parking_h",
        )
        .copy()
    )

    high[
        "_label_priority"
    ] = np.arange(
        0,
        len(
            high
        ),
    )

    high[
        "_label_reason"
    ] = "high"

    low = (
        valid.nsmallest(
            N_EXTREME_LABELS,
            "mean_parking_h",
        )
        .copy()
    )

    low[
        "_label_priority"
    ] = (
        100
        + np.arange(
            0,
            len(
                low
            ),
        )
    )

    low[
        "_label_reason"
    ] = "low"

    low_sample = (
        valid[
            valid[
                "parking_events"
            ]
            < LOW_SAMPLE_THRESHOLD
        ]
        .copy()
    )

    # Low-sample labels are given highest visual priority,
    # since hatching without an identifier can be difficult to interpret.

    low_sample[
        "_label_priority"
    ] = (
        -100
        + np.arange(
            0,
            len(
                low_sample
            ),
        )
    )

    low_sample[
        "_label_reason"
    ] = "low_sample"

    candidates = pd.concat(
        [
            low_sample,
            high,
            low,
        ],
        ignore_index=True,
    )

    # If the same zone belongs to two categories,
    # retain the highest-priority version.

    candidates = (
        candidates.sort_values(
            "_label_priority"
        )
        .drop_duplicates(
            subset=[
                "zone_id",
            ],
            keep="first",
        )
        .reset_index(
            drop=True
        )
    )

    return candidates


# =============================================================================
# 14. THE KEY FIX:
#     DRAW LABELS ONLY AFTER LEGEND BBOX IS KNOWN
# =============================================================================


def add_collision_safe_zone_labels(
    fig,
    ax,
    map_data: gpd.GeoDataFrame,
    legend,
) -> tuple[list, list[str]]:
    """
    Core overlap solution.

    Procedure:
      1. Legend already exists.
      2. Canvas is rendered.
      3. Exact legend bounding box is measured in display pixels.
      4. Each zone label is drawn temporarily.
      5. Exact text bounding box is measured.
      6. Label is removed if it overlaps:
           - legend,
           - any previously accepted label.
      7. Otherwise it is retained.

    Therefore no hard-coded zone IDs or hand-tuned coordinates are necessary.
    """

    # Make sure the final axes geometry is already fixed BEFORE this call.
    fig.canvas.draw()

    renderer = (
        fig.canvas.get_renderer()
    )

    legend_bbox = (
        legend.get_window_extent(
            renderer=renderer
        )
    )

    legend_bbox = expanded_bbox(
        legend_bbox,
        LEGEND_COLLISION_PAD_PX,
    )

    candidates = select_label_zones(
        map_data
    )

    accepted_texts = []

    accepted_bboxes: list[Bbox] = []

    suppressed_zone_ids = []

    for _, row in candidates.iterrows():

        zone_id = row[
            "zone_id"
        ]

        x = row[
            "label_x"
        ]

        y = row[
            "label_y"
        ]

        mean_h = row[
            "mean_parking_h"
        ]

        if (
            pd.isna(
                x
            )
            or pd.isna(
                y
            )
        ):
            continue

        # ---------------------------------------------------------------------
        # Text contrast
        # ---------------------------------------------------------------------

        if mean_h >= 24:

            text_color = "white"

            stroke_color = "black"

        else:

            text_color = "#111111"

            stroke_color = "white"

        text = ax.text(
            x,
            y,
            str(
                zone_id
            ),
            ha="center",
            va="center",
            fontsize=ZONE_LABEL_SIZE,
            fontweight="bold",
            color=text_color,

            # Important:
            # labels remain BELOW legend.
            zorder=50,

            path_effects=[
                pe.withStroke(
                    linewidth=1.6,
                    foreground=stroke_color,
                )
            ],
        )

        # Render temporary text so Matplotlib can calculate
        # its exact bounding box.

        fig.canvas.draw()

        text_bbox = (
            text.get_window_extent(
                renderer=renderer
            )
        )

        padded_text_bbox = expanded_bbox(
            text_bbox,
            LABEL_COLLISION_PAD_PX,
        )

        # ---------------------------------------------------------------------
        # Rule A:
        # absolutely no zone label is allowed to touch legend.
        # ---------------------------------------------------------------------

        if padded_text_bbox.overlaps(
            legend_bbox
        ):

            text.remove()

            suppressed_zone_ids.append(
                str(
                    zone_id
                )
            )

            continue

        # ---------------------------------------------------------------------
        # Rule B:
        # suppress label-label collisions.
        # ---------------------------------------------------------------------

        if bbox_overlaps_any(
            padded_text_bbox,
            accepted_bboxes,
        ):

            text.remove()

            suppressed_zone_ids.append(
                str(
                    zone_id
                )
            )

            continue

        accepted_texts.append(
            text
        )

        accepted_bboxes.append(
            padded_text_bbox
        )

    # Final render
    fig.canvas.draw()

    # -------------------------------------------------------------------------
    # FINAL AUTOMATIC SAFETY CHECK
    # -------------------------------------------------------------------------

    renderer = (
        fig.canvas.get_renderer()
    )

    final_legend_bbox = expanded_bbox(
        legend.get_window_extent(
            renderer=renderer
        ),
        1.0,
    )

    for text in accepted_texts:

        text_bbox = (
            text.get_window_extent(
                renderer=renderer
            )
        )

        if text_bbox.overlaps(
            final_legend_bbox
        ):

            raise RuntimeError(
                "Legend-label overlap remained after collision filtering: "
                f"zone {text.get_text()}"
            )

    return (
        accepted_texts,
        suppressed_zone_ids,
    )


# =============================================================================
# 15. CREATE ONE MAP
# =============================================================================


def create_parking_map(
    zones: gpd.GeoDataFrame,
    zone_summary: pd.DataFrame,
    scope: str,
):

    config = MAP_CONFIG[
        scope
    ]

    scope_summary = (
        zone_summary[
            zone_summary[
                "analysis_scope"
            ]
            == scope
        ]
        .copy()
    )

    scope_summary[
        "zone_id"
    ] = (
        scope_summary[
            "zone_id"
        ]
        .map(
            canonical_zone_id
        )
    )

    map_data = zones.merge(
        scope_summary[
            [
                "zone_id",
                "parking_events",
                "mean_parking_h",
            ]
        ],
        on="zone_id",
        how="left",
        validate="one_to_one",
    )

    map_data[
        "duration_class"
    ] = (
        map_data[
            "mean_parking_h"
        ]
        .apply(
            duration_class
        )
    )

    map_data[
        "fill_color"
    ] = (
        map_data[
            "duration_class"
        ]
        .map(
            CLASS_COLOR
        )
        .fillna(
            NO_DATA_COLOR
        )
    )

    map_data[
        "low_sample"
    ] = (
        map_data[
            "parking_events"
        ]
        .notna()
        & (
            map_data[
                "parking_events"
            ]
            < LOW_SAMPLE_THRESHOLD
        )
    )

    # -------------------------------------------------------------------------
    # Figure
    # -------------------------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=FIGSIZE,
        facecolor="white",
    )

    ax.set_facecolor(
        "white"
    )

    # FIXED margins.
    #
    # Do not call tight_layout AFTER legend-label collision calculation,
    # because that would move the axes and invalidate measured bounding boxes.

    fig.subplots_adjust(
        left=0.025,
        right=0.975,
        bottom=0.075,
        top=0.900,
    )

    # -------------------------------------------------------------------------
    # Base polygons
    # -------------------------------------------------------------------------

    map_data.plot(
        ax=ax,
        color=map_data[
            "fill_color"
        ],
        edgecolor=ZONE_EDGE_COLOR,
        linewidth=0.48,
        zorder=10,
    )

    # -------------------------------------------------------------------------
    # Low-sample hatch overlay
    # -------------------------------------------------------------------------

    low_sample = map_data[
        map_data[
            "low_sample"
        ]
    ]

    if not low_sample.empty:

        low_sample.plot(
            ax=ax,
            facecolor="none",
            edgecolor="black",
            linewidth=1.0,
            hatch=LOW_SAMPLE_HATCH,
            zorder=25,
        )

    # -------------------------------------------------------------------------
    # Stronger municipal outer boundary
    # -------------------------------------------------------------------------

    municipal = (
        zones[
            [
                "geometry",
            ]
        ]
        .dissolve()
    )

    municipal.boundary.plot(
        ax=ax,
        color=OUTER_BOUNDARY_COLOR,
        linewidth=1.15,
        zorder=30,
    )

    # -------------------------------------------------------------------------
    # Equal aspect / map limits
    # -------------------------------------------------------------------------

    minx, miny, maxx, maxy = (
        zones.total_bounds
    )

    width = (
        maxx
        - minx
    )

    height = (
        maxy
        - miny
    )

    xpad = (
        0.055
        * width
    )

    ypad = (
        0.045
        * height
    )

    ax.set_xlim(
        minx - xpad,
        maxx + xpad,
    )

    ax.set_ylim(
        miny - ypad,
        maxy + ypad,
    )

    ax.set_aspect(
        "equal"
    )

    ax.axis(
        "off"
    )

    # -------------------------------------------------------------------------
    # Title
    # -------------------------------------------------------------------------

    ax.set_title(
        config[
            "title"
        ],
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=18,
    )

    # -------------------------------------------------------------------------
    # North arrow + scale bar
    # -------------------------------------------------------------------------

    add_north_arrow(
        ax
    )

    add_scale_bar(
        ax,
        bounds=zones.total_bounds,
        length_m=2000,
    )

    # -------------------------------------------------------------------------
    # LEGEND IS CREATED BEFORE LABELS
    # -------------------------------------------------------------------------

    legend = ax.legend(
        handles=build_legend_handles(),
        title="Mean parking duration",
        loc="upper left",

        # Use the empty northwest margin, leaving southwest zones visible.
        bbox_to_anchor=(
            0.012,
            1.0,
        ),

        borderaxespad=0.0,
        frameon=True,

        # CRITICAL FIX:
        framealpha=1.0,
        facecolor="white",
        edgecolor="#b0b0b0",

        fontsize=LEGEND_FONT_SIZE,
        title_fontsize=LEGEND_TITLE_SIZE,
        labelspacing=0.35,
        borderpad=0.55,
        handlelength=1.55,
        handletextpad=0.55,
    )

    # -------------------------------------------------------------------------
    # CRITICAL FIX:
    # legend is always above maps / hatches / text.
    # -------------------------------------------------------------------------

    legend.set_zorder(
        1000
    )

    legend.get_frame().set_alpha(
        1.0
    )

    legend.get_frame().set_facecolor(
        "white"
    )

    # -------------------------------------------------------------------------
    # Draw zone labels WITH actual legend-overlap detection
    # -------------------------------------------------------------------------

    (
        accepted_labels,
        suppressed_labels,
    ) = add_collision_safe_zone_labels(
        fig=fig,
        ax=ax,
        map_data=map_data,
        legend=legend,
    )

    # Reinforce legend z-order after labels were created.
    legend.set_zorder(
        1000
    )

    # -------------------------------------------------------------------------
    # Footnote
    # -------------------------------------------------------------------------

    fig.text(
        0.5,
        0.025,
        (
            "Inactivity proxy: positive inter-trip gap; "
            "end-to-next-start displacement ≤100 m; "
            "duration ≤7 days.\n"
            "Not confirmed continuous parking. Official Torino statistical zones."
        ),
        ha="center",
        va="center",
        fontsize=7.4,
        color="#111111",
    )

    # -------------------------------------------------------------------------
    # Final map QA
    # -------------------------------------------------------------------------

    zones_with_data = int(
        map_data[
            "parking_events"
        ]
        .notna()
        .sum()
    )

    zones_low_sample = int(
        map_data[
            "low_sample"
        ]
        .sum()
    )

    total_events = int(
        np.nansum(
            map_data[
                "parking_events"
            ]
        )
    )

    print(
        "\n"
        + "-" * 90
    )

    print(
        f"MAP QA — {scope}"
    )

    print(
        f"Parking events: {total_events:,}"
    )

    print(
        f"Zones with parking observations: {zones_with_data}"
    )

    print(
        f"Low-sample zones (<{LOW_SAMPLE_THRESHOLD}): "
        f"{zones_low_sample}"
    )

    print(
        f"Displayed labels: {len(accepted_labels)}"
    )

    if suppressed_labels:

        print(
            "Suppressed labels because of legend/label collision: "
            + ", ".join(
                suppressed_labels
            )
        )

    else:

        print(
            "Suppressed labels because of collision: none"
        )

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    output_path = (
        FIGURE_DIR
        / config[
            "filename"
        ]
    )

    fig.savefig(
        output_path,
        dpi=DPI,
        facecolor="white",
        edgecolor="none",
    )

    plt.close(
        fig
    )

    print(
        f"Saved -> {output_path}"
    )

    return output_path


# =============================================================================
# 16. MAIN
# =============================================================================


def main():

    print(
        "=" * 100
    )

    print(
        "EXERCISE 4 — FINAL PARKING DURATION MAPS"
    )

    print(
        "=" * 100
    )

    print(
        "\nLoading official Torino zoning..."
    )

    zones = load_zoning()

    print(
        f"Zones loaded: {len(zones)}"
    )

    print(
        f"CRS: {zones.crs}"
    )

    # -------------------------------------------------------------------------
    # Try using the already-produced zone-level analytical table first.
    # -------------------------------------------------------------------------

    zone_summary = (
        find_precomputed_zone_summary()
    )

    # -------------------------------------------------------------------------
    # If no complete table can be identified safely,
    # reconstruct it from parking candidates.
    # -------------------------------------------------------------------------

    if zone_summary is None:

        zone_summary = (
            rebuild_zone_summary_from_candidates()
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    validate_zone_summary(
        zone_summary
    )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "GENERATING MAPS"
    )

    print(
        "=" * 100
    )

    output_paths = []

    for scope in SCOPES:

        output_paths.append(
            create_parking_map(
                zones=zones,
                zone_summary=zone_summary,
                scope=scope,
            )
        )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "EXERCISE 4 — Q1 MAP GENERATION COMPLETED"
    )

    print(
        "=" * 100
    )

    print(
        "\nGenerated figures:"
    )

    for path in output_paths:

        print(
            path
        )

    print(
        "\nFINAL CARTOGRAPHIC VALIDATION:"
    )

    print(
        "- Fixed parking-duration classes are identical across all four maps."
    )

    print(
        f"- Low sample = fewer than {LOW_SAMPLE_THRESHOLD} valid parking events."
    )

    print(
        "- No-data zones are shown in grey."
    )

    print(
        "- Low-sample zones are hatched."
    )

    print(
        "- Labels use representative points inside official zones."
    )

    print(
        "- Label-label collisions are automatically suppressed."
    )

    print(
        "- Legend-label collisions are automatically suppressed using "
        "rendered bounding boxes."
    )

    print(
        "- Legend frame is fully opaque and rendered above every map element."
    )

    print(
        "- North arrow and 2-km metric scale bar are included."
    )

    print(
        "- System map is an event-weighted pooled estimate."
    )

    print(
        "- Figure generation does not alter any analytical trip data."
    )


if __name__ == "__main__":
    main()
