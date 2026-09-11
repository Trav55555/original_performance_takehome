# Research follow-up: cache reselection and joint startup scheduling

## Decision at the end of this experiment

No faster executable kernel emerged from this bounded follow-up on 2026-09-10. The decision was to keep the verified 1,076-cycle prototype as the integration candidate, with production still at 1,082 cycles.

The subsequent [promotion receipt](rebuilt_promotion_results.md) records integration at 1,076 cycles and 1,236 scratch words. The results below preserve this earlier experiment's measurements.

Cache reselection found a verified speed tie using 1,245 scratch words instead of 1,253. Eight saved words do not justify replacing the existing candidate on speed grounds. The regional exact solver timed out; its results do not establish optimality.

## Completed TODO list

- [x] Reproduce the 1,076-cycle, 1,253-word control with frozen execution.
- [x] Reselect caches with the winning constant policy and scheduler fixed.
- [x] Jointly choose constant implementations and instruction times in startup regions.
- [x] Compare exact solving with stochastic scheduling under matched time limits.
- [x] Verify the best cache tie and record controls, limits, and replay commands.

These tasks were experiments, not production integration. Full hash/branch/index synthesis, a joint register allocator, and an e-graph implementation remain outside this experiment.

## Cache reselection

The search held representation, constant policy, and scheduler parameters fixed. Its eligible sites covered 32 blocks at rounds 4, 5, and 15, including depth-5 additions. It tested single toggles, ranked swaps, a neighborhood around the best result, and seeded multi-site mutations. Canonical site sets prevented repeated compilation.

| Stage completed | Cumulative unique configurations | Best cycles | Best scratch words |
|---|---:|---:|---:|
| Control | 1 | 1,076 | 1,253 |
| Single toggles | 97 | 1,076 | 1,253 |
| Ranked swaps | 353 | 1,076 | 1,245 |
| Best-result neighborhood | 447 | 1,076 | 1,245 |
| Bounded mutations | 512 | 1,076 | 1,245 |

Of 512 configurations, 481 fit scratch and passed a frozen full-width input. The other 31 exceeded scratch; no exceptions or feasible correctness failures occurred. The fastest over-scratch configuration took 1,082 cycles, so none hid a faster allocation-infeasible winner. The four-worker search took 24.54 seconds on this host.

The best tie removes cache site `(12, 15)` and adds `(28, 4)`. Its allocation uses 53 scalar slots and 149 vector slots, one fewer vector slot than the control. First and last gather cycles remain 76 and 1,063. Counts are load 2,027, flow 897, VALU 6,281, ALU 12,511, and store 32.

Three repeated compiles produced identical instructions and scratch usage. Their times were 0.128, 0.128, and 0.136 seconds. These are host compilation measurements, not simulated execution times or a comparative compilation-speed claim.

## Joint regional scheduling

The regional experiment used the original 1,076-cycle control, independently of cache reselection. It offered two equivalent implementations for scalar constants:

```text
load constant n
flow add_imm from a live scalar 7, with immediate n - 7
```

Z3 proved their wrapping-32-bit identity. The scheduler jointly chose constant forms and instruction times, retaining physical registers. Constraints covered read-after-write, write-after-write, and read-before-overwrite dependencies. Optional flow reads required the correct live version of the scalar seven; the immediate-load alternative did not require that read.

Each target shortened a startup region by one cycle and shifted the untouched suffix earlier by one cycle. Cross-boundary dependencies still had to hold. This fixes the outside schedule and allocation; it does not search arbitrary legal programs.

Both methods received a nominal 20-second wall-time budget per window, including method-specific construction. Shared preparation took 0.418 seconds. The stochastic method used seed 1, restarts, operation moves, swaps, and constant-engine flips. Exact solving used satisfiability modulo theories through Z3.

| Startup window | Instructions | Constant choices | Exact result | Stochastic result |
|---|---:|---:|---|---|
| 32 cycles | 367 | 57 | Unknown, timeout | Budget exhausted |
| 64 cycles | 973 | 57 | Unknown, timeout | Budget exhausted |
| 96 cycles | 1,607 | 57 | Unknown, timeout | Budget exhausted |

Exact wall times were 20.026, 20.152, and 20.065 seconds. Model construction consumed 1.263, 3.132, and 6.365 seconds of those totals. Stochastic wall times were 20.006, 20.010, and 20.002 seconds, with 93,824, 106,752, and 107,520 proposals. Process CPU times are recorded separately in the JSON receipts. Small overruns reflect solver timeout and loop-check granularity.

Neither method reached the 1,075-cycle target. This single-seed, bounded comparison cannot rank the methods generally. In particular, timeout is not an unsatisfiability proof, and a local-search failure proves no lower bound. Larger windows also left less solver time after construction.

## Verification

Both regional methods solved and executed a known three-to-two-cycle control. Fixing its original constant form made the two-cycle target unsatisfiable. A wrong arithmetic identity produced a counterexample; corrupted constants and a missing anchor dependency were rejected.

The cache tie passed:

- 100 full-width random inputs and five asymmetric bit patterns.
- Nine other emitter shapes and all three non-benchmark performance ceilings.
- Logical lane identities, dependency and flow-constant corruption controls.
- All nine unchanged frozen tests through an explicit experimental adapter.
- The supplementary verifier at a 1,076-cycle ceiling, including 100 generated inputs, pause/store behavior, and corruption rejection.

The real supplementary 1,075-cycle gate rejected the tie exactly as `((1076, 1075),)`. Its scheduler-unit checks exercise the retained production scheduler; separate lane-identity checks cover the prototype scheduler. The local lane checker now treats immediate constant loads as having no anchor read, matching the machine semantics.

Production separately passed all nine frozen tests at 1,082 cycles. The adapter is verification infrastructure, not an integrated production generator. Other shapes filter the selected cache sites to eligible positions; this does not establish optimal cache selection for those shapes.

## Artifacts and replay

The complete temporary experiment is under `/tmp/perf-research-followup.r9axAq/`:

- `program.md`, `baseline.json`, `baseline_receipt.json`.
- `cache_search.py`, `cache_results.json`, `cache_winner.json`, `cache_program.json`.
- `regional.py`, `regional_results.json`, `regional_controls.json`.
- `verify_finalist.py`, `verification.json`, `probe.py`, and execution logs.
- Local generator, scheduler, and verifier source copies.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-research-followup.r9axAq/cache_search.py
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-research-followup.r9axAq/regional.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-research-followup.r9axAq/verify_finalist.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-research-followup.r9axAq/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-research-followup.r9axAq/probe.py
```

The solver environment contains `z3-solver==4.15.4.0`. No project or global dependency changed. Temporary artifacts and hardcoded workspace paths mean a fresh checkout alone cannot replay these experiments. Repeated timed searches can produce different outcomes; the JSON files record the actual run.

## Research connection and decision before promotion

[Scheduling Modulo Equality](https://pldi26.sigplan.org/details/egraphs-2026-papers/15/A-Joint-Approach-to-Instruction-Scheduling-and-Algebraic-Rewriting-with-E-Graphs) motivated joint expression and schedule choices. [Rewrite System Showdown](https://arxiv.org/html/2605.19005v2) motivated the bounded stochastic comparison. Neither source predicts a cycle count for this simulator.

Archive this search without promoting a new kernel. Return to self-contained integration of the existing 1,076 candidate before spending more time on broad searches. Any further exact-solver work should first reduce model construction and tighten scheduling domains, rather than treating longer timeouts as progress. No commits, pushes, or external submissions occurred during this experiment.
