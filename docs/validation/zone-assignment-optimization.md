# Zone-assignment batch optimization

The strict-interior storage loop in `src/analysis/exercise2_assign_zones.py` was replaced with three batch writes using the existing `analysis_row_id` lookup. Spatial joins, boundary/ambiguity rules, coordinate filtering, and the later status pass were unchanged.

## Implementation equivalence

Six focused regression cases in `tests/test_zone_assignment_batch.py` compare the actual assignment block with the original scalar-write oracle: empty, partial, and reordered matches for origin/destination, with nonconsecutive result indices. Exact frame assertions include values, index, dtypes, and nulls. Run with the tested environment's Python:

```sh
python -I -B tests/test_zone_assignment_batch.py
```

Real-data equivalence used 1,000 evenly spaced 2024 rows per operator plus the first ten missing values and ten smallest/largest values for each endpoint coordinate, deduplicated and sorted by original row index. Inputs were regenerated harmonized data and regenerated zoning from the isolated usage/Exercise 2 workspace. Both complete `assign_endpoint` functions were extracted via AST, together with `valid_coordinate_mask`, without importing project modules or triggering their top-level file operations. Both endpoints were compared with exact frame equality. All selected operators span all twelve source months. Timings are single measurements on CPython 3.13.13, macOS 14.6 arm64, not a general benchmark.

| Operator | Endpoint | Trips | Original seconds | Optimized seconds |
|---|---|---:|---:|---:|
| bird | origin | 1070 | 0.0926 | 0.0150 |
| bird | destination | 1070 | 0.0650 | 0.0136 |
| lime | origin | 1061 | 0.0648 | 0.0134 |
| lime | destination | 1061 | 0.0651 | 0.0136 |
| voi | origin | 1066 | 0.0653 | 0.0132 |
| voi | destination | 1066 | 0.0650 | 0.0132 |

All six real-subset endpoint comparisons passed. Selection IDs, source periods, observed status counts, and unrounded timings are retained in `/private/tmp/transport-exercises-xaw9_enm/subset-equivalence.json`; the comparison runner is `subset_equivalence.py` in that directory. These artifacts are temporary.

## Full-reference reproduction

The optimized full assignment finished with exit code 0 in **31.73 seconds**. The earlier unchanged run was stopped at the user's request after 462.45 seconds; it had not completed, so no full-run speedup ratio is claimed. The six synthetic and six real-subset checks establish implementation equivalence on their fixtures. Separately, reproduction comparison aligned all three full zoned Parquet datasets by unique `trip_uid`, checked complete Arrow schemas and every column, and compared four assignment audit CSVs. All seven artifacts matched existing references. Float tolerances were `rtol=1e-10`, `atol=1e-9`; non-floating values, dtypes, and nulls were checked exactly.

Assigned/unassigned accounting and valid-OD flags reconciled for all 1,693,159 input trips. Raw-to-cleaned processing was not rerun. Reference agreement establishes computational reproduction from the supplied cleaned data, not independent scientific correctness.
