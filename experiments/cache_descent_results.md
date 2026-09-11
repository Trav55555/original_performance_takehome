# Continued cache descent below 1,000 cycles

## Decision

Keep a verified **993-cycle / 1,426-word candidate**. It saves 44 cycles against the [1,037-cycle starting candidate](cache_neighborhood_results.md) and 48 cycles against the current 1,041-cycle local default.

All twelve accepted changes added a cache site. The search stopped at its declared neighborhood budget while performance was still improving, not at a plateau. The conditional swap screen was therefore not run. No implementation changes were promoted.

## Bounded search

Freeze the compiler, startup priority, arithmetic, lookahead, and allocation. Starting from fifteen cache sites, examine complete one-toggle neighborhoods and accept only strictly faster feasible plans. Break ties between equally fast improvements using scratch and canonical site order. Do not continue through scratch-only ties.

The budget allowed twelve neighborhoods and one conditional 128-swap screen at the first plateau, with at most 896 new plans. Compiler source identity was checked before reusing the prior experiment's 65 scores. The 1,037 control reproduced its digest and passed frozen execution again.

The search evaluated **745 new plans** across the twelve neighborhoods. Combined with the 65 prior plans, the archive holds 810 distinct configurations. All new plans fit scratch and passed full-width frozen seed 461. There were no compilation exceptions, timeouts, or correctness failures. Runtime was 94.81 seconds with four local workers and a 20-second limit per compilation.

| Step | Added block / round | Sites | Cycles | Scratch words |
|---|---|---:|---:|---:|
| Control | None | 15 | 1,037 | 1,434 |
| 1 | 8 / 15 | 16 | 1,033 | 1,418 |
| 2 | 12 / 15 | 17 | 1,029 | 1,418 |
| 3 | 11 / 15 | 18 | 1,025 | 1,434 |
| 4 | 9 / 15 | 19 | 1,021 | 1,417 |
| 5 | 16 / 15 | 20 | 1,017 | 1,401 |
| 6 | 30 / 4 | 21 | 1,013 | 1,410 |
| 7 | 25 / 4 | 22 | 1,009 | 1,411 |
| 8 | 22 / 4 | 23 | 1,005 | 1,411 |
| 9 | 17 / 4 | 24 | 1,001 | 1,434 |
| 10 | 12 / 4 | 25 | 997 | 1,442 |
| 11 | 10 / 4 | 26 | 996 | 1,450 |
| 12 | 23 / 4 | 27 | 993 | 1,426 |

No removals or swaps were accepted. The best 27-site plan's own neighborhood remains untested.

## What changed

Twelve more cached visits remove 96 scalar loads and add 156 flow selects. Five additions occur on the final round. Existing dead-code elimination removes four now-unused index updates for each of those walkers, reducing the index-update count from 412 to 392. The twelve lookups add 24 arithmetic leaves, so the net logical multiply-add count increases by four.

The complete schedule also chooses different ALU/VALU assignments:

| Measurement | 1,037 control | Candidate |
|---|---:|---:|
| Loads | 2,000 | 1,904 |
| Flow, including pause | 794 | 950 |
| VALU | 5,797 | 5,772 |
| ALU | 11,411 | 11,451 |
| First gather | 61 | 61 |
| Last gather | 1,025 | 980 |
| Startup / middle / drain load holes | 50 / 2 / 22 | 50 / 8 / 24 |

Total empty load slots increase from 74 to 82. The 96 fewer loads would save 48 cycles if the hole count stayed fixed; the eight extra holes account for the observed saving being 44 cycles. This is an accounting identity, not a proof that the remaining gaps are avoidable.

The resource balance has changed again. Final instruction-stream bounds are 952 cycles for load, 950 for flow, 962 for VALU, and 955 for ALU. The strongest is now VALU, not load. These bounds are close enough that further cache additions may simply move pressure between engines. The last two improvements were one and three cycles, so the earlier four-cycle pattern should not be extrapolated.

The 962 bound belongs to the final instruction stream. Its 31-cycle gap is not guaranteed recoverable, and no bound here establishes challenge-wide optimality. Running below the previous stream's 1,000-cycle bound is legitimate because the instruction stream changed.

## Verification

The final candidate passed 100 full-width seeds, five asymmetric patterns, logical lane ownership, and three deterministic compiles. Dependency, encoding-constant, and selector mutations were rejected. The recorded twelve cache transitions reconstruct the final plan. A fresh hash-seed-17 process reproduced its digest with runtime-data and reference helpers forbidden during compilation.

An experimental adapter passed all nine unchanged frozen tests and the supplementary verifier at a 993-cycle ceiling. Supplementary coverage included 100 generated inputs, five patterns, nine other shapes, three non-benchmark performance ceilings, scheduler hazards, pause/store completion, and corruption rejection. Other shapes use unchanged legacy generation. Full-width and pattern checks also verified preservation of non-output memory.

The same supplementary ceiling rejected both executed controls exactly: `((1037, 993),)` and `((1041, 993),)`.

Selected-plan compilation took 0.438 seconds in the screen and about 0.431 / 0.432 seconds in repeat checks. These measurements exclude the full selection search. A production port that simply repeats every exhaustive neighborhood would substantially increase cold-build cost; that integration and its cost have not been measured.

Instruction SHA-256:

```text
37fcbb8e6138d443343aeea4887679b34397e35dd1b718c3364a71672d99f935
```

## Artifacts and next step

The workspace is `/tmp/perf-cache-descent.R1FmvT/`. It contains `program.md`, copied compiler sources, prior scores, the reproduced baseline, `search.py`, `steps.json`, `new_rows.json`, the complete `screen.json`, `receipt.json`, final configuration/instructions, diagnostics, verification logs, source hashes, and `decision.md`.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-descent.R1FmvT/search.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-descent.R1FmvT/verify_winner.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-descent.R1FmvT/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-descent.R1FmvT/probe.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-descent.R1FmvT/probe.py control
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-descent.R1FmvT/probe.py integrated
```

Replay depends on the temporary sources and configurations. This report preserves conclusions, not a portable implementation.

The next research question is where this descent actually plateaus. The integration question is how to express continued admission with an explicit compilation budget instead of importing 27 saved sites. Neither question was resolved by reaching the current cap.

The local default remained 1,041 cycles during this experiment. The then-uncommitted integration changes, prior reports, tests, and simulator files were preserved. No promotion, commit, push, cloud work, or external submission occurred.
