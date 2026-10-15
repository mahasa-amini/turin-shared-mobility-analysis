# Scooter dataset release and retained private staging

The owner-authorized [scooter dataset release](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1) publishes **only the 40 original Bird/Lime/Voi inputs**. The original mixed package at `data/distribution-staging/2026-10-14/` remains local and unchanged; its Torino/GTT and runtime-config archives were not uploaded. Bulk data remains outside ordinary Git history.

## Published assets and access

| Asset | Bytes | Contents |
|---|---:|---|
| [turin-scooter-inputs-2024-2025-v1.tar.gz](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/download/scooter-inputs-2024-2025-v1/turin-scooter-inputs-2024-2025-v1.tar.gz) | 107,905,912 | 40 unchanged exports + 4 scooter-specific metadata files |
| [SHA256SUMS](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/download/scooter-inputs-2024-2025-v1/SHA256SUMS) | 107 | Entire archive's SHA-256 |

Payload: **299,970,142 bytes**; two Bird annual CSVs, 16 Lime monthly CSVs, 22 Voi monthly XLSX workbooks. Metadata: `scooter-dataset/README.md`, `PROVENANCE.md`, `manifest.csv`, `SHA256SUMS`. Payload paths are relative `data/raw/{bird,lime,voi}/` paths; metadata cannot overwrite the project README. See [download/extraction/preflight commands](reproduction.md#download-original-scooter-inputs), [published manifest](validation/scooter-release-evidence/manifest.csv) and [release validation](validation/scooter-release.md).

The dataset-specific tag `scooter-inputs-2024-2025-v1` identifies the previously validated preparation-source commit `9da4f68ca5587dcd9381203c204c6b6e1adcbf3e`; current `main` adds the release utilities and documentation. The synthetic demo remains available in Git and does not read real records. GitHub Release assets are the actual download mechanism; there is no separate request service.

## Inspection, retained identifiers and permissions

All **actual** columns in all 40 exports and all workbook sheets match the expected 11 Bird / 13 Lime / 13 Voi source fields. [Inspection evidence](validation/scooter-release-evidence/column-inspection.json) records schemas, row counts and input hashes. No direct rider-name/contact or credential columns were found. A full-cell heuristic scan found no email, credential or explicitly labelled telephone patterns. It emitted no trip values. These checks do not certify anonymization or exclude every possible unlabelled personal value.

The publication retains Bird/Lime `ID_VEICOLO`, Voi `Targa veicolo` and `Identificativo noleggio`, all precise source timestamps and endpoint coordinates, reservation indicators and available battery readings. Persistent IDs and precise time/location records support linkage with external observations. Bird `PERCORSO` is entirely empty/`N/A`; Lime/Voi have no route trace column. Damaged Voi January 2024 timestamps remain unchanged. Cleaning and masking happen after extraction, according to [documented quality rules](data-quality.md).

The owner explicitly authorized this public scooter publication on **15 October 2026**; that authorization is recorded in the [release provenance](validation/scooter-release-evidence/package-PROVENANCE.md). No conflicting scooter redistribution restriction was found in the available provenance records. A dataset license has **not** been assigned, and unrestricted reuse is **not** asserted. Original acquisition dates, provider/course agreements and broader reuse grants are not supplied; none are invented. Choosing broader redistribution/reuse terms still requires documenting those grants and applicable attribution/conditions. Publication authorization is not presented as an open-data license or privacy certification.

## Excluded external inputs

Full spatial/PT and complete scooter reproduction still require the following separately acquired assets. They are absent from the release, and scooter-owner authorization is not applied to them.

| Asset | Required files and installation path | Acquisition and evidence requirements |
|---|---|---|
| Torino statistical zones | `data/raw/external/torino_zones/zone_statistiche_geo.{shp,shx,dbf,prj}` | Start at the [official catalog](https://aperto.comune.torino.it/dataset/zone-statistiche); it returned HTTP 502 again on 15 October 2026. Recover the exact original archive/version, acquisition date and applicable license/attribution notice. Verify the four files against `config/input_manifest.csv`. A catalog title, CRS or similar geometry is not proof of identical bytes or redistribution rights. |
| GTT GTFS | `data/raw/external/gtt_gtfs/`: `agency.txt`, `routes.txt`, `stops.txt`, `stop_attributes.txt`, `trips.txt`, `shapes.txt`, `feed_info.txt`, `calendar.txt`, `calendar_dates.txt`, `stop_times.txt` | The [official current archive endpoint](https://www.gtt.to.it/open_data/gtt_gtfs.zip) returned HTTP 200 on 15 October 2026; this is **not** verified as the historical snapshot. For matching reproduction obtain feed version **20260813**, valid **12 August 2026–31 January 2027**, establish its original archive/download date and snapshot-specific terms, and compare the ten extracted hashes with `config/input_manifest.csv`. |

[Current GTT terms](https://www.gtt.to.it/gtt_gtfs_license.html), rechecked on 15 October 2026, require attribution and restrict use to non-commercial purposes unless GTT provides prior written commercial authorization. Required source attribution names GTT S.p.A. – Gruppo Torinese Trasporti and links to [GTT](https://www.gtt.to.it). These restrictions cannot be described as unrestricted reuse. Their applicability to the exact local dated feed remains unverified. Torino's applicable license and byte-identical source remain unresolved. Neither external asset is included until its own evidence and applicable conditions are established and met.

If matching historical assets cannot be obtained, a current alternative requires an intentional manifest update and fresh analytical validation; do not claim identical reproduction or silently bypass hash failures. Optional QGIS styles, extra GTFS tables and caches are not required. Economic configuration is already tracked under `config/exercise_5/`.

## Preserved staging and reproducibility boundary

The original staging manifest has 58 payload files: 40 scooter exports (299,970,142 bytes), 14 external files (86,681,461 bytes), and four tracked configuration files (5,852 bytes). Its original three archives and manifests are preserved. [Original manifest](validation/cleaning-evidence/distribution-manifest.csv), [archive sizes/hashes](validation/cleaning-evidence/distribution-sizes.json), [archive validation](validation/cleaning-evidence/distribution-verification.json), and the [private staging script](../scripts/stage_data_package.py) document this earlier local package. The public archive is rebuilt from its scooter part, with a filtered manifest/checksum set and publication-specific metadata; it contains no external files or their private package metadata.

[Packaging utility](../scripts/package_scooter_release.py) refuses an existing destination, checks staged payload hashes against the inspected inputs, writes only 40 payload + 4 metadata files, and extracts/rechecks every payload and metadata file. Archive bytes can differ across rebuilds because tar/gzip metadata is retained; the published checksum identifies this exact release. [Public-download evidence](validation/scooter-release.md) records unauthenticated download, checksum verification, raw-input preflight and the boundary of additional raw regeneration/downstream preflight.

The earlier [raw-only reproduction](validation/cleaning-reproduction.md) matched six cleaned and eight harmonized Parquets byte-for-byte. Downstream analyses retain separate validation reports. Publishing raw inputs does not validate their ground truth, historical GTFS service, reports or a single raw-through-all-results execution.
