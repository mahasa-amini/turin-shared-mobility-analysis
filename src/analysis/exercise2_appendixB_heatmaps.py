from pathlib import Path
import re

import numpy as np
import pandas as pd
import geopandas as gpd

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LogNorm


# =============================================================================
# 1. PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEMPORAL_OD_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "temporal_od"
    / "system_conventional_period_od_2024.parquet"
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
    / "outputs"
    / "report"
    / "exercise_2"
    / "appendices"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# 2. OUTPUT FILES
# =============================================================================

OUTPUT_FILES = {
    "AM peak": (
        OUTPUT_DIR
        / "Figure_B1_am_peak_OD_matrix_heatmap.png"
    ),
    "PM peak": (
        OUTPUT_DIR
        / "Figure_B2_pm_peak_OD_matrix_heatmap.png"
    ),
    "Off-peak": (
        OUTPUT_DIR
        / "Figure_B3_offpeak_OD_matrix_heatmap.png"
    ),
}


# =============================================================================
# 3. FIGURE METADATA
# =============================================================================

PERIOD_META = {
    "AM peak": {
        "figure_no": "Figure B.1",
        "title": "AM Peak Origin–Destination Matrix — Turin, 2024",
        "subtitle": (
            "07:00–09:59 | Official 94 × 94 system-wide "
            "e-scooter O–D matrix"
        ),
    },

    "PM peak": {
        "figure_no": "Figure B.2",
        "title": "PM Peak Origin–Destination Matrix — Turin, 2024",
        "subtitle": (
            "16:00–19:59 | Official 94 × 94 system-wide "
            "e-scooter O–D matrix"
        ),
    },

    "Off-peak": {
        "figure_no": "Figure B.3",
        "title": "Off-peak Origin–Destination Matrix — Turin, 2024",
        "subtitle": (
            "17 remaining hours/day | Official 94 × 94 "
            "system-wide e-scooter O–D matrix"
        ),
    },
}


# =============================================================================
# 4. EXPECTED VALUES FROM VALIDATED TEMPORAL PIPELINE
# =============================================================================

EXPECTED = {
    "AM peak": {
        "total": 153_096,
        "intra": 20_725,
        "inter": 132_371,
        "active_od": 4_200,
        "active_inter": 4_118,
    },

    "PM peak": {
        "total": 428_893,
        "intra": 74_389,
        "inter": 354_504,
        "active_od": 5_383,
        "active_inter": 5_299,
    },

    "Off-peak": {
        "total": 1_024_952,
        "intra": 165_263,
        "inter": 859_689,
        "active_od": 5_945,
        "active_inter": 5_861,
    },
}


# =============================================================================
# 5. GENERAL UTILITIES
# =============================================================================

def print_header(title):
    print("\n" + "=" * 110)
    print(title)
    print("=" * 110)


def normalize_zone_id(value):
    """
    Standardize official zone IDs.

    Examples:
        1       -> 01
        "1"     -> 01
        "01"    -> 01
        9bis    -> 09bis
        "09bis" -> 09bis
    """

    if pd.isna(value):
        return None

    text = (
        str(value)
        .strip()
        .replace(" ", "")
    )

    if text == "":
        return None

    numeric_match = re.fullmatch(
        r"(\d+)(?:\.0+)?",
        text,
    )

    if numeric_match:
        return f"{int(numeric_match.group(1)):02d}"

    bis_match = re.fullmatch(
        r"(\d+)(bis)",
        text,
        flags=re.IGNORECASE,
    )

    if bis_match:
        return f"{int(bis_match.group(1)):02d}bis"

    return text


def zone_sort_key(zone_id):
    """
    Natural order:
    01, 02, ..., 09, 09bis, 10, ..., 17, 17bis, ...
    """

    zone_id = normalize_zone_id(zone_id)

    match = re.fullmatch(
        r"(\d+)(.*)",
        zone_id,
    )

    if match is None:
        return (
            9999,
            1,
            zone_id,
        )

    number = int(
        match.group(1)
    )

    suffix = (
        match.group(2)
        .lower()
        .strip()
    )

    suffix_rank = (
        0
        if suffix == ""
        else 1
    )

    return (
        number,
        suffix_rank,
        suffix,
    )


# =============================================================================
# 6. LOAD OFFICIAL ZONE ORDER
# =============================================================================

def load_official_zone_order():

    print_header(
        "LOADING OFFICIAL TORINO ZONING"
    )

    if not ZONING_PATH.exists():
        raise FileNotFoundError(
            f"Official zoning file not found:\n{ZONING_PATH}"
        )

    zones = gpd.read_file(
        ZONING_PATH,
        layer="zones",
        engine="pyogrio",
    )

    print(
        f"Loaded zoning layer: {len(zones)} zones"
    )

    print(
        f"Columns: {list(zones.columns)}"
    )

    # Support either canonical or source field name.
    if "zone_id" in zones.columns:

        zone_col = "zone_id"

    elif "ZONASTAT" in zones.columns:

        zone_col = "ZONASTAT"

    else:
        raise KeyError(
            "Could not find zone_id or ZONASTAT "
            "in zoning layer."
        )

    zone_ids = (
        zones[zone_col]
        .map(normalize_zone_id)
        .tolist()
    )

    if len(zone_ids) != 94:
        raise ValueError(
            f"Expected 94 zones, found {len(zone_ids)}."
        )

    if len(set(zone_ids)) != 94:
        raise ValueError(
            "Official zoning contains duplicate zone IDs."
        )

    zone_ids = sorted(
        zone_ids,
        key=zone_sort_key,
    )

    print(
        f"Official zone count: {len(zone_ids)}"
    )

    print(
        f"First IDs: {zone_ids[:10]}"
    )

    print(
        f"Last IDs:  {zone_ids[-10:]}"
    )

    return zone_ids


# =============================================================================
# 7. COLUMN DETECTION
# =============================================================================

def detect_column(
    df,
    candidates,
    description,
):
    """
    Find a column safely using a list of possible names.
    """

    lowercase_map = {
        str(col).lower(): col
        for col in df.columns
    }

    for candidate in candidates:

        if candidate.lower() in lowercase_map:

            found = lowercase_map[
                candidate.lower()
            ]

            print(
                f"{description}: {found}"
            )

            return found

    raise KeyError(
        f"Could not identify {description}.\n"
        f"Available columns:\n{list(df.columns)}"
    )


# =============================================================================
# 8. LOAD LONG-FORM TEMPORAL OD DATA
# =============================================================================

def load_temporal_od():

    print_header(
        "LOADING SYSTEM CONVENTIONAL TEMPORAL OD DATA"
    )

    if not TEMPORAL_OD_FILE.exists():

        raise FileNotFoundError(
            f"Temporal OD parquet not found:\n"
            f"{TEMPORAL_OD_FILE}"
        )

    df = pd.read_parquet(
        TEMPORAL_OD_FILE
    )

    print(
        f"Rows loaded: {len(df):,}"
    )

    print(
        f"Columns: {list(df.columns)}"
    )

    # -------------------------------------------------------------------------
    # Detect relevant columns
    # -------------------------------------------------------------------------

    period_col = detect_column(
        df,
        [
            "conventional_period",
            "period",
            "time_period",
            "transport_period",
            "analysis_period",
            "period_name",
        ],
        "period column",
    )

    origin_col = detect_column(
        df,
        [
            "origin_zone_id",
            "origin_zone",
            "origin",
            "o_zone_id",
            "from_zone_id",
        ],
        "origin-zone column",
    )

    destination_col = detect_column(
        df,
        [
            "destination_zone_id",
            "destination_zone",
            "destination",
            "dest_zone_id",
            "d_zone_id",
            "to_zone_id",
        ],
        "destination-zone column",
    )

    trips_col = detect_column(
        df,
        [
            "trips",
            "system_trips",
            "trip_count",
            "od_trips",
            "flow_trips",
            "count",
        ],
        "trip-count column",
    )

    # -------------------------------------------------------------------------
    # Standardize
    # -------------------------------------------------------------------------

    out = df[
        [
            period_col,
            origin_col,
            destination_col,
            trips_col,
        ]
    ].copy()

    out.columns = [
        "period",
        "origin_zone_id",
        "destination_zone_id",
        "trips",
    ]

    out["period"] = (
        out["period"]
        .astype(str)
        .str.strip()
    )

    out["origin_zone_id"] = (
        out["origin_zone_id"]
        .map(normalize_zone_id)
    )

    out["destination_zone_id"] = (
        out["destination_zone_id"]
        .map(normalize_zone_id)
    )

    out["trips"] = pd.to_numeric(
        out["trips"],
        errors="coerce",
    )

    if out["trips"].isna().any():

        bad_count = int(
            out["trips"]
            .isna()
            .sum()
        )

        raise ValueError(
            f"{bad_count:,} rows have invalid trip counts."
        )

    # -------------------------------------------------------------------------
    # Inspect period values
    # -------------------------------------------------------------------------

    print(
        "\nPeriod values found:"
    )

    print(
        out["period"]
        .value_counts()
        .to_string()
    )

    return out


# =============================================================================
# 9. NORMALIZE PERIOD NAMES
# =============================================================================

def normalize_period(value):

    text = (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if text in {
        "am peak",
        "morning peak",
        "am",
        "morning",
    }:
        return "AM peak"

    if text in {
        "pm peak",
        "evening peak",
        "pm",
        "evening",
    }:
        return "PM peak"

    if text in {
        "off peak",
        "offpeak",
        "non peak",
        "nonpeak",
    }:
        return "Off-peak"

    return str(value).strip()


# =============================================================================
# 10. BUILD 94 × 94 MATRIX
# =============================================================================

def build_matrix(
    temporal_od,
    period,
    official_zone_ids,
):

    print_header(
        f"BUILDING {period.upper()} MATRIX"
    )

    temp = temporal_od.copy()

    temp["period_normalized"] = (
        temp["period"]
        .map(normalize_period)
    )

    subset = temp[
        temp["period_normalized"]
        == period
    ].copy()

    if subset.empty:

        raise ValueError(
            f"No rows found for period '{period}'.\n"
            f"Available normalized periods:\n"
            f"{sorted(temp['period_normalized'].dropna().unique())}"
        )

    print(
        f"Long-form OD rows: {len(subset):,}"
    )

    # -------------------------------------------------------------------------
    # Validate zone IDs
    # -------------------------------------------------------------------------

    invalid_origins = sorted(
        set(
            subset["origin_zone_id"]
            .dropna()
        )
        - set(
            official_zone_ids
        )
    )

    invalid_destinations = sorted(
        set(
            subset["destination_zone_id"]
            .dropna()
        )
        - set(
            official_zone_ids
        )
    )

    if invalid_origins:
        raise ValueError(
            f"Unknown origin zone IDs in {period}:\n"
            f"{invalid_origins}"
        )

    if invalid_destinations:
        raise ValueError(
            f"Unknown destination zone IDs in {period}:\n"
            f"{invalid_destinations}"
        )

    # -------------------------------------------------------------------------
    # Aggregate, in case duplicate long-form rows exist
    # -------------------------------------------------------------------------

    grouped = (
        subset
        .groupby(
            [
                "origin_zone_id",
                "destination_zone_id",
            ],
            as_index=False,
        )["trips"]
        .sum()
    )

    # -------------------------------------------------------------------------
    # Pivot to square matrix
    # -------------------------------------------------------------------------

    matrix = (
        grouped
        .pivot(
            index="origin_zone_id",
            columns="destination_zone_id",
            values="trips",
        )
        .reindex(
            index=official_zone_ids,
            columns=official_zone_ids,
            fill_value=0,
        )
        .fillna(0)
    )

    # Trip counts should be integers.
    if not np.allclose(
        matrix.to_numpy(),
        np.round(
            matrix.to_numpy()
        ),
    ):
        raise ValueError(
            f"{period} matrix contains non-integer trip counts."
        )

    matrix = (
        matrix
        .round()
        .astype("int64")
    )

    matrix.index.name = (
        "origin_zone_id"
    )

    matrix.columns.name = (
        "destination_zone_id"
    )

    print(
        f"Matrix shape: {matrix.shape}"
    )

    return matrix


# =============================================================================
# 11. VALIDATE TEMPORAL MATRIX
# =============================================================================

def validate_matrix(
    matrix,
    period,
):

    arr = matrix.to_numpy(
        dtype=np.int64
    )

    if matrix.shape != (
        94,
        94,
    ):
        raise AssertionError(
            f"{period}: expected 94×94 matrix, "
            f"obtained {matrix.shape}."
        )

    total = int(
        arr.sum()
    )

    intra = int(
        np.trace(
            arr
        )
    )

    inter = int(
        total
        - intra
    )

    active_od = int(
        np.count_nonzero(
            arr
        )
    )

    inter_arr = (
        arr.copy()
    )

    np.fill_diagonal(
        inter_arr,
        0,
    )

    active_inter = int(
        np.count_nonzero(
            inter_arr
        )
    )

    expected = EXPECTED[
        period
    ]

    checks = {
        "total": (
            total,
            expected["total"],
        ),

        "intra": (
            intra,
            expected["intra"],
        ),

        "inter": (
            inter,
            expected["inter"],
        ),

        "active_od": (
            active_od,
            expected["active_od"],
        ),

        "active_inter": (
            active_inter,
            expected["active_inter"],
        ),
    }

    print(
        f"\n{period} validation:"
    )

    print(
        f"  Total trips:              {total:,}"
    )

    print(
        f"  Intra-zonal trips:        {intra:,}"
    )

    print(
        f"  Inter-zonal trips:        {inter:,}"
    )

    print(
        f"  Active OD cells:          {active_od:,}"
    )

    print(
        f"  Active inter-zonal cells: {active_inter:,}"
    )

    for metric, (
        actual,
        target,
    ) in checks.items():

        if actual != target:

            raise AssertionError(
                f"{period} validation failed for "
                f"{metric}: expected {target:,}, "
                f"obtained {actual:,}."
            )

    print(
        "  Validation: PASS"
    )

    return {
        "period": period,
        "total_trips": total,
        "intra_zonal_trips": intra,
        "inter_zonal_trips": inter,
        "active_od_cells": active_od,
        "active_interzonal_cells": active_inter,
    }


# =============================================================================
# 12. HEATMAP
# =============================================================================

def make_heatmap(
    matrix,
    period,
    global_vmin,
    global_vmax,
):

    arr = matrix.to_numpy(
        dtype=float
    )

    # Zero cells appear as light grey.
    masked = np.ma.masked_where(
        arr == 0,
        arr,
    )

    # Same palette as Appendix A.
    cmap = (
        mpl.colormaps[
            "YlOrRd"
        ]
        .copy()
    )

    cmap.set_bad(
        color="#f5f5f5"
    )

    fig, ax = plt.subplots(
        figsize=(
            14,
            12,
        )
    )

    im = ax.imshow(
        masked,
        cmap=cmap,
        norm=LogNorm(
            vmin=global_vmin,
            vmax=global_vmax,
        ),
        interpolation="nearest",
        aspect="equal",
    )

    # -------------------------------------------------------------------------
    # Axis labels
    # -------------------------------------------------------------------------

    zone_ids = (
        matrix.index
        .tolist()
    )

    # A label every 5 zones, same philosophy as Figure A.1.
    tick_step = 5

    tick_positions = np.arange(
        0,
        len(zone_ids),
        tick_step,
    )

    tick_labels = [
        zone_ids[i]
        for i in tick_positions
    ]

    ax.set_xticks(
        tick_positions
    )

    ax.set_yticks(
        tick_positions
    )

    ax.set_xticklabels(
        tick_labels,
        rotation=90,
        fontsize=8,
    )

    ax.set_yticklabels(
        tick_labels,
        fontsize=8,
    )

    ax.set_xlabel(
        "Destination zone",
        fontsize=12,
    )

    ax.set_ylabel(
        "Origin zone",
        fontsize=12,
    )

    # -------------------------------------------------------------------------
    # Titles
    # -------------------------------------------------------------------------

    meta = (
        PERIOD_META[
            period
        ]
    )

    fig.suptitle(
        meta["title"],
        fontsize=22,
        fontweight="bold",
        y=0.97,
    )

    ax.set_title(
        (
            f"{meta['figure_no']} | "
            f"{meta['subtitle']}"
        ),
        fontsize=14,
        pad=16,
    )

    # -------------------------------------------------------------------------
    # Colour bar
    # -------------------------------------------------------------------------

    cbar = fig.colorbar(
        im,
        ax=ax,
        fraction=0.045,
        pad=0.03,
    )

    cbar.set_label(
        "Trips per O–D cell (log scale)",
        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # Figure note
    # -------------------------------------------------------------------------

    note = (
        "Rows represent origin zones and columns represent destination zones. "
        "All 94 official Torino statistical zones are retained, including "
        "zero-flow cells and the intra-zonal diagonal. "
        "Colour intensity represents observed trip counts using the same "
        "logarithmic scale across Figures B.1–B.3; "
        "light-grey cells indicate zero observed trips."
    )

    fig.text(
        0.5,
        0.028,
        note,
        ha="center",
        va="center",
        fontsize=9.5,
    )

    plt.tight_layout(
        rect=[
            0.03,
            0.07,
            0.98,
            0.94,
        ]
    )

    output_path = (
        OUTPUT_FILES[
            period
        ]
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        f"Saved -> {output_path}"
    )


# =============================================================================
# 13. MAIN
# =============================================================================

def main():

    print_header(
        "EXERCISE 2 — APPENDIX B TEMPORAL OD HEATMAPS"
    )

    # -------------------------------------------------------------------------
    # Official zone order
    # -------------------------------------------------------------------------

    official_zone_ids = (
        load_official_zone_order()
    )

    # -------------------------------------------------------------------------
    # Temporal OD long-form file
    # -------------------------------------------------------------------------

    temporal_od = (
        load_temporal_od()
    )

    # -------------------------------------------------------------------------
    # Build all matrices
    # -------------------------------------------------------------------------

    matrices = {}

    validation_rows = []

    for period in [
        "AM peak",
        "PM peak",
        "Off-peak",
    ]:

        matrix = build_matrix(
            temporal_od,
            period,
            official_zone_ids,
        )

        validation = (
            validate_matrix(
                matrix,
                period,
            )
        )

        matrices[
            period
        ] = matrix

        validation_rows.append(
            validation
        )

    # -------------------------------------------------------------------------
    # Common logarithmic scale
    # -------------------------------------------------------------------------

    print_header(
        "CALCULATING COMMON COLOUR SCALE"
    )

    positive_values = []

    for matrix in matrices.values():

        arr = matrix.to_numpy(
            dtype=float
        )

        positive = arr[
            arr > 0
        ]

        positive_values.extend(
            positive.tolist()
        )

    if not positive_values:

        raise ValueError(
            "No positive O–D values found."
        )

    global_vmin = max(
        1,
        float(
            min(
                positive_values
            )
        ),
    )

    global_vmax = float(
        max(
            positive_values
        )
    )

    print(
        f"Common positive minimum: {global_vmin:,.0f}"
    )

    print(
        f"Common maximum:          {global_vmax:,.0f}"
    )

    print(
        "One common logarithmic scale will be "
        "used across AM, PM and Off-peak."
    )

    # -------------------------------------------------------------------------
    # Generate figures
    # -------------------------------------------------------------------------

    print_header(
        "GENERATING APPENDIX B HEATMAPS"
    )

    for period in [
        "AM peak",
        "PM peak",
        "Off-peak",
    ]:

        print(
            f"\nCreating {PERIOD_META[period]['figure_no']}..."
        )

        make_heatmap(
            matrices[
                period
            ],
            period,
            global_vmin,
            global_vmax,
        )

    # -------------------------------------------------------------------------
    # Save validation summary
    # -------------------------------------------------------------------------

    validation_df = pd.DataFrame(
        validation_rows
    )

    validation_path = (
        OUTPUT_DIR
        / "Appendix_B_temporal_heatmap_validation.csv"
    )

    validation_df.to_csv(
        validation_path,
        index=False,
    )

    # -------------------------------------------------------------------------
    # Final summary
    # -------------------------------------------------------------------------

    print_header(
        "APPENDIX B COMPLETE"
    )

    print(
        validation_df.to_string(
            index=False
        )
    )

    print(
        "\nGenerated figures:"
    )

    for period in [
        "AM peak",
        "PM peak",
        "Off-peak",
    ]:

        print(
            f"  {PERIOD_META[period]['figure_no']} -> "
            f"{OUTPUT_FILES[period]}"
        )

    print(
        "\nValidation file ->"
    )

    print(
        validation_path
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
    )

    print(
        "- Temporal matrices were reconstructed directly from "
        "system_conventional_period_od_2024.parquet."
    )

    print(
        "- All matrices contain the same 94 official Torino zones."
    )

    print(
        "- Zero-flow O–D cells are retained explicitly."
    )

    print(
        "- AM, PM and Off-peak totals reconcile exactly with the "
        "validated temporal OD pipeline."
    )

    print(
        "- All three figures use identical zone ordering."
    )

    print(
        "- All three figures use one common logarithmic colour scale."
    )

    print(
        "- Heatmaps include both intra-zonal and inter-zonal trips."
    )

    print(
        "\nAll Appendix B checks: PASSED"
    )


if __name__ == "__main__":
    main()