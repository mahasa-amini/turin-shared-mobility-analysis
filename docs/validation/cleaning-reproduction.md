# Cleaning reproduction — 14 October 2026

## Result and boundary

All **six cleaned and eight harmonized Parquets match their existing references byte-for-byte**. All-column logical comparisons also pass: same row/column order, identifiers, dtypes, null counts and positions, timestamps and numeric values. Maximum observed numerical difference is zero. There are no representation differences requiring an exception. This run validates raw → interim → cleaned → harmonized processing; downstream analyses were validated separately in the linked project reports, not rerun here.

| Operator | 2024 raw → cleaned | 2025 raw → cleaned | Cleaned columns |
|---|---:|---:|---:|
| Bird | 390,844 → 390,844 | 467,176 → 467,176 | 47 |
| Lime | 1,196,210 → 1,196,200 | 428,318 → 428,318 | 72 |
| Voi | 130,769 → 106,115 | 160,996 → 120,773 | 87 |

Harmonized files each have 45 columns. Combined 2024 has 1,693,159 rows; combined 2025 has 1,016,267. The three final cleaning-summary CSVs also pass all-column comparisons against the original summaries.

## Isolation and execution

The final run used `/private/tmp/transport-cleaning-locked-env/bin/python`: CPython 3.13.13, macOS arm64, with all 24 versions from `requirements-lock.txt`. A new temporary environment was created with `.venv/bin/python -m venv /private/tmp/transport-cleaning-locked-env`, then its interpreter ran `-m pip install -r requirements-lock.txt`. The project `.venv` was preserved. [Installed versions](cleaning-evidence/run/environment.txt), [pip check](cleaning-evidence/pip-check.log) and [nine synthetic dependency checks](cleaning-evidence/environment-check.log) document the environment. Dependencies were installed only in the new temporary environment; no project or global environment was changed. A checked environment/lock is platform-specific; this does not validate full-data execution on Linux.

The maintained [reproduction harness](../../scripts/reproduce_cleaning.py) refuses installed-version drift from the lock, optimized Python that would disable quality assertions, and existing workspace/evidence paths. It copies source and **only the original 40 operator raw inputs** into an empty root, then runs these scripts in order:

1. `src/cleaning/clean_bird.py`
2. `src/cleaning/finalize_bird.py`
3. `src/cleaning/audit_lime.py`
4. `src/cleaning/finalize_lime.py`
5. `src/cleaning/audit_voi.py`
6. `src/cleaning/finalize_voi.py`
7. All six cleaned comparisons must pass before `src/harmonization/harmonize_operators.py`.
8. Compare all eight regenerated harmonized files and the three final cleaning summaries.

No existing interim, cleaned, harmonized or audit outputs were copied into the workspace. No symlinks to reference datasets were used. References were read only after regeneration for comparisons. No spatial/GTFS input is required for these seven scripts.

Actual command, from the repository root:

```sh
/private/tmp/transport-cleaning-locked-env/bin/python scripts/reproduce_cleaning.py \
  --workspace /private/tmp/transport-cleaning-20261014-locked \
  --evidence docs/validation/cleaning-evidence/run
```

For a later run choose **new** workspace and evidence paths. The final local workspace is retained for inspection but is not a committed execution dependency. Preliminary runs in the project `.venv` also reproduced every file byte-for-byte. The first had a dictionary evidence-copy filename typo after all research steps passed; that was fixed. A later explicit lock comparison found five installed-version differences in the project environment (`contourpy`, `fonttools`, `kiwisolver`, `lxml`, `pyparsing`), despite identical cleaning-library versions. Rather than accept that environment difference, the final run repeated every step from raw in the newly pinned environment. Preliminary evidence remains local in `data/validation/cleaning-first-run-evidence/` and `data/validation/cleaning-project-venv-evidence/`; the committed evidence is the successful locked run.

## Evidence and comparisons

- [Source schema audit](cleaning-evidence/source-column-checks.json): all 40 source files have the expected columns, and Bird has no non-placeholder route entries.
- [Staged-input preflight](cleaning-evidence/staged-preflight.json): the downstream scooter plan passes hash verification using regenerated cleaned/summary files and the staged external inputs, without executing downstream analyses.
- [Final checks](cleaning-evidence/final-checks.json): 772 columns checked, archive hashes verified, raw input/package lineage matched, and locked installed versions confirmed.
- [Execution record](cleaning-evidence/run/execution.json): interpreter, exact commands, working directories, exits and durations for all seven scripts. Per-script logs live alongside it; [harness completion log](cleaning-evidence/reproduction.log).
- [Input manifest/hashes](cleaning-evidence/run/input-hashes.json): every original raw input copied for regeneration; [executed source hashes](cleaning-evidence/run/source-hashes.json).
- [All-column comparisons](cleaning-evidence/run/comparisons.json): per-column dtypes, null counts/masks, comparison mode, unequal-value counts and maximum numerical differences, plus actual/reference file SHA-256.
- [Cleaning-summary comparisons](cleaning-evidence/run/summary-comparisons.json): all three aggregate summaries.
- [Original artifact hashes](cleaning-evidence/run/original-hashes.json) and [preservation result](cleaning-evidence/run/preservation.json): all 541 pre-existing non-metadata files under raw/interim/cleaned/processed, audit and outputs remain unchanged. The distribution staging package is a separate newly created output, outside this preservation set.
- Regenerated raw/monthly/final aggregate audit CSVs and the [common-field dictionary](cleaning-evidence/run/harmonized_data_dictionary.csv) are included; row-level suspicious/removed/duplicate exports remain local to avoid publishing detailed records in Git.

Comparisons require identical shape and column order, compare all rows in their emitted order, and require identical null masks. Integers are exact; timestamps compare exact clock values/instants; strings and booleans compare logical values. Float comparisons permit only `rtol=atol=1e-12` roundoff and report the actual maximum. Here every maximum is **0**, dtypes match, and byte equality is stronger than the numerical tolerance. Reordering, lost leading zeros, changed identifiers, missing timestamps or shifted nulls cannot be excused by an aggregate-only match. The harness raises on an unexplained value/schema discrepancy and does not harmonize if cleaned comparisons fail. Parquet bytes need not generally be identical across library versions, but no such difference occurred here.

## Regression coverage and quality decisions

[Cleaning rule tests](../../tests/test_cleaning_rules.py) use only synthetic DataFrames and copy imported modules into a temporary root, so module-scope directory creation cannot affect production paths. They cover:

- Bird invalid distance/speed masking, retained short displacements and possible-DST duration reconstruction.
- Lime spring/autumn correction, sentinel masking without long-distance classification, legitimate rounded zero, positive subminute trips, zero-elapsed rejection, missing coordinates and spatial-only invalidity.
- Voi canonical duplicate collapse, conflicting reservation metadata, hard failure on trip-defining disagreements, damaged compact timestamps, provider-duration fallback and UTC→Rome conversion.
- Comparison failures for changed identifiers, timestamps, null positions and numeric values.

Run `python -m unittest discover -s tests -v` in the locked environment; the final [test log](cleaning-evidence/tests.log) includes the existing runner and spatial-assignment regression suite. [Data-quality decisions and metrics](../data-quality.md) distinguish exclusion, masking and warning policies. [Distribution evidence](../data-distribution.md) describes the separately staged raw-to-results inputs. The existing downstream runner still begins at cleaned files; use this harness for validated raw preparation, then the runner for analyses.

## Remaining limits

Matching references demonstrates reproduction, not ground truth. No correction was made to the research thresholds or cleaning results. Timezone interpretation, rounded/sentinel measurement semantics, the missing January Voi detail, snapshot-specific assertions, unequal coverage and later GTFS remain substantive limits. Full Word/PDF report reconciliation and a single fresh raw-through-all-results execution remain outside this run. No package or bulk data has been published or added to Git.
