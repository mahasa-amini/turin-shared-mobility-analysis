from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEMPORAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "temporal_od"
)

ZONE_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "zoning"
    / "torino_statistical_zones.gpkg"
)

TABLE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "exercise_2"
    / "temporal_contrasts"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "exercise_2"
    / "temporal_contrasts"
)

TABLE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


CONVENTIONAL_FILE = (
    TEMPORAL_DIR
    / "system_conventional_period_od_2024.parquet"
)


PERIOD_HOURS = {
    "AM peak": 3,
    "PM peak": 4,
    "Off-peak": 17,
}

CALENDAR_DAYS = 335


# ============================================================
# LOAD
# ============================================================

def load_data():

    od = pd.read_parquet(
        CONVENTIONAL_FILE
    )

    zones = gpd.read_file(
        ZONE_GPKG,
        layer="zones",
    )

    zones["zone_id"] = (
        zones["zone_id"]
        .astype("string")
    )

    od["origin_zone_id"] = (
        od["origin_zone_id"]
        .astype("string")
    )

    od["destination_zone_id"] = (
        od["destination_zone_id"]
        .astype("string")
    )

    return (
        od,
        zones,
    )


# ============================================================
# BUILD COMPLETE OD × PERIOD PANEL
#
# We retain every inter-zonal OD observed in at least one
# conventional period.
# Missing period observations become zero.
# ============================================================

def build_panel(
    od,
):

    data = od.loc[
        ~od["intra_zonal"]
    ].copy()

    pairs = (
        data[
            [
                "origin_zone_id",
                "destination_zone_id",
            ]
        ]
        .drop_duplicates()
    )

    periods = pd.DataFrame(
        {
            "conventional_period":
                [
                    "AM peak",
                    "PM peak",
                    "Off-peak",
                ]
        }
    )

    panel = (
        pairs.merge(
            periods,
            how="cross",
        )
        .merge(
            data[
                [
                    "conventional_period",
                    "origin_zone_id",
                    "destination_zone_id",
                    "system_trips",
                ]
            ],
            on=[
                "conventional_period",
                "origin_zone_id",
                "destination_zone_id",
            ],
            how="left",
            validate="one_to_one",
        )
    )

    panel["system_trips"] = (
        panel["system_trips"]
        .fillna(0)
        .astype("int64")
    )

    # --------------------------------------------------------
    # Clock-hour-normalized flow intensity
    # --------------------------------------------------------

    panel["hours_per_day"] = (
        panel["conventional_period"]
        .map(PERIOD_HOURS)
    )

    panel[
        "mean_trips_per_clock_hour"
    ] = (
        panel["system_trips"]
        /
        (
            panel["hours_per_day"]
            *
            CALENDAR_DAYS
        )
    )

    # --------------------------------------------------------
    # OD share within each period
    #
    # This removes the different total volumes of AM, PM,
    # and off-peak networks.
    # --------------------------------------------------------

    period_totals = (
        panel.groupby(
            "conventional_period"
        )["system_trips"]
        .transform("sum")
    )

    panel[
        "period_od_share_pct"
    ] = np.where(
        period_totals > 0,
        panel["system_trips"]
        /
        period_totals
        * 100,
        np.nan,
    )

    return panel


# ============================================================
# WIDE CONTRAST TABLE
# ============================================================

def build_contrasts(
    panel,
    zones,
):

    trips = (
        panel.pivot(
            index=[
                "origin_zone_id",
                "destination_zone_id",
            ],
            columns="conventional_period",
            values="system_trips",
        )
        .fillna(0)
    )

    intensity = (
        panel.pivot(
            index=[
                "origin_zone_id",
                "destination_zone_id",
            ],
            columns="conventional_period",
            values="mean_trips_per_clock_hour",
        )
        .fillna(0)
    )

    share = (
        panel.pivot(
            index=[
                "origin_zone_id",
                "destination_zone_id",
            ],
            columns="conventional_period",
            values="period_od_share_pct",
        )
        .fillna(0)
    )

    result = pd.DataFrame(
        index=trips.index
    )

    # ========================================================
    # RAW TRIPS
    # ========================================================

    result["am_trips"] = (
        trips["AM peak"]
    )

    result["pm_trips"] = (
        trips["PM peak"]
    )

    result["offpeak_trips"] = (
        trips["Off-peak"]
    )

    # ========================================================
    # CLOCK-HOUR INTENSITY
    # ========================================================

    result["am_rate"] = (
        intensity["AM peak"]
    )

    result["pm_rate"] = (
        intensity["PM peak"]
    )

    result["offpeak_rate"] = (
        intensity["Off-peak"]
    )

    # ========================================================
    # PERIOD-NORMALIZED OD SHARES
    # ========================================================

    result["am_share_pct"] = (
        share["AM peak"]
    )

    result["pm_share_pct"] = (
        share["PM peak"]
    )

    result["offpeak_share_pct"] = (
        share["Off-peak"]
    )

    # ========================================================
    # CONTRASTS
    #
    # Positive PM-minus-AM:
    # corridor is relatively more represented in PM.
    #
    # Positive AM-minus-PM:
    # corridor is relatively more represented in AM.
    # ========================================================

    result[
        "pm_minus_am_share_pp"
    ] = (
        result["pm_share_pct"]
        -
        result["am_share_pct"]
    )

    result[
        "am_minus_pm_share_pp"
    ] = (
        -result[
            "pm_minus_am_share_pp"
        ]
    )

    result[
        "pm_minus_offpeak_share_pp"
    ] = (
        result["pm_share_pct"]
        -
        result["offpeak_share_pct"]
    )

    result[
        "am_minus_offpeak_share_pp"
    ] = (
        result["am_share_pct"]
        -
        result["offpeak_share_pct"]
    )

    result[
        "pm_minus_am_rate"
    ] = (
        result["pm_rate"]
        -
        result["am_rate"]
    )

    result[
        "am_minus_pm_rate"
    ] = (
        result["am_rate"]
        -
        result["pm_rate"]
    )

    result[
        "total_common_window_trips"
    ] = (
        result[
            [
                "am_trips",
                "pm_trips",
                "offpeak_trips",
            ]
        ]
        .sum(axis=1)
    )

    result = (
        result.reset_index()
    )

    # ========================================================
    # ADD ZONE NAMES
    # ========================================================

    origin_lookup = (
        zones[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .rename(
            columns={
                "zone_id":
                    "origin_zone_id",

                "zone_name":
                    "origin_zone_name",
            }
        )
    )

    destination_lookup = (
        zones[
            [
                "zone_id",
                "zone_name",
            ]
        ]
        .rename(
            columns={
                "zone_id":
                    "destination_zone_id",

                "zone_name":
                    "destination_zone_name",
            }
        )
    )

    result = (
        result.merge(
            origin_lookup,
            on="origin_zone_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            destination_lookup,
            on="destination_zone_id",
            how="left",
            validate="many_to_one",
        )
    )

    return result


# ============================================================
# SELECT TEMPORALLY DISTINCT FLOWS
#
# Ranking is based on absolute period-share shift rather
# than raw ratios, avoiding instability from tiny flows.
# ============================================================

def select_extremes(
    contrasts,
    n=20,
):

    pm_specialized = (
        contrasts
        .sort_values(
            [
                "pm_minus_am_share_pp",
                "total_common_window_trips",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(n)
        .copy()
    )

    am_specialized = (
        contrasts
        .sort_values(
            [
                "am_minus_pm_share_pp",
                "total_common_window_trips",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(n)
        .copy()
    )

    pm_vs_offpeak = (
        contrasts
        .sort_values(
            [
                "pm_minus_offpeak_share_pp",
                "total_common_window_trips",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(n)
        .copy()
    )

    am_vs_offpeak = (
        contrasts
        .sort_values(
            [
                "am_minus_offpeak_share_pp",
                "total_common_window_trips",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(n)
        .copy()
    )

    return {
        "pm_vs_am":
            pm_specialized,

        "am_vs_pm":
            am_specialized,

        "pm_vs_offpeak":
            pm_vs_offpeak,

        "am_vs_offpeak":
            am_vs_offpeak,
    }


# ============================================================
# DISPLAY
# ============================================================

def display_table(
    title,
    data,
    contrast_col,
):

    print(
        "\n"
        + "=" * 120
    )

    print(title)

    print(
        "=" * 120
    )

    columns = [
        "origin_zone_id",
        "origin_zone_name",
        "destination_zone_id",
        "destination_zone_name",
        "am_trips",
        "pm_trips",
        "offpeak_trips",
        "am_share_pct",
        "pm_share_pct",
        "offpeak_share_pct",
        contrast_col,
        "total_common_window_trips",
    ]

    display = (
        data[
            columns
        ]
        .head(15)
        .copy()
    )

    for col in [
        "am_share_pct",
        "pm_share_pct",
        "offpeak_share_pct",
        contrast_col,
    ]:

        display[col] = (
            display[col]
            .round(4)
        )

    print(
        display.to_string(
            index=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 120
    )

    print(
        "EXERCISE 2 — TEMPORAL OD FLOW CONTRASTS"
    )

    print(
        "=" * 120
    )

    (
        od,
        zones,
    ) = load_data()

    panel = build_panel(
        od
    )

    contrasts = build_contrasts(
        panel,
        zones,
    )

    extremes = select_extremes(
        contrasts,
        n=20,
    )

    # ========================================================
    # SAVE
    # ========================================================

    contrasts.to_parquet(
        OUTPUT_DIR
        / "system_temporal_od_contrasts_2024.parquet",
        index=False,
    )

    contrasts.to_csv(
        TABLE_DIR
        / "system_temporal_od_contrasts_2024.csv",
        index=False,
    )

    for label, table in (
        extremes.items()
    ):

        table.to_csv(
            TABLE_DIR
            / f"top_20_{label}_specialized_flows_2024.csv",
            index=False,
        )

    # ========================================================
    # TERMINAL
    # ========================================================

    display_table(
        "TOP PM-SPECIALIZED OD PAIRS RELATIVE TO AM",
        extremes[
            "pm_vs_am"
        ],
        "pm_minus_am_share_pp",
    )

    display_table(
        "TOP AM-SPECIALIZED OD PAIRS RELATIVE TO PM",
        extremes[
            "am_vs_pm"
        ],
        "am_minus_pm_share_pp",
    )

    display_table(
        "TOP PM-SPECIALIZED OD PAIRS RELATIVE TO OFF-PEAK",
        extremes[
            "pm_vs_offpeak"
        ],
        "pm_minus_offpeak_share_pp",
    )

    display_table(
        "TOP AM-SPECIALIZED OD PAIRS RELATIVE TO OFF-PEAK",
        extremes[
            "am_vs_offpeak"
        ],
        "am_minus_offpeak_share_pp",
    )

    print(
        "\nVALIDATION / INTERPRETATION:"
        "\n- Analysis contains inter-zonal OD pairs only."
        "\n- AM, PM, and off-peak totals come from the same Feb-Dec 2024 common window."
        "\n- Period OD shares normalize for different overall period volumes."
        "\n- Clock-hour rates normalize for different period durations."
        "\n- Temporal specialization is ranked using differences in OD period share."
        "\n- Raw PM/AM ratios are intentionally not used for primary ranking."
        "\n- This avoids promoting tiny OD pairs with unstable percentage ratios."
        "\n- Positive PM-minus-AM share means the corridor occupies a larger "
        "fraction of the PM network than of the AM network."
        "\n- Selected OD pairs are candidates for Exercise 2 temporal-pattern maps."
        "\n- No travel purpose is inferred from specialization alone."
    )


if __name__ == "__main__":
    main()