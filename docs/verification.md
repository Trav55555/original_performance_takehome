# Verification and tool guide

[Home and setup](../README.md#build-and-run) · [Architecture](architecture.md) · [Full history](performance-progression.md) · [Technique wiki](reference/README.md)

This guide describes the published `2c4705b` verification baseline, not unverified working-tree experiments. Run commands from the repository root, in the environment installed from `requirements.txt`, with Python assertions enabled. That release must execute in at most **979 cycles** and use at most **1536 scratch words**. The promoted result uses 1463 words.

## Choose the check before starting a build

| Command | What it checks | Default benchmark discovery |
|---|---|---|
| `git diff --exit-code 5452f74 -- tests/ problem.py` | Test/simulator integrity against the frozen upstream checkpoint | None |
| `python scripts/verify_justify.py` | Small executable scheduling examples, missing dependencies, budget and reservation failures | None |
| `python tests/submission_tests.py` | The nine unchanged official correctness/speed tests | One cold build in a fresh process |
| `python scripts/verify_retry.py --max-cycles 979` | 100 generated inputs, five patterns, nine other shapes, three other-shape ceilings, pause/store hazards and a corruption control | One cold build, plus fallback cases |
| `python scripts/verify_optimizer.py` | Retiming round trips, fresh allocation, dependency/lane mutations, scratch rejection, budget guards and slower controls | One cold build, plus control construction |
| `python scripts/verify_compiler.py` | Public builder, 100 full-width inputs, independent lane checks, fallbacks, historical controls, cache isolation and source-only reproduction | One local cold build plus two isolated cold rebuilds |

The submission suite's historical speed thresholds are looser than 979. Passing it alone is not a current performance promotion gate. `verify_retry.py` also retains a standalone default of 980; pass `--max-cycles 979` explicitly.

Cold discovery took about 16 minutes per process on the verification host. The compiler verifier needs three such discoveries when started cold, plus its other checks. These are planning estimates from recorded measurements, not portable runtime guarantees. Other verifiers also spend time constructing controls.

Every command starts a separate Python process and therefore a separate compiler cache. Running all commands in succession repeats discovery. The inexpensive scheduling check does not replace the full-kernel gates.

## Match verification to the change

For documentation-only edits, check relative links, fragment targets, source citations and whitespace. Confirm production files and frozen sources are unchanged. Do not spend an hour recompiling an unchanged kernel just to validate prose.

For scheduler changes, start with the small scheduling controls, then exercise real graph reconstruction, fresh allocation and frozen execution. For compiler changes intended for promotion, use the public builder and source-only checks as well as the official and supplementary suites. Report exactly which commands ran.

A saved timing replay can validate that selected program. It cannot demonstrate automatic discovery. Likewise, same-process reconstruction is not a cold source-only build.

## What the published evidence covers

The [979 promotion report](../experiments/promotion_979_results.md), [receipt](../experiments/promotion_979_receipt.json) and [evidence directory](../experiments/promotion_979_evidence/) preserve the completed campaign. It included the public builder, two isolated builds at hash seeds 0 and 17, failure-sensitive controls and checks of source hashes between stages.

That campaign's combined driver took 2941.31 seconds. It reused a warm in-process compilation between some checks. Running the standalone commands above separately is not the same timed procedure. The original combined driver remains a temporary-workspace artifact; the maintained standalone verifiers reproduce the compiler checks without that driver.

The compiler verifier's `cold_seconds` field measures the build call in that process. In the combined promotion driver it was a warm call. Use `public_build.json` for the recorded genuinely cold public build.

The supported contract is root-starting traversal and final values, with non-output memory preserved. Neither these checks nor the reports establish general non-root/final-index equivalence or global optimality. An attempted independent subagent review failed before work; the execution evidence is not a claim of independent code review.

## Research and diagnostic scripts

Only the named verifiers above are listed here as current verification entry points. The other scripts are retained tools, not a supported run-all test suite.

| Files | Role and caution |
|---|---|
| `scripts/analyze_*.py`, `profiler.py`, `bottleneck_detector.py`, `visualize_schedule.py`, `value_reuse_profiler.py` | Historical analysis tools. Inspect their imports, shape assumptions and build calls before use; some construct a kernel. |
| `scripts/breakthrough_experiments.py`, `scheduler_experiments.py`, `experiment_batching.py`, `validate_speculative.py` | Historical experimental drivers, not permission to start another search or evidence of current compatibility. |
| `experiments/baseline.py`, `batch_sweep.py`, `medium_tree_opt.py` | Early prototypes. See the [experiment index](../experiments/README.md#historical-prototypes-and-guides) for their original status. |
| [`experiments/archive/`](../experiments/archive/README.md) | Historical root-level prototypes and sweep output, relocated without repairing or rerunning their algorithms. Not production entry points. |
| [`tools/trace/`](../tools/trace/README.md) | Trace viewer and HTML asset. Run `python tools/trace/watch_trace.py` from the root to view an existing `trace.json`. Debug behavior must not change the measured kernel or oracle. |

No historical driver was rerun to prepare this guide. Old `/tmp` commands may depend on missing artifacts or source hashes from a different compiler version. Do not adjust old receipts to make those guards pass. New searches need a new scope and budget.
