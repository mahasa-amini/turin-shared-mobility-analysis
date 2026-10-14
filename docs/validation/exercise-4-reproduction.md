# Exercise 4 reproduction

Status: **passed**, 2026-10-14. All 6 listed analytical scripts exited 0 and all 46 emitted CSV/Parquet/GeoPackage artifacts matched existing local references. These checks establish computational reproduction, not independent scientific correctness. **Raw-to-cleaned processing was not rerun.** Figures, Word reports, and the separate commuting-cost exercise were deferred.

## Environment and isolation

Execution used CPython 3.13.13, macOS 14.6 arm64, in `/private/tmp/transport-pyproj-ab-mrdjlkw4/venv`, with all 24 application versions matching [requirements-lock.txt](../../requirements-lock.txt). The only change from the originally tested dependency set is the [controlled PyProj 3.7.2 pin](pt-geometry-diagnosis.md); GeoPandas 1.1.4, Shapely 2.1.2/GEOS 3.13.1, Pyogrio 0.13.0/GDAL 3.12.4 remain fixed. This environment passed `pip check`, all nine smoke checks, and a zero-change lock dry run.

The continuation workspace was `/private/tmp/transport-usage-kpz9n9_x/project`, with current source copied in and preceding stages regenerated there. No expected downstream artifacts were seeded. For Exercise 3 preparation, outputs were legitimately regenerated in the separate PyProj experiment and then copied to this continuation workspace, after full-reference comparisons. Writable destinations are real isolated directories; original inputs/references were read only.

## Inputs

The following manifest identifies supplied or previously regenerated prerequisite inputs. Intermediate outputs within this exercise are produced by the ordered scripts below. Input binary hashes identify the run inputs; result agreement was checked by content rather than binary hashes.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `data/processed/exercise_2/gis/exercise2_od_layers.gpkg` | 13299712 | `f6831931904ef1d0d1bac1d17c12af32d1de90e8527784f1ff3ae2976cc510a8` |
| `data/processed/exercise_2/trips_zoned/bird_2024_zoned.parquet` | 22491746 | `d315eeb2ac6e06a376475b4c7e9f1e3579910f457edf6e209450eee9d2ed31c3` |
| `data/processed/exercise_2/trips_zoned/lime_2024_zoned.parquet` | 43260992 | `f072a791c6b0cf520795a794ec26c1cbd899acc3969154f744fd094a3147ed1b` |
| `data/processed/exercise_2/trips_zoned/voi_2024_zoned.parquet` | 10177704 | `6713294753b22c7666609647c2bc2e074f4a1ee18b693e65f96759d94d04c091` |
| `data/processed/exercise_2/zoning/torino_statistical_zones.gpkg` | 536576 | `3a6d2eae33d5a1f0e72224374360f090588d391c7834fe47ced14fa2d09a87b1` |
| `data/processed/harmonized/bird_2024_harmonized.parquet` | 32633111 | `760acfb0c2042b1bd1d24ed0cd8d44d44a142331a975da59ccc128e390935b32` |
| `data/processed/harmonized/bird_2025_harmonized.parquet` | 37961690 | `66a14eb028a321a8f4bb3e674a3a548ede9075a18ae8acbbfe76d5d4d37533f5` |
| `data/processed/harmonized/lime_2024_harmonized.parquet` | 73796645 | `a496e78a851876e85e0ba0396ca1228310db158d670b2904f51eb367f6ce3628` |
| `data/processed/harmonized/lime_2025_harmonized.parquet` | 27313845 | `0eaebad9cf5be1c9b9c7d8394511859929ea61f67630029d82594680f318a3d1` |
| `data/processed/harmonized/voi_2024_harmonized.parquet` | 20640572 | `e041745ebb919c706f5b1307666422be97d2a242038fa89f4469f179d7f54d12` |
| `data/processed/harmonized/voi_2025_harmonized.parquet` | 23641896 | `0cfcd3a001dda66d08ea3fd8d1bae79df08f477ebcd51e6b1b834def1687a192` |

## Execution coverage

Each command used the environment's Python with `-I -B -u` and the copied script's absolute path; working directory was the isolated project. The PT-reference controlled experiment used its own isolated project. Exact expanded commands, logs, exit codes, per-artifact comparison keys, schema/row/column/layer counts, and invariant details are recorded in the temporary run directory.

| Script | Exit | Matched artifacts |
|---|---:|---:|
| `src/analysis/exercise4_parking_interval_audit.py` | 0 | 18 |
| `src/analysis/exercise4_parking_definition_sensitivity.py` | 0 | 3 |
| `src/analysis/exercise4_finalize_parking_events.py` | 0 | 5 |
| `src/analysis/exercise4_zone_parking_statistics.py` | 0 | 8 |
| `src/analysis/exercise4_temporal_parking_statistics.py` | 0 | 8 |
| `src/analysis/exercise4_od_parking_relationship.py` | 0 | 4 |

Outputs stayed under `data/processed/exercise_4/`, `audit/exercise_4/`, and `outputs/tables/exercise_4/` in the copy. Evidence directory: `/private/tmp/transport-exercises-xaw9_enm`, including `exercise-4-results.json`, numbered execution logs, comparison/invariant runners, and environment metadata. This directory is temporary, outside Git; the controlled-environment installation/preparation evidence is in `/private/tmp/transport-pyproj-ab-mrdjlkw4`. Matching output-file existence alone was not accepted as success.

## Comparisons and consistency checks

CSV/Parquet tables were aligned by available identifying keys; unique `trip_uid` was used for trip tables. If selected keys were nonunique, complete non-floating column tuples retained row multiplicity. All columns, nulls, row counts, dtypes, and values were compared. Parquet Arrow schemas were checked excluding serialization metadata. Non-floating values were exact; floating values used `rtol=1e-10`, `atol=1e-9` for arithmetic/serialization roundoff. GeoPackages additionally matched layer sets, CRS, attributes, and topological or coordinate equality within `1e-7` projected metres. The geometry tolerance was not changed after the PT discrepancy.

Accepted parking events were checked for unique event keys, a next trip, resolved positive elapsed time, assigned destination zone, relocation distance at most 100 m, and duration at most 10,080 minutes. Duration fields reconciled with elapsed gaps and minute/hour conversion. These checks follow the implemented operational-inactivity definition; they do not establish continuous physical parking. Script-level zonal/temporal accounting and sensitivity assertions also passed.

Recorded additional invariant results:

- `exercise4_finalize_parking_events.py`: `[{"all_five_filters": "pass", "operator": "bird", "valid_events": 310300}, {"all_five_filters": "pass", "operator": "lime", "valid_events": 1063020}, {"all_five_filters": "pass", "operator": "voi", "valid_events": 85507}]`

## Exclusions and limitations

No extra legacy CSV/Parquet/GeoPackage artifacts in this exercise's data/audit/table directories were omitted.

Figure/report outputs and any legacy consumers outside the executed sequence remain unverified. The original data/audit/output inventory is checked for preservation across the continuation. Upstream cleaning, data completeness, external source truth, and causal interpretation are not established by matching references.
