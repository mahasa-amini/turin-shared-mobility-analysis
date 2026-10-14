# Exercise 2 reproduction

Status: **passed** on 2026-10-14, CPython 3.13.13, macOS 14.6 arm64, using the previously tested application environment. The source baseline was `f1e67fddccbf4d2ab2e04cb7480207fb6a108491`, with the isolated assignment optimization subsequently committed as `7002c09`. All six analytical scripts exited 0; all 58 emitted CSV/Parquet/GeoPackage artifacts matched existing references. Matching references establishes computational reproduction, not independent scientific correctness. Raw-to-cleaned processing was not rerun.

## Isolation and inputs

The isolated project was `/private/tmp/transport-usage-kpz9n9_x/project`. Regenerated harmonized inputs came from the successful [usage run](usage-reproduction.md); raw zoning sidecars were copied from the original project. No Exercise 2 expected outputs were seeded. All writable destinations were real directories in the isolated copy. Figures, map rendering, and Word/appendix production were deferred.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `data/raw/external/torino_zones/zone_statistiche_geo.dbf` | 10062 | `92e775b381914290b7c95ead99fdd363e146c34e5c2c50fb2b2ec410512e2dbc` |
| `data/raw/external/torino_zones/zone_statistiche_geo.shx` | 852 | `4cc97be0cba5d1c2d1fb9ca627233898475977ea26408ff11a9a390038be3d55` |
| `data/raw/external/torino_zones/zone_statistiche_geo.shp` | 314152 | `976b6bb057d3eaa9cfc306f02530d4fbf22a702ccba7c1584c8ba95d6d1ab3c4` |
| `data/raw/external/torino_zones/zone_statistiche_geo.prj` | 430 | `b860cf0cfdb0047b3afd7965ced7cf74493ed41a4e11cb4ab889765df0b98404` |
| `data/processed/harmonized/bird_2024_harmonized.parquet` | 32633111 | `760acfb0c2042b1bd1d24ed0cd8d44d44a142331a975da59ccc128e390935b32` |
| `data/processed/harmonized/lime_2024_harmonized.parquet` | 73796645 | `a496e78a851876e85e0ba0396ca1228310db158d670b2904f51eb367f6ce3628` |
| `data/processed/harmonized/voi_2024_harmonized.parquet` | 20640572 | `e041745ebb919c706f5b1307666422be97d2a242038fa89f4469f179d7f54d12` |

## Execution

Every script below ran as `<tested-python> -I -B [-u] <isolated-project>/<script>` with the isolated project as working directory. The zoning audit completed before the interruption and was not repeated. The initial assignment was stopped at the user's request, then rerun after equivalence testing of the batch-write optimization. The successful optimized assignment took 31.73 seconds. [Optimization evidence](zone-assignment-optimization.md) separates old/new subset equivalence from full-reference reproduction.

| Script | Exit | Artifact comparisons | Execution seconds |
|---|---:|---:|---:|
| `src/analysis/exercise2_zoning_audit.py` | 0 | 3 | 0.45 |
| `src/analysis/exercise2_assign_zones.py` | 0 | 7 | 31.73 |
| `src/analysis/exercise2_build_od.py` | 0 | 22 | 0.93 |
| `src/analysis/exercise2_temporal_od.py` | 0 | 17 | 2.81 |
| `src/analysis/exercise2_temporal_flow_contrasts.py` | 0 | 6 | 0.37 |
| `src/analysis/exercise2_prepare_gis.py` | 0 | 3 | 0.95 |

Destinations were `data/processed/exercise_2/`, `audit/exercise_2/`, and `outputs/tables/exercise_2/` within the copy. Exact commands, exits, selected keys, row/column counts, layer results, and invariant values are in `/private/tmp/transport-exercises-xaw9_enm/exercise-2-results.json`. Numbered logs, copied-input manifest, environment metadata, and comparison runner are alongside it. These temporary logs/datasets are outside Git.

## Comparisons and invariants

Parquet schemas were checked excluding serialization metadata; trip tables were aligned by unique `trip_uid` and every column compared, including all assignment flags/statuses. CSV and other tables were aligned by available identifying keys, falling back to complete non-floating row tuples with multiplicity retained. Values, nulls, and dtypes were compared; non-floating values were exact and floating values used `rtol=1e-10`, `atol=1e-9` to allow roundoff only. GeoPackages matched layer sets, CRS, attributes, and geometry, using topological equality or coordinate equality within `1e-7` projected metres. No binary dataset hashes were used as result comparisons.

Additional independent accounting checks confirmed unique trip IDs and complete preservation of the harmonized trip-key set, endpoint assigned/unassigned totals, assigned flags equal to non-null zone IDs, and valid OD equal to both endpoints assigned.

| Operator | Input trips | Valid OD | Invalid OD |
|---|---:|---:|---:|
| Bird | 390,844 | 382,533 | 8,311 |
| Lime | 1,196,200 | 1,193,572 | 2,628 |
| Voi | 106,115 | 105,822 | 293 |

The system OD table had 6,154 unique origin/destination pairs and 1,681,927 trips. Its per-operator sums matched valid zoned-trip counts, and every system cell equaled its operator components. These expectations were derived from generated assignment flags rather than merely accepting hard-coded counts. Script-level temporal-window and GIS consistency assertions also passed.

## Exclusions and limits

No additional historical CSV/Parquet/GeoPackage artifacts in the Exercise 2 data/audit/table directories were omitted.

Maps, figures, Word reports, and report appendix artifacts were excluded. Temporal OD retains the February–December detailed-time population, while all-day OD uses the full 2024 zoned population; these totals should not be conflated. Upstream cleaning, observation completeness, and scientific interpretation remain outside this reproduction test. Original data/audit/output preservation was checked against the pre-run inventory.
