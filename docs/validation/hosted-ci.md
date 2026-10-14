# Hosted GitHub Actions validation

The public [repository](https://github.com/mahasa-amini/turin-shared-mobility-analysis) was published on 2026-10-14, preserving the original 21 commits. The [first actual hosted run](https://github.com/mahasa-amini/turin-shared-mobility-analysis/actions/runs/38634273103) completed with **success** for commit `1d4b7a96eec5415044e87ba17b9a86c9e06413be`.

The `checks` job ran on Ubuntu 24.04 with CPython **3.13.16**. All configured steps passed:

- Installation of all 24 pinned dependencies from `requirements-lock.txt`, followed by `pip check`.
- Syntax parsing of 81 Python files and checking of 182 local Markdown targets.
- All 16 runner/handoff and zone-assignment regression tests.
- All nine synthetic environment checks, including geospatial, Parquet, spreadsheet, plotting and document-library capabilities.
- Scooter/figure stage listing and commuting dry-run without research datasets.

[Recorded run/job/step metadata](publication-evidence/hosted-ci-first-run.json) identifies the checked commit, timestamps and results. No CI fix or weakened check was needed. A subsequent documentation-only commit records this result; its current status is available from the [workflow runs](https://github.com/mahasa-amini/turin-shared-mobility-analysis/actions/workflows/checks.yml).

This establishes hosted installation and data-independent test coverage. It does not establish Linux full-data analytical reproduction, raw-to-cleaned processing, full report validation, input provenance/licensing or actual historical GTFS service. Bulk local `data/`, `audit/`, `outputs/` and the virtual environment were excluded from publication. No release claiming full-data reproducibility was created.
