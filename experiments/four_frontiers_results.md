# Four frontier experiments

## Decision at experiment close

This historical report precedes the [1,052-cycle promotion](technique_promotion_results.md).

Keep a verified **1,074-cycle, 1,240-word prototype** as the next integration candidate. It combines bounded engine lookahead with one address rewrite and retains the promoted cache plan. Production remained at 1,076 cycles and 1,236 words in commit `0bef02a` during this experiment.

The earlier [cache and joint-scheduling follow-up](research_followup_results.md) used a different 1,076-cycle program. This experiment starts from the [promoted compiler](rebuilt_promotion_results.md), whose automatic selector produced twelve cache sites. Its instruction digest reproduced exactly before screening.

No production code, frozen tests, or simulator files changed during this exploration. The earlier promotion commit and push were completed before it started. This prototype was not promoted, committed, pushed, or externally submitted during the experiment.

## Results

| Arm | Configurations | Scratch-feasible and smoke-passed | Best actual change, cycles / words | Decision |
|---|---:|---:|---:|---|
| Control | Included in each arm | Passed | 1,076 / 1,236 | Preserve |
| Cache reselection | 512 unique cache sets | 495 | 1,075 / 1,244 | Keep as an independent improvement |
| Engine lookahead | 21 | 21 | 1,075 / 1,256 | Keep |
| Traversal ordering | 24 | 12 | 1,122 / 1,234 | Reject tested alternatives |
| Joint-output rewrites | 165 | 165 | 1,075 / 1,242 | Keep address form |
| Combinations | 12 | 12 | 1,074 / 1,240 | Advance to integration review |

These are 734 screen rows, not 734 distinct instruction streams. Controls and some ordering aliases repeat. All 705 scratch-feasible rows passed a full-width frozen execution using seed 461. The other 29 exceeded 1,536 words and were not executed. There were no compilation exceptions, timeouts, or smoke correctness failures.

## Cache reselection

Freeze the promoted scheduler, constant policy, and traversal order. Consider each block's depth-4 visits at rounds 4 and 15, plus its depth-5 visit at round 5. Charge the full additional table setup when depth 5 is admitted.

The bounded search evaluated the control, 96 single toggles, 256 ranked swaps, 94 new neighbors of the best set, and 65 new mutations. It took 26.00 seconds with four workers while the separate lookahead screen also ran. Seventeen sets exceeded scratch. The fastest rejected schedule was 1,085 cycles and required 1,585 words, so it was not a hidden faster executable result.

The best feasible swap removes `(6, 15)` and adds `(8, 15)`. It reaches 1,075 cycles with 1,244 words. Several other swaps tie its cycle count. This revises the earlier negative result for the old prototype; it does not contradict that experiment's measurements.

The lowest-scratch 1,074 combination does not use a cache swap. Some combinations with swapped sites also reach 1,074, but need more scratch.

## Engine lookahead

The scheduler considers alternatives only when both engines are legal and have slots. Already-partially-issued operations keep their engine. Each forecast copies readiness, progress, engine choices, outstanding uses, and completion state. It packs a bounded part of the current cycle and one or two future cycles using the existing greedy policy.

The winning policy uses one future cycle, an eight-operation forecast width, all eligible binary/constant operations, and at most one decision per cycle. It first prefers discounted gather-lane progress, then critical-path and near-load progress. Ties retain the original choice. The forecast is truncated and heuristic, not an exact scheduling oracle.

Zero-horizon lookahead reproduced the control's instructions exactly. The independent winner made 1,062 decisions and changed 199 immediate choices. It emitted 1,075 cycles. A constants-only probe advanced the first gather from cycle 76 to 75 but still took 1,076 cycles, a useful warning against optimizing startup alone.

The combined winner made 1,058 decisions, evaluated 2,116 forecasts, and changed 183 immediate choices. Later greedy decisions can also change as readiness and pressure diverge.

## Traversal ordering

The screen compared block-major, round-major, tiles of 2, 4, 8, and 12 rounds, and staggered orders. Staggering sorts visits by `round + lag * floor(block / width)`, then block and round. Widths were 1, 2, 4, 8, 16, and 32, with lags 1, 2, and 4.

All 32 logical walker contexts remain present. No context cap or new serialization barrier was introduced. Each order preserves every walker's ascending round sequence and the semantic operation multiset before scheduling.

Block-major ran in 1,146 cycles with 1,233 words. Round-major produced a 1,544-cycle schedule requiring 1,737 words and was not executable. The best non-control order staggered individual blocks with lag 2 and ran in 1,122 cycles with 1,234 words. These results reject the tested orders under the fixed scheduler and cache plan, not all possible traversal scheduling.

## Joint hash/index/address outputs

Four proposed forms were checked with Z3 over wrapping 32-bit values. This was a proof-checked search over hand-derived forms, not unrestricted synthesis. The solver checked the full encoded value, normalized branch bit, next index, and next address together.

At the last affine hash stage, let:

```text
T = 9*X + 0xFD7046C5
S = T >> 16                 # logical shift
V = T XOR S
b = V AND 1
q_next = 2*q + b
address = D - q_next
```

The tested alternatives were:

- Split the index update into `(q << 1) OR b`.
- Split it into `(q << 1) XOR b`.
- Compute branch parity as `((X XOR 1) XOR S) AND 1`, retaining the full `V` output.
- Precompute `base = -2*q + D`, then obtain the address as `base - b`, retaining the original index update.

All four equivalence queries returned UNSAT. A deliberately wrong parity expression returned SAT with `X = 0` as a counterexample. These are expression proofs, not proofs of the scheduler or allocator.

The screen tested whole-program, per-round, per-block, and single-site applications. The best actual split-index and early-parity changes tied 1,076. The address form reached 1,075 when applied at block 0, round 3, to prepare the following round's gather. This is a benchmark-tuned positional choice, not a demonstrated general placement rule. The extra multiply-add, constant construction, broadcast, and lifetimes are charged.

The shorter address dependency did not advance that walker's measured gather. Its lanes moved from cycles 76 through 79 to cycles 82 through 85. The first gather across all walkers stayed at cycle 76; the last moved from 1,063 to 1,062, then to 1,061 in the combination. The full schedule improved, but these measurements do not isolate arithmetic latency savings from changed priorities, engine choices, and packing.

## Winner and verification

The winner uses the promoted cache sites, default tile-12 order, one-cycle/eight-operation engine lookahead, and the address rewrite at `(0, 3)`. Its instruction counts are:

| Engine | Instructions | Capacity-only cycle bound |
|---|---:|---:|
| Load | 2,018 | 1,009 |
| Flow | 914 | 914 |
| VALU | 6,283 | 1,048 |
| ALU | 12,519 | 1,044 |
| Store | 32 | 16 |

The 1,048 bound belongs only to this instruction stream. It does not establish an attainable schedule or challenge-wide optimum.

Five finalists, one per arm including the combination and the losing traversal alternative, each passed 100 full-width inputs, five patterns, lane-identity checks, and three deterministic compiles. Dependency, constant, and selector corruptions were rejected for each finalist.

The three independent 1,075 winners and the combined 1,074 winner also passed all nine unchanged frozen tests through an experimental adapter. Each passed the supplementary verifier at its own cycle ceiling, including 100 generated inputs, five patterns, nine other shapes, three shape-specific performance gates, pause/store checks, and corruption rejection. Other shapes use the unchanged legacy generator. They do not establish generality of the new benchmark-only passes. Supplementary scheduler-unit checks cover the legacy scheduler; separate lane-identity checks cover the experimental one.

The real supplementary 1,074 gate rejected the executed 1,076 control exactly as `((1076, 1074),)`.

Selected-program compilation took 0.411 seconds in the screen and 0.485 and 0.487 seconds in repeat checks. These timings exclude automatic cache selection. They are not cold production-build measurements and do not establish an end-to-end compilation-speed improvement.

## Artifacts and next step

The complete local experiment is under `/tmp/perf-four-frontiers.Tfb8Ko/`:

- `program.md`, `baseline.json`, copied `kernel_compiler.py`, and `ir_variants.py`.
- `lookahead.py`, `common.py`, `screens.py`, and four arm result files and logs.
- `proofs.py`, `proofs.json`, `combinations.py`, and `combinations.json`.
- `verify_finalists.py`, `verification.json`, `winner.json`, and `winner_program.json`.
- `probe.py`, `arm_gates.py`, frozen/supplementary logs, `source_hashes.json`, and `decision.md`.

The JSON results preserve configs, counts, scratch, timings, and failure classifications. Temporary paths and the isolated Z3 environment are replay dependencies. This report preserves conclusions if those files disappear, not a portable implementation.

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-four-frontiers.Tfb8Ko/proofs.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/screens.py cache
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/screens.py lookahead
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/screens.py orders
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/screens.py hashes
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/combinations.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/verify_finalists.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/probe.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-four-frontiers.Tfb8Ko/probe.py control
```

The next step is self-contained integration with normal-entry-point verification and compilation-cost measurement, if requested. Do not replace production with a saved temporary program or assume the three independent one-cycle wins add together.
