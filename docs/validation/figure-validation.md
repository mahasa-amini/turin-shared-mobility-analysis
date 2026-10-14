# Scooter figure and showcase validation

Validated 2026-10-14. **All 18 scooter figure scripts completed successfully after the focused parking-loader fix.** Five selected PNGs were visually reviewed and published with compact tables in [the results showcase](../results/README.md). This validates the stated figure scope, not raw-to-cleaned processing or the full course reports.

## Environment, inputs and isolation

Starting source commit: `4b641ed`. Earlier temporary workspaces were no longer present. A fresh copy was created at `/private/tmp/transport-showcase/project`; only tracked source/configuration, six supplied cleaned Parquets, external zoning/GTFS inputs and three cleaning-summary inputs were seeded. No downstream processed data, tables or figures were copied in. [Input hashes](figure-evidence/input-manifest.json) identify the 32 files supplied to this run. The separate commuting exercise used its own sibling directory.

A fresh environment at `/private/tmp/transport-showcase-env` was installed from [requirements-lock.txt](../../requirements-lock.txt), including corrected PyProj 3.7.2. The initial sandboxed installation failed DNS resolution; the authorized network retry succeeded without changing pins. All 24 application versions matched; `pip check` passed and all nine synthetic environment checks passed. [Environment metadata](figure-evidence/environment.json), [smoke log](figure-evidence/environment-check.log). Original `.venv` was not modified.

All 33 prerequisite scripts (harmonization and the previously documented analytical sequences for Exercises 1–5) ran again with exit 0. Then all 18 figure scripts ran against those newly generated outputs. [Exact ordered commands, working-project paths, exit codes and timings](figure-evidence/execution.json), [runner](figure-evidence/run.py), [source hashes](figure-evidence/source-hashes.json), and [final rerun commands](figure-evidence/reruns.json) are retained. Commands used the pinned interpreter with `-I -B -u`; the working directory was the isolated project, with `MPLBACKEND=Agg` and a temporary `MPLCONFIGDIR`.

SHA-256 before/after inventories confirmed that all **558 original files** under repository `data/`, `audit/` and `outputs/` were unchanged, with no additions or removals. [Preservation result](figure-evidence/preservation.json). Only curated documentation artifacts and the focused figure fixes were written into tracked repository content.

## Figure execution coverage

| Script | Final exit | Notes |
|---|---:|---|
| `src/analysis/exercise1_hourly_figures.py` | 0 | Selected weekday/hour heatmap |
| `src/analysis/exercise1_temporal_figures.py` | 0 | Execution/decode only |
| `src/analysis/exercise1_usage_pattern_figures.py` | 0 | Execution/decode only |
| `src/analysis/exercise1_vehicle_figures.py` | 0 | Execution/decode only |
| `src/analysis/exercise2_appendixA_heatmap.py` | 0 | Standalone appendix heatmap, not full report |
| `src/analysis/exercise2_appendixB_heatmaps.py` | 0 | Standalone appendix heatmaps, not full report |
| `src/analysis/exercise2_map01_all_day.py` | 0 | Selected OD core |
| `src/analysis/exercise2_map02_am_peak.py` | 0 | Execution/decode only |
| `src/analysis/exercise2_map03_pm_peak.py` | 0 | Execution/decode only |
| `src/analysis/exercise2_map04_offpeak.py` | 0 | Execution/decode only |
| `src/analysis/exercise2_map05_reversals.py` | 0 | Execution/decode only |
| `src/analysis/exercise2_map_origin_density.py` | 0 | Execution/decode only |
| `src/analysis/exercise2_map_temporal_comparison.py` | 0 | Execution/decode only |
| `src/analysis/exercise3_access_egress_figures.py` | 0 | Execution/decode only |
| `src/analysis/exercise3_route_overlap_figures.py` | 0 | Selected paired seasonal map; caption rerun |
| `src/visualization/exercise4_od_parking_overlays.py` | 0 | Execution/decode only |
| `src/visualization/exercise4_parking_maps.py` | 0 | Initially exit 1; canonical-loader, caption and legend reruns passed |
| `src/visualization/exercise5_business_model_figures.py` | 0 | Selected base-cost scenario |

The scripts emitted **37 PNGs, 11 PDFs and 2 figure-support CSVs**, including outputs in the standalone appendix directory. All PNGs decoded successfully. [Complete artifact inventory and hashes](figure-evidence/figure-artifacts.json). PDF existence/hashes were recorded; their pages were not visually validated. No pixel-identity comparison to old figures was claimed.

## Diagnosed failure and focused changes

The parking map loader recursively mixed full-period zonal means with temporal period-specific tables. Conflicting rows triggered a fallback expecting columns absent from the current candidate-interval schema, causing a `KeyError`. The four canonical `parking_by_zone_<scope>_2024.csv` outputs already existed. Fix `2b875ff` explicitly prefers those outputs and retains duplicate-zone and exact event-total checks; no analytical calculation changed. [Initial failure](figure-evidence/exercise4_parking_maps.log), [successful loader rerun](figure-evidence/parking-rerun.log). The old fallback remains unvalidated and is not claimed to support the current candidate schema when canonical tables are missing.

Fix `88bff80` adds the later GTFS date range and interpretive limitation to the route-map captions, and labels the parking gap an inactivity proxy. The parking caption wraps onto two lines to avoid clipping. Fix `b5875e4` moves the parking legend into the empty northwest margin: the previous placement hid southwest zones. Final PT and parking logs are [here](figure-evidence/exercise3_route_overlap_figures-final.log) and [here](figure-evidence/exercise4_parking_maps-final.log). Parking was rerun after the caption wrap and legend adjustment with the same recorded command, exit 0; the final log and output/source hashes represent the final version.

## Numerical and visual review

**200 newly generated audit/table CSVs** match the existing references in original row/column order, including nulls and dtypes; non-floating values match exactly, floating values use `rtol=1e-10`, `atol=1e-9`. The three copied cleaning-summary inputs are explicitly excluded from that count. [Per-table results](figure-evidence/csv-comparisons.json), [comparison code](figure-evidence/compare_csv.py). This run did not repeat full Parquet/GeoPackage reference comparisons; earlier analytical validation reports document those. No historical output was used as an input to the regenerated downstream pipeline.

The [selection/checking script](figure-evidence/select_results.py) and [headline checks](figure-evidence/headline-checks.json) additionally reconcile heatmap totals and weekday denominators, the smallest OD set reaching 25%, PT counts summed across the three operators against existing system rows, parking operator contributions and minute/hour conversion, and economic revenue-minus-cost/component accounting. During preparation, a helper used the wrong GIS layer name and initially summed the already-pooled PT system rows alongside operator rows. Only the helper was corrected; final system totals were explicitly checked against the generated system rows before publication. Analytical outputs were unchanged.

| Selected figure | Visual and numerical review |
|---|---|
| [Temporal usage](../figures/temporal_usage_2024.png) | 7 × 24 grid; weekday/hour labels, mean-trips colorbar and peak outlines clear. Counts divide by 47/48 weekday occurrences within 335 days. |
| [Spatial OD](../figures/spatial_od_2024.png) | Title, 94-zone boundary, direction arrows, trip-count width legend, north arrow, scale bar and centroid-flow caption readable. Central crossings are expected; exact pairs are supplied in CSV. |
| [PT compatibility](../figures/pt_compatibility_2024.png) | Both months use one mentions-per-1,000 scale; denominator boxes and 100 m threshold readable. Later feed dates and compatibility-only qualification are visible. Routes are not individually labeled; IDs/counts are supplied in CSV. |
| [Parking proxy](../figures/parking_proxy_2024.png) | Fixed hour classes, low-sample hatch, no-observation grey, zone labels and two-line proxy caption readable. Legend no longer covers southwest zones; pooled event counts reconcile. |
| [Economic base scenario](../figures/economics_base_2024.png) | Euro axis, components, revenue diamonds and profit/loss annotations agree with the three base-scenario rows. Caption states fleet/OPEX/overhead/depreciation assumptions and electricity exclusion. |

All selected figures were opened at generated resolution (the viewer may downsample) and reinspected after relevant edits. [Selected PNG hashes/dimensions](figure-evidence/selected-figures.json) and [table source/transformation hashes](figure-evidence/selected-tables.json) tie the delivered copies to the regenerated outputs. The unselected hourly-index figure was also inspected: its empirical-peak text touches the peak lines, so the clearer weekday heatmap was selected. No exhaustive visual approval of the other 32 PNGs is implied.

## Exclusions and remaining release blockers

- Raw-to-cleaned processing, provenance/completeness of supplied records, and external-source truth were not validated. Public distribution still needs the agreed input access/provenance arrangements.
- Full Word/PDF reports, narrative/table reconciliation, `exercise2_build_appendix_a.py`, and legacy artifacts outside the executed sequence remain outside coverage. Standalone appendix heatmaps do not constitute report validation.
- Unselected figures need visual and caption review before a full figure/report release; the unselected access/egress plot was executed but its embedded caption was not updated to include the later GTFS dates.
- Historical GTFS service for 2024 is not established; no acquisition implementation is provided (the empty placeholder was subsequently removed). Compatibility cannot prove transfers or substitution. Parking, fleet exposure and economic outcomes retain their proxy/scenario limitations.
- The parking map's legacy candidate-data fallback remains incompatible with the current candidate schema if canonical summaries are absent. The validated path requires the canonical upstream tables.
- Only the recorded macOS/Python/pinned environment is tested. The separate commuting workflow has its own [validation and manual-handoff limitation](commuting-validation.md).

Markdown relative-file targets and Git whitespace/diffs were checked before committing. Nothing was pushed.
