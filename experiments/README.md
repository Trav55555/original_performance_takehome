# Experiments and evidence

[Home](../README.md) · [Full performance history](../docs/performance-progression.md) · [Technique wiki](../docs/reference/README.md) · [Verification commands](../docs/verification.md)

## Current production

The normal builder discovers **979 cycles / 1463 scratch words**, with zero solver queries. The implementation was published in commit [`2c4705b`](https://github.com/Trav55555/original_performance_takehome/commit/2c4705b73038b723b1021ff65943d54b5d1fe842).

- [Promotion report](promotion_979_results.md): result, discovery method and verification scope.
- [Receipt](promotion_979_receipt.json): source hashes, program digest and measurements.
- [Detailed evidence](promotion_979_evidence/): build records, test outputs, guard checks and the original protocol.

The compiler does not read this directory during default discovery. Research results, experimental controls and production inputs are different things.

## How to read historical status

Reports describe their run-closure state. Phrases such as "production remains 980", "not integrated" and "no commit or push" may precede a later promotion. The 979 receipt's local-promotion scope is historical; publication followed in `2c4705b`. Do not rewrite immutable receipts to reflect later events.

A result table may contain executed candidates, scratch-rejected timings, lower bounds or solver outcomes. Read the verification section before comparing numbers. An experimental 980/1449 program is smaller than production 980/1465, but those are different programs with different discovery evidence. OOM and timeout mean unknown, not infeasible.

All research budgets described by this index are closed. Old proposed next steps are historical recommendations, not an active queue or permission to restart a driver.

## Production promotion records

The [milestone ledger](../docs/performance-progression.md#milestone-ledger) is the chronological source of truth, including the original scalar baseline and January work. These reports document the later source-only compiler promotions.

| Published commit | Cycles / scratch words | Report | Later superseded by |
|---|---:|---|---|
| `0bef02a` | 1076 / 1236 | [Rebuilt compiler](rebuilt_promotion_results.md) | 1052 promotion |
| `0accd81` | 1052 / 1457 | [Technique integration](technique_promotion_results.md) | 1041 promotion |
| `5691617` | 1041 / 1458 | [Startup-policy integration](startup_promotion_results.md) | 980 promotion |
| `168e0f2` | 980 / 1465 | [Exact suffix-repair compiler](promotion_980_results.md), [receipt](promotion_980_receipt.json), [evidence](promotion_980_evidence/) | 979 promotion |
| `2c4705b` | 979 / 1463 | [Solver-free compiler](promotion_979_results.md) | Current |

## Completed research by phase

These are records of tests performed, not guarantees that an old script still runs against today's source.

| Phase | Records | Outcome and later connection |
|---|---|---|
| Representation and scheduling retry | [Retry](retry_results.md), [lookahead packing](lookahead_packing_results.md), [scheduling bounds](scheduling_bounds_results.md) | 1303 through 1113; representation, load urgency and pause/store packing |
| Selection-only virtual registers | [Prototype](virtual_register_results.md) | Tied 1117; did not justify promotion. Later full SSA rebuild tested a broader change. |
| Predicate reuse and caches | [Cross-domain work](cross_domain_results.md), [domain sweep](domain_sweep_results.md), [Algorithmica instruction selection](algorithmica_results.md) | Retained 1088, then 1084 and 1082 |
| Full SSA rebuild and constants | [Algorithmica follow-up](algorithmica_followup_results.md), [cache/regional follow-up](research_followup_results.md) | Experimental 1076; pointer regeneration saved some scratch but no cycles. Automatic promotion later reached 1076/1236. |
| Engine choice and addressing | [Four frontiers](four_frontiers_results.md) | Experimental 1074; precursor to the technique ports |
| External implementation audit | [1063-cycle fork audit](github_1063_audit.md) | Benchmark reproduced; general-shape and fail-open defects found. Useful techniques were reimplemented rather than adopting the generator. |
| Fusion and lookup representation | [Technique ports](technique_port_results.md) | Combination and cache reselection reached 1052, then promoted |
| Startup gather stream | [Load-gap experiments](load_gap_results.md) | Experimental 1042; automatic reselection promoted 1041 |
| Cache neighborhoods | [First neighborhood](cache_neighborhood_results.md), [continued descent](cache_descent_results.md) | Experimental 1037 then 993; later plateau/selector work appears in the [published discovery trace](promotion_980_evidence/progress.jsonl) |
| Resource-order scheduling | [Protocol](resource_order_program.md), [results](resource_order_results.md), [receipt](resource_order_receipt.json), [scheduler](resource_order_scheduler.py) | Solver-free 980 tie. Deadline variants exceeded scratch. Later combined with final-hash rewriting in the 979 promotion. |

For algebraic models, neural scheduling, larger exact searches and the final-hash pilot, see the wiki's [research catalog](../docs/reference/search-and-research.md). It distinguishes published sources from local-only records.

## Historical prototypes and guides

The directory originally indexed only three January prototypes. Their descriptions below are archival, not current recommendations:

| File | Original role/status |
|---|---|
| [`baseline.py`](baseline.py) | Early snapshot described as about 3053 cycles, not the current builder and not the original 147734-cycle scalar baseline |
| [`batch_sweep.py`](batch_sweep.py) | Batch-size experiments around the early manually scheduled implementation |
| [`medium_tree_opt.py`](medium_tree_opt.py) | Early arithmetic lookup prototype, documented as failing correctness; its predicted speedup was not a measured valid result |

Former root-level notes now live in [docs/history](../docs/history/README.md): [implementation log](../docs/history/implementation_guide.md), [algorithmic proposals](../docs/history/algorithmic_optimizations.md), [expert analysis](../docs/history/expert_analysis.md), [initialization guide](../docs/history/init_optimization_guide.md) and [vectorization research](../docs/history/vector_research.md). Their historical banners point to maintained guidance. Old root-level prototypes and sweep output are in [experiments/archive](archive/README.md); their contents were preserved rather than repaired or rerun.

## Artifact availability

The [preserved campaign collection](archive/campaigns/README.md) now includes final-hash ordering, mathematical models, model combinations and slope/select. It preserves 336 archive members plus 12 raw record copies. Saved F08 replay is verified; complete historical search reexecution is not. The index documents exact contents, exclusions and verification commands.

The promotion source and maintained verifiers reproduce production without `/tmp` research workspaces. Other reports may preserve only decisions and provenance while referring to temporary drivers, graphs or timing files. A receipt is not necessarily a complete executable archive.

At the documentation review on 2026-09-15, the local checkout also contained 58 untracked research files under this directory. They were left untouched and are not part of a fresh clone. To inspect local availability without starting an experiment:

```sh
git ls-files experiments/
git ls-files --others --exclude-standard experiments/
```

The selected campaign collection copies a subset of those records without changing or removing the originals. Remaining records still require a separate selection and provenance check. Do not bulk-add them, hide them with a broad ignore rule, or delete them as part of navigation cleanup.
