from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "vehicles"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "vehicles"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_1"
    / "vehicles"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ANNUAL_FILE = (
    DATA_DIR
    / "vehicle_level_annual_observed.parquet"
)

MATCHED_FILE = (
    DATA_DIR
    / "vehicle_level_matched_feb_apr_yoy.parquet"
)

SUMMARY_FILE = (
    TABLE_DIR
    / "vehicle_matched_yoy_summary.csv"
)


OPERATORS = [
    "bird",
    "lime",
    "voi",
]

LABELS = {
    "bird": "Bird",
    "lime": "Lime",
    "voi": "VOI",
}


# ============================================================
# SAVE
# ============================================================

def save_figure(
    fig,
    filename,
):

    path = (
        FIGURE_DIR
        / filename
    )

    fig.savefig(
        path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"Saved -> {path}"
    )

    return path


# ============================================================
# FIGURE 1
# 2024 FULL-YEAR HISTOGRAMS
#
# y-axis = percentage of observed vehicles.
#
# Each operator has its own x scale because trip volumes
# differ substantially.
# ============================================================

def figure_2024_histograms():

    df = pd.read_parquet(
        ANNUAL_FILE
    )

    df = df.loc[
        df["year"] == 2024
    ].copy()

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10, 10),
    )

    for ax, operator in zip(
        axes,
        OPERATORS,
    ):

        subset = df.loc[
            df[
                "operator"
            ] == operator,
            "trips",
        ].dropna()

        weights = np.ones(
            len(subset)
        ) / len(subset)

        ax.hist(
            subset,
            bins=30,
            weights=weights,
            alpha=0.75,
        )

        mean_value = (
            subset.mean()
        )

        median_value = (
            subset.median()
        )

        ax.axvline(
            mean_value,
            linestyle="--",
            linewidth=1.7,
            label=(
                f"Mean = "
                f"{mean_value:.0f}"
            ),
        )

        ax.axvline(
            median_value,
            linestyle=":",
            linewidth=2,
            label=(
                f"Median = "
                f"{median_value:.0f}"
            ),
        )

        ax.yaxis.set_major_formatter(
            PercentFormatter(
                1.0
            )
        )

        ax.set_title(
            LABELS[
                operator
            ],
            loc="left",
        )

        ax.set_xlabel(
            "Trips per observed vehicle"
        )

        ax.set_ylabel(
            "Share of vehicles"
        )

        ax.grid(
            axis="y",
            alpha=0.25,
        )

        ax.legend(
            frameon=False,
        )

    fig.suptitle(
        "Distribution of Trips per Observed Vehicle, 2024",
        fontsize=14,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Complete 2024 calendar-year data. "
            "Observed vehicles are identifiers "
            "with at least one recorded trip."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.035,
            1,
            0.96,
        ]
    )

    return save_figure(
        fig,
        "trips_per_vehicle_histogram_2024.png",
    )


# ============================================================
# FIGURE 2
# MATCHED YOY HISTOGRAMS
#
# Uses the same Feb 1-Apr 29, 88-day comparison window.
#
# Within each operator, 2024 and 2025 use the SAME bin edges.
# This is essential for valid visual comparison.
# ============================================================

def figure_matched_yoy_histograms():

    df = pd.read_parquet(
        MATCHED_FILE
    )

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10, 10),
    )

    for ax, operator in zip(
        axes,
        OPERATORS,
    ):

        subset = df.loc[
            df[
                "operator"
            ] == operator
        ].copy()

        maximum = (
            subset[
                "trips"
            ].max()
        )

        bins = np.linspace(
            0,
            maximum,
            31,
        )

        for year in [
            2024,
            2025,
        ]:

            values = subset.loc[
                subset[
                    "year"
                ] == year,
                "trips",
            ].dropna()

            weights = (
                np.ones(
                    len(values)
                )
                /
                len(values)
            )

            ax.hist(
                values,
                bins=bins,
                weights=weights,
                alpha=0.45,
                label=str(year),
            )

        ax.yaxis.set_major_formatter(
            PercentFormatter(
                1.0
            )
        )

        ax.set_title(
            LABELS[
                operator
            ],
            loc="left",
        )

        ax.set_xlabel(
            "Trips per observed vehicle"
        )

        ax.set_ylabel(
            "Share of vehicles"
        )

        ax.grid(
            axis="y",
            alpha=0.25,
        )

        ax.legend(
            frameon=False,
        )

    fig.suptitle(
        "Trips per Vehicle: Matched 2024 vs 2025 Period",
        fontsize=14,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Feb 1-Apr 29; February 29, 2024 "
            "excluded. Each operator-year covers "
            "88 calendar days."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.035,
            1,
            0.96,
        ]
    )

    return save_figure(
        fig,
        "trips_per_vehicle_histogram_matched_yoy.png",
    )


# ============================================================
# FIGURE 3
# UTILIZATION DECOMPOSITION
#
# Panel A:
# mean number of active vehicles per calendar day
#
# Panel B:
# trips per active vehicle-day
#
# Together they explain growth in total trips.
# ============================================================

def figure_utilization_decomposition():

    df = pd.read_csv(
        SUMMARY_FILE
    )

    operators = OPERATORS

    x = np.arange(
        len(operators)
    )

    width = 0.36

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(9, 9),
    )

    # --------------------------------------------------------
    # Panel A: daily active vehicles
    # --------------------------------------------------------

    pivot_active = (
        df.pivot(
            index="operator",
            columns="year",
            values=(
                "mean_daily_active_vehicles"
            ),
        )
        .reindex(
            operators
        )
    )

    bars_a_2024 = axes[0].bar(
        x - width / 2,
        pivot_active[2024],
        width,
        label="2024",
    )

    bars_a_2025 = axes[0].bar(
        x + width / 2,
        pivot_active[2025],
        width,
        label="2025",
    )

    axes[0].set_xticks(
        x
    )

    axes[0].set_xticklabels(
        [
            LABELS[o]
            for o in operators
        ]
    )

    axes[0].set_ylabel(
        "Mean daily active vehicles"
    )

    axes[0].set_title(
        "A. Vehicles Generating at Least One Trip per Day",
        loc="left",
    )

    axes[0].grid(
        axis="y",
        alpha=0.25,
    )

    axes[0].legend(
        frameon=False,
    )

    axes[0].bar_label(
        bars_a_2024,
        fmt="%.0f",
        padding=3,
    )

    axes[0].bar_label(
        bars_a_2025,
        fmt="%.0f",
        padding=3,
    )

    # --------------------------------------------------------
    # Panel B: trips per active vehicle-day
    # --------------------------------------------------------

    pivot_intensity = (
        df.pivot(
            index="operator",
            columns="year",
            values=(
                "trips_per_active_vehicle_day"
            ),
        )
        .reindex(
            operators
        )
    )

    bars_b_2024 = axes[1].bar(
        x - width / 2,
        pivot_intensity[2024],
        width,
        label="2024",
    )

    bars_b_2025 = axes[1].bar(
        x + width / 2,
        pivot_intensity[2025],
        width,
        label="2025",
    )

    axes[1].set_xticks(
        x
    )

    axes[1].set_xticklabels(
        [
            LABELS[o]
            for o in operators
        ]
    )

    axes[1].set_ylabel(
        "Trips per active vehicle-day"
    )

    axes[1].set_title(
        "B. Usage Intensity of Active Vehicles",
        loc="left",
    )

    axes[1].grid(
        axis="y",
        alpha=0.25,
    )

    axes[1].legend(
        frameon=False,
    )

    axes[1].bar_label(
        bars_b_2024,
        fmt="%.2f",
        padding=3,
    )

    axes[1].bar_label(
        bars_b_2025,
        fmt="%.2f",
        padding=3,
    )

    fig.suptitle(
        "Vehicle Utilization Decomposition: "
        "Matched 2024 vs 2025 Period",
        fontsize=14,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Matched 88-day Feb-Apr window. "
            "Changes in total trips reflect both "
            "observed vehicle activation and use intensity."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.035,
            1,
            0.96,
        ]
    )

    return save_figure(
        fig,
        "vehicle_utilization_decomposition_matched_yoy.png",
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
        "EXERCISE 1 — VEHICLE UTILIZATION FIGURES"
    )

    print(
        "=" * 105
    )

    for path in [
        ANNUAL_FILE,
        MATCHED_FILE,
        SUMMARY_FILE,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                path
            )

    generated = []

    generated.append(
        figure_2024_histograms()
    )

    generated.append(
        figure_matched_yoy_histograms()
    )

    generated.append(
        figure_utilization_decomposition()
    )

    print(
        "\nGenerated figures:"
    )

    for path in generated:

        print(path)

    print(
        "\nIMPORTANT:"
        "\n- 2024 histogram uses the complete calendar year."
        "\n- Matched YoY histograms use identical 88-day windows."
        "\n- Histogram y-axes show vehicle shares, not raw counts."
        "\n- 2024 and 2025 use identical bin edges within each operator."
        "\n- Utilization decomposition separates daily vehicle activation "
        "from trips generated per active vehicle-day."
        "\n- Unique observed vehicles are not interpreted as official fleet size."
    )


if __name__ == "__main__":
    main()