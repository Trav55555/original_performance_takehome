# One cache neighborhood beyond the 1,041-cycle plan

## Decision

Keep a verified **1,037-cycle / 1,434-word candidate**. It adds cache site `(0,15)` to the [integrated 1,041-cycle plan](startup_promotion_results.md), saving four cycles and 24 scratch words.

The existing two-step selection limit was leaving improvements. This result does not establish a local optimum around the new fifteen-site plan: that next neighborhood was not searched. The local default remained 1,041 cycles, and its then-uncommitted integration changes were preserved during this experiment.

## Bounded screen

Freeze the compiler, startup policy, arithmetic, lookahead, and allocation. Toggle each of the 64 eligible depth-4 sites around the final fourteen-site plan, giving 50 additions and 14 removals. Reproduce the control separately.

| Candidates | Count | Cycle range | Faster than 1,041 |
|---|---:|---:|---:|
| Add one site | 50 | 1,037 to 1,048 | 46 |
| Remove one site | 14 | 1,045 to 1,048 | 0 |
| Control | 1 | 1,041 | 0 |

All 65 rows fit within 1,536 words and passed a full-width frozen execution using seed 461. Scratch ranged from 1,426 to 1,506 words. There were no compilation exceptions, timeouts, or correctness failures. The screen took 8.49 seconds with four local workers and a 20-second compilation cap per configuration.

Thirty-nine additions tied at 1,037 cycles. Adding `(0,15)` used the least scratch among them. No swaps, second neighborhood, or other tuning followed this screen.

## What the extra cache removes

The depth-4 table and pair differences are already present, so this addition needs no extra preload or broadcast setup. It replaces one eight-lane gather with two arithmetic leaves and thirteen flow selects.

This is a final-round lookup. Earlier shallow lookups use stored branch history, so caching the last lookup also removes the remaining need for that walker's mirrored-index chain on its second tree traversal. Existing dead-code elimination drops four index-update multiply-adds. The measured index-update count falls from 416 to 412; total multiply-add operations fall by two after adding the two arithmetic leaves.

| Measurement | Integrated control | Candidate |
|---|---:|---:|
| Cycles | 1,041 | 1,037 |
| Scratch words | 1,458 | 1,434 |
| Load instructions | 2,008 | 2,000 |
| Flow instructions, including pause | 781 | 794 |
| VALU instructions | 5,793 | 5,797 |
| ALU instructions | 11,475 | 11,411 |
| First gather | 60 | 61 |
| Last gather | 1,029 | 1,025 |
| Startup / middle / drain load holes | 48 / 4 / 22 | 50 / 2 / 22 |

Both programs have 74 unused load slots. The eight fewer loads account for four fewer cycles at two load slots per cycle; this is workload reduction rather than a further reduction in total empty slots. The first gather actually starts later. Complete execution time remains the objective.

The scratch reduction is a whole-schedule allocation result. The removed index chain helps explain why an additional cache need not increase storage, but these measurements do not isolate its contribution from changed scheduling and other lifetimes.

## Verification

The control reproduced its integrated instruction digest exactly. The winning neighbor passed 100 full-width seeds, five asymmetric patterns, lane-ownership checks, and three deterministic compiles. Dependency, encoding-constant, and selector mutations were rejected. A fresh process under hash seed 17 reproduced the candidate with runtime-data and reference helpers forbidden during compilation.

Through an experimental adapter, the candidate passed all nine unchanged frozen tests and the supplementary verifier at a 1,037-cycle ceiling. The supplementary run covered 100 generated inputs, five patterns, nine other shapes, three non-benchmark performance ceilings, scheduler hazards, pause/store completion, and corruption rejection. Other shapes retained the unchanged legacy generator. Full-width and pattern checks also verified all non-output memory.

The same supplementary ceiling rejected the executed 1,041 control exactly as `((1041, 1037),)`.

Selected-plan compilation took 0.450 seconds in the screen and 0.409 / 0.405 seconds in repeats. These timings exclude automatic selection and production integration. The new stream's capacity-only bound is 1,000 cycles; its 37-cycle gap does not establish recoverable savings or a challenge-wide optimum.

Instruction SHA-256:

```text
10aa29de284533332e60d999ecee2bb1ed47203574248cf5022625a6a25324ce
```

## Artifacts and next step

The workspace is `/tmp/perf-cache-neighborhood.AzJCGk/`. It contains the protocol, copied compiler sources, baseline receipt, 64-entry manifest, all 65 screen rows, diagnostics, winner configuration/instructions, strong verification receipts, source hashes, and decision note.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-neighborhood.AzJCGk/screen.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-neighborhood.AzJCGk/verify_winner.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-neighborhood.AzJCGk/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-neighborhood.AzJCGk/probe.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-neighborhood.AzJCGk/probe.py control
```

Replay needs the temporary sources and experimental baseline configuration. This report preserves conclusions, not a portable implementation.

Stop at the agreed neighborhood boundary. The evidence supports revisiting the automatic selection stopping rule, rather than hardcoding this winning site. Continued admission would need its own bounded search and compilation-cost checks; neither convergence nor the right search budget was established here.

No production code, previous reports, tests, or simulator files changed during this experiment. No promotion, commit, push, or external submission occurred.
