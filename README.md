# Shared E-Scooter Mobility in Turin

How do shared e-scooters fit into urban travel, and what can rental records reveal about their use and operation? This university transport course project analyzes Bird, Lime, and Voi records from Turin in 2024–2025, combining temporal analysis, spatial origin–destination (OD) analysis, public-transport reference data, and operational and economic models.

The scooter analysis addresses five questions:

1. **Temporal usage:** How does activity vary by operator, season, weekday, and time of day within comparable observation windows?
2. **Spatial OD patterns:** Which statistical zones generate and attract trips, and how do flows change across time periods?
3. **Potential public-transport interaction:** Where are trip endpoints near stops, and which trips are compatible with a direct public-transport route?
4. **Inferred parking intervals:** What do gaps between successive rentals of the same vehicle suggest about inactivity and its spatial distribution?
5. **Economic scenarios:** How do assumed tariffs, fleet exposure, and operating costs affect estimated revenue and profitability?

A separate **generalized commuting-cost exercise** compares a home–Politecnico di Torino round trip across transport modes. It combines monetary costs with travel, access, and waiting time, value-of-time sensitivity, and Pareto comparisons. It is not a downstream stage of the scooter-data pipeline.

## Run and check the project

Start with the [clean-checkout reproduction guide](docs/reproduction.md). Original scooter inputs are downloadable from the [dataset release](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1); full spatial/PT execution also requires separately acquired Torino/GTT inputs listed in the [input manifest](config/input_manifest.csv). Git includes code, configuration, curated results and a wholly synthetic preparation demo.

```sh
python scripts/run_pipeline.py scooter --list
python scripts/run_pipeline.py scooter --preflight --verify-inputs
python scripts/run_pipeline.py figures --stages figures1 --dry-run
python scripts/run_pipeline.py commuting --dry-run
```

Activate a Python 3.13 environment and install the pinned dependencies first. Scooter analysis, figures and commuting are separate workflows; stage selection never automatically reruns upstream work. [Automated checks](.github/workflows/checks.yml) cover syntax, local links, runner/regression tests and synthetic dependencies. [Hosted data-independent checks](docs/validation/hosted-ci.md) passed on Ubuntu 24.04 with Python 3.13.16. Raw-to-cleaned validation now passes locally; full report validation remains incomplete.

## Data preparation and quality

The verified raw-only run processed **2,774,313 raw rows → 2,709,426 cleaned rows**:

| Operator | 2024 raw → cleaned | 2025 raw → cleaned | Decision |
|---|---:|---:|---|
| Bird | 390,844 → 390,844 | 467,176 → 467,176 | Retain trips; mask nonpositive distance and speed >30 km/h; flag DST ambiguity and spatial errors |
| Lime | 1,196,210 → 1,196,200 | 428,318 → 428,318 | Exclude 10 zero-elapsed trips; retain rounded zeros and positive subminute trips; mask 100 km sentinel distance; adjust ±60-minute discrepancies |
| Voi | 130,769 → 106,115 | 160,996 → 120,773 | Collapse 64,877 duplicate excess rows after checking trip fields; flag reservation conflicts; retain damaged January timestamps with provider-duration fallback |

[Quality decisions and regenerated summaries](docs/data-quality.md) distinguish trip exclusion, measurement masking and overlapping warnings. Harmonization uses a **45-field common Arrow schema** with consistent types/units, operator-qualified identifiers, source-file/row lineage and analysis-specific validity. It preserves distance semantics and timestamp uncertainty; it does not scale features. A fresh run from the 40 original raw files reproduced **all six cleaned and eight harmonized Parquets byte-for-byte**, with all-column comparisons and unchanged originals: [execution, hashes and comparison evidence](docs/validation/cleaning-reproduction.md). Downstream analyses have **separate validation scopes**, linked below; this preparation result does not establish ground truth or a full raw-to-report run.

After installing [pinned dependencies](requirements-lock.txt) in Python 3.13, run the public demo from the repository root:

```sh
python scripts/demo_preparation.py
```

The [clearly labeled SYNTHETIC fixtures](examples/synthetic/README.md) are hand-authored examples for all three operators, with **no transformed or sampled real trip records**. This command runs the seven actual preparation scripts in a disposable workspace and checks expected identities, counts, masks, timestamps, lineage and schema (22 raw → 19 cleaned/harmonized rows). It requires no private inputs, GIS assets or network access and runs in CI.

**Access:** the owner-authorized [original scooter dataset release](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1) hosts [40 raw inputs in a tar.gz](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/download/scooter-inputs-2024-2025-v1/turin-scooter-inputs-2024-2025-v1.tar.gz) and [SHA-256 checksums](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/download/scooter-inputs-2024-2025-v1/SHA256SUMS). Follow the [download, checksum, extraction and raw-preflight instructions](docs/reproduction.md#download-original-scooter-inputs). Persistent vehicle/rental IDs and precise times/endpoints are retained; no dataset license or unrestricted reuse grant is asserted. Torino/GTT are excluded and [must be acquired separately](docs/data-distribution.md#excluded-external-inputs). The synthetic demo stays in Git; the original mixed staging package is preserved locally.

## Methods and tools

The Python workflow performs operator-specific cleaning, retains quality and provenance fields in a harmonized schema, compares coverage-aware temporal aggregates, assigns endpoints to statistical zones, and constructs OD tables. Spatial analysis uses projected geometries, nearest-stop distances, and ordered GTFS stop patterns. Parking and economic analyses include explicit filters and sensitivity scenarios.

The code uses pandas, NumPy, PyArrow, GeoPandas, Shapely, and Matplotlib; Excel input and Word appendix generation use openpyxl and python-docx. Local artifacts include Parquet datasets, CSV tables, GeoPackage layers, figures, and reports.

## Repository guide

| Location | Purpose |
|---|---|
| `src/cleaning/`, `src/harmonization/` | Operator preparation and common data schema |
| `src/analysis/`, `src/visualization/` | Five scooter analyses and associated figures |
| `config/exercise_5/` | Economic assumptions, tariffs, and source registers |
| Root-level `stage4_*.py` through `stage7_*.py` | Separate commuting-cost exercise |
| `data/`, `audit/`, `outputs/` | Local inputs and generated artifacts; excluded from Git |

See [Methodology](docs/methodology.md) for analytical definitions and [Data and reproduction](docs/data-and-reproduction.md) for input coverage, dependencies, and current blockers.

## Reproduced results

Five [figures with captions and supporting tables](docs/results/README.md) show the verified results. Each row uses its own period and denominator; unequal observation windows are not treated as full-year comparisons.

| Result | Reproduced value | Evidence |
|---|---|---|
| Temporal usage, Feb–Dec 2024 | Friday 18:00–18:59 peaks at 404.04 trips per Friday (19,394 / 48); population 1,617,965 trips | [Figure](docs/figures/temporal_usage_2024.png), [table](docs/results/temporal_hour_weekday_2024.csv) |
| Spatial OD, 2024 | 107 directional pairs carry 354,646 / 1,409,705 interzonal trips (25.16%) | [Figure](docs/figures/spatial_od_2024.png), [table](docs/results/od_displayed_core_2024.csv) |
| Direct PT compatibility, Feb/Jul 2024 | 7,231 / 82,396 (8.78%) and 15,568 / 186,194 (8.36%), at 100 m | [Figure](docs/figures/pt_compatibility_2024.png), [table](docs/results/pt_system_100m.csv) |
| Inactivity proxy, Feb–Dec 2024 | 1,458,827 accepted / 1,617,923 candidate intervals; pooled mean 9.29 h | [Figure](docs/figures/parking_proxy_2024.png), [table](docs/results/parking_event_summary_2024.csv) |
| Base economic scenario, 2024 | Profit proxies: Bird €628,484 / 390,844 trips; Lime €1,814,759 / 1,196,200; Voi −€65,871 / 106,115 | [Figure](docs/figures/economics_base_2024.png), [table](docs/results/economics_base_scenario_2024.csv) |

PT uses the **later 12 August 2026–31 January 2027 GTFS reference**, not verified historical service or observed transfers. Parking gaps and fleet exposure are proxies; the economic figures are tariff/cost scenarios, not audited profits. The [figure validation](docs/validation/figure-validation.md) records execution and visual-review scope. In the separate [validated commuting scenario](docs/validation/commuting-validation.md), bicycle has the lowest baseline generalized cost, €6.11 per round trip at €10/hour; Stage 4 costs agree with Stage 5's rounded manual inputs.

## Status and limitations

The original 69 analysis Python files passed in-memory syntax parsing with Python 3.13.13 after the PT-reference syntax repair. The tested environment on CPython 3.13.13, macOS 14.6 arm64 passed installation, `pip check`, and all nine synthetic smoke checks. Its PyProj pin is supported by the [controlled PT geometry diagnosis](docs/validation/pt-geometry-diagnosis.md). [Harmonization and Exercise 1](docs/validation/usage-reproduction.md) reproduced 98 artifacts; [Exercise 2](docs/validation/exercise-2-reproduction.md) reproduced 58. Further analytical reproduction passed: [Exercise 3](docs/validation/exercise-3-reproduction.md); [Exercise 4](docs/validation/exercise-4-reproduction.md); [Exercise 5](docs/validation/exercise-5-reproduction.md). The [figure showcase](docs/validation/figure-validation.md) and [separate commuting workflow](docs/validation/commuting-validation.md) have now been checked within their recorded scopes. The [raw-to-cleaned reproduction](docs/validation/cleaning-reproduction.md) now passes; full Word/PDF report production/reconciliation remains unverified. The validation reports identify legacy artifacts excluded from the executed sequences.

The GTFS feed covers August 2026–January 2027 and serves as a later spatial/topological reference for earlier scooter observations, not verified historical service. Proximity and route compatibility cannot establish actual transfers or substitution. Inter-trip gaps and fleet exposure are proxies; revenues, profitability, and commuting costs depend on assumptions. Unequal temporal coverage also limits direct comparisons between operators and years.
