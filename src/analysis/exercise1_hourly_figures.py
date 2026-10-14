from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "hourly"
)

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "hourly"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_1"
    / "hourly"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


HOURLY_FILE = (
    TABLE_DIR
    / "hourly_profile_2024_common.csv"
)

SYSTEM_HEATMAP_FILE = (
    DATA_DIR
    / "system_hourly_weekday_2024_common.parquet"
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

WEEKDAYS_SHORT = [
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
    "Sun",
]


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
#
# NORMALIZED 24-HOUR PROFILE
#
# 100 = operator's mean hourly activity.
#
# Purpose:
# - Compare temporal shape across operators.
# - Remove Bird/Lime/VOI scale differences.
# - Show conventional AM/PM transport periods.
# - Show empirical 2024 scooter-demand peak separately.
# ============================================================

def figure_normalized_hourly_profile():

    if not HOURLY_FILE.exists():

        raise FileNotFoundError(
            HOURLY_FILE
        )

    df = pd.read_csv(
        HOURLY_FILE
    )

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    required_columns = {
        "operator",
        "year",
        "hour",
        "hourly_activity_index",
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:

        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    df = df.loc[
        df["year"] == 2024
    ].copy()

    for operator in OPERATORS:

        subset = df.loc[
            df["operator"] == operator
        ]

        assert (
            subset["hour"].nunique()
            == 24
        ), (
            f"{operator}: expected 24 hourly bins."
        )

    # --------------------------------------------------------
    # Plot
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(11, 6)
    )

    for operator in OPERATORS:

        subset = (
            df.loc[
                df["operator"]
                == operator
            ]
            .sort_values(
                "hour"
            )
        )

        ax.plot(
            subset["hour"],
            subset[
                "hourly_activity_index"
            ],
            marker="o",
            linewidth=2.2,
            label=LABELS[
                operator
            ],
        )

    # --------------------------------------------------------
    # Baseline
    #
    # 100 = mean operator-hour activity
    # --------------------------------------------------------

    ax.axhline(
        100,
        linestyle="--",
        linewidth=1.2,
    )

    # --------------------------------------------------------
    # Conventional AM transport peak
    #
    # 07:00-09:59
    #
    # Because hourly observations are plotted at integer
    # hour centers, the graphical bin boundaries are:
    #
    # 06.5 -> 09.5
    # --------------------------------------------------------

    ax.axvspan(
        6.5,
        9.5,
        alpha=0.08,
        label="AM transport peak",
    )

    # --------------------------------------------------------
    # Conventional PM transport peak
    #
    # 16:00-19:59
    #
    # Graphical boundaries:
    #
    # 15.5 -> 19.5
    # --------------------------------------------------------

    ax.axvspan(
        15.5,
        19.5,
        alpha=0.08,
        label="PM transport peak",
    )

    # --------------------------------------------------------
    # Empirical scooter-demand peak
    #
    # The six highest system-wide hourly bins in the
    # 2024 baseline were:
    #
    # 15, 16, 17, 18, 19, 20
    #
    # Rather than using another shaded region, we use
    # dotted boundaries to clearly distinguish the
    # empirical definition from conventional peaks.
    # --------------------------------------------------------

    ax.axvline(
        14.5,
        linestyle=":",
        linewidth=1.5,
    )

    ax.axvline(
        20.5,
        linestyle=":",
        linewidth=1.5,
    )

    # --------------------------------------------------------
    # Empirical peak label
    # --------------------------------------------------------

    y_min, y_max = (
        ax.get_ylim()
    )

    ax.text(
        17.5,
        y_max
        - 0.035
        * (
            y_max
            - y_min
        ),
        (
            "2024 empirical peak: "
            "15:00–20:59"
        ),
        ha="center",
        va="top",
        fontsize=9,
    )

    # --------------------------------------------------------
    # Axes
    # --------------------------------------------------------

    ax.set_xticks(
        range(
            0,
            24,
            2,
        )
    )

    ax.set_xlim(
        -0.5,
        23.5,
    )

    ax.set_xlabel(
        "Trip start hour"
    )

    ax.set_ylabel(
        "Hourly activity index "
        "(operator mean hour = 100)"
    )

    ax.set_title(
        "Normalized Hour-of-Day Pattern "
        "of Scooter Activity, 2024"
    )

    ax.grid(
        alpha=0.25
    )

    # --------------------------------------------------------
    # Legend
    #
    # Remove accidental duplicate labels.
    # --------------------------------------------------------

    handles, labels = (
        ax.get_legend_handles_labels()
    )

    unique = {}

    for handle, label in zip(
        handles,
        labels,
    ):

        if label not in unique:

            unique[
                label
            ] = handle

    ax.legend(
        unique.values(),
        unique.keys(),
        frameon=False,
        ncol=3,
    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    fig.text(
        0.5,
        0.01,
        (
            "Common detailed-time window: "
            "1 February–31 December 2024. "
            "Conventional AM peak = 07:00–09:59; "
            "PM peak = 16:00–19:59. "
            "Empirical system peak hours = "
            "15:00–20:59."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.045,
            1,
            1,
        ]
    )

    return save_figure(
        fig,
        "hourly_activity_index_2024.png",
    )


# ============================================================
# FIGURE 2
#
# SYSTEM HOUR × WEEKDAY HEATMAP
#
# Values:
#
# Average system trips for each weekday-hour occurrence.
#
# Example:
#
# Friday × 18 means:
# mean number of Bird + Lime + VOI trips observed
# during the 18:00 hour across Fridays in the
# common 2024 detailed-time window.
#
# Peak cells:
#
# Each weekday's maximum activity cell is outlined
# using a rectangle.
# ============================================================

def figure_system_hourly_weekday_heatmap():

    if not SYSTEM_HEATMAP_FILE.exists():

        raise FileNotFoundError(
            SYSTEM_HEATMAP_FILE
        )

    df = pd.read_parquet(
        SYSTEM_HEATMAP_FILE
    )

    value_col = (
        "mean_system_trips_per_weekday_occurrence_at_hour"
    )

    required_columns = {
        "weekday_number",
        "weekday",
        "hour",
        value_col,
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:

        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # --------------------------------------------------------
    # Construct 7 × 24 matrix
    # --------------------------------------------------------

    matrix = (
        df.pivot(
            index="weekday_number",
            columns="hour",
            values=value_col,
        )
        .reindex(
            range(7)
        )
        .reindex(
            columns=range(24)
        )
    )

    assert (
        matrix.shape
        == (
            7,
            24,
        )
    ), (
        "Heatmap matrix must be 7 × 24."
    )

    assert (
        matrix
        .notna()
        .all()
        .all()
    ), (
        "Heatmap matrix contains missing cells."
    )

    # --------------------------------------------------------
    # Plot
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(13, 5.8)
    )

    image = ax.imshow(
        matrix.to_numpy(),
        aspect="auto",
        interpolation="nearest",
    )

    # --------------------------------------------------------
    # Y axis
    # --------------------------------------------------------

    ax.set_yticks(
        range(7)
    )

    ax.set_yticklabels(
        WEEKDAYS_SHORT
    )

    # --------------------------------------------------------
    # X axis
    # --------------------------------------------------------

    ax.set_xticks(
        range(
            0,
            24,
            2,
        )
    )

    ax.set_xticklabels(
        [
            f"{hour:02d}:00"
            for hour
            in range(
                0,
                24,
                2,
            )
        ]
    )

    ax.set_xlabel(
        "Trip start hour"
    )

    ax.set_ylabel(
        "Day of week"
    )

    ax.set_title(
        "System-wide Hour × Weekday "
        "Scooter Activity, 2024"
    )

    # --------------------------------------------------------
    # Colorbar
    # --------------------------------------------------------

    colorbar = fig.colorbar(
        image,
        ax=ax,
        pad=0.02,
    )

    colorbar.set_label(
        "Mean system trips per weekday-hour"
    )

    # --------------------------------------------------------
    # Highlight highest-activity cell for each weekday
    #
    # No text is placed inside the cell because the
    # x-axis already identifies the hour.
    # --------------------------------------------------------

    for weekday_number in range(7):

        row = matrix.loc[
            weekday_number
        ]

        peak_hour = int(
            row.idxmax()
        )

        rectangle = Rectangle(
            (
                peak_hour
                - 0.5,
                weekday_number
                - 0.5,
            ),
            1,
            1,
            fill=False,
            edgecolor="black",
            linewidth=1.8,
        )

        ax.add_patch(
            rectangle
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    fig.text(
        0.5,
        0.01,
        (
            "Common detailed-time window: "
            "1 February–31 December 2024. "
            "Outlined cells identify each weekday's "
            "highest-activity hour."
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[
            0,
            0.045,
            1,
            1,
        ]
    )

    return save_figure(
        fig,
        "system_hourly_weekday_heatmap_2024.png",
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
        "EXERCISE 1 — HOURLY PATTERN FIGURES"
    )

    print(
        "=" * 105
    )

    generated = []

    # --------------------------------------------------------
    # Figure 1
    # --------------------------------------------------------

    generated.append(
        figure_normalized_hourly_profile()
    )

    # --------------------------------------------------------
    # Figure 2
    # --------------------------------------------------------

    generated.append(
        figure_system_hourly_weekday_heatmap()
    )

    # --------------------------------------------------------
    # Terminal output
    # --------------------------------------------------------

    print(
        "\nGenerated figures:"
    )

    for path in generated:

        print(
            path
        )

    print(
        "\n"
        + "=" * 105
    )

    print(
        "VALIDATION / INTERPRETATION"
    )

    print(
        "=" * 105
    )

    print(
        "- Hourly profile is normalized within operator."
    )

    print(
        "- Activity index = 100 represents each "
        "operator's mean hourly activity."
    )

    print(
        "- AM and PM transport peaks are predefined "
        "transport-analysis periods."
    )

    print(
        "- AM peak = 07:00-09:59."
    )

    print(
        "- PM peak = 16:00-19:59."
    )

    print(
        "- Empirical system peak hours are "
        "15:00-20:59."
    )

    print(
        "- Empirical peak boundaries are visually "
        "separated from conventional peak shading."
    )

    print(
        "- Heatmap uses absolute pooled system activity."
    )

    print(
        "- Heatmap values are average trips per "
        "weekday-hour occurrence."
    )

    print(
        "- Heatmap rectangles identify observed "
        "weekday-specific maximum activity cells."
    )

    print(
        "- Both figures use the common "
        "Feb-Dec 2024 detailed-time window."
    )

    print(
        "- VOI January 2024 is excluded because "
        "detailed timestamps are unavailable."
    )

    print(
        "- No behavioural trip-purpose interpretation "
        "is imposed by these figures."
    )

    print(
        "\nAnalysis figures completed successfully."
    )


if __name__ == "__main__":
    main()