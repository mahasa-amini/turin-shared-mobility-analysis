# Exercise 5 reproduction

Status: **passed**, 2026-10-14. All 6 listed analytical scripts exited 0 and all 29 emitted CSV/Parquet/GeoPackage artifacts matched existing local references. These checks establish computational reproduction, not independent scientific correctness. **Raw-to-cleaned processing was not rerun.** Figures, Word reports, and the separate commuting-cost exercise were deferred.

## Environment and isolation

Execution used CPython 3.13.13, macOS 14.6 arm64, in `/private/tmp/transport-pyproj-ab-mrdjlkw4/venv`, with all 24 application versions matching [requirements-lock.txt](../../requirements-lock.txt). The only change from the originally tested dependency set is the [controlled PyProj 3.7.2 pin](pt-geometry-diagnosis.md); GeoPandas 1.1.4, Shapely 2.1.2/GEOS 3.13.1, Pyogrio 0.13.0/GDAL 3.12.4 remain fixed. This environment passed `pip check`, all nine smoke checks, and a zero-change lock dry run.

The continuation workspace was `/private/tmp/transport-usage-kpz9n9_x/project`, with current source copied in and preceding stages regenerated there. No expected downstream artifacts were seeded. For Exercise 3 preparation, outputs were legitimately regenerated in the separate PyProj experiment and then copied to this continuation workspace, after full-reference comparisons. Writable destinations are real isolated directories; original inputs/references were read only.

## Inputs

The following manifest identifies supplied or previously regenerated prerequisite inputs. Intermediate outputs within this exercise are produced by the ordered scripts below. Input binary hashes identify the run inputs; result agreement was checked by content rather than binary hashes.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `config/exercise_5/cost_assumptions_2024.csv` | 948 | `8f53f5dc4bf068e05a1b3b00e4ac78a0af1c39a42e766c6cf2b1a42280ae0fd8` |
| `config/exercise_5/cost_sources_2024.csv` | 3247 | `94c6bac6a0015e4c6d85452e7a2615375d9e14a284c708369d9e2b7d47c0428a` |
| `config/exercise_5/tariff_sources_2024.csv` | 1084 | `3e2facb7618872747ebce630c564cb744fd7f183ac4983155a98bc3cf989fb37` |
| `config/exercise_5/tariffs_2024.csv` | 573 | `0b49c11f023ef170793aef062832a10aaa639bbb1a2554ac00b1aaf58029a87d` |
| `data/processed/harmonized/all_operators_2024_harmonized.parquet` | 127065678 | `779540195f55afd440d13ea7760424746e1358a1d66032b98a70fb884b27d74f` |

## Execution coverage

Each command used the environment's Python with `-I -B -u` and the copied script's absolute path; working directory was the isolated project. The PT-reference controlled experiment used its own isolated project. Exact expanded commands, logs, exit codes, per-artifact comparison keys, schema/row/column/layer counts, and invariant details are recorded in the temporary run directory.

| Script | Exit | Matched artifacts |
|---|---:|---:|
| `src/analysis/exercise5_cost_assumption_audit.py` | 0 | 0 |
| `src/analysis/exercise5_revenue_engine.py` | 0 | 5 |
| `src/analysis/exercise5_fleet_exposure_audit.py` | 0 | 6 |
| `src/analysis/exercise5_revenue_diagnostics.py` | 0 | 9 |
| `src/analysis/exercise5_cost_profitability_engine.py` | 0 | 5 |
| `src/analysis/exercise5_robustness_vat_sensitivity.py` | 0 | 4 |

Outputs stayed under `data/processed/exercise_5/`, `audit/exercise_5/`, and `outputs/tables/exercise_5/` in the copy. Evidence directory: `/private/tmp/transport-exercises-xaw9_enm`, including `exercise-5-results.json`, numbered execution logs, comparison/invariant runners, and environment metadata. This directory is temporary, outside Git; the controlled-environment installation/preparation evidence is in `/private/tmp/transport-pyproj-ab-mrdjlkw4`. Matching output-file existence alone was not accepted as success.

## Comparisons and consistency checks

CSV/Parquet tables were aligned by available identifying keys; unique `trip_uid` was used for trip tables. If selected keys were nonunique, complete non-floating column tuples retained row multiplicity. All columns, nulls, row counts, dtypes, and values were compared. Parquet Arrow schemas were checked excluding serialization metadata. Non-floating values were exact; floating values used `rtol=1e-10`, `atol=1e-9` for arithmetic/serialization roundoff. GeoPackages additionally matched layer sets, CRS, attributes, and topological or coordinate equality within `1e-7` projected metres. The geometry tolerance was not changed after the PT discrepancy.

Per-trip lower-bound PAYG revenues reconciled to unlock plus time revenue, with missing duration time components treated as zero only for that explicit lower bound. Scenario keys were unique. Direct vehicle OPEX reconciled to its three components; total cost equaled direct OPEX plus market overhead and depreciation; profit equaled revenue minus total cost. Per-operator scenario revenues reconciled to sums of trip-level modeled revenue. Comparisons used `rtol=1e-10`, `atol=1e-8` for component arithmetic at monetary aggregate scale. This supplements the scripts' own fleet-exposure, cost-sensitivity, VAT, and accounting checks. These are tariff/benchmark scenarios, not audited operator financial results.

Recorded additional invariant results:

- `exercise5_revenue_engine.py`: `[{"revenue_unlock_plus_time": "pass", "trips": 1693159}]`
- `exercise5_cost_profitability_engine.py`: `[{"direct_cost_total_cost_profit_and_revenue_reconciliation": "pass", "operator_scenarios": 9}]`

## Exclusions and limitations

No extra legacy CSV/Parquet/GeoPackage artifacts in this exercise's data/audit/table directories were omitted.

Figure/report outputs and any legacy consumers outside the executed sequence remain unverified. The original data/audit/output inventory is checked for preservation across the continuation. Upstream cleaning, data completeness, external source truth, and causal interpretation are not established by matching references.
