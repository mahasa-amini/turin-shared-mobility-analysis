# Publication readiness review

Review date: 2026-10-14. The maintained entry point is [scripts/run_pipeline.py](../../scripts/run_pipeline.py); installation, input placement, stage selection and test commands are in the [reproduction guide](../reproduction.md). This is a source/results release with separately supplied full-data inputs. Raw-to-cleaned processing and full report reconciliation remain incomplete.

## Runner and local check coverage

The runner follows the previously validated 33-script scooter order and 18-script figure order. Commuting is a separate Stage 4–7 workflow with a cost-handoff gate before Stage 5. Selection is explicit, upstream stages are never added automatically, dry runs do not execute children, and subprocesses use the active interpreter. Byte-size preflight is standard; supplied-input SHA-256 verification is opt-in. Complete upstream output contracts are presence/nonempty checks, not scientific or freshness checks.

Ten new runner/handoff tests plus the six existing zone-assignment regression tests passed locally. They cover stage ordering/workflow separation, missing/size/hash input checks, deferred and omitted dependencies, dry-run nonmutation, subprocess interpreter/cwd/logs, stop-on-failure, missing produced outputs, stage-boundary rechecks, validated-order equivalence and mismatched manual costs. All nine synthetic environment checks passed in the recorded Python 3.13 environment. The pinned installation command completed with packages already satisfied in the previously installed environment, and `pip check` passed locally. Full analyses and figures were not rerun for this release-preparation work.

A source-only copy with no `data/`, `audit/` or `outputs/` passed syntax/link checks and all 16 tests. Stage lists and commuting dry-run returned 0; scooter preflight and figure dry-run returned the expected exit 2 for missing data, without creating outputs. Absolute-path invocation from an unrelated directory also passed. [Clean-checkout evidence](publication-evidence/clean-checkout-checks.json), [local command results](publication-evidence/local-checks.json).

The [GitHub Actions workflow](../../.github/workflows/checks.yml) installs Python 3.13 and the pinned dependencies on Ubuntu 24.04, checks syntax/local links, runs all 16 tests and nine synthetic environment checks, and inspects the runner without research data. **Hosted CI is pending until it actually runs**; local macOS success is not Ubuntu execution evidence.

## Input and release boundary

The [input manifest](../../config/input_manifest.csv) records 27 required paths: six cleaned Parquets, three cleaning-audit CSVs, four shapefile components, ten extracted GTFS tables, and four tracked configuration CSVs. It includes purposes, byte sizes, SHA-256 and known provenance, with acquisition dates, licenses and download locations explicitly unestablished. [Stage output contracts](../../config/pipeline.json) separately identify reproducible intermediates; bulk inputs and generated local outputs remain ignored.

All 18 reachable commits and 200 reachable blobs at the start of this change were reviewed for sensitive paths and scanned for private-key headers, common service-token formats and credential assignments. No matching secrets or unintended bulk-data/credential paths were found. Current release files were also checked. [Recorded review scope and findings](publication-evidence/release-review.json). This is a bounded pattern/path review, not a guarantee against every possible secret encoding. The largest tracked artifact is the intended PT showcase PNG (2,027,474 bytes); there are no oversized archives or bulk trip datasets in reachable history. Curated aggregate tables and figure/commuting evidence are intentional release artifacts.

Historical validation helpers contain local absolute paths/usernames, and Git author metadata includes a personal name/email. These are retained as existing provenance; the maintained reproduction commands do not use those historical paths. No history rewrite was performed. No repository code license has been selected; dataset distribution/licensing also remains unresolved. Choose appropriate licenses before promising reuse rights.

The final release tree contains 176 files totaling 5,913,152 bytes (5.64 MiB), measured as the sum of file contents; this excludes ignored local data, virtual environments and `.git` storage.

The empty GTFS downloader placeholder was removed. No downloader is implemented, and supplied extracted files are required. Stale claims about figure execution and checksums were updated. Local Markdown targets and diff whitespace are checked by the maintained repository checker and Git.

## Material limitations and verdict

- Full-data execution requires separately supplied cleaned records, cleaning summaries and external references; no public distribution arrangement or established input licenses are provided.
- Raw-to-cleaned validation, complete report validation and visual approval of every unselected figure remain incomplete. Later GTFS topology does not verify historical 2024 service.
- The parking map's validated path uses canonical full-period summaries. The legacy candidate fallback remains incompatible with the current candidate schema; the runner requires the canonical upstream files.
- The commuting Stage 4→5 handoff remains manual. Its new gate detects inconsistency at the embedded rounding precision and stops before changing calculations; it does not propagate updated costs automatically.
- Preflight cannot detect stale or scientifically invalid intermediate content. Hosted Ubuntu CI and broader platform support remain pending.

**Verdict:** ready for a transparent source/results publication with local checks passed, with the above data-access, licensing and validation limitations stated. It is not a verified end-to-end data/report release. Nothing has been pushed.
