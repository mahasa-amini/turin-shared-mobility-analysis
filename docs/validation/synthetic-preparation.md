# Public SYNTHETIC preparation validation — 15 October 2026

**Access update — 15 October 2026:** owner-authorized original scooter inputs are now [GitHub Release assets](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1); Torino/GTT remain excluded. The statements below about unpublished inputs describe the earlier validation boundary. See [current distribution status](../data-distribution.md).

The [demo command](../../scripts/demo_preparation.py), `python scripts/demo_preparation.py`, passes locally on CPython 3.13.13, macOS arm64, in the existing project environment. It executes all seven unmodified production preparation scripts on only [hand-authored synthetic fixtures](../../examples/synthetic/README.md), in a fresh temporary root. No existing real inputs, reference outputs or private staging files are copied or read by the demo.

| Operator/year | Raw → cleaned → harmonized |
|---|---:|
| Bird 2024 | 4 → 4 → 4 |
| Bird 2025 | 1 → 1 → 1 |
| Lime 2024 | 8 → 6 → 6 |
| Lime 2025 | 1 → 1 → 1 |
| Voi 2024 | 1 → 1 → 1 |
| Voi 2025 | 7 → 6 → 6 |
| **Total** | **22 → 19 → 19** |

Expected case identities, cleaned/harmonized values, masks, flags and timestamps pass. All six operator/year harmonized files and both pooled files have the production 45-field Arrow schema; pooled frames equal the concatenated operator frames. Trip IDs are unique, lineage fields are present, and Bird/Lime UTC fields remain missing. Production validation assertions and Parquet readback checks remain enabled. No production-script adaptation was necessary, so default full-data behavior is preserved.

Additional local verification passed:

- `python -m unittest discover -s tests -v`: all 21 cleaning/comparison, runner/handoff and spatial-assignment regression tests.
- `python scripts/check_environment.py`: all nine synthetic dependency checks.
- `python -m pip check`: no broken requirements.
- `python scripts/check_repository.py`: Python syntax and local Markdown targets.
- `git diff --check`: no whitespace errors.
- Before/after SHA-256 comparison: all **656** non-`.DS_Store` private files under `data/`, `audit/` and `outputs/` unchanged, including the staged real-data package. The comparison inventory stayed outside Git.

The [hosted workflow](../../.github/workflows/checks.yml) installs `requirements-lock.txt` and runs the demo as its own step. Local verification here used the existing environment, not a newly installed locked environment. The [hosted run for `dd6baa7`](https://github.com/mahasa-amini/turin-shared-mobility-analysis/actions/runs/38722186467) subsequently passed on Ubuntu 24.04 / CPython 3.13.16, including the demo, all 21 regressions and nine environment checks; see [hosted CI evidence](hosted-ci.md).

This validates the public synthetic execution path and regression behavior. The separately recorded [real raw-only reproduction](cleaning-reproduction.md) supplies before/after research counts and exact raw-to-harmonized comparisons. Downstream analyses retain their separate validation scopes; no new full-data or raw-to-report run is claimed. Real inputs are not publicly hosted and no request/download service exists.
