from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# STAGE 7 — FINAL GENERALISED COST FIGURES
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

TABLE_DIR = Path(
    "outputs/tables/generalised_cost"
)

FIGURE_DIR = Path(
    "outputs/figures/generalised_cost"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


BASELINE_FILE = (
    TABLE_DIR
    / "stage5_baseline_generalised_cost.csv"
)

SENSITIVITY_FILE = (
    TABLE_DIR
    / "stage5_vot_sensitivity.csv"
)

PARETO_FILE = (
    TABLE_DIR
    / "stage6_pareto_efficiency.csv"
)


# ------------------------------------------------------------
# MODE LABELS
# ------------------------------------------------------------

SHORT_LABELS = {
    "Private car": "Private car",
    "Car sharing": "Car sharing",
    "Private bicycle": "Private bicycle",
    "Bike sharing": "Bike sharing",
    "Private e-scooter": "Private e-scooter",
    "Shared e-scooter": "Shared e-scooter",
    "Taxi": "Taxi",
    "Ride hailing (Uber)": "Uber",
    "Public transport": "Public transport",
}


# ============================================================
# SAVE FIGURE
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
# GENERALISED COST DECOMPOSITION
# ============================================================

def figure_gc_decomposition():

    df = pd.read_csv(
        BASELINE_FILE
    )

    df = (
        df
        .sort_values(
            "generalised_cost_eur",
            ascending=True,
        )
        .reset_index(
            drop=True
        )
    )

    labels = [
        SHORT_LABELS.get(
            mode,
            mode,
        )
        for mode
        in df["mode"]
    ]

    fig, ax = plt.subplots(
        figsize=(10, 6.5)
    )

    # --------------------------------------------------------
    # Monetary component
    # --------------------------------------------------------

    ax.barh(
        labels,
        df["monetary_cost_eur"],
        label="Monetary cost",
    )

    # --------------------------------------------------------
    # Time component
    # --------------------------------------------------------

    ax.barh(
        labels,
        df["time_cost_eur"],
        left=df["monetary_cost_eur"],
        label="Time cost",
    )

    # --------------------------------------------------------
    # Total GC labels
    # --------------------------------------------------------

    for i, row in df.iterrows():

        ax.text(
            row["generalised_cost_eur"] + 0.6,
            i,
            f"€{row['generalised_cost_eur']:.2f}",
            va="center",
            fontsize=9,
        )

    # Cheapest mode at the top
    ax.invert_yaxis()

    ax.set_xlabel(
        "Round-trip generalised cost (€)"
    )

    ax.set_ylabel(
        "Transport mode"
    )

    ax.set_title(
        "Generalised Cost of the Home–Politecnico Round Trip"
    )

    ax.legend(
        frameon=False
    )

    ax.grid(
        axis="x",
        alpha=0.25,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Baseline Value of Time = €10/hour. "
            "Generalised cost = monetary cost + time cost."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.04,
            1,
            1,
        ]
    )

    return save_figure(
        fig,
        "generalised_cost_decomposition.png",
    )


# ============================================================
# FIGURE 2
# VALUE-OF-TIME SENSITIVITY
# ============================================================

def figure_vot_sensitivity():

    df = pd.read_csv(
        SENSITIVITY_FILE
    )

    fig, ax = plt.subplots(
        figsize=(11, 6.5)
    )

    # --------------------------------------------------------
    # One line per mode
    # --------------------------------------------------------

    for mode in df["mode"].unique():

        subset = (
            df.loc[
                df["mode"]
                == mode
            ]
            .sort_values(
                "vot_eur_hour"
            )
        )

        ax.plot(
            subset["vot_eur_hour"],
            subset["generalised_cost_eur"],
            marker="o",
            linewidth=2,
            label=SHORT_LABELS.get(
                mode,
                mode,
            ),
        )

    ax.set_xlabel(
        "Value of Time (€/hour)"
    )

    ax.set_ylabel(
        "Round-trip generalised cost (€)"
    )

    ax.set_title(
        "Sensitivity of Generalised Cost to Value of Time"
    )

    ax.set_xticks(
        sorted(
            df[
                "vot_eur_hour"
            ].unique()
        )
    )

    ax.grid(
        alpha=0.25
    )

    ax.legend(
        frameon=False,
        bbox_to_anchor=(
            1.02,
            1,
        ),
        loc="upper left",
    )

    fig.text(
        0.5,
        0.01,
        (
            "Sensitivity scenarios: VOT = €5, €10 and €20/hour. "
            "Door-to-door travel times are held constant."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.04,
            0.84,
            1,
        ]
    )

    return save_figure(
        fig,
        "generalised_cost_vot_sensitivity.png",
    )


# ============================================================
# FIGURE 3
# MONEY–TIME PARETO FRONTIER
# ============================================================

def figure_pareto():

    df = pd.read_csv(
        PARETO_FILE
    )

    # --------------------------------------------------------
    # Robust boolean conversion
    # --------------------------------------------------------

    if df[
        "pareto_efficient"
    ].dtype != bool:

        df[
            "pareto_efficient"
        ] = (
            df[
                "pareto_efficient"
            ]
            .astype(str)
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                }
            )
        )

    if df[
        "pareto_efficient"
    ].isna().any():

        raise ValueError(
            "Invalid values found in pareto_efficient."
        )

    # --------------------------------------------------------
    # Split efficient and dominated modes
    # --------------------------------------------------------

    efficient = (
        df.loc[
            df[
                "pareto_efficient"
            ]
        ]
        .sort_values(
            "total_time_min",
            ascending=False,
        )
    )

    dominated = (
        df.loc[
            ~df[
                "pareto_efficient"
            ]
        ]
    )

    fig, ax = plt.subplots(
        figsize=(10, 6.8)
    )

    # --------------------------------------------------------
    # Dominated modes
    # --------------------------------------------------------

    ax.scatter(
        dominated[
            "total_time_min"
        ],
        dominated[
            "monetary_cost_eur"
        ],
        s=75,
        alpha=0.65,
        label="Dominated modes",
    )

    # --------------------------------------------------------
    # Pareto-efficient modes
    # --------------------------------------------------------

    ax.scatter(
        efficient[
            "total_time_min"
        ],
        efficient[
            "monetary_cost_eur"
        ],
        s=130,
        marker="D",
        label="Pareto-efficient modes",
    )

    # --------------------------------------------------------
    # Pareto frontier
    # --------------------------------------------------------

    ax.plot(
        efficient[
            "total_time_min"
        ],
        efficient[
            "monetary_cost_eur"
        ],
        linestyle="--",
        linewidth=1.5,
        label="Pareto frontier",
    )

    # --------------------------------------------------------
    # Custom label offsets
    #
    # Used to avoid overlapping labels for modes
    # located close to one another.
    # --------------------------------------------------------

    label_offsets = {

        "Private bicycle":
            (8, -14),

        "Private e-scooter":
            (8, 8),

        "Shared e-scooter":
            (8, -14),

        "Bike sharing":
            (8, 8),

        "Public transport":
            (8, 5),

        "Car sharing":
            (8, 5),

        "Private car":
            (8, 5),

        "Taxi":
            (8, 5),

        "Ride hailing (Uber)":
            (8, 5),
    }

    # --------------------------------------------------------
    # Mode labels
    # --------------------------------------------------------

    for _, row in df.iterrows():

        label = SHORT_LABELS.get(
            row["mode"],
            row["mode"],
        )

        offset = label_offsets.get(
            row["mode"],
            (6, 5),
        )

        ax.annotate(
            label,
            (
                row[
                    "total_time_min"
                ],
                row[
                    "monetary_cost_eur"
                ],
            ),
            xytext=offset,
            textcoords="offset points",
            fontsize=8.5,
        )

    ax.set_xlabel(
        "Round-trip door-to-door time (min)"
    )

    ax.set_ylabel(
        "Round-trip monetary cost (€)"
    )

    ax.set_title(
        "Money–Time Trade-off and Pareto Efficiency"
    )

    ax.grid(
        alpha=0.25
    )

    ax.legend(
        frameon=False
    )

    fig.text(
        0.5,
        0.01,
        (
            "A mode is Pareto-efficient if no other evaluated mode "
            "is simultaneously cheaper and faster."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.04,
            1,
            1,
        ]
    )

    return save_figure(
        fig,
        "money_time_pareto_frontier.png",
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
        "STAGE 7 — FINAL GENERALISED COST FIGURES"
    )

    print(
        "=" * 105
    )

    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------

    required_files = [
        BASELINE_FILE,
        SENSITIVITY_FILE,
        PARETO_FILE,
    ]

    for path in required_files:

        if not path.exists():

            raise FileNotFoundError(
                path
            )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    generated = []

    generated.append(
        figure_gc_decomposition()
    )

    generated.append(
        figure_vot_sensitivity()
    )

    generated.append(
        figure_pareto()
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\nGenerated figures:"
    )

    for path in generated:

        print(
            path
        )

    print(
        "\nINTERPRETATION NOTES"
    )

    print(
        "- Figure 1 separates monetary and "
        "time-related components of generalised cost."
    )

    print(
        "- Figure 2 tests the sensitivity of "
        "generalised cost to alternative Values of Time."
    )

    print(
        "- Figure 3 evaluates monetary-cost versus "
        "door-to-door-time trade-offs independently of VOT."
    )

    print(
        "- Pareto efficiency does not imply overall "
        "superiority in comfort, safety, reliability "
        "or other unmodelled attributes."
    )

    print(
        "- Private bicycle and private e-scooter are "
        "the Pareto-efficient modes under the current "
        "cost and travel-time assumptions."
    )


if __name__ == "__main__":

    main()