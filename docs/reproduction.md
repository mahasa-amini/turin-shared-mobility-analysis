# Reproduce selected stages

A source checkout includes code, economic configuration and the curated results showcase. **Full-data execution requires separately supplied inputs.** There is no established public input download location or dataset license. The supported entry point begins with supplied cleaned records; raw-to-cleaned processing and full Word/PDF report validation remain incomplete. This is not a claim of verified end-to-end reproduction.

## Install and check a clean checkout

From the repository root, with Python 3.13 available:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
python scripts/check_repository.py
python -m unittest discover -s tests -v
python scripts/check_environment.py
```

The lock records the tested macOS arm64 environment, including PyProj 3.7.2. Other platforms are not yet validated. The GitHub Actions workflow attempts these data-independent checks on Ubuntu with Python 3.13; **hosted CI remains pending until it actually runs**. The environment checks create only synthetic temporary files and include optional report-library imports; passing them does not validate reports.

The runner uses the active `sys.executable` for child processes; activating the intended environment matters. It resolves the repository root from its own script location, so it also works when invoked by absolute path from another directory. No production command depends on an earlier temporary validation workspace. Scripts under `docs/validation/*-evidence/` are historical run records, not the maintained entry point.

## Supply inputs

Place files at the exact repository-relative paths in [config/input_manifest.csv](../config/input_manifest.csv). The 27 entries distinguish **23 separately supplied inputs** from **4 tracked economic configuration files**, and record purpose, stage, byte size, SHA-256 and known provenance:

- Six finalized Bird/Lime/Voi Parquets for 2024/2025 go under `data/cleaned/<operator>/`.
- Three final cleaning-summary CSVs go under `audit/<operator>/`; cleaned Parquets alone are insufficient for Exercise 1.
- Four Torino shapefile components go under `data/raw/external/torino_zones/`.
- Ten extracted GTFS tables go under `data/raw/external/gtt_gtfs/`. This entry point uses the extracted reference snapshot, not automatic archive download. Feed version 20260813 covers 12 August 2026–31 January 2027, later than the scooter observations.

The manifest describes the supplied validation snapshot. Acquisition dates, original archive URLs and licenses are unknown and have not been invented. Optional GTFS extras and the QGIS `.qml` style are not required by this entry point. Hashes identify local bytes, not authenticity or upstream-cleaning correctness. New data or scenario changes require an intentional manifest update and new validation; do not silently bypass mismatch errors.

`data/processed/`, downstream `audit/harmonization/` and `audit/exercise_*/`, and `outputs/` contain **reproducible intermediates/results**, not additional source inputs. [config/pipeline.json](../config/pipeline.json) lists the previously generated stage output contracts separately. It is deliberately conservative: resuming a downstream stage requires the complete outputs of its directly required upstream stages, not just a single sentinel file. These intermediate contracts check existence/nonempty files, not their freshness, hashes, schemas or scientific validity.

## Inspect and preflight

```sh
python scripts/run_pipeline.py scooter --list
python scripts/run_pipeline.py figures --list
python scripts/run_pipeline.py commuting --list
python scripts/run_pipeline.py scooter --preflight --verify-inputs
python scripts/run_pipeline.py scooter --stages harmonize exercise1 --dry-run
```

`--preflight` checks selected scripts, supplied input byte sizes and omitted upstream-stage output contracts. `--verify-inputs` additionally streams SHA-256 checks for the supplied inputs used by the selected stages. For a complete scooter plan, intermediate outputs scheduled earlier in that plan are deferred until their stage boundary. A successful preflight of that plan means the supplied inputs are present, not that downstream data already exist.

`--dry-run` prints exact command arguments and performs preflight without launching children or creating logs. On a checkout without scooter inputs it exits **2** and reports missing paths; `--list` works without data. Unknown stages or mixing workflow stage names also fail. Selective figure preflight checks regenerated upstream outputs; it does not require the original external inputs again.

## Execute only the stages needed

```sh
# Fresh supplied inputs → scooter analyses (33 scripts; potentially substantial work)
python scripts/run_pipeline.py scooter --verify-inputs

# Resume only selected analyses; existing omitted dependencies must be complete
python scripts/run_pipeline.py scooter --stages exercise3 exercise4

# Generate figures separately, after the corresponding analyses
python scripts/run_pipeline.py figures --stages figures1 figures2 figures3 figures4 figures5

# Separate commuting scenario: no scooter data required
python scripts/run_pipeline.py commuting
```

Scooter stages are `harmonize`, `exercise1` through `exercise5`; figure stages are `figures1` through `figures5`; commuting stages are `stage4` through `stage7`. Omit `--stages` to run all stages **within that workflow only**. Argument order is normalized to the validated order. Dependencies are never automatically added, and completed stages are never inferred or skipped: select only what needs rerunning. Output files can be overwritten by the selected research scripts. Use a separate checkout/copy for a fresh isolated reproduction; do not copy old downstream results into it.

Each execution gets a new `outputs/logs/<UTC-timestamp>/` directory containing numbered stdout/stderr logs and `run.json` with interpreter, working directory, commands, exits and timings. `--log-dir <new-path>` overrides the location and refuses an existing directory. Stage boundaries recheck inputs/dependencies and expected analytical output files. The first failed subprocess, missing output or failed preflight stops execution; already written outputs are retained and are not rolled back. Review the failed log before retrying. A script exit 0 is execution success, not full numerical or visual validation.

Before Stage 5, the runner executes [check_commuting_handoff.py](../scripts/check_commuting_handoff.py): Stage 4 values are recalculated and compared with Stage 5's manually embedded literals at 2/3/3 decimal places. A mismatch stops before Stage 5 and does not edit calculations. Stage 4 may therefore be evaluated twice in a full commuting run; these are small self-contained calculations. This guard does **not** replace the manual handoff with automatic cost propagation. Stages 6–7 consume existing Stage 5/6 CSVs if those stages are omitted; stale files cannot be detected by presence checks.

The parking maps prefer the canonical four `parking_by_zone_<scope>_2024.csv` outputs. The runner's `exercise4` contract requires those files and prevents the known incompatible legacy candidate-data fallback from being used through this entry point. Directly invoking the map script without canonical summaries can still fail in that fallback; it has not been refactored or validated.

## Validation boundary

[Figure validation](validation/figure-validation.md) records the reproduced analytical prerequisites, 18 executed figure scripts and five visually reviewed showcase figures. [Commuting validation](validation/commuting-validation.md) records arithmetic and visual checks for the separate scenario. The runner reuses those orders; it does not automatically repeat reference comparisons, scientific invariants or image review. Raw cleaning, full report reconciliation, unselected-figure visual approval, source licensing/provenance and historical GTFS service remain outside that evidence. See the [publication review](validation/publication-readiness.md) for checks performed on the release boundary.
