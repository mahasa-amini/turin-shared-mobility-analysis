from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = (
    PROJECT_ROOT
    / "audit"
    / "exercise_3"
    / "temporal_adduction"
    / "pt_interaction_by_transport_period_100m.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_3"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FIGURE = (
    OUTPUT_DIR
    / "am_pm_access_egress_winter_summer.png"
)

OUTPUT_TABLE = (
    OUTPUT_DIR
    / "am_pm_access_egress_figure_data.csv"
)

TARGET_OPERATOR = "system"

TARGET_PERIODS = [
    "AM peak",
    "PM peak",
]

SEASON_CONFIG = {
    "winter_february": {
        "title": "Winter — February 2024",
    },
    "summer_july": {
        "title": "Summer — July 2024",
    },
}


# =============================================================================
# LOAD / VALIDATE
# =============================================================================

def load_figure_data() -> pd.DataFrame:

    if not INPUT_CSV.exists():

        raise FileNotFoundError(
            "Temporal interaction summary not found:\n"
            f"{INPUT_CSV}"
        )

    df = pd.read_csv(
        INPUT_CSV,
        dtype={
            "operator": "string",
            "season": "string",
            "transport_period": "string",
        },
    )

    required = [
        "operator",
        "season",
        "transport_period",
        "trips",
        "access_pct",
        "egress_pct",
        "feeder_total_pct",
        "egress_minus_access_pp",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise RuntimeError(
            f"Required columns missing: {missing}"
        )

    figure_df = (
        df.loc[
            (df["operator"] == TARGET_OPERATOR)
            &
            (df["season"].isin(SEASON_CONFIG))
            &
            (df["transport_period"].isin(TARGET_PERIODS))
        ]
        .copy()
    )

    expected_rows = (
        len(SEASON_CONFIG)
        * len(TARGET_PERIODS)
    )

    if len(figure_df) != expected_rows:

        raise RuntimeError(
            "Unexpected number of system AM/PM rows.\n"
            f"Expected: {expected_rows}\n"
            f"Observed: {len(figure_df)}"
        )

    if figure_df.duplicated(
        [
            "season",
            "transport_period",
        ]
    ).any():

        raise RuntimeError(
            "Duplicate season × transport-period rows found."
        )

    figure_df[
        "period_order"
    ] = (
        figure_df[
            "transport_period"
        ]
        .map(
            {
                "AM peak": 0,
                "PM peak": 1,
            }
        )
    )

    figure_df[
        "season_order"
    ] = (
        figure_df[
            "season"
        ]
        .map(
            {
                "winter_february": 0,
                "summer_july": 1,
            }
        )
    )

    figure_df = (
        figure_df
        .sort_values(
            [
                "season_order",
                "period_order",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return figure_df


# =============================================================================
# TERMINAL AUDIT
# =============================================================================

def build_audit_table(
    figure_df: pd.DataFrame,
) -> pd.DataFrame:

    audit = (
        figure_df[
            [
                "season",
                "transport_period",
                "trips",
                "access_pct",
                "egress_pct",
                "feeder_total_pct",
                "egress_minus_access_pp",
            ]
        ]
        .copy()
    )

    # Positive:
    # access is greater than egress.
    #
    # Negative:
    # egress is greater than access.
    audit[
        "access_minus_egress_pp"
    ] = (
        audit[
            "access_pct"
        ]
        -
        audit[
            "egress_pct"
        ]
    )

    return audit


# =============================================================================
# PANEL PLOTTING
# =============================================================================

def plot_season_panel(
    ax,
    season_df: pd.DataFrame,
    title: str,
    shared_ymax: float,
    show_ylabel: bool,
):

    season_df = (
        season_df
        .sort_values(
            "period_order"
        )
        .copy()
    )

    access_values = (
        season_df[
            "access_pct"
        ]
        .astype(float)
        .to_numpy()
    )

    egress_values = (
        season_df[
            "egress_pct"
        ]
        .astype(float)
        .to_numpy()
    )

    trip_counts = (
        season_df[
            "trips"
        ]
        .astype(int)
        .to_numpy()
    )

    x = np.arange(
        len(season_df)
    )

    bar_width = 0.34

    # =========================================================================
    # BARS
    # =========================================================================

    bars_access = ax.bar(
        x - bar_width / 2,
        access_values,
        width=bar_width,
        label="Potential access / first-mile",
    )

    bars_egress = ax.bar(
        x + bar_width / 2,
        egress_values,
        width=bar_width,
        label="Potential egress / last-mile",
    )

    # =========================================================================
    # BAR VALUE LABELS
    # =========================================================================

    for bar in bars_access:

        value = bar.get_height()

        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.35,
            f"{value:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    for bar in bars_egress:

        value = bar.get_height()

        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.35,
            f"{value:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    # =========================================================================
    # ACCESS / EGRESS DIFFERENCE
    # =========================================================================

    for i, (
        access,
        egress,
        trips,
    ) in enumerate(
        zip(
            access_values,
            egress_values,
            trip_counts,
        )
    ):

        difference = (
            access
            - egress
        )

        pair_top = max(
            access,
            egress,
        )

        if difference > 0:

            direction_text = (
                f"Access +{difference:.1f} pp"
            )

        elif difference < 0:

            direction_text = (
                f"Egress +{abs(difference):.1f} pp"
            )

        else:

            direction_text = (
                "Balanced"
            )

        # Directional difference
        ax.text(
            i,
            pair_top + 2.25,
            direction_text,
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

        # Number of trips in period
        ax.text(
            i,
            pair_top + 1.25,
            f"n = {trips:,}",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )

    # =========================================================================
    # PANEL TITLE
    # =========================================================================

    ax.set_title(
        title,
        fontsize=14,
        pad=12,
    )

    # =========================================================================
    # X AXIS
    # =========================================================================

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        [
            "AM peak\n07:00–09:59",
            "PM peak\n16:00–19:59",
        ],
        fontsize=11,
    )

    # =========================================================================
    # Y AXIS
    # =========================================================================

    ax.set_ylim(
        0,
        shared_ymax,
    )

    if show_ylabel:

        ax.set_ylabel(
            "Share of scooter trips (%)",
            fontsize=11,
        )

    else:

        ax.set_ylabel(
            ""
        )

    # =========================================================================
    # STYLE
    # =========================================================================

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    ax.set_axisbelow(
        True
    )

    ax.spines[
        "top"
    ].set_visible(
        False
    )

    ax.spines[
        "right"
    ].set_visible(
        False
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "=" * 100
    )

    print(
        "EXERCISE 3 — AM / PM POTENTIAL ACCESS-EGRESS FIGURE"
    )

    print(
        "=" * 100
    )

    # =========================================================================
    # LOAD DATA
    # =========================================================================

    figure_df = (
        load_figure_data()
    )

    audit = (
        build_audit_table(
            figure_df
        )
    )

    audit.to_csv(
        OUTPUT_TABLE,
        index=False,
    )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "SYSTEM AM / PM ACCESS-EGRESS FIGURE DATA — 100 m"
    )

    print(
        "=" * 100
    )

    print(
        audit.to_string(
            index=False,
            float_format=lambda x: (
                f"{x:.2f}"
            ),
        )
    )

    # =========================================================================
    # SHARED Y SCALE
    # =========================================================================

    maximum_value = max(
        figure_df[
            "access_pct"
        ].max(),
        figure_df[
            "egress_pct"
        ].max(),
    )

    # Leave enough room for:
    #
    # bar %
    # n
    # access/egress pp difference
    shared_ymax = (
        np.ceil(
            (
                maximum_value
                + 6.5
            )
            / 5
        )
        * 5
    )

    # =========================================================================
    # FIGURE
    # =========================================================================

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14, 7.5),
        sharey=True,
    )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    #
    # Do not use constrained_layout here.
    # We explicitly reserve space for:
    #
    # - main title
    # - legend
    # - panel titles
    # - x labels
    # - methodological footer
    # -------------------------------------------------------------------------

    fig.subplots_adjust(
        left=0.07,
        right=0.98,
        bottom=0.17,
        top=0.77,
        wspace=0.08,
    )

    # =========================================================================
    # PANELS
    # =========================================================================

    season_order = [
        "winter_february",
        "summer_july",
    ]

    for i, season in enumerate(
        season_order
    ):

        season_df = (
            figure_df.loc[
                figure_df[
                    "season"
                ]
                == season
            ]
            .copy()
        )

        plot_season_panel(
            ax=axes[i],
            season_df=season_df,
            title=(
                SEASON_CONFIG[
                    season
                ][
                    "title"
                ]
            ),
            shared_ymax=shared_ymax,
            show_ylabel=(
                i == 0
            ),
        )

    # =========================================================================
    # SHARED LEGEND
    # =========================================================================

    handles, labels = (
        axes[0]
        .get_legend_handles_labels()
    )

    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            0.855,
        ),
        ncol=2,
        frameon=False,
        fontsize=11,
    )

    # =========================================================================
    # MAIN TITLE
    # =========================================================================

    fig.suptitle(
        (
            "Potential Public-Transport Access and Egress "
            "during Scooter Peak Periods"
        ),
        fontsize=17,
        y=0.965,
    )

    # =========================================================================
    # FOOTER
    # =========================================================================

    fig.text(
        0.5,
        0.055,
        (
            "100 m endpoint-to-PT-stop threshold. "
            "Access and egress indicate spatial feeder potential, "
            "not observed transfers."
        ),
        ha="center",
        va="center",
        fontsize=9.5,
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    fig.savefig(
        OUTPUT_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        "\nSaved -> "
        f"{OUTPUT_FIGURE}"
    )

    print(
        "Figure data -> "
        f"{OUTPUT_TABLE}"
    )

    # =========================================================================
    # DIRECTIONAL INTERPRETATION
    # =========================================================================

    print(
        "\n"
        + "=" * 100
    )

    print(
        "DIRECTIONAL INTERPRETATION"
    )

    print(
        "=" * 100
    )

    for season in season_order:

        season_rows = (
            audit.loc[
                audit[
                    "season"
                ]
                == season
            ]
            .set_index(
                "transport_period"
            )
        )

        am_gap = float(
            season_rows.loc[
                "AM peak",
                "access_minus_egress_pp",
            ]
        )

        pm_gap = float(
            season_rows.loc[
                "PM peak",
                "access_minus_egress_pp",
            ]
        )

        print(
            f"\n{season}"
        )

        print(
            "AM peak: "
            f"access - egress = "
            f"{am_gap:+.2f} pp"
        )

        print(
            "PM peak: "
            f"access - egress = "
            f"{pm_gap:+.2f} pp"
        )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "FIGURE VALIDATION"
    )

    print(
        "=" * 100
    )

    print(
        "- Winter and summer use one shared y-axis scale."
    )

    print(
        "- AM and PM definitions match the Exercise 1/2 "
        "transport-period definitions."
    )

    print(
        "- Access/egress percentages are calculated relative "
        "to all scooter trips in each period."
    )

    print(
        "- Access-minus-egress is expressed in percentage points."
    )

    print(
        "- Positive values indicate stronger potential "
        "first-mile orientation."
    )

    print(
        "- Negative values indicate stronger potential "
        "last-mile orientation."
    )

    print(
        "- These are spatial feeder indicators, "
        "not observed multimodal transfers."
    )


if __name__ == "__main__":

    main()