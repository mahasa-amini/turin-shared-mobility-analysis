# Raw-data cleaning and harmonization

The 14 October 2026 raw-only reproduction regenerated all six cleaned datasets and then all eight harmonized datasets. **Every file matches its existing reference byte-for-byte**, with exact matching values across every column. This validates implementation reproducibility for this snapshot, not the completeness or accuracy of operator reporting. [Execution and comparison evidence](validation/cleaning-reproduction.md) records the environment, commands, hashes and limitations.

## Actual workflow and dependencies

| Operator | Raw entry point → interim → finalizer | Source differences |
|---|---|---|
| Bird | [clean_bird.py](../src/cleaning/clean_bird.py) → two annual typed/flagged Parquets → [finalize_bird.py](../src/cleaning/finalize_bird.py) | Two annual CSVs, 11 expected source columns; vehicle ID but no rental ID, local clock timestamps, decimal reported km/minutes, `PERCORSO`, reservation; no battery columns |
| Lime | [audit_lime.py](../src/cleaning/audit_lime.py) → 16 monthly typed/flagged Parquets → [finalize_lime.py](../src/cleaning/finalize_lime.py) | 16 CSVs, 13 expected columns; vehicle ID but no rental ID, local timestamps with seconds, integer-rounded distance/duration, battery, `ANNO_MESE`; no route field |
| Voi | [audit_voi.py](../src/cleaning/audit_voi.py) → 22 monthly typed/flagged Parquets → [finalize_voi.py](../src/cleaning/finalize_voi.py) | 22 Excel workbooks, 13 expected columns; rental and vehicle IDs, compact timestamp codes, `Tempo Tot`, `KM Tot`, battery and reservation; mixed text/numeric Excel cells |

All three finalizers precede [harmonize_operators.py](../src/harmonization/harmonize_operators.py). The five `inspect_*` scripts are diagnostic tools, not runtime dependencies: no finalizer consumes their outputs. Thresholds and decisions are already encoded in the finalizers. pandas/NumPy provide typing and vectorized checks, openpyxl reads Voi, and PyArrow writes Parquet; no GIS or GTFS input is needed until downstream spatial/PT analysis. Scripts resolve paths from their own location and create local output directories, so the reproduction copies source into a separate root.

The [40-file source-header audit](validation/cleaning-evidence/source-column-checks.json) confirms the actual schemas have no missing or unexpected columns. CSV loaders treat empty strings as missing while preserving literal `N/A`. All 858,020 Bird `PERCORSO` entries are placeholders, not usable routes. Source-column names, including the supplied `LONGITUTIDE` spelling, are retained until harmonization. Required missing schema columns raise errors; unexpected columns are reported, not silently dropped. Voi strips header whitespace, accepts decimal commas through `to_numeric_safe`, and strips a trailing `.0` from timestamp codes before explicit `%Y%m%d%H%M%S` parsing. Numeric/date coercion failures become missing values and are audited. Voi raw text/identifier columns are stabilized as nullable strings for Parquet; Lime clean distance is explicitly float64 to avoid monthly Arrow int/float schema conflicts.

## Before and after

Counts below are from regenerated [final summaries](validation/cleaning-evidence/run/bird_final_cleaning_summary.csv), [Lime](validation/cleaning-evidence/run/lime_final_cleaning_summary.csv) and [Voi](validation/cleaning-evidence/run/voi_final_cleaning_summary.csv). Flag counts overlap and must not be added as exclusions.

| Operator/year | Raw rows | Clean rows | Globally removed/collapsed | Clean invalid distance | Clean invalid prezone spatial | Clean duration >180 min |
|---|---:|---:|---:|---:|---:|---:|
| Bird 2024 | 390,844 | 390,844 | 0 | 35 | 271 | 25 |
| Bird 2025 | 467,176 | 467,176 | 0 | 28 | 399 | 13 |
| Lime 2024 | 1,196,210 | 1,196,200 | 10 zero-elapsed | 61 | 5 | 0 |
| Lime 2025 | 428,318 | 428,318 | 0 | 9 | 4 | 0 |
| Voi 2024 | 130,769 | 106,115 | 24,654 duplicate excess | 10 | 10 | 3 |
| Voi 2025 | 160,996 | 120,773 | 40,223 duplicate excess | 70 | 70 | 3 |
| **Total** | **2,774,313** | **2,709,426** | **64,887** | **213** | **759** | **44** |

Voi duplicate collapse and Lime trip exclusion have different meanings. Voi retains 27 canonical trips with invalid duration; it does not require a valid duration for a core trip. Bird asserts structural validity and stops if it fails instead of implementing a general invalid-trip deletion policy. Lime requires essential identifiers, timestamps, all four endpoint coordinates and positive cleaned elapsed duration, and removes failures. In this snapshot its only global removals are ten zero-elapsed trips.

## Missing values, duplicates and anomalies

| Quality issue | Raw observation → cleaned decision/result |
|---|---|
| Missing essential values | Bird and Lime have no missing IDs, timestamps, endpoint coordinates, reported distance or duration. Voi has no missing core IDs, but 6,126 malformed start/end timestamps in 2024 raw rows, 1/86 missing endpoint-coordinate and distance rows in 2024/2025. After collapse: 5,236 trips without timestamp detail and 1/67 trips with incomplete coordinates. No fabricated replacements. |
| Duplicates | Bird/Lime exact duplicate rows: 0; Lime cross-file hash candidates: 0. Voi raw duplicate-ID excess: 24,654/40,223. Exact-duplicate excess: 24,654/38,241. Finalizer checks all trip-defining fields excluding reservation, raises on conflicts, selects the first source-period/source-row representative, and preserves duplicate-group size and collapsed count. Reservation disagreement affects 1,982 canonical 2025 trips: normalized variants are retained and clean reservation is missing. |
| Nonpositive reported duration | Bird: 0. Lime: 13,143/3,900 raw integer-rounded nonpositive values; after removing ten zero-elapsed trips, 13,133/3,900 rounded-zero trips remain because precise elapsed duration is positive. Voi: 11/20 nonpositive `Tempo Tot` rows before collapse; after UTC-duration priority/fallback, 10/17 canonical invalid durations remain flagged. |
| Raw reversed timestamps | Bird: 6/20; Lime: 15/0; Voi: 0/0. These are not equivalent to invalid trips because local-clock DST crossings can reverse the wall clock. |
| Zero and anomalous distance | Bird: 35/28 nonpositive reported distances become missing analytical distance, while trips remain. Lime retains 152,444/50,583 rounded-zero distances; 61/9 exact 100 km sentinel values become missing analytical distance. Voi retains 10/162 zero-displacement trips; its measurement is endpoint displacement, not route length. |
| Spatial quality | Bird has complete endpoints but 271/399 clear errors (>30 km displacement or >40 km/h endpoint speed); these invalidate spatial use. Lime has 5/4 broad-box outliers and 2/2 displacements >30 km; the union gives 5/4 spatial-invalid trips. Voi has 9/3 canonical broad-box outliers, also >30 km; together with missing endpoints, 10/70 fail spatial validity. |
| High speed / geometry | Bird masks reported speeds >30 km/h and retains 2,399/3,619 distance/geometry warnings (>1.10 ratio AND >0.10 km excess). Lime flags 449/96 endpoint-speed warnings >40 km/h without global deletion or speed-only spatial invalidation. Voi flags 68/65 kinematic warnings and marks speed invalid; trips remain. |
| Long/short trips | Long-duration flags are informational: Bird 38, Voi 6 above 180 minutes, Lime none after correction. Bird retains 17,231 displacements <20 m. No blanket outlier trimming, winsorization or numerical feature scaling is implemented. |

The [raw Bird audit](validation/cleaning-evidence/run/bird_cleaning_audit_summary.csv), [raw Lime audit](validation/cleaning-evidence/run/lime_yearly_raw_audit.csv) and [raw Voi audit](validation/cleaning-evidence/run/voi_yearly_raw_audit.csv) give the full before counts. Voi raw counts include duplicates; compare them to canonical counts with that change in denominator in mind. Battery values outside 0–100 or missing are handled by measurement validity; increases during trips are audit warnings, not deletion criteria.

## Timestamps and timezones

Bird parses naive Europe/Rome clock values and uses provider duration for analysis, preserving raw end time and a separately reconstructed end time. Differences of 55–65 minutes from timestamp-derived duration flag possible DST ambiguity: 11/38 records are retained. This is a heuristic, not a verified timezone repair. Harmonization preserves `END_TIME_RAW` as Bird/Lime `end_time_local` and leaves **all Bird and Lime UTC fields missing**. Their local end-minus-start interval therefore need not equal cleaned duration across DST; no exact UTC reconstruction or corrected endpoint clock is claimed.

Lime computes precise duration from raw local timestamps. A timestamp-minus-provider duration difference in [55,65] minutes applies −60 minutes; [−65,−55] applies +60 minutes. The finalizer validates remaining duration differences against rounding tolerance and stops on unexplained inconsistency. It corrects 24/53 records. This adjustment does not timezone-localize the raw timestamps or prove that every approximately one-hour discrepancy is DST. Original timestamps and integer-rounded duration remain available in cleaned data.

Voi interprets parsed compact timestamps as UTC, converts to Europe/Rome, and stores both UTC instants and naive local display values. This is the implementation's empirically motivated source-timezone assumption; the source export lacks explicit offsets. The finalizer checks converted local reporting months and provider/timestamp duration consistency. January 2024 day-zero timestamp damage cannot be repaired: 5,236 canonical trips retain their source month and provider-duration fallback, with local/UTC timestamp detail missing. Positive UTC elapsed duration has priority; positive `Tempo Tot` is fallback. Day/hour analyses must filter temporal detail rather than spreading those trips across artificial dates.

## Common schema, units and provenance

Harmonization/standardization aligns field names, physical types, units, identifiers and quality metadata; **it does not perform numerical feature scaling**. An explicit 45-field Arrow schema prevents all-null columns or operator inference from changing physical types. [The regenerated dictionary](validation/cleaning-evidence/run/harmonized_data_dictionary.csv) defines the fields.

| Fields | Common physical type / interpretation |
|---|---|
| `operator`, `vehicle_type`, `trip_uid`, `source_trip_id`, `vehicle_id`, `vehicle_uid` | Arrow string; pooled trip/vehicle IDs are operator-qualified. Bird/Lime have no source rental ID, so their trip IDs rely on provenance. |
| `start_time_local`, `end_time_local` | timestamp[ns], naive local clock; not a UTC instant |
| `start_time_utc`, `end_time_utc` | timestamp[ns, UTC], available for Voi only |
| `duration_min_clean` | float64 minutes, accompanied by `duration_source`, `timestamp_source_timezone`, `timestamp_precision` strings |
| `start_lat`, `start_lon`, `end_lat`, `end_lon` | float64 WGS84 degrees; downstream zoning projects to EPSG:3003 |
| `endpoint_displacement_km`, `endpoint_speed_kmh` | float64 km and km/h; common straight-line diagnostic, not travelled route length/speed |
| `distance_value_km`, `speed_value_kmh` | float64 km and km/h; accompanying measure-type/precision strings preserve operator semantics. Bird route distance, Lime integer-rounded reported distance and Voi endpoint displacement are not interchangeable. |
| `source_period`, `source_file`, `source_row`, `year` | strings for YYYY-MM and filename, int64 row/year; source rows are one-based data-row positions, not Excel worksheet line numbers |
| `valid_*`, `temporal_clock_ambiguous`, `endpoint_speed_warning_40`, `reservation_conflict`, `battery_available` | Boolean analysis eligibility and warning fields; availability and validity are distinct |
| `reservation_status`, `battery_start_pct`, `battery_end_pct` | nullable string and float64 percentages; unavailable source features remain missing |

Cleaned operator files retain detailed source fields, warnings and duplicate metadata; the smaller common schema preserves selected analysis/provenance fields, not every operator flag. Dataset lineage also needs the input checksums because identical source filenames can be replaced with different bytes.

## Unresolved limitations

Coordinate checks are preliminary: Bird tests completeness and displacement/kinematics without a broad bounding box or explicit latitude/longitude range check. Lime/Voi use latitude 44.90–45.20 and longitude 7.40–7.90 plus a 30 km displacement limit. These are not official zone membership, GPS validation or coordinate repair; final zoning happens later. Synthetic tests expose these distinct policies without silently changing research results.

Neither matching references nor flags prove that operator distances, timestamp assumptions, sentinel interpretation or observation coverage are externally correct. Count assertions and temporal checks are snapshot-specific and can reject new legitimate datasets. Voi IDs are deduplicated across all supplied months; null IDs are not safely canonicalizable and are rejected by final validity checks. Bird/Lime have no rental IDs; their zero observed duplicate counts are not a general identity guarantee. 2025 coverage differs by operator. GTFS is a later 2026–2027 reference, not historical service. Distribution, privacy and external-asset rights are addressed in the [distribution plan](data-distribution.md).
