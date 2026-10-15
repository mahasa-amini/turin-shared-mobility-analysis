# Original Turin scooter inputs — 2024–2025, v1

This scooter-only dataset contains 40 original owner-supplied exports: two Bird annual CSVs, 16 Lime monthly CSVs and 22 Voi monthly Excel workbooks. The owner explicitly authorized their public publication on 15 October 2026. No dataset license is assigned and no unrestricted reuse permission is asserted. See PROVENANCE.md and manifest.csv in this directory.

Source repository: https://github.com/mahasa-amini/turin-shared-mobility-analysis
Dataset release: https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1

Verify the downloaded archive with the separate release SHA256SUMS before extracting. From the source repository root:

```sh
# The archive and its separate SHA256SUMS are in your download directory.
(cd /path/to/downloads && shasum -a 256 -c SHA256SUMS)
tar -xzf /path/to/downloads/turin-scooter-inputs-2024-2025-v1.tar.gz
shasum -a 256 -c scooter-dataset/SHA256SUMS
python scripts/check_raw_inputs.py --root . --manifest scooter-dataset/manifest.csv
```

Extract into a fresh checkout to avoid overwriting existing local inputs. Payload paths start with data/raw/{bird,lime,voi}/. Metadata stays under scooter-dataset/, so it does not overwrite the project README. No cleaned, harmonized or row-level audit records are included.

With Python 3.13 and requirements-lock.txt installed, run actual raw preparation in this order:

```sh
python src/cleaning/clean_bird.py
python src/cleaning/finalize_bird.py
python src/cleaning/audit_lime.py
python src/cleaning/finalize_lime.py
python src/cleaning/audit_voi.py
python src/cleaning/finalize_voi.py
python src/harmonization/harmonize_operators.py
python scripts/run_pipeline.py scooter --stages harmonize exercise1 --preflight --verify-inputs
```

The raw comparison harness additionally needs existing reference outputs and an exactly locked environment; it is not required to generate outputs from this archive. See docs/reproduction.md for downstream commands and validation limits.

Torino/GTT are excluded. Spatial/PT and the complete scooter workflow additionally require zone_statistiche_geo.{shp,shx,dbf,prj} under data/raw/external/torino_zones/ and ten GTT tables under data/raw/external/gtt_gtfs/: agency.txt, routes.txt, stops.txt, stop_attributes.txt, trips.txt, shapes.txt, feed_info.txt, calendar.txt, calendar_dates.txt, stop_times.txt. Obtain these separately with applicable rights. The recorded GTT snapshot is version 20260813, valid 12 August 2026–31 January 2027; the exact original archive/acquisition date and snapshot terms are unverified. The Torino original archive/version/license is also unverified. A new current download cannot be claimed byte-identical; compare against config/input_manifest.csv and intentionally revalidate a changed snapshot. Official starting points are https://aperto.comune.torino.it/dataset/zone-statistiche and https://www.gtt.to.it/open_data/gtt_gtfs.zip . GTT terms are at https://www.gtt.to.it/gtt_gtfs_license.html . These are acquisition leads, not a guarantee of the historical bytes or redistribution rights.

The files retain persistent vehicle IDs, Voi rental IDs, precise timestamps and endpoint coordinates, reservation indicators and available battery readings. Bird PERCORSO is empty/N/A, not a route trace. Voi January 2024 compact timestamps are damaged in the original export. No direct rider/contact or credential fields were found in actual columns or the documented heuristic scan; this is not anonymization certification.
