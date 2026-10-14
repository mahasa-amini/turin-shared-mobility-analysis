# Separate commuting exercise validation

Validated 2026-10-14 in `/private/tmp/transport-showcase/commuting`, using `/private/tmp/transport-showcase-env/bin/python` and the corrected [pinned environment](../../requirements-lock.txt). This is an independent scenario exercise, not part of the scooter pipeline. Source files were copied; no existing output tables or figures were seeded. No calculations changed.

## Stage 4 → Stage 5 gate

Both Stage 4 scripts ran via `runpy.run_path` before Stage 5 was executed. Their console outputs were captured and their full-precision daily round-trip values compared with Stage 5 literals extracted with `ast` (without executing Stage 5). All three agree after rounding to the precision of the embedded literal:

| Cost (EUR per round trip) | Stage 4 | Stage 5 literal | Decimal places |
|---|---:|---:|---:|
| Private car, including 9 h parking | 19.175920705892466 | 19.18 | 2 |
| Private bicycle | 0.7749916666666666 | 0.775 | 3 |
| Private e-scooter | 1.66304345 | 1.663 | 3 |

Evidence: [handoff values](commuting-evidence/commuting-handoff.json), [comparison code](commuting-evidence/check_handoff.py), [car log](commuting-evidence/stage4_private_car.log), [active-mode log](commuting-evidence/stage4_private_active_modes.log). **Manual handoff limitation:** Stage 5 does not import Stage 4 outputs; subsequent assumption edits can silently make its rounded literals stale. Passing this gate establishes consistency only for the recorded source versions.

## Execution and checks

Stages 5, 6 and 7 each exited 0 with `python -I -B -u <absolute-script>` and the commuting copy as working directory. Stage 7 was rerun after the layout-only fix `ef3317a`, which adds room for the longest cost label and the rightmost PT annotation. [Exact commands and exit codes](commuting-evidence/commuting-execution.json), [Stage 7 rerun log](commuting-evidence/stage7-rerun.log), and [source hashes](commuting-evidence/source-hashes.json) identify coverage.

The [independent checker](commuting-evidence/validate_commuting.py) and [results](commuting-evidence/commuting-checks.json) cover:

- Stage 5: nine unique modes, nonnegative numeric values, round-trip time components, EUR 10/hour valuation, monetary-plus-time accounting, ranks and baseline/master agreement; all 27 mode/VOT combinations at EUR 5/10/20 per hour and their ranks.
- Stage 6: travel/access/wait weights 1/1.5/2, weighted costs and ranks; an independent 9 × 9 pairwise dominance matrix; allocated-pass versus zero-marginal-cost PT scenarios. Numeric comparisons use `rtol=1e-10`, `atol=1e-9`.
- Stage 7: all three PNGs decode; decomposition, VOT sensitivity and Pareto figures were visually inspected for labels, units, legends, captions and plotted values. The two border-crossing labels were corrected and both figures reinspected. The sensitivity legend remains readable; near-coincident lines are resolved by the supporting table. PNG dimensions/hashes are recorded. Images remain in the isolated run; this exercise's six compact CSV outputs are [preserved separately](../results/commuting/).

For this 7.8 km daily round-trip scenario, private bicycle has the lowest baseline generalized cost: **EUR 6.108333 (EUR 6.11 displayed)** at EUR 10/hour, including EUR 0.775 monetary cost and 32 minutes. Private bicycle and private e-scooter are the two Pareto-efficient modes. The baseline uses annual ownership/subscription allocation over 150 university days; these are modeled costs, not measured population outcomes. [Baseline evidence](../results/commuting/stage5_baseline_generalised_cost.csv), [Pareto evidence](../results/commuting/stage6_pareto_efficiency.csv).

## Exclusions and release limits

No upstream route/tariff/insurance/legal-source verification, real-world travel-time validation, historical quote verification, full report reconciliation or Word/PDF report validation was performed. Stage 4 cost arithmetic was executed and checked at the handoff, not independently rederived component by component. Stage 7 contains no weighted-GC chart; no such output is claimed. Outputs were checked by arithmetic and visual inspection, not by pixel identity with historical images. The manual Stage 4→5 handoff remains a reproducibility limitation. Raw-to-cleaned scooter processing is outside this exercise and was not validated.
