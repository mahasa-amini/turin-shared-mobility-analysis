# SYNTHETIC preparation demo

All seven CSV fixtures here were hand-authored using invented identifiers, simple coordinates and chosen timestamps. **No real trip record was read, transformed, sampled or used as a template for a fixture row.** Similarity to a location or timestamp is incidental. These examples demonstrate implementation behavior, not operator statistics or validated real-world trips.

From the repository root, with Python 3.13 and `requirements-lock.txt` installed:

```sh
python scripts/demo_preparation.py
```

The command copies only the seven production preparation scripts and these fixtures into a new temporary directory. It converts the Voi CSVs to native Excel input format (preserving strings), gives the inputs the filenames expected by the existing loaders, and runs Bird cleaning/finalization, Lime audit/finalization, Voi audit/finalization and common harmonization. It leaves production code and default full-data behavior unchanged; all production quality assertions remain enabled. Temporary raw/interim/cleaned/audit/harmonized files are removed on success or failure. A failing script prints its captured log and exits nonzero. No real input, reference output, staged package, GIS data or network is used.

[Expected outputs](expected.json) are independent hand-written assertions about retained case identities, cleaned and harmonized values/nulls, flags and timestamps. The command also checks raw/cleaned counts, lineage availability, pooled trip uniqueness, the canonical 45-field Arrow schema and exact equality between pooled outputs and concatenated operator outputs. The production scripts add their own validation/readback checks. A missing case, changed mask/time/flag or schema mismatch fails the demo.

| Fixtures | Representative cases | Raw → cleaned |
|---|---|---:|
| `bird_2024.csv`, `bird_2025.csv` | Possible spring DST discrepancy; nonpositive distance masked; reported speed >30 km/h masked; zero displacement retained; spatial error flagged; ordinary trip | 5 → 5 |
| `lime_2024-03.csv`, `lime_2024-10.csv`, `lime_2025-07.csv` | Spring/autumn ±60-minute duration adjustment; 100 km sentinel masked; rounded-zero distance retained; positive 15-second rounded-zero duration retained; zero elapsed and missing essential coordinate excluded; spatial-only invalidity; invalid battery; ordinary trip | 9 → 7 |
| `voi_2024-01.csv`, `voi_2025-07.csv` | Damaged day-zero timestamp with provider fallback; compact timestamp `.0` normalization; decimal commas; UTC→Rome conversion; duplicate collapse with unresolved reservation conflict; zero displacement retained; invalid duration retained; missing/outlying coordinate masks distance; invalid battery | 8 → 7 |
| **Total** | Six cleaned and eight harmonized Parquets, including two pooled years | **22 → 19** |

Trip-defining duplicate conflicts intentionally raise rather than produce an output; the existing [cleaning regression tests](../../tests/test_cleaning_rules.py) cover that rejection and additional edge cases. The [local validation record](../../docs/validation/synthetic-preparation.md) records the successful demo and checks. The [CI workflow](../../.github/workflows/checks.yml) runs this standalone demo and the regression suite. Neither establishes full-data accuracy or downstream analytical reproduction: see [real raw-to-harmonized evidence](../../docs/validation/cleaning-reproduction.md) and the separately scoped validation links in the [project README](../../README.md).

This synthetic demo is available in Git. Owner-authorized original scooter inputs are separately available as [GitHub Release assets](https://github.com/mahasa-amini/turin-shared-mobility-analysis/releases/tag/scooter-inputs-2024-2025-v1); Torino/GTT are excluded. See [download and extraction instructions](../../docs/reproduction.md#download-original-scooter-inputs). The synthetic demo never reads those real inputs.
