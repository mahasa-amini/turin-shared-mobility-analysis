from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEMPORAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_1"
    / "temporal"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_1"
    / "temporal"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "figures"
    / "exercise_1"
    / "temporal"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


DAILY_MATCHED_FILE = (
    TEMPORAL_DIR
    / "daily_trip_counts_matched_yoy.parquet"
)

WEEKLY_MATCHED_FILE = (
    TEMPORAL_DIR
    / "weekly_matched_yoy.parquet"
)

MONTHLY_FILE = (
    TEMPORAL_DIR
    / "monthly_trip_counts_with_trends.parquet"
)

JAN_MAR_FILE = (
    TABLE_DIR
    / "yearly_common_jan_mar_operator_summary.csv"
)


# ============================================================
# DISPLAY HELPERS
# ============================================================

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

MONTH_LABELS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def comma_formatter(x, pos):

    return f"{x:,.0f}"


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
# DAILY MATCHED YOY
#
# Feb 1-Apr 29.
# Feb 29 removed from 2024.
#
# Rolling mean is recalculated AFTER constructing the
# matched 88-day sequence. It is visualization-only.
# ============================================================

def figure_daily_matched_yoy():

    df = pd.read_parquet(
        DAILY_MATCHED_FILE
    )

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.sort_values(
        [
            "operator",
            "year",
            "date",
        ]
    )

    df[
        "comparison_day"
    ] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )
        .cumcount()
        + 1
    )

    df[
        "rolling_7d_matched"
    ] = (
        df.groupby(
            [
                "operator",
                "year",
            ]
        )[
            "trip_count"
        ]
        .transform(
            lambda s:
                s.rolling(
                    7,
                    center=True,
                    min_periods=4,
                ).mean()
        )
    )

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10, 10),
        sharex=True,
    )

    for ax, operator in zip(
        axes,
        OPERATORS,
    ):

        subset = df.loc[
            df[
                "operator"
            ] == operator
        ]

        for year in [
            2024,
            2025,
        ]:

            y = subset.loc[
                subset[
                    "year"
                ] == year
            ]

            ax.plot(
                y[
                    "comparison_day"
                ],
                y[
                    "rolling_7d_matched"
                ],
                label=str(year),
                linewidth=2,
            )

        ax.set_title(
            OPERATOR_LABELS[
                operator
            ],
            loc="left",
        )

        ax.set_ylabel(
            "Trips/day"
        )

        ax.yaxis.set_major_formatter(
            FuncFormatter(
                comma_formatter
            )
        )

        ax.grid(
            alpha=0.25
        )

        ax.legend(
            frameon=False,
        )

    axes[-1].set_xlabel(
        "Matched comparison day (Feb 1-Apr 29)"
    )

    fig.suptitle(
        "Daily Scooter Activity: Matched 2024 vs 2025 Period",
        fontsize=14,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Seven-day moving averages. "
            "February 29, 2024 excluded only "
            "from the matched comparison."
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
        "daily_matched_yoy_7d.png",
    )


# ============================================================
# FIGURE 2
# WEEKLY MATCHED YOY
# ============================================================

def figure_weekly_matched_yoy():

    df = pd.read_parquet(
        WEEKLY_MATCHED_FILE
    )

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10, 10),
        sharex=True,
    )

    for ax, operator in zip(
        axes,
        OPERATORS,
    ):

        subset = df.loc[
            df[
                "operator"
            ] == operator
        ]

        for year in [
            2024,
            2025,
        ]:

            y = subset.loc[
                subset[
                    "year"
                ] == year
            ].sort_values(
                "matched_week_index"
            )

            ax.plot(
                y[
                    "matched_week_index"
                ],
                y[
                    "trip_count"
                ],
                marker="o",
                linewidth=2,
                label=str(year),
            )

        ax.set_title(
            OPERATOR_LABELS[
                operator
            ],
            loc="left",
        )

        ax.set_ylabel(
            "Trips/week"
        )

        ax.yaxis.set_major_formatter(
            FuncFormatter(
                comma_formatter
            )
        )

        ax.grid(
            alpha=0.25
        )

        ax.legend(
            frameon=False,
        )

    axes[-1].set_xlabel(
        "Matched full-week index"
    )

    axes[-1].set_xticks(
        range(
            1,
            13,
        )
    )

    fig.suptitle(
        "Weekly Scooter Activity: 12 Matched Full Weeks",
        fontsize=14,
    )

    fig.text(
        0.5,
        0.01,
        (
            "2024: Feb 5-Apr 28; "
            "2025: Feb 3-Apr 27. "
            "Only complete Monday-Sunday weeks."
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
        "weekly_matched_yoy.png",
    )


# ============================================================
# FIGURE 3
# 2024 NORMALIZED MONTHLY SEASONALITY
#
# Index = monthly daily rate /
#         operator's 2024 average daily rate * 100
#
# This compares the SHAPE of seasonality rather than
# absolute operator scale.
# ============================================================

def figure_monthly_seasonality_index():

    df = pd.read_parquet(
        MONTHLY_FILE
    )

    df = df.loc[
        df[
            "year"
        ] == 2024
    ].copy()

    df[
        "period"
    ] = pd.PeriodIndex(
        df[
            "source_period"
        ],
        freq="M",
    )

    df[
        "month_number"
    ] = (
        df[
            "period"
        ].dt.month
    )

    if (
        "trips_per_calendar_day"
        not in df.columns
    ):

        df[
            "days_in_month"
        ] = (
            df[
                "period"
            ].dt.days_in_month
        )

        df[
            "trips_per_calendar_day"
        ] = (
            df[
                "trip_count"
            ]
            /
            df[
                "days_in_month"
            ]
        )

    mean_rate = (
        df.groupby(
            "operator"
        )[
            "trips_per_calendar_day"
        ]
        .transform(
            "mean"
        )
    )

    df[
        "seasonality_index"
    ] = (
        df[
            "trips_per_calendar_day"
        ]
        /
        mean_rate
        * 100
    )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    for operator in OPERATORS:

        subset = (
            df.loc[
                df[
                    "operator"
                ] == operator
            ]
            .sort_values(
                "month_number"
            )
        )

        ax.plot(
            subset[
                "month_number"
            ],
            subset[
                "seasonality_index"
            ],
            marker="o",
            linewidth=2,
            label=(
                OPERATOR_LABELS[
                    operator
                ]
            ),
        )

    ax.axhline(
        100,
        linewidth=1,
        linestyle="--",
    )

    ax.set_xticks(
        range(
            1,
            13,
        )
    )

    ax.set_xticklabels(
        MONTH_LABELS
    )

    ax.set_ylabel(
        "Activity index (operator annual mean = 100)"
    )

    ax.set_xlabel(
        "Month"
    )

    ax.set_title(
        "Monthly Seasonality of Scooter Activity in 2024"
    )

    ax.grid(
        alpha=0.25
    )

    ax.legend(
        frameon=False,
        ncol=3,
    )

    fig.tight_layout()

    return save_figure(
        fig,
        "monthly_2024_seasonality_index.png",
    )


# ============================================================
# FIGURE 4
# 2024 SYSTEM-WIDE MONTHLY DAILY RATE
# ============================================================

def figure_system_monthly_2024():

    df = pd.read_parquet(
        MONTHLY_FILE
    )

    df = df.loc[
        df[
            "year"
        ] == 2024
    ].copy()

    df[
        "period"
    ] = pd.PeriodIndex(
        df[
            "source_period"
        ],
        freq="M",
    )

    df[
        "month_number"
    ] = (
        df[
            "period"
        ].dt.month
    )

    df[
        "days_in_month"
    ] = (
        df[
            "period"
        ].dt.days_in_month
    )

    system = (
        df.groupby(
            [
                "source_period",
                "month_number",
                "days_in_month",
            ],
            as_index=False,
        )
        .agg(
            system_trip_count=(
                "trip_count",
                "sum",
            )
        )
    )

    system[
        "system_trips_per_day"
    ] = (
        system[
            "system_trip_count"
        ]
        /
        system[
            "days_in_month"
        ]
    )

    system = system.sort_values(
        "month_number"
    )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        system[
            "month_number"
        ],
        system[
            "system_trips_per_day"
        ],
        marker="o",
        linewidth=2.3,
    )

    ax.set_xticks(
        range(
            1,
            13,
        )
    )

    ax.set_xticklabels(
        MONTH_LABELS
    )

    ax.set_xlabel(
        "Month"
    )

    ax.set_ylabel(
        "Trips per calendar day"
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            comma_formatter
        )
    )

    ax.set_title(
        "System-wide Monthly Scooter Activity in Turin, 2024"
    )

    ax.grid(
        alpha=0.25
    )

    fig.tight_layout()

    return save_figure(
        fig,
        "monthly_system_2024_daily_rate.png",
    )


# ============================================================
# FIGURE 5
# JAN-MAR YOY DAILY RATE
# ============================================================

def figure_jan_mar_yoy():

    df = pd.read_csv(
        JAN_MAR_FILE
    )

    df[
        "avg_trips_per_calendar_day"
    ] = (
        df[
            "trips"
        ]
        /
        df[
            "calendar_days"
        ]
    )

    pivot = (
        df.pivot(
            index="operator",
            columns="year",
            values=(
                "avg_trips_per_calendar_day"
            ),
        )
        .reindex(
            OPERATORS
        )
    )

    x = np.arange(
        len(
            OPERATORS
        )
    )

    width = 0.36

    fig, ax = plt.subplots(
        figsize=(9, 5.5)
    )

    bars_2024 = ax.bar(
        x - width / 2,
        pivot[
            2024
        ],
        width,
        label="2024",
    )

    bars_2025 = ax.bar(
        x + width / 2,
        pivot[
            2025
        ],
        width,
        label="2025",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        [
            OPERATOR_LABELS[
                operator
            ]
            for operator
            in OPERATORS
        ]
    )

    ax.set_ylabel(
        "Average trips per calendar day"
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            comma_formatter
        )
    )

    ax.set_title(
        "Observed Scooter Activity: Jan-Mar 2024 vs 2025"
    )

    ax.legend(
        frameon=False
    )

    ax.grid(
        axis="y",
        alpha=0.25
    )

    ax.bar_label(
        bars_2024,
        fmt="%.0f",
        padding=3,
    )

    ax.bar_label(
        bars_2025,
        fmt="%.0f",
        padding=3,
    )

    fig.text(
        0.5,
        0.01,
        (
            "Jan-Mar is the common complete-month "
            "comparison window for all three operators."
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
        "jan_mar_2024_2025_daily_activity.png",
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
        "EXERCISE 1 — TEMPORAL FIGURE GENERATION"
    )

    print(
        "=" * 100
    )

    required = [
        DAILY_MATCHED_FILE,
        WEEKLY_MATCHED_FILE,
        MONTHLY_FILE,
        JAN_MAR_FILE,
    ]

    for path in required:

        if not path.exists():

            raise FileNotFoundError(
                path
            )

    paths = []

    paths.append(
        figure_daily_matched_yoy()
    )

    paths.append(
        figure_weekly_matched_yoy()
    )

    paths.append(
        figure_monthly_seasonality_index()
    )

    paths.append(
        figure_system_monthly_2024()
    )

    paths.append(
        figure_jan_mar_yoy()
    )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "FIGURE GENERATION COMPLETED"
    )

    print(
        "=" * 100
    )

    print(
        "\nGenerated figures:"
    )

    for path in paths:

        print(path)

    print(
        "\nIMPORTANT:"
        "\n- No raw or cleaned trip data were modified."
        "\n- Daily rolling averages are visualization-only."
        "\n- Daily and weekly YoY plots use matched seasonal windows."
        "\n- Monthly seasonality is normalized within operator "
        "to compare temporal shape rather than operator size."
        "\n- 2024 system-wide monthly activity uses all three operators."
        "\n- Jan-Mar is used for the common 2024-vs-2025 monthly comparison."
    )


if __name__ == "__main__":
    main()