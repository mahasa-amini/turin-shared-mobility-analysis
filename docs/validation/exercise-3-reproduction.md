# Exercise 3 reproduction

Status: **passed**, 2026-10-14. All 5 listed analytical scripts exited 0 and all 30 emitted CSV/Parquet/GeoPackage artifacts matched existing local references. These checks establish computational reproduction, not independent scientific correctness. **Raw-to-cleaned processing was not rerun.** Figures, Word reports, and the separate commuting-cost exercise were deferred.

## Environment and isolation

Execution used CPython 3.13.13, macOS 14.6 arm64, in `/private/tmp/transport-pyproj-ab-mrdjlkw4/venv`, with all 24 application versions matching [requirements-lock.txt](../../requirements-lock.txt). The only change from the originally tested dependency set is the [controlled PyProj 3.7.2 pin](pt-geometry-diagnosis.md); GeoPandas 1.1.4, Shapely 2.1.2/GEOS 3.13.1, Pyogrio 0.13.0/GDAL 3.12.4 remain fixed. This environment passed `pip check`, all nine smoke checks, and a zero-change lock dry run.

The continuation workspace was `/private/tmp/transport-usage-kpz9n9_x/project`, with current source copied in and preceding stages regenerated there. No expected downstream artifacts were seeded. For Exercise 3 preparation, outputs were legitimately regenerated in the separate PyProj experiment and then copied to this continuation workspace, after full-reference comparisons. Writable destinations are real isolated directories; original inputs/references were read only.

## Inputs

The following manifest identifies supplied or previously regenerated prerequisite inputs. Intermediate outputs within this exercise are produced by the ordered scripts below. Input binary hashes identify the run inputs; result agreement was checked by content rather than binary hashes.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `data/processed/exercise_2/zoning/torino_statistical_zones.gpkg` | 536576 | `3a6d2eae33d5a1f0e72224374360f090588d391c7834fe47ced14fa2d09a87b1` |
| `data/processed/harmonized/bird_2024_harmonized.parquet` | 32633111 | `760acfb0c2042b1bd1d24ed0cd8d44d44a142331a975da59ccc128e390935b32` |
| `data/processed/harmonized/lime_2024_harmonized.parquet` | 73796645 | `a496e78a851876e85e0ba0396ca1228310db158d670b2904f51eb367f6ce3628` |
| `data/processed/harmonized/voi_2024_harmonized.parquet` | 20640572 | `e041745ebb919c706f5b1307666422be97d2a242038fa89f4469f179d7f54d12` |
| `data/raw/external/gtt_gtfs/agency.txt` | 932 | `3e102cbbb3456129a144de33ff123957ec7d2638b50291cac52a1bf504adcb93` |
| `data/raw/external/gtt_gtfs/calendar.txt` | 52608 | `f402d384b205c5f633b360f971453544429644a3766fea156a479097d0b551af` |
| `data/raw/external/gtt_gtfs/calendar_dates.txt` | 895662 | `8e2f37c2ac7a7cdc5d2616863ad06803a6ee823ac07dcb16f389098dfb2dfdb9` |
| `data/raw/external/gtt_gtfs/fare_attributes.txt` | 166 | `0538fb0288e91ec8d88d166adb490a437c1855803feb79e09e03be9f1c62a173` |
| `data/raw/external/gtt_gtfs/fare_rules.txt` | 106 | `04702cf3cdf885ec90cd95506de2c2e256c211c826baa3c93a353f98acd9b4ea` |
| `data/raw/external/gtt_gtfs/feed_info.txt` | 305 | `b8e02b9b731cdcdfbfd11c2738c5c01e472313d86b583dffa32ada88fb7a1fc5` |
| `data/raw/external/gtt_gtfs/routes.txt` | 47674 | `7baf28093f9da6e57eaaaf24e3e031ad0abd002cb7011cebdc0cdafa628817cb` |
| `data/raw/external/gtt_gtfs/shapes.txt` | 8329850 | `0d6136c96f8278e87019c36158c5b6d09e40bcbbc7a5c180a712d5ca5d52733f` |
| `data/raw/external/gtt_gtfs/stop_attributes.txt` | 142478 | `b0fdb106ad2474c2bf169552fbeffd2f25716f981810959287e86537f4ab6c30` |
| `data/raw/external/gtt_gtfs/stop_times.txt` | 71893736 | `77373afb2e897092949b1366c3b545a5bbd8553b23d524d8d32dbb0ec6be1f09` |
| `data/raw/external/gtt_gtfs/stops.txt` | 1420721 | `d333f7a03fd4c5c7ee0933da2ff9624bc14de99add146d3a61dcb572ae40fd51` |
| `data/raw/external/gtt_gtfs/timetable_pages.txt` | 35158 | `c081011d196a1b7cb1d2783fcf4f2b36c058bc7e824b9f784e97dffe555d4536` |
| `data/raw/external/gtt_gtfs/timetable_stop_order.txt` | 1874 | `2bb39006fb1bcb14a9140660b8a84303d0497a71ec0fcb44fd5a9bd5df9ae3c6` |
| `data/raw/external/gtt_gtfs/timetables.txt` | 256347 | `856eb92d707a39d19fee03458d1fc521200a156dd8aa00bb01c8b928c22fc749` |
| `data/raw/external/gtt_gtfs/trips.txt` | 3571999 | `04c962be7530238360ccad07179c54a1cced2e830480bf9736fe6b418c8b1056` |
| `data/raw/external/gtt_gtfs/trips_booking.txt` | 188 | `d8b79a66e4c6b6ee7ec5956f99643ce180d33ec01890f909f803840dba24823b` |
| `data/raw/external/gtt_gtfs/vehicle_categories.txt` | 20543 | `54a0ab8c11e1f0386937e001968babcb22ae9908df645143036aedd0680073b7` |
| `data/raw/external/gtt_gtfs/vehicles.txt` | 51876 | `6c2d0ed741b5c2dc54d523f73d0a93fee45e91c2d5a39ad23fe61b0b1918a11d` |

## Execution coverage

Each command used the environment's Python with `-I -B -u` and the copied script's absolute path; working directory was the isolated project. The PT-reference controlled experiment used its own isolated project. Exact expanded commands, logs, exit codes, per-artifact comparison keys, schema/row/column/layer counts, and invariant details are recorded in the temporary run directory.

| Script | Exit | Matched artifacts |
|---|---:|---:|
| `src/analysis/exercise3_prepare_pt_reference.py` | 0 | 5 |
| `src/analysis/exercise3_pt_proximity.py` | 0 | 13 |
| `src/analysis/exercise3_route_overlap.py` | 0 | 6 |
| `src/analysis/exercise3_temporal_adduction.py` | 0 | 5 |
| `src/analysis/exercise3_prepare_gis.py` | 0 | 1 |

Outputs stayed under `data/processed/exercise_3/`, `audit/exercise_3/`, and `outputs/tables/exercise_3/` in the copy. Evidence directory: `/private/tmp/transport-exercises-xaw9_enm`, including `exercise-3-results.json`, numbered execution logs, comparison/invariant runners, and environment metadata. This directory is temporary, outside Git; the controlled-environment installation/preparation evidence is in `/private/tmp/transport-pyproj-ab-mrdjlkw4`. Matching output-file existence alone was not accepted as success.

## Comparisons and consistency checks

CSV/Parquet tables were aligned by available identifying keys; unique `trip_uid` was used for trip tables. If selected keys were nonunique, complete non-floating column tuples retained row multiplicity. All columns, nulls, row counts, dtypes, and values were compared. Parquet Arrow schemas were checked excluding serialization metadata. Non-floating values were exact; floating values used `rtol=1e-10`, `atol=1e-9` for arithmetic/serialization roundoff. GeoPackages additionally matched layer sets, CRS, attributes, and topological or coordinate equality within `1e-7` projected metres. The geometry tolerance was not changed after the PT discrepancy.

PT proximity flags were recomputed from nearest-stop distances at 250/400/600 m; distances were nonnegative, trip keys unique, and classifications partitioned the trip population. Direct-route IDs were checked as a subset of shared route IDs at 50/100/150 m; stored route counts matched decoded collections. Summary percentages were within 0–100, category shares summed to 100, and category trip totals reconciled by operator/season/threshold. Temporal direct-overlap/network/access/egress/independent counts partitioned trips; feeder totals equaled access plus egress.

An initial validation-helper assertion mistakenly treated serialized pipe-delimited route IDs as Python collections. Source inspection confirmed the documented serialization; only the helper was corrected and rerun on the existing outputs. All invariant checks then passed; the scientific script and outputs were unchanged. The earlier PT geometry discrepancy was independently resolved by the controlled runtime pin, with every reference layer restored. Downstream PT outputs now match references; source inspection alone is not presented as proof of invariance under the unpinned runtime.

GTFS version 20260813 covers 2026-08-12–2027-01-31. It is a later spatial/topological reference for February/July 2024 scooter observations, not historical timetable verification or observed transfers.

Recorded additional invariant results:

- `exercise3_pt_proximity.py`: `[{"distance_flags_and_class_partition": "pass", "unique_trips": 268590}]`
- `exercise3_route_overlap.py`: `[{"direct_routes_subset_shared_and_proportion_partition": "pass", "trips": 268590}]`

## Exclusions and limitations

- `audit/exercise_3/proximity/threshold_sensitivity_extended.csv` was not emitted by the current analytical scripts and was not treated as reproduced.

Figure/report outputs and any legacy consumers outside the executed sequence remain unverified. The original data/audit/output inventory is checked for preservation across the continuation. Upstream cleaning, data completeness, external source truth, and causal interpretation are not established by matching references.
