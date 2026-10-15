# Public scooter dataset release — 15 October 2026

Published: [Original Turin scooter inputs 2024–2025, v1](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1), tag `scooter-inputs-2024-2025-v1`, with [recorded GitHub asset metadata](scooter-release-evidence/release.json). The owner explicitly authorized public scooter publication; no repeat authorization was requested. No conflicting scooter redistribution restriction was found in the available provenance records. No dataset license or unrestricted reuse grant is assigned.

## Contents and inspection

The release contains 40 unchanged original exports: two Bird annual CSVs, 16 Lime monthly CSVs, 22 Voi monthly Excel workbooks, **299,970,142 payload bytes / 2,774,313 raw rows**. The archive adds four metadata files under `scooter-dataset/`: README, provenance, filtered manifest and per-file SHA-256. It excludes all Torino/GTT assets, generated records/results, row-level audit exports, credentials/caches and runtime configuration already tracked in Git. The dataset tag points at previously validated preparation source commit `9da4f68ca5587dcd9381203c204c6b6e1adcbf3e`; current `main` supplies release/preflight utilities and documentation.

The [maintained inspector](../../scripts/inspect_scooter_inputs.py) read all actual CSV columns/cells and every sheet of all 22 workbooks, and verified their staged byte sizes/hashes. All schemas matched the source loaders: Bird 11 columns, Lime/Voi 13. No direct rider/contact or credential fields, email patterns, credential patterns or explicitly labelled telephone patterns were found. [Inspection evidence](scooter-release-evidence/column-inspection.json) contains only field/sheet names, aggregate row counts and input hashes, not sensitive values. Reinspection with the maintained script reproduced the same report.

Retained: Bird/Lime `ID_VEICOLO`, Voi `Targa veicolo` and `Identificativo noleggio`, precise source timestamps and endpoint coordinates, reservation fields and available battery readings. These records can support linkage and are not certified anonymized. Unlabelled personal text is not exhaustively detectable by the heuristic scan. All Bird `PERCORSO` cells were empty/`N/A`; Voi's original January timestamp damage remains.

## Packaging and public verification

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `turin-scooter-inputs-2024-2025-v1.tar.gz` | 107,905,912 | `ab046c7b082387cd9d9195d415dc7dd6e5e7ba19e3600e5be202718b4b64b9ed` |
| `SHA256SUMS` | 107 | `bc31b3163b282581f1c37c29b0ef72ac3f4b99f907cfa2c6b7a6a8fd8fc9cd05` |

The [packager](../../scripts/package_scooter_release.py) used only the existing owner-scooter staging part, checked all 40 hashes, created a scooter-only manifest/checksum set and verified safe extraction of exactly **40 payload + 4 metadata files**. All extracted bytes matched; no extra files or nonregular members occurred. [Package verification](scooter-release-evidence/package-verification.json), [manifest](scooter-release-evidence/manifest.csv), [archive README](scooter-release-evidence/package-README.md), [provenance](scooter-release-evidence/package-PROVENANCE.md) and [release notes](scooter-release-evidence/release-notes.md) record the concrete scope. Server asset digests matched the local package.

After publishing, unauthenticated `curl -fL` downloaded both actual public asset URLs into a new temporary download directory. The downloaded archive matched the **published checksum** and the expected local/server SHA-256 and size. Extraction into a new root produced exactly the expected 44 files; all 40 extracted payload hashes matched. `python scripts/check_raw_inputs.py --root <extracted-root> --manifest <extracted-root>/scooter-dataset/manifest.csv` passed. [Public-download verification](scooter-release-evidence/public-download-verification.json) records the result and subsequent commands. No local archive was substituted for the public download.

## Regeneration and preflight boundary

A new isolated workspace contained only the publicly downloaded raw payloads, production source, scripts, tracked configuration and the small trusted manifest required by raw preflight. No existing cleaned/interim/harmonized/audit/reference outputs or external assets were copied into it. The seven production preparation scripts all exited 0, regenerating six cleaned and eight harmonized files. **All 14 Parquet hashes matched the previously recorded reference hashes**; all nine regenerated cleaned/summary input hashes matched `config/input_manifest.csv`.

The run used the existing macOS arm64 / CPython 3.13.13 project environment, not a new locked environment: [installed/locked version comparison](scooter-release-evidence/environment.json). This publication verification does not claim fresh Linux full-data execution or a new all-column comparison report; byte identity is checked against the earlier [raw preparation validation](cleaning-reproduction.md).

- `scooter --stages harmonize exercise1 --preflight --verify-inputs`: **exit 0**, all supplied inputs verified; [preflight log](scooter-release-evidence/temporal-preflight.log).
- Full `scooter --preflight --verify-inputs`: **expected exit 2**, missing **exactly the 14 excluded Torino/GTT paths**, with no other missing input; [boundary log](scooter-release-evidence/full-preflight-external-boundary.log).

Downstream analyses and full reports were not rerun. [External acquisition requirements](../data-distribution.md#excluded-external-inputs) identify the four zone components, ten GTT tables, dated feed version and unresolved snapshot-specific rights. The current GTT download endpoint was reachable by HTTP HEAD, but was not downloaded or claimed identical. The Torino catalog again returned HTTP 502. Current [GTT terms](https://www.gtt.to.it/gtt_gtfs_license.html) were rechecked and do not establish historical snapshot terms.

[Staging preservation](scooter-release-evidence/staging-preservation.json) confirms all **58 original staged payload hashes** and all **three original archive hashes/sizes** remain unchanged. The full mixed package is still private; only the new scooter-only archive was published outside Git history.

## Code and CI checks

All **25** data-independent regression tests pass locally, including four new raw-preflight tests for valid inputs, missing files, same-size corruption and substituted manifests. The synthetic preparation demo also passes. Syntax/Markdown links and whitespace checks pass. Hosted CI is verified for the pushed documentation/utility commit; its result is reported with the final commit and run link.
