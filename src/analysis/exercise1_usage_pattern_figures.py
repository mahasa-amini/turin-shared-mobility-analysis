from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "patterns"
    / "weekday_profile_2024_common.csv"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_1"
    / "patterns"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# CONSTANTS
# ============================================================

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

WEEKDAY_LABELS = [
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
    "Sun",
]


# ============================================================
# FIGURE
# ============================================================

def build_weekday_profile_figure():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            INPUT_FILE
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    fig, ax = plt.subplots(
        figsize=(10, 5.8)
    )

    for operator in OPERATORS:

        subset = (
            df.loc[
                df["operator"] == operator
            ]
            .sort_values(
                "weekday_number"
            )
        )

        ax.plot(
            subset[
                "weekday_number"
            ],
            subset[
                "weekday_activity_index"
            ],
            marker="o",
            linewidth=2.2,
            label=LABELS[
                operator
            ],
        )

    # Operator mean
    ax.axhline(
        100,
        linestyle="--",
        linewidth=1.2,
    )

    ax.set_xticks(
        range(7)
    )

    ax.set_xticklabels(
        WEEKDAY_LABELS
    )

    ax.set_xlabel(
        "Day of week"
    )

    ax.set_ylabel(
        "Activity index (operator mean = 100)"
    )

    ax.set_title(
        "Day-of-Week Pattern of Scooter Activity, 2024"
    )

    ax.grid(
        alpha=0.25
    )

    ax.legend(
        frameon=False,
        ncol=3,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Common detailed-time window: "
            "1 February-31 December 2024. "
            "Index values compare each weekday with "
            "the operator's mean daily activity."
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

    output = (
        FIGURE_DIR
        / "weekday_activity_index_2024.png"
    )

    fig.savefig(
        output,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"Saved -> {output}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 100
    )

    print(
        "EXERCISE 1 — WEEKDAY PATTERN FIGURE"
    )

    print(
        "=" * 100
    )

    build_weekday_profile_figure()

    print(
        "\nIMPORTANT:"
        "\n- The figure uses the common Feb-Dec 2024 detailed-time window."
        "\n- Activity is normalized within operator."
        "\n- 100 represents each operator's mean daily activity."
        "\n- The plot describes day-of-week pattern, not causal travel purpose."
    )


if __name__ == "__main__":
    main()