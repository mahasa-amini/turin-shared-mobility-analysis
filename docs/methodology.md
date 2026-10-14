# Methodology

This document describes the implemented analysis from source inspection. Existing local audit tables support provenance and coverage descriptions; the results have not been independently reproduced during the repository upgrade.

## What the quantities represent

| Type | Examples | Interpretation |
|---|---|---|
| Recorded attributes | Vehicle identifiers, timestamps, endpoint coordinates, provider distance and duration, reservation/battery fields where available | Supplied records, subject to provider-specific precision and errors |
| Derived measures | Cleaned durations, endpoint displacement, zone assignments, OD counts | Calculated from records under explicit validity rules |
| Proxies | Potential PT interaction, inter-trip parking intervals, fleet exposure | Indicators of behavior or operational conditions not directly observed |
| Scenario outputs | PAYG billings, costs, profitability, generalized commuting cost | Conditional model outputs, not observed accounts or mode choices |

## Cleaning and harmonization

Preparation starts with [Bird cleaning](../src/cleaning/clean_bird.py), [Lime auditing](../src/cleaning/audit_lime.py), and [Voi auditing](../src/cleaning/audit_voi.py), which create typed/flagged intermediates. Finalization applies operator-specific decisions:

- [Bird](../src/cleaning/finalize_bird.py) retains records while distinguishing temporal, distance, speed, and spatial suitability.
- [Lime](../src/cleaning/finalize_lime.py) distinguishes reported duration from elapsed time, handles identified clock-change anomalies, removes invalid elapsed-time records, and flags distance sentinels without treating every measurement issue as a reason to discard a trip.
- [Voi](../src/cleaning/finalize_voi.py) checks duplicate trip consistency, collapses repeated trip IDs, preserves reservation conflicts, and distinguishes detailed timestamps from month-only records.

[Harmonization](../src/harmonization/harmonize_operators.py) creates common trip/vehicle identifiers, local and UTC time fields, source-file/row provenance, measurement-type fields, and analysis-specific validity flags. Provider distances and speeds are not assumed to have identical meanings. Endpoint displacement is distinct from a traveled route distance.

## Temporal coverage and comparison

[Coverage preparation](../src/analysis/exercise1_temporal_coverage.py) combines declared coverage windows with harmonization audits. The workflow distinguishes monthly availability from detailed timestamp availability: Voi January 2024 supports monthly counts, but not daily/hourly analysis. Unequal 2025 end dates prevent interpreting observed-year totals as equivalent full years.

[Yearly comparison](../src/analysis/exercise1_yearly_comparison.py) separates full-year 2024 from common January–March comparisons. [Hourly analysis](../src/analysis/exercise1_hourly_weekday.py) includes matched windows and a 12-full-week comparison to address weekday composition. [Vehicle utilization](../src/analysis/exercise1_vehicle_utilization.py) measures activity among observed vehicle identifiers; it does not enumerate all deployed vehicles. The coverage table is in [Data and reproduction](data-and-reproduction.md).

## Spatial assignment and OD construction

[Zoning preparation](../src/analysis/exercise2_zoning_audit.py) inspects the supplied Torino statistical-zone geometry and uses EPSG:3003. [Endpoint assignment](../src/analysis/exercise2_assign_zones.py) first tests polygon interiors, then intersections for unmatched boundary points. Unique boundary matches are retained; multiple matches are flagged as ambiguous. No nearest-zone snapping is used.

[OD construction](../src/analysis/exercise2_build_od.py) aggregates trips with assigned origins and destinations, including intra-zonal movements. [Temporal OD analysis](../src/analysis/exercise2_temporal_od.py) separates conventional and empirical time periods. These are endpoint flows, not reconstructed scooter trajectories; unassigned endpoints affect spatial coverage.

## Potential public-transport interaction

Local `data/raw/external/gtt_gtfs/feed_info.txt` identifies GTT as publisher, feed version **20260813**, with coverage **2026-08-12 through 2027-01-31**. The existing `audit/exercise_3/pt_reference/gtfs_reference_network_audit.csv` agrees and records no 2024 overlap. This later feed is a spatial/topological reference for earlier observations, not evidence of historical service availability.

[PT-reference preparation](../src/analysis/exercise3_prepare_pt_reference.py) selects urban bus, tram, and metro data. [Proximity analysis](../src/analysis/exercise3_pt_proximity.py) examines February and July 2024 using nearest-stop distances in projected coordinates, with 250, 400, and 600 m thresholds and a 400 m baseline. These distances do not represent routed pedestrian access.

[Route compatibility](../src/analysis/exercise3_route_overlap.py) uses ordered GTFS stop patterns to test directional direct-route compatibility, with 50, 100, and 150 m endpoint thresholds and a 100 m baseline. `stop_times` supplies stop order, not historically verified departure times or frequencies. [Temporal adduction](../src/analysis/exercise3_temporal_adduction.py) summarizes potential feeder patterns by time period. These measures cannot establish observed transfers, travel purpose, causality, or actual competition with PT.

## Parking and inactivity proxy

[Interval construction](../src/analysis/exercise4_parking_interval_audit.py) combines 2024 and available 2025 records, sequences trips by vehicle, and calculates the gap from a trip's end to the next trip's start. Detailed timestamp pairs are required; unresolved clock-change times are not guessed. The subsequent analysis targets 2024 parking candidates, with later observations helping identify following rentals.

[Finalization](../src/analysis/exercise4_finalize_parking_events.py) requires all of the following:

- A next trip exists.
- Elapsed time is resolved and strictly positive.
- End-to-next-start relocation distance is present and at most **100 m**.
- The preceding trip has an assigned destination zone.
- The interval is at most **10,080 minutes (7 days)**.

[Definition sensitivity](../src/analysis/exercise4_parking_definition_sensitivity.py) explores alternative duration and relocation thresholds. Accepted gaps are operational inactivity proxies: they do not establish uninterrupted physical parking or exclude every unobserved handling event.

## Economic scenarios

[Revenue estimation](../src/analysis/exercise5_revenue_engine.py) applies the [tariff configuration](../config/exercise_5/tariffs_2024.csv) to rental durations: EUR 1 unlock plus EUR 0.20/min for Bird and EUR 0.19/min for Lime/Voi. It compares continuous-minute billing with rounding up. The [source register](../config/exercise_5/tariff_sources_2024.csv) labels the numerical rates as a Torino snapshot updated 2024-02-09, with current official pages supporting pricing structure. Estimated PAYG billings are not actual receipts; passes, discounts, and actual billing behavior are not observed.

[Fleet exposure](../src/analysis/exercise5_fleet_exposure_audit.py) uses February–December 2024. Its lower proxy is mean daily active vehicles; its base proxy assumes continuous presence between each vehicle's first and last observed trip; its upper proxy uses all distinct observed vehicle IDs. These are scenario definitions, not guaranteed bounds on deployed fleet size.

The [cost/profitability engine](../src/analysis/exercise5_cost_profitability_engine.py) combines revenues, fleet proxies, and [low/base/high assumptions](../config/exercise_5/cost_assumptions_2024.csv). Depreciation, per-trip operations, and fleet-related overhead use external benchmarks, including VOI Group benchmarks applied across operators; [sources](../config/exercise_5/cost_sources_2024.csv) record their scope. [Robustness analysis](../src/analysis/exercise5_robustness_vat_sensitivity.py) examines parameter and VAT sensitivity. These scenarios do not reconstruct operator-specific Turin accounts.

## Separate generalized commuting cost

[Private car](../stage4_private_car.py) and [active-mode ownership](../stage4_private_active_modes.py) calculations feed a **manual** handoff: [Stage 5](../stage5_generalised_cost.py) embeds their monetary costs as constants rather than reading generated outputs. Stage 5 combines money and time, using EUR 10/hour as baseline value of time and EUR 5/10/20 per hour for sensitivity. [Stage 6](../stage6_weighted_pareto.py) weights travel, access/egress, and waiting time by 1, 1.5, and 2, and evaluates money–time Pareto efficiency. [Stage 7](../stage7_generalised_cost_figures.py) reads Stage 5/6 tables to create figures. Updating Stage 4 does not automatically update Stage 5.
