# Search methods and research catalog

[Wiki](README.md) · [Full history](../performance-progression.md) · [Published experiment index](../../experiments/README.md) · [Evidence method](evidence-and-experiments.md)

This catalog records what was tried and how strongly the result is supported. It is not an active backlog. All historical search budgets are closed; speculative next steps require a new decision and finite protocol.

## Deterministic configuration search

**Production.** Cache admission begins from generated source choices rather than a saved winning configuration. `Plan` identifies cache sites, arithmetic-pair profiles, selector rewrites and final-hash blocks. `Cost` ranks scratch feasibility before cycles, then scratch and stable plan order.

The early rebuilt selector stopped after useful admissions and reached 1076/1236. Later policies explored full single-toggle neighborhoods, bounded swaps and arithmetic profiles. A single-toggle plateau at 987 was escaped by a cache swap to 984. A tied arithmetic profile then enabled an additional cache and reached 981.

Current discovery memoizes scores and caps the combined count at 4096. Final backward/forward neighborhoods reserve scores before construction and contribute at most eight schedules. The published total is 1959. Source-only reproduction verifies the procedure, not merely the winning site list.

Sources: [rebuilt promotion](../../experiments/rebuilt_promotion_results.md), [descent](../../experiments/cache_descent_results.md), [optimizer](../../kernel_optimizer.py), [refinement](../../kernel_refinement.py).

## Interaction tests and candidate selection

Strictly discarding every non-winning standalone rewrite can miss combinations. Cache/profile coupling and final-hash/justification both demonstrate this. But favorable interaction does not itself establish a better program.

The mathematical mixing program used:

```text
I(A,B) = T(A+B) - T(A) - T(B) + T(base)
```

Nineteen of forty pairs had negative interaction, yet none beat its better component. One pair's additive prediction was 989, its actual result 985, and its better component 983. That is a favorable interaction and still a poor promotion candidate.

Keep output identity and resource effects as diagnostics. Two edits that advance different stores can still compete for arithmetic or scratch when combined. Rank the complete allocated program, not a sorted list of isolated consumer times.

## Solver and learned scheduling research

| Approach | Recorded outcome | Scope that must stay attached |
|---|---|---|
| Physical-register suffix solving | Several small suffixes were UNSAT for one-cycle improvement | Fixed prefix, engines, graph and physical hazards; not unrestricted rescheduling |
| Aggregate arithmetic and dependency-window bounds | Stronger lower bounds and checkable certificates | Relaxed graph/resource models; witnesses were not executable schedules |
| Coupled engine/timing models | Scoped flow-tail obstruction; no faster incumbent in those runs | Constraints and prefix choices differ between models |
| Compact and ordered-lane models | Bounded queries returned timeout unknown | Fitting in memory or adding valid order constraints did not establish SAT/UNSAT |
| Earlier-region reallocation models | Some cheap certificates rejected cases; admitted probes exhausted memory | Preflight admission did not imply coupled feasibility |
| Large original and hybrid exact queries | Both ended unknown, out of memory, after roughly 10.5 hours | 2 GiB cap; neither produced a winning executable program |
| Neural/GPU scheduling | No lower cycle incumbent; scratch-saving 981/1449 arose during candidate work | Do not attribute that tie to a learned scheduling win |
| Small exact repair on a changed late-selector graph | Experimental 980/1449, then separate automatic production 980/1465 | Fresh allocation and execution followed SAT; production did not replay the experimental timing |
| Later target-979 query | Unknown, out of memory after about 16 h 52 m | Different graph/scope from constructive 979; no global impossibility conclusion |
| Backward/forward justification | Experimental 980 tie, then production 979 with final-hash rewriting | Fixed engines per graph; fresh scratch allocation mandatory |

The original large and hybrid query terminal times were 38281 and 37841 solver seconds in their local closure record. Earlier launch/status notes describing those workers as running are historical snapshots. A worker exiting normally after recording OOM is not an optimization success.

Published sources cover the [980 promotion](../../experiments/promotion_980_results.md), [archived experimental control](../../experiments/promotion_980_evidence/archived_980_control.json), [resource-order pilot](../../experiments/resource_order_results.md) and [979 promotion](../../experiments/promotion_979_results.md). Other model details come from the local records below.

## Mathematical and lookup screens

| Program | Coverage | Best result or decision |
|---|---|---|
| Five mathematical arms | 74 candidates: two-bit tensors, recursive Mobius, radix/parity, geometric priorities and event graphs | 65 executable, nine scratch-rejected; no candidate beat native 981 or published 980 |
| Matched combinations and sharing | 88 profiles, including 40 two-component pairs | All feasible; none reached 980. Some coefficient sharing helped matched variants. |
| Slope-select | 16 configurations crossing sites, bit order and reuse policy | Best 981/1473; useful local changes, no complete-cycle incumbent |
| Resource-order pilot | 18 candidates plus controls and conditional verification | Eight justification variants tied 980; deadline variants exceeded scratch; paired slopes regressed under native scheduling |
| Final-hash/justification pilot | Eight candidates with unchanged cache/selector control | Seven executable; one 1537-word rejection. Best selected program 979/1463, later automatically reproduced in production. |

These screens did not authorize broad materialization sweeps, every tensor site, unrestricted cache reselection or indefinite solver retries. Unused conditional slots expired when their gates failed or the protocol closed.

## Local-only records

The following paths existed in the local checkout at the 2026-09-15 documentation review but were untracked. They are plain-text provenance labels, deliberately not broken fresh-clone links. This wiki preserves a summary, not their full evidence or runnable archive. Published corroborating reports are linked above where available.

| Local record under `experiments/` | Subject and closure |
|---|---|
| `plateau_selector_results.md`, `leaf_placement_results.md` | Cache/selector plateau escape to 981; alternative leaf placement did not improve it |
| `math_bounds_results.md`, `math_bounds_certificate.json` | Retained-work bounds, dependency windows, modular algebra and restricted exact suffixes |
| `coupled_scheduling_results.md`, `compact_scheduling_results.md`, `ordered_scheduling_results.md`, `earlier_coupling_results.md` and adjacent certificates | Model-specific obstructions, timeouts and memory unknowns |
| `neural_scheduling_results.md`, `hybrid_scheduling_results.md` and receipts | Learned/heuristic research and scratch-saving tie, not a lower cycle result |
| `untimed_scheduling_run.md`, `untimed_solver_outcomes.json`, `research_lessons_and_directions.md` | Launch and later terminal closure of the two large exact queries; old recommendations subsequently tested or superseded |
| `breakthrough_research_*` | Four-arm program, equal-cost alternatives and no faster incumbent |
| `followup_research_*`, `followup_980/` | Small exact-repair experiment and selected-timing reconstruction; not automatic source-only production |
| `below_980_exploration*`, `final_gather_tail_*` | Early-address screening and later target-979 query; launch snapshots are not terminal results |
| `mathematical_models_*`, `mathematical_models_mix_*` | Five-arm and combination screens, protocols, receipts and scoped negative results |
| `slope_select_*` | Sixteen-case coefficient/select experiment |
| `finalhash_order_*` | Selected 979 pilot before production promotion |

Some drivers, symbolic probes, scheduling-literature audits and physical programs survive only in temporary workspaces named by those records. Reconstructing the exact experiment may be impossible after those files disappear. Archival selection remains separate work; this documentation does not add, delete or alter those untracked files.

## Sources that informed the work

- [Algorithmica, Algorithms for Modern Hardware](https://en.algorithmica.org/hpc/), particularly [instruction-level parallelism](https://en.algorithmica.org/hpc/pipelining/), [throughput](https://en.algorithmica.org/hpc/pipelining/throughput/) and [machine-code analyzers](https://en.algorithmica.org/hpc/profiling/mca/). The [local follow-up](../../experiments/algorithmica_followup_results.md) distinguishes guidance from measured simulator results.
- [Audited 1063-cycle public fork](../../experiments/github_1063_audit.md). It motivated isolated fusion/selector ports; its fixed tuning, general-shape failures and fail-open behavior were not adopted as production policy.
- [LLVM ScheduleDAGMILive](https://llvm.org/doxygen/classllvm_1_1ScheduleDAGMILive.html). Official documentation connects machine scheduling with live intervals and register pressure.
- [Valls et al., Justification and RCPSP](https://doi.org/10.1016/j.ejor.2004.04.008) and the [ALNS executable example](https://alns.readthedocs.io/en/latest/examples/resource_constrained_project_scheduling_problem.html). These explain right/left justification; the local implementation adds ISA-specific checks.
- [Unison, Combinatorial Register Allocation and Instruction Scheduling](https://chschulte.github.io/papers/castanedacarlssonea-toplas-2019.html). Integrated allocation/scheduling is relevant background. The local compiler uses bounded heuristics, not a claim of reproducing Unison's optimizer or results.
- [Resource-aware VLIW scheduling research, CASES 2011](https://cgi.cse.unsw.edu.au/~jingling/papers/cases11.pdf). It motivated deadline hypotheses; the rejected local approximation was not a full reproduction of that algorithm.

Tensor/Mobius, common-subexpression reuse, FFTW/SPIRAL-style search and materialization ideas also informed local research. Literature interest is not evidence of an implemented technique. External speedups are not predictions for this simulator or for a future hardware port.
