from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

REVENUE_COMPOSITION_FILE = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "revenue_diagnostics"
    / "revenue_composition_2024.csv"
)

BASE_COST_FILE = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "costs"
    / "base_case_profitability_2024.csv"
)

SCENARIO_FILE = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "costs"
    / "cost_profitability_scenarios_2024.csv"
)

OAT_FILE = (
    ROOT
    / "outputs"
    / "tables"
    / "exercise_5"
    / "robustness"
    / "one_at_a_time_sensitivity_2024.csv"
)

FIG_DIR = (
    ROOT
    / "outputs"
    / "figures"
    / "exercise_5"
)

FIG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# DISPLAY ORDER
# =============================================================================

OPERATORS = [
    "bird",
    "lime",
    "voi",
]

OPERATOR_LABELS = {
    "bird": "Bird",
    "lime": "Lime",
    "voi": "VOI",
}

SCENARIOS = [
    "low",
    "base",
    "high",
]


# =============================================================================
# COLORS
#
# Consistent across all figures.
# =============================================================================

UNLOCK_COLOR = "#4C78A8"
TIME_COLOR = "#72B7B2"

COST_COLORS = {
    "spares_maintenance_cost_eur":
        "#4C78A8",

    "vehicle_personnel_charging_cost_eur":
        "#F58518",

    "other_direct_vehicle_opex_eur":
        "#E45756",

    "market_overhead_including_insurance_eur":
        "#72B7B2",

    "annual_depreciation_eur":
        "#B279A2",
}

SCENARIO_COLORS = {
    "low": "#59A14F",
    "base": "#4C78A8",
    "high": "#E15759",
}

OAT_LOW_COLOR = "#59A14F"
OAT_HIGH_COLOR = "#E15759"


# =============================================================================
# HELPERS
# =============================================================================

def euro_formatter(value, pos=None):

    abs_value = abs(value)

    if abs_value >= 1_000_000:
        return f"€{value / 1_000_000:.1f}m"

    if abs_value >= 1_000:
        return f"€{value / 1_000:.0f}k"

    return f"€{value:.0f}"


def euro_label(value):

    sign = "-" if value < 0 else ""

    value = abs(value)

    if value >= 1_000_000:
        return f"{sign}€{value / 1_000_000:.2f}m"

    if value >= 1_000:
        return f"{sign}€{value / 1_000:.0f}k"

    return f"{sign}€{value:.0f}"


def save_figure(fig, stem):

    png = (
        FIG_DIR
        / f"{stem}.png"
    )

    pdf = (
        FIG_DIR
        / f"{stem}.pdf"
    )

    fig.savefig(
        png,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )

    fig.savefig(
        pdf,
        bbox_inches="tight",
        facecolor="white",
    )

    print(
        f"Saved -> {png}"
    )

    print(
        f"Saved -> {pdf}"
    )


def style_axis(ax):

    ax.spines[
        "top"
    ].set_visible(False)

    ax.spines[
        "right"
    ].set_visible(False)

    ax.grid(
        axis="y",
        alpha=0.20,
        linewidth=0.8,
    )

    ax.set_axisbelow(True)


# =============================================================================
# FIGURE 1
#
# ESTIMATED PAYG REVENUE COMPOSITION
# =============================================================================

def figure_1_revenue_composition():

    df = pd.read_csv(
        REVENUE_COMPOSITION_FILE
    )

    df["operator"] = (
        df["operator"]
        .astype(str)
        .str.lower()
    )

    df = (
        df.set_index(
            "operator"
        )
        .loc[
            OPERATORS
        ]
        .reset_index()
    )

    x = np.arange(
        len(df)
    )

    unlock = (
        df[
            "unlock_revenue_eur"
        ]
        .to_numpy()
    )

    time = (
        df[
            "time_revenue_known_eur"
        ]
        .to_numpy()
    )

    total = (
        df[
            "total_payg_estimate_eur"
        ]
        .to_numpy()
    )

    unlock_share = (
        df[
            "unlock_share_pct"
        ]
        .to_numpy()
    )

    time_share = (
        df[
            "time_share_pct"
        ]
        .to_numpy()
    )

    fig, ax = plt.subplots(
        figsize=(9.2, 6.3)
    )

    width = 0.62

    bars_unlock = ax.bar(
        x,
        unlock,
        width=width,
        label="Unlock fee",
        color=UNLOCK_COLOR,
        edgecolor="white",
        linewidth=0.7,
    )

    bars_time = ax.bar(
        x,
        time,
        width=width,
        bottom=unlock,
        label="Time-based charge",
        color=TIME_COLOR,
        edgecolor="white",
        linewidth=0.7,
    )

    # -------------------------------------------------------------------------
    # Labels
    # -------------------------------------------------------------------------

    for i in range(
    len(df)
    ):

        operator = df.loc[
            i,
            "operator",
        ]

        # -------------------------------------------------------------------------
        # Percentage labels
        # Bird/Lime: inside bars
        # VOI: outside because the bar is too short for clean internal labels
        # -------------------------------------------------------------------------

        if operator != "voi":

            ax.text(
                x[i],
                unlock[i] / 2,
                f"{unlock_share[i]:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                fontweight="bold",
            )

            ax.text(
                x[i],
                unlock[i]
                +
                time[i] / 2,
                f"{time_share[i]:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                color="black",
                fontweight="bold",
            )

        else:

            label_x = (
                x[i]
                +
                width / 2
                +
                0.06
            )

            ax.text(
                label_x,
                unlock[i] / 2,
                f"Unlock {unlock_share[i]:.1f}%",
                ha="left",
                va="center",
                fontsize=8.5,
                color=UNLOCK_COLOR,
                fontweight="bold",
            )

            ax.text(
                label_x,
                unlock[i]
                +
                time[i] / 2,
                f"Time {time_share[i]:.1f}%",
                ha="left",
                va="center",
                fontsize=8.5,
                color=TIME_COLOR,
                fontweight="bold",
            )

        # -------------------------------------------------------------------------
        # Total revenue label
        # -------------------------------------------------------------------------

        ax.text(
            x[i],
            total[i]
            +
            total.max() * 0.025,
            euro_label(
                total[i]
            ),
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        [
            OPERATOR_LABELS[o]
            for o in OPERATORS
        ],
        fontsize=11,
    )
    ax.set_xlim(
        -0.5,
        len(df) - 0.25,
    )

    ax.set_ylabel(
        "Estimated gross PAYG fare revenue (€)",
        fontsize=11,
    )

    ax.set_title(
        "Estimated PAYG Fare Revenue and Revenue Composition — 2024",
        fontsize=14,
        fontweight="bold",
        pad=14,
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            euro_formatter
        )
    )

    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    style_axis(
        ax
    )

    ax.set_ylim(
        0,
        total.max()
        * 1.16,
    )

    fig.text(
        0.5,
        0.01,
        (
            "PAYG scenario based on the locked 2024 Torino tariff assumptions. "
            "Values represent estimated gross fare billings, not audited company revenue."
        ),
        ha="center",
        fontsize=8.5,
    )

    fig.tight_layout(
        rect=[
            0,
            0.05,
            1,
            1,
        ]
    )

    save_figure(
        fig,
        "figure5_1_revenue_composition_2024",
    )

    plt.close(
        fig
    )


# =============================================================================
# FIGURE 2
#
# BASE-CASE COST BREAKDOWN
# =============================================================================

def figure_2_base_cost_breakdown():

    df = pd.read_csv(
        BASE_COST_FILE
    )

    df["operator"] = (
        df["operator"]
        .astype(str)
        .str.lower()
    )

    df = (
        df.set_index(
            "operator"
        )
        .loc[
            OPERATORS
        ]
        .reset_index()
    )

    components = [
        (
            "spares_maintenance_cost_eur",
            "Maintenance / spares",
        ),
        (
            "vehicle_personnel_charging_cost_eur",
            "Vehicle personnel / charging",
        ),
        (
            "other_direct_vehicle_opex_eur",
            "Other direct vehicle OPEX",
        ),
        (
            "market_overhead_including_insurance_eur",
            "Market overhead incl. insurance",
        ),
        (
            "annual_depreciation_eur",
            "Depreciation",
        ),
    ]

    x = np.arange(
        len(df)
    )

    fig, ax = plt.subplots(
        figsize=(10.2, 6.7)
    )

    bottom = np.zeros(
        len(df)
    )

    width = 0.58

    for column, label in components:

        values = (
            df[
                column
            ]
            .to_numpy()
        )

        ax.bar(
            x,
            values,
            width=width,
            bottom=bottom,
            label=label,
            color=COST_COLORS[
                column
            ],
            edgecolor="white",
            linewidth=0.7,
        )

        bottom += values

    revenue = (
        df[
            "estimated_gross_payg_revenue_eur"
        ]
        .to_numpy()
    )

    profit = (
        df[
            "operating_profit_proxy_eur"
        ]
        .to_numpy()
    )

    # -------------------------------------------------------------------------
    # Revenue markers
    # -------------------------------------------------------------------------

    ax.scatter(
        x,
        revenue,
        marker="D",
        s=75,
        color="black",
        zorder=5,
        label="Estimated PAYG revenue",
    )

    # connector: revenue vs cost
    for i in range(
        len(df)
    ):

        ax.plot(
            [
                x[i],
                x[i],
            ],
            [
                bottom[i],
                revenue[i],
            ],
            color="black",
            linewidth=1.0,
            linestyle="--",
            alpha=0.6,
        )

        profit_text = (
            f"Profit {euro_label(profit[i])}"
            if profit[i] >= 0
            else
            f"Loss {euro_label(profit[i])}"
        )

        y_position = max(
            bottom[i],
            revenue[i],
        )

        ax.text(
            x[i],
            y_position
            +
            max(
                revenue.max(),
                bottom.max(),
            )
            * 0.025,
            profit_text,
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
        )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        [
            OPERATOR_LABELS[o]
            for o in OPERATORS
        ],
        fontsize=11,
    )

    ax.set_ylabel(
        "Annual modeled value (€)",
        fontsize=11,
    )

    ax.set_title(
        "Base-Case Cost Structure and Modeled Profitability — 2024",
        fontsize=14,
        fontweight="bold",
        pad=14,
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            euro_formatter
        )
    )

    ax.legend(
        frameon=False,
        fontsize=8.5,
        ncol=2,
        loc="upper left",
    )

    style_axis(
        ax
    )

    max_value = max(
        revenue.max(),
        bottom.max(),
    )

    ax.set_ylim(
        0,
        max_value
        * 1.20,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Base scenario: service-span fleet proxy, base direct-OPEX benchmark, "
            "base market overhead and base depreciation assumptions. "
            "Electricity memo cost is excluded from primary total cost."
        ),
        ha="center",
        fontsize=8.3,
    )

    fig.tight_layout(
        rect=[
            0,
            0.06,
            1,
            1,
        ]
    )

    save_figure(
        fig,
        "figure5_2_base_cost_breakdown_2024",
    )

    plt.close(
        fig
    )


# =============================================================================
# FIGURE 3
#
# COMBINED LOW / BASE / HIGH PROFITABILITY
# =============================================================================

def figure_3_profitability_scenarios():

    df = pd.read_csv(
        SCENARIO_FILE
    )

    df["operator"] = (
        df["operator"]
        .astype(str)
        .str.lower()
    )

    df["scenario"] = (
        df["scenario"]
        .astype(str)
        .str.lower()
    )

    x = np.arange(
        len(OPERATORS)
    )

    width = 0.23

    fig, ax = plt.subplots(
        figsize=(10.2, 6.5)
    )

    offsets = {
        "low": -width,
        "base": 0,
        "high": width,
    }

    for scenario in SCENARIOS:

        values = []

        for operator in OPERATORS:

            value = (
                df.loc[
                    (
                        df[
                            "operator"
                        ]
                        == operator
                    )
                    &
                    (
                        df[
                            "scenario"
                        ]
                        == scenario
                    ),
                    "operating_profit_proxy_eur",
                ]
                .iloc[0]
            )

            values.append(
                value
            )

        values = np.asarray(
            values
        )

        bars = ax.bar(
            x
            +
            offsets[
                scenario
            ],
            values,
            width=width,
            label=scenario.capitalize(),
            color=SCENARIO_COLORS[
                scenario
            ],
            edgecolor="white",
            linewidth=0.7,
        )

        for bar, value in zip(
            bars,
            values,
        ):

            if value >= 0:
                va = "bottom"
                y = value + 40_000
            else:
                va = "top"
                y = value - 40_000

            ax.text(
                bar.get_x()
                +
                bar.get_width()
                / 2,
                y,
                euro_label(
                    value
                ),
                ha="center",
                va=va,
                fontsize=8.1,
                rotation=90,
            )

    ax.axhline(
        0,
        color="black",
        linewidth=1.1,
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        [
            OPERATOR_LABELS[o]
            for o in OPERATORS
        ],
        fontsize=11,
    )

    ax.set_ylabel(
        "Operating profit / loss proxy (€)",
        fontsize=11,
    )

    ax.set_title(
        "Modeled Profitability Under Combined Cost Scenarios — 2024",
        fontsize=14,
        fontweight="bold",
        pad=14,
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            euro_formatter
        )
    )

    ax.legend(
        frameon=False,
        ncol=3,
        loc="upper left",
    )

    style_axis(
        ax
    )
    # -------------------------------------------------------------------------
    # Add vertical headroom for value labels
    # -------------------------------------------------------------------------

    all_profit_values = (
        df[
            "operating_profit_proxy_eur"
        ]
        .to_numpy()
    )

    data_min = min(
        0,
        all_profit_values.min(),
    )

    data_max = max(
        0,
        all_profit_values.max(),
    )

    data_range = (
        data_max
        -
        data_min
    )

    ax.set_ylim(
        data_min
        -
        0.08
        * data_range,

        data_max
        +
        0.15
        * data_range,
    )
    fig.text(
        0.5,
        0.01,
        (
            "Low/Base/High are combined scenario envelopes: fleet exposure, depreciation, "
            "direct OPEX and market overhead change simultaneously. "
            "They are not statistical confidence intervals."
        ),
        ha="center",
        fontsize=8.4,
    )

    fig.tight_layout(
        rect=[
            0,
            0.06,
            1,
            1,
        ]
    )

    save_figure(
        fig,
        "figure5_3_profitability_scenarios_2024",
    )

    plt.close(
        fig
    )


# =============================================================================
# FIGURE 4
#
# ONE-AT-A-TIME SENSITIVITY
#
# Tornado-style:
#   positive delta = improves profit relative to Base
#   negative delta = worsens profit relative to Base
# =============================================================================

def figure_4_oat_sensitivity():

    df = pd.read_csv(
        OAT_FILE
    )

    df["operator"] = (
        df["operator"]
        .astype(str)
        .str.lower()
    )

    df["level"] = (
        df["level"]
        .astype(str)
        .str.lower()
    )

    driver_labels = {
        "fleet_exposure":
            "Fleet exposure",

        "annual_depreciation":
            "Annual depreciation",

        "direct_vehicle_opex":
            "Direct vehicle OPEX",

        "market_overhead":
            "Market overhead",
    }

    fig, axes = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(10.5, 11.0),
    )

    for ax, operator in zip(
        axes,
        OPERATORS,
    ):

        op = df.loc[
            df[
                "operator"
            ]
            == operator
        ].copy()

        rows = []

        for driver in (
            op[
                "driver"
            ]
            .unique()
        ):

            driver_data = op.loc[
                op[
                    "driver"
                ]
                == driver
            ]

            low = (
                driver_data.loc[
                    driver_data[
                        "level"
                    ]
                    == "low",
                    "absolute_profit_change_vs_base_eur",
                ]
                .iloc[0]
            )

            high = (
                driver_data.loc[
                    driver_data[
                        "level"
                    ]
                    == "high",
                    "absolute_profit_change_vs_base_eur",
                ]
                .iloc[0]
            )

            base_profit = (
                driver_data.loc[
                    driver_data[
                        "level"
                    ]
                    == "base",
                    "base_profit_eur",
                ]
                .iloc[0]
            )

            sensitivity = max(
                abs(low),
                abs(high),
            )

            rows.append(
                {
                    "driver":
                        driver,

                    "low_delta":
                        low,

                    "high_delta":
                        high,

                    "sensitivity":
                        sensitivity,

                    "base_profit":
                        base_profit,
                }
            )

        plot_df = (
            pd.DataFrame(
                rows
            )
            .sort_values(
                "sensitivity",
                ascending=True,
            )
            .reset_index(
                drop=True
            )
        )

        y = np.arange(
            len(
                plot_df
            )
        )

        low_delta = (
            plot_df[
                "low_delta"
            ]
            .to_numpy()
        )

        high_delta = (
            plot_df[
                "high_delta"
            ]
            .to_numpy()
        )

        ax.barh(
            y,
            low_delta,
            height=0.55,
            color=OAT_LOW_COLOR,
            alpha=0.90,
            label="Low assumption",
        )

        ax.barh(
            y,
            high_delta,
            height=0.55,
            color=OAT_HIGH_COLOR,
            alpha=0.90,
            label="High assumption",
        )

        ax.axvline(
            0,
            color="black",
            linewidth=1.0,
        )
        # -------------------------------------------------------------------------
        # Horizontal padding so sensitivity labels do not touch plot boundaries
        # -------------------------------------------------------------------------

        sensitivity_values = np.concatenate(
            [
                low_delta,
                high_delta,
            ]
        )

        x_min = min(
            0,
            sensitivity_values.min(),
        )

        x_max = max(
            0,
            sensitivity_values.max(),
        )

        x_range = (
            x_max
            -
            x_min
        )

        ax.set_xlim(
            x_min
            -
            0.10
            * x_range,

            x_max
            +
            0.10
            * x_range,
        )

        labels = []

        for driver in (
            plot_df[
                "driver"
            ]
        ):

            label = (
                driver_labels[
                    driver
                ]
            )

            if (
                operator
                == "voi"
                and driver
                == "fleet_exposure"
            ):
                label += " *"

            labels.append(
                label
            )

        ax.set_yticks(
            y
        )

        ax.set_yticklabels(
            labels,
            fontsize=9.5,
        )

        base_profit = (
            plot_df[
                "base_profit"
            ]
            .iloc[0]
        )

        ax.set_title(
            (
                f"{OPERATOR_LABELS[operator]}  "
                f"— Base profit: {euro_label(base_profit)}"
            ),
            fontsize=11,
            fontweight="bold",
            loc="left",
        )

        ax.xaxis.set_major_formatter(
            FuncFormatter(
                euro_formatter
            )
        )

        ax.grid(
            axis="x",
            alpha=0.20,
            linewidth=0.8,
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

        for yi, low, high in zip(
            y,
            low_delta,
            high_delta,
        ):

            if low != 0:

                ax.text(
                    low,
                    yi,
                    f" {euro_label(low)}",
                    va="center",
                    ha=(
                        "left"
                        if low > 0
                        else "right"
                    ),
                    fontsize=8,
                )

            if high != 0:

                ax.text(
                    high,
                    yi,
                    (
                        f"{euro_label(high)} "
                        if high < 0
                        else
                        f" {euro_label(high)}"
                    ),
                    va="center",
                    ha=(
                        "right"
                        if high < 0
                        else "left"
                    ),
                    fontsize=8,
                )

    axes[
        -1
    ].set_xlabel(
        "Change in modeled operating profit relative to Base (€)",
        fontsize=11,
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=OAT_LOW_COLOR,
            linewidth=8,
            label="Low assumption",
        ),

        Line2D(
            [0],
            [0],
            color=OAT_HIGH_COLOR,
            linewidth=8,
            label="High assumption",
        ),
    ]

    fig.legend(
        handles=legend_handles,
        frameon=False,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            0.965,
        ),
    )

    fig.suptitle(
        "One-at-a-Time Sensitivity of Modeled Operating Profit — 2024",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )

    fig.text(
        0.5,
        0.025,
        (
            "Each parameter block changes independently while all other assumptions remain at Base. "
            "Positive values improve modeled profit; negative values reduce it. "
            "* For VOI, fleet exposure changes the profit/loss sign across the tested range."
        ),
        ha="center",
        fontsize=8.4,
    )

    fig.tight_layout(
        rect=[
            0,
            0.055,
            1,
            0.95,
        ],
        h_pad=2.2,
    )

    save_figure(
        fig,
        "figure5_4_oat_sensitivity_2024",
    )

    plt.close(
        fig
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EXERCISE 5 — FINAL BUSINESS MODEL FIGURES"
    )

    print(
        "=" * 110
    )

    figure_1_revenue_composition()

    figure_2_base_cost_breakdown()

    figure_3_profitability_scenarios()

    figure_4_oat_sensitivity()

    print(
        "\nCompleted."
    )

    print(
        f"Figures saved in -> {FIG_DIR}"
    )


if __name__ == "__main__":
    main()