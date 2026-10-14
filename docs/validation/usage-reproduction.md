# Harmonization and usage reproduction

Validation date: 2026-10-14. Source commit: `20da4823e4d99bfe7e8a90de3d3b12ea3de42f69`.

**Result:** harmonization and all nine Exercise 1 analytical scripts completed with exit code 0. All 98 regenerated CSV/Parquet artifacts matched their existing local counterparts under the comparison rules below. This reproduces the cleaned-data-to-usage workflow on the tested platform; it does not validate the truth of the observations or every scientific assumption. **Raw-to-cleaned processing was not rerun.** Figures, reports, Exercises 2–5, and the separate commuting-cost workflow were not executed.

## Isolation and environment

Current tracked files were copied into a fresh `tempfile.mkdtemp` project at `/private/tmp/transport-usage-kpz9n9_x/project`. Only the nine inputs listed below were then copied in. No downstream `data/processed/`, harmonization audits, or `outputs/` were seeded. There were no symlinks. Generated datasets/audits/tables stayed inside the temporary copy, outside Git; logs and comparison metadata stayed in its parent directory.

The previously tested interpreter was `/private/tmp/transport-env-check-vgwa9s73/venv/bin/python`: CPython 3.13.13, macOS 14.6, arm64. No installation or environment replacement was performed. Resolved application versions are recorded in [requirements-lock.txt](../../requirements-lock.txt); runtime metadata, including packaging tools, was captured in `environment.json` in the run directory.

Before/after SHA-256 inventory checks confirmed all 558 original files under `data/`, `audit/`, and `outputs/` were unchanged, with no additions or removals. Input hashes identify the exact supplied cleaned datasets and audit inputs, not reproducibility of their upstream creation.

## Input manifest

Paths are relative to the original repository and were preserved in the temporary copy.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `data/cleaned/bird/bird_2024_clean.parquet` | 45540964 | `94aa899f9baade764ec4c592bdcbbeef0e202d6b5c7980db8959a17282112fb1` |
| `data/cleaned/bird/bird_2025_clean.parquet` | 52911266 | `daaf5eb06d69f728ff10ce8b217ec7e3a85607516a15e8bfed5d91ccdcb167fb` |
| `data/cleaned/lime/lime_2024_clean.parquet` | 125350385 | `ab433df9d699975f1c7b8121ceaaa9e13e6ddc737a3fb190ae357dcceb97d302` |
| `data/cleaned/lime/lime_2025_clean.parquet` | 44875071 | `b826e5cf5b34d5bb14de344436d3a4df414553d8f4ae59040e0fbce2e99e9662` |
| `data/cleaned/voi/voi_2024_clean.parquet` | 24047788 | `9e335243b123425f614bec2d84a43900df85ff5858440700122579b1d733c200` |
| `data/cleaned/voi/voi_2025_clean.parquet` | 27652189 | `4ae79cadfe4ba37284f2639bb75a400ac3223629241b46353d5647d797438ede` |
| `audit/bird/bird_final_cleaning_summary.csv` | 512 | `07b2131a893c7ec0b9b59a41a54a92a1a484c0cc5a4364dfdfab57084a0732df` |
| `audit/lime/lime_final_cleaning_summary.csv` | 579 | `bf681ebe252fbc3fd3234b24a841ef9d415d8a0f1b7128764bacd75fd5eb0f54` |
| `audit/voi/voi_final_cleaning_summary.csv` | 680 | `0566b1b3063bcd77d2932320697780ad9a4a4dced8244ff63c36fefbe75b2274` |

## Execution and destinations

Dependency inspection established: cleaned datasets → harmonization; harmonization and cleaning audits → cleaning impact/temporal coverage; coverage aggregates → daily/weekly/monthly trends; monthly trends → yearly comparison; daily/monthly outputs → usage patterns; harmonized records → hourly and vehicle analyses. Vehicle utilization also reads the regenerated harmonization summary.

Harmonization writes `data/processed/harmonized/` and `audit/harmonization/`. Exercise 1 writes `data/processed/exercise_1/` and `outputs/tables/exercise_1/`. These destinations were all inside the temporary copy.

Each command used the interpreter above with `-I -B`, the absolute path to the copied script, and the copied project as working directory. Standard output/error were captured together in numbered logs. The runner compared artifacts immediately after each successful script and was configured to stop at the first execution failure or comparison failure.

| Order | Executed script | Exit | Compared artifacts |
|---|---|---:|---:|
| 1 | `src/harmonization/harmonize_operators.py` | 0 | 11 |
| 2 | `src/analysis/exercise1_cleaning_impact.py` | 0 | 5 |
| 3 | `src/analysis/exercise1_temporal_coverage.py` | 0 | 12 |
| 4 | `src/analysis/exercise1_daily_trends.py` | 0 | 7 |
| 5 | `src/analysis/exercise1_weekly_trends.py` | 0 | 7 |
| 6 | `src/analysis/exercise1_monthly_trends.py` | 0 | 9 |
| 7 | `src/analysis/exercise1_yearly_comparison.py` | 0 | 7 |
| 8 | `src/analysis/exercise1_usage_patterns.py` | 0 | 10 |
| 9 | `src/analysis/exercise1_hourly_weekday.py` | 0 | 20 |
| 10 | `src/analysis/exercise1_vehicle_utilization.py` | 0 | 10 |

Command form (executed once for each script above):

```sh
/private/tmp/transport-env-check-vgwa9s73/venv/bin/python -I -B /private/tmp/transport-usage-kpz9n9_x/project/<script>
```

The placeholder represents the exact script paths in the execution table; fully expanded commands, elapsed times, exits, comparison keys, row/column counts, and per-artifact outcomes are captured in `results.json`. The run directory also contains `run_validation.py`, `driver.log`, numbered script logs, `input-manifest.json`, `original-hashes.json`, `source-commit.txt`, `environment.json`, and `final-checks.json`. These temporary artifacts are not committed and are not a permanent evidence distribution location.

## Content comparisons

References were read from the original repository; reference datasets were never supplied as pipeline inputs. CSV and Parquet contents were compared, not binary hashes. Checks covered column sets, row counts, key alignment, nulls, timestamps, coverage fields, integer counts, and numerical values in every regenerated artifact.

Harmonized Parquet files were aligned by unique `trip_uid`, with the complete key set checked and every column compared. Other tables were aligned by available identifying fields (operator/year, vehicle, period/date, weekday/hour, season, metric, etc.). Where those did not uniquely identify rows, the comparator used the complete non-floating column tuple and preserved multiplicity. The exact selected keys are recorded per table in `results.json`; no rows or value columns were excluded. Dtypes, non-floating values, and null positions were checked exactly. Floating values used `rtol=1e-10`, `atol=1e-9`, allowing only small serialization/arithmetic roundoff rather than substantive analytical changes.

An additional 505 numeric-column sum comparisons passed. Integer sums were exact; floating sums used `rtol=1e-10` and `atol=1e-9 × row count` to allow accumulation of the per-value absolute tolerance. Sums of rates/percentages were consistency checks only, not interpreted as scientific totals.

Regenerated harmonization summary and coverage tables matched in full, including operator/year row counts, source periods, observed timestamp endpoints, and temporal-detail availability:

| Operator | 2024 trips | 2025 observed trips |
|---|---:|---:|
| Bird | 390,844 | 467,176 |
| Lime | 1,196,200 | 428,318 |
| Voi | 106,115 | 120,773 |
| Total | 1,693,159 | 1,016,267 |

The totals describe different observation windows; they are not a full-year year-on-year comparison. Voi January 2024 remains month-only. The regenerated coverage registry also matched the existing record of Bird through November 18, Lime through April 29, and Voi through October 31 in 2025.

## Scope limits and historical artifacts

No execution failure or material value discrepancy was found among the 98 regenerated artifacts. Six pre-existing legacy hourly artifacts were not emitted by the current scripts and were not validated:

- `data/processed/exercise_1/hourly/hourly_profile_matched_yoy.parquet`
- `outputs/tables/exercise_1/hourly/empirical_peak_summary_matched_yoy.csv`
- `outputs/tables/exercise_1/hourly/peak_offpeak_matched_yoy_comparison.csv`
- `outputs/tables/exercise_1/hourly/peak_offpeak_summary_matched_yoy.csv`
- `outputs/tables/exercise_1/hourly/transport_period_summary_matched_yoy.csv`
- `outputs/tables/exercise_1/hourly/hourly_profile_matched_yoy.csv`

The current hourly script emits matched 12-full-week outputs; those regenerated outputs matched their corresponding references. The older matched-window artifacts above were neither silently reused nor treated as reproduced. Figure/report consumers and any dependence on legacy artifacts remain outside this run.

Matching existing results establishes computational agreement from these cleaned inputs, not independent confirmation of raw-data cleaning, external provenance, causal interpretation, or correctness of every model. Other analytical exercises remain unverified. No scientific code was changed to obtain these results.
