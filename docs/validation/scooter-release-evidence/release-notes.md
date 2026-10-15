# Original Turin scooter inputs (Bird, Lime, Voi), 2024–2025 — v1

Owner-authorized public publication of the **original scooter inputs only**. Dataset tag: `scooter-inputs-2024-2025-v1`. This snapshot supports the recorded raw-to-harmonized reproduction; it is not a new validation of all downstream analyses or reports.

**Contents:** 40 unchanged operator exports (2 Bird annual CSVs, 16 Lime monthly CSVs, 22 Voi monthly XLSX workbooks), totaling 299,970,142 uncompressed payload bytes and 2,774,313 raw rows. The archive includes repository-relative `data/raw/{bird,lime,voi}/` paths and `scooter-dataset/{README.md,PROVENANCE.md,manifest.csv,SHA256SUMS}`. No real trip records were added to ordinary Git history. Source code and economic configuration remain in Git; generated cleaned/harmonized/audit/results files are not included.

**Privacy/identifiers:** actual columns and all CSV/workbook-sheet cells were inspected. No direct rider-name/contact or credential fields, email patterns, credential patterns or explicitly labelled telephone patterns were found. This heuristic review is not anonymization certification. Persistent vehicle IDs, Voi rental IDs, precise source times/endpoints, reservation indicators and available battery readings are retained unchanged. Voi January 2024 timestamp defects remain; Bird route entries are empty/N/A.

**Permissions:** the owner explicitly authorized this public publication on 15 October 2026. No conflicting scooter redistribution restriction was found in the available provenance records. No dataset license is assigned and no unrestricted reuse permission is claimed; broader grants and original acquisition dates are not documented.

**Excluded external assets:** Torino statistical zones and all GTT GTFS tables. Their snapshot-specific redistribution evidence remains unresolved. Full spatial/PT reproduction separately requires the four zone shapefile components and ten GTFS tables listed in the package README and [reproduction guide](https://github.com/mahasa-amini/turin-shared-mobility-analysis/blob/main/docs/reproduction.md). The recorded GTT feed is version 20260813, valid 12 August 2026–31 January 2027; a current feed is not claimed byte-identical. Current [GTT terms](https://www.gtt.to.it/gtt_gtfs_license.html) restrict commercial use and require attribution; those terms do not establish the local historical snapshot's chain of custody.

Download both attached assets into a separate directory, then from a fresh repository checkout:

```sh
(cd /path/to/downloads && shasum -a 256 -c SHA256SUMS)
tar -xzf /path/to/downloads/turin-scooter-inputs-2024-2025-v1.tar.gz
shasum -a 256 -c scooter-dataset/SHA256SUMS
python scripts/check_raw_inputs.py --root . --manifest scooter-dataset/manifest.csv
```

Use the current `main` checkout for the added preflight utility and release documentation. The dataset tag initially identifies the previously validated preparation source commit; the raw input manifest records the dataset independently. The public archive is integrity-checked before publication; post-publication public-download and extracted-input verification are recorded in the repository's release validation report.
