# Data distribution plan and private staging

A local raw-to-results package has been staged under `data/distribution-staging/2026-10-14/` and **has not been published**. The project already records owner authorization for scooter-data publication in [Data and reproduction](data-and-reproduction.md); this does not select a dataset license, establish external-asset rights, or certify privacy. No dataset license has been invented.

## Access model

Real inputs are **not publicly hosted**. No request/download service exists and no release destination has been selected. The [SYNTHETIC demo](../examples/synthetic/README.md) is available in Git and contains no transformed or sampled real trip records. The real package below stays local and private; public demo execution does not read or modify it.

## Evidence still needed to choose redistribution terms

| Asset | Specific missing evidence |
|---|---|
| Owner-supplied scooter files | Retain the actual dated authorization and provenance record, identifying the rights holder, covered operators/files, authority to permit onward redistribution, intended recipients and permitted uses (including commercial use and derivatives). Confirm any provider/course agreements and attribution conditions. Complete a cell-level privacy/linkage review of precise endpoint/time/vehicle/rental fields, document the proposed release granularity or controls, and select explicit terms compatible with those permissions. Recorded owner authorization alone is not a dataset license or privacy certification. |
| Torino `zone_statistiche_geo.{shp,shx,dbf,prj}` | Recover the exact official source URL, version/publication and acquisition dates, original archive or byte-identical components, and the license/attribution notice applicable to that version. Preserve the notice and establish whether redistribution and derivatives are permitted. CRS/attributes and a catalog title do not establish rights. |
| GTT feed version `20260813`, valid 12 August 2026–31 January 2027 | Recover the original archive/download URL and acquisition date, connect archive/table hashes to this snapshot, and retain the terms supplied with it or written GTT confirmation of applicable terms. Confirm redistribution/derivative conditions for the intended audience/use, required attribution and any commercial-use authorization. The current terms checked on 14 October 2026, described below, do not prove which terms accompanied this dated local feed. |

Keep asset-specific permissions and notices separate; do not infer one umbrella license for the bundle. These are unresolved evidence requirements, not a claim that permission has been denied or that a public service is available.

## Minimum inputs and layout

The package replaces supplied cleaned/interim/audit inputs with their original raw sources. Its manifest has 58 payload files. After raw regeneration, all downstream scooter-stage inputs passed [preflight with SHA-256 verification](validation/cleaning-evidence/staged-preflight.json) using external files copied only from this staging package; [the log](validation/cleaning-evidence/staged-preflight.log) records the checks. This is dependency preflight, not execution of the analyses.

| Part | Minimum contents | Payload bytes | Compressed archive bytes |
|---|---|---:|---:|
| `owner-scooter` | 2 Bird annual CSVs, 16 Lime monthly CSVs, 22 Voi monthly XLSX files | 299,970,142 | 107,906,158 |
| `external-review` | 4 Torino shapefile components, 10 required GTT GTFS tables | 86,681,461 | 9,958,543 |
| `runtime-config` | 4 economic assumptions/tariff/source-register CSVs, also tracked in Git | 5,852 | 7,959 |
| **Total** | **58 payload files** | **386,657,455 (368.75 MiB)** | 117,872,660 |

Each part has an unpacked directory and a `.tar.gz` archive. Each archive also includes `manifest.csv`, `SHA256SUMS` and `PROVENANCE.md`; these list relative installation paths, bytes, per-file hashes and provenance. The top-level `sizes.json` records archive sizes/hashes. [Committed manifest](validation/cleaning-evidence/distribution-manifest.csv), [payload checksums](validation/cleaning-evidence/distribution-SHA256SUMS), [size/hash report](validation/cleaning-evidence/distribution-sizes.json) and [archive verification](validation/cleaning-evidence/distribution-verification.json) allow review without adding data to Git. Total local staging storage, including both unpacked and compressed copies and metadata, is 504,557,172 bytes.

The four shape components are `zone_statistiche_geo.{shp,shx,dbf,prj}`. The required extracted GTFS tables are `agency.txt`, `routes.txt`, `stops.txt`, `stop_attributes.txt`, `trips.txt`, `shapes.txt`, `feed_info.txt`, `calendar.txt`, `calendar_dates.txt` and `stop_times.txt`. This set follows `REQUIRED_GTFS_FILES` in [PT preparation](../src/analysis/exercise3_prepare_pt_reference.py) and the [downstream input manifest](../config/input_manifest.csv). Shapefile `.qml`, `.DS_Store` and extra GTFS fare, timetable and vehicle tables are omitted because the maintained workflow does not need them. No hidden account credentials or runtime caches are packaged.

Source code, pinned requirements and documentation come from the Git checkout, not the data archives. Raw cleaning uses pandas/NumPy/openpyxl/PyArrow; spatial/results execution additionally uses the pinned GIS/plotting dependencies. Interim, cleaned, harmonized, zoned, PT reference, parking and revenue files, generated audit summaries and figures are outputs to regenerate. Final cleaning summaries are required by Exercise 1 but are produced by the raw workflow. The separate commuting calculation needs no scooter/external data; its scenario inputs are embedded in tracked code. Full report reconciliation remains unverified.

To reconstruct inputs, unpack each approved archive and copy the contents of each part (`data/` or `config/`) onto a clean source checkout. Run raw cleaning/finalization/harmonization in the order in [cleaning reproduction](validation/cleaning-reproduction.md). The harness additionally requires references for validation; these references are deliberately **not** part of the minimum execution bundle. For execution without references, invoke the seven research scripts directly in that order. After raw preparation, use `scripts/run_pipeline.py scooter --verify-inputs` and the separate figure workflow described in [reproduction](reproduction.md). The supplied manifest preflight hashes match the regenerated cleaned outputs for this environment. On another platform, review any representation differences and intentionally update the manifest only after validation; do not bypass discrepancies silently.

The [staging script](../scripts/stage_data_package.py) accepts a new destination and refuses overwrite:

```sh
.venv/bin/python scripts/stage_data_package.py \
  --destination data/distribution-staging/2026-10-14
```

For later staging choose a new destination. It copies, hashes and compresses locally; it has no upload function. Archive bytes/hashes can vary between stagings because tar metadata is retained; payload hashes identify the source bytes. Git ignores all of `data/`, so bulk staging remains local.

## Actual provenance, privacy and licensing findings

Scooter expected schemas contain precise trip endpoint coordinates, clock times, persistent vehicle identifiers, and Voi rental IDs. These fields are necessary for detailed spatial, temporal, duplicate and parking analysis, but make trip-level release sensitive to linkage with outside observations. No direct rider-name, rider-email or rider-phone fields occur in the expected source schemas; this is not a certification of anonymization. Bird's route column is entirely empty/`N/A`, and Lime/Voi provide no route trace column. Raw Voi January timestamps are damaged, not anonymized intentionally. Detailed row-level audit exports replicate sensitive trip fields and are excluded from the Git evidence and input package. A schema-level review does not establish that all cell values are free of personal information.

GTT's [current official terms](https://www.gtt.to.it/gtt_gtfs_license.html), checked 14 October 2026, specify non-commercial use, attribution and prior written authorization for commercial use. The required attribution names GTT S.p.A. – Gruppo Torinese Trasporti and links to [GTT](https://www.gtt.to.it). These are concrete restrictions, so the external part must not be presented as unrestricted open data. The local feed is version **20260813**, valid **12 August 2026–31 January 2027**. Its original archive/download date and the terms that accompanied that snapshot are unavailable; current website terms do not establish the historical local file's chain of custody. Do not substitute the current downloadable feed and claim identical reproduction.

The [Torino statistical-zone catalog](https://aperto.comune.torino.it/dataset/zone-statistiche) was located, but the primary page returned HTTP 502 during this check. No applicable license or byte-identical source archive was verified. The bundled shapefile's CRS and attributes support analytical use; they do not establish redistribution rights. Its external-review status remains unresolved.

## Decisions before public distribution

1. Confirm the intended scope of the already recorded scooter-owner authorization, choose explicit dataset terms, and retain the authorization/provenance record with the release. Decide whether trip-level records should be access-controlled or whether public users receive aggregates/synthetic examples; removing vehicle IDs alone would also break parking reproduction without eliminating endpoint/time linkage risk.
2. Establish snapshot-specific GTT terms and preserve required attribution; obtain any permission needed for the intended use. Recover the exact Torino source/version and its applicable license. Keep these external assets separate, or provide verified acquisition instructions if redistribution cannot be established.
3. Choose an appropriate research-data repository or controlled storage, version the release, document access and retention, and publish checksums/provenance alongside it. Ordinary Git is not the bulk-data channel. Do not use a single invented umbrella license for mixed assets.
4. Validate reconstruction from the staged bundle on the target environment, then approve the concrete release contents. This task verifies the raw cleaning and harmonization portion, archive contents and original preservation; it does not claim a new full raw-to-report run.

No release destination has been selected and no upload has occurred.
