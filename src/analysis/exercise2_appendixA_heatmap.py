from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib as mpl

try:
    import geopandas as gpd
except ImportError:
    gpd = None


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_MATRIX_PATHS = [
    PROJECT_ROOT / "outputs/tables/exercise_2/od/od_matrix_system_2024.csv",
    PROJECT_ROOT / "outputs/report/exercise_2/appendices/Appendix_A_system_all_day_OD_matrix_94x94.csv",
]

ZONING_PATH = PROJECT_ROOT / "data/processed/exercise_2/zoning/torino_statistical_zones.gpkg"

OUTPUT_DIR = PROJECT_ROOT / "outputs/report/exercise_2/appendices"
OUTPUT_FIG = OUTPUT_DIR / "Figure_A1_all_day_OD_matrix_heatmap.png"


# =============================================================================
# HELPERS
# =============================================================================

def locate_matrix_file(paths):
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not locate system all-day OD matrix CSV in any expected path."
    )


def load_official_zone_order(zoning_path):
    if gpd is None:
        print("geopandas not installed -> official zone ordering skipped.")
        return None

    if not zoning_path.exists():
        print("Official zoning file not found -> official zone ordering skipped.")
        return None

    gdf = gpd.read_file(zoning_path)
    if "zone_id" not in gdf.columns:
        print("zone_id field not found in zoning -> official zone ordering skipped.")
        return None

    zone_ids = gdf["zone_id"].astype(str).tolist()
    print(f"Loaded official zoning order: {len(zone_ids)} zones")
    return zone_ids


def clean_labels(labels):
    return [str(x).strip() for x in labels]


def ensure_square_matrix(df):
    if df.shape[0] != df.shape[1]:
        raise ValueError(f"Matrix is not square: shape={df.shape}")


def reorder_to_official(df, official_ids):
    if official_ids is None:
        return df

    row_ids = clean_labels(df.index.tolist())
    col_ids = clean_labels(df.columns.tolist())

    df.index = row_ids
    df.columns = col_ids

    missing_rows = [z for z in official_ids if z not in row_ids]
    missing_cols = [z for z in official_ids if z not in col_ids]
    extra_rows = [z for z in row_ids if z not in official_ids]
    extra_cols = [z for z in col_ids if z not in official_ids]

    if missing_rows or missing_cols or extra_rows or extra_cols:
        raise ValueError(
            "Matrix labels do not match official zoning.\n"
            f"Missing rows: {missing_rows[:10]}\n"
            f"Missing cols: {missing_cols[:10]}\n"
            f"Extra rows: {extra_rows[:10]}\n"
            f"Extra cols: {extra_cols[:10]}"
        )

    df = df.loc[official_ids, official_ids]
    return df


def validate_numeric_matrix(df):
    if not np.issubdtype(df.to_numpy().dtype, np.number):
        raise TypeError("Matrix contains non-numeric values.")

    if (df.to_numpy() < 0).any():
        raise ValueError("Matrix contains negative values.")


def summarise_matrix(df):
    arr = df.to_numpy()
    diag = np.diag(arr)
    total = int(arr.sum())
    intra = int(diag.sum())
    inter = int(total - intra)
    active_pairs = int((arr > 0).sum())
    active_inter = int(((arr > 0) & (~np.eye(arr.shape[0], dtype=bool))).sum())

    print("\n" + "=" * 100)
    print("APPENDIX A HEATMAP SUMMARY")
    print("=" * 100)
    print(f"Matrix shape:                {df.shape[0]} x {df.shape[1]}")
    print(f"Possible OD cells:           {df.shape[0] * df.shape[1]:,}")
    print(f"Total valid OD trips:        {total:,}")
    print(f"Intra-zonal trips:           {intra:,}")
    print(f"Inter-zonal trips:           {inter:,}")
    print(f"Active OD cells:             {active_pairs:,}")
    print(f"Active inter-zonal cells:    {active_inter:,}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "=" * 100)
    print("EXERCISE 2 — APPENDIX A HEATMAP")
    print("=" * 100)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    matrix_path = locate_matrix_file(CANDIDATE_MATRIX_PATHS)
    print(f"Using matrix file:\n{matrix_path}")

    df = pd.read_csv(matrix_path, index_col=0)
    df.index = clean_labels(df.index)
    df.columns = clean_labels(df.columns)

    ensure_square_matrix(df)
    validate_numeric_matrix(df)

    official_ids = load_official_zone_order(ZONING_PATH)
    df = reorder_to_official(df, official_ids)

    summarise_matrix(df)

    arr = df.to_numpy(dtype=float)

    # Mask zeros so they remain visible as empty / very light cells
    masked = np.ma.masked_where(arr == 0, arr)

    cmap = mpl.colormaps["YlOrRd"].copy()
    cmap.set_bad(color="#f5f5f5")

    positive_vals = arr[arr > 0]
    if len(positive_vals) == 0:
        raise ValueError("Matrix contains no positive flows.")

    vmin = max(1, positive_vals.min())
    vmax = positive_vals.max()

    fig, ax = plt.subplots(figsize=(14, 12))

    im = ax.imshow(
        masked,
        cmap=cmap,
        norm=LogNorm(vmin=vmin, vmax=vmax),
        interpolation="nearest",
        aspect="equal"
    )

    n = df.shape[0]
    tick_step = 5 if n <= 100 else 10
    tick_positions = np.arange(0, n, tick_step)
    tick_labels = [df.index[i] for i in tick_positions]

    ax.set_xticks(tick_positions)
    ax.set_yticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=90, fontsize=8)
    ax.set_yticklabels(tick_labels, fontsize=8)

    ax.set_xlabel("Destination zone", fontsize=12)
    ax.set_ylabel("Origin zone", fontsize=12)

    fig.suptitle(
        "Complete All-day Origin–Destination Matrix — Turin, 2024",
        fontsize=22,
        fontweight="bold",
        y=0.97
    )
    ax.set_title(
        "Figure A.1 | Official 94 × 94 system-wide e-scooter O–D matrix",
        fontsize=14,
        pad=16
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("Trips per O–D cell (log scale)", fontsize=11)

    note = (
        "Rows represent origin zones and columns represent destination zones. "
        "All 94 official Torino statistical zones are retained, including zero-flow cells "
        "and the intra-zonal diagonal. Colour intensity shows trip counts by O–D cell."
    )
    fig.text(
        0.5, 0.03, note,
        ha="center", va="center",
        fontsize=10
    )

    plt.tight_layout(rect=[0.03, 0.07, 0.98, 0.94])
    fig.savefig(OUTPUT_FIG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print("\nSaved heatmap ->")
    print(OUTPUT_FIG)
    print("\nDONE.")


if __name__ == "__main__":
    main()