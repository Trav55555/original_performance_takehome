# Deterministic lookahead packing

## Result

**Retained: 1,114 cycles**, down from 1,117 (three cycles, 0.27%). The kernel is 189 cycles below the original 1,303-cycle retry baseline, a 14.5% reduction.

The emitted instructions, including operands, are unchanged as a multiset. Only their ordering and bundle placement changed. Scratch remains 1,416 of 1,536 words. The simulator, `tests/`, arithmetic, and engine assignments were not modified.

## Experiment

Question: can predicting near-term load demand eliminate idle load slots and shorten the tail without changing the computation?

Baseline generator content hash: `a3fbf5fa166348e4dadb213a5001b7e2514dbd0b`.

A disposable cycle-by-cycle scheduler first reproduced the 1,117-cycle baseline. It then compared candidate priority policies over bounded windows. Each candidate prefix was completed with the baseline policy, so its rollout score was the actual predicted total cycle count of a fully legal static schedule, not immediate utilization or an input-dependent estimate.

The search retained small beams of alternative prefixes. Policies included source-order/critical-path blends, distance-to-load bonuses, and prioritization of the first gathers' prerequisites. Startup and tail windows were tested separately, with policy windows of 4, 8, 12, 16, or 24 cycles and beam widths of 2, 4, or 8.

Startup probes did not beat the baseline. Tail rollouts reached 1,115 cycles. The best rollout removed two entirely empty load cycles from the original tail, at cycles 1,054 and 1,063.

The rollout search is not part of the production generator.

## Compact retained rule

Distillation tested static load-urgency hints instead of shipping beam search. A four-cycle dependency-distance horizon reproduced the benefit and improved it by another cycle.

In the existing reverse dependency pass:

- Load-engine operations have distance zero.
- Other operations inherit the minimum successor distance plus the edge latency.
- Nodes with no nearby downstream load receive no bonus.

The ready-operation priority is now:

```text
source_order - 80 * critical_path - 200 * max(0, 4 - distance_to_load)
```

The distance is a dependency-based lower-bound estimate, not a promise that a load will issue within four wall-clock cycles. It uses the existing RAW/WAW latency-one and WAR latency-zero graph. All dependencies and engine limits still constrain placement.

Nearby bonus weights from 200 through 600 tied at 1,114 in the refined search; 200 was retained. The rule applies to the dependency graph, not hardcoded cycle numbers, runtime data, or predicted tree branches.

## Measurements

All cycle positions below are zero-based; the final pause contributes the last counted cycle.

| Measurement | Previous | Retained hint |
|---|---:|---:|
| Total cycles | 1,117 | **1,114** |
| First gather | 70 | 70 |
| Last gather | 1,103 | 1,100 |
| Last store | 1,115 | 1,112 |
| Empty load cycles after 960, before the last gather | 1,054 and 1,063 | None |
| Scratch words | 1,416 | 1,416 |

The operation counts remain: 6,556 VALU, 12,304 ALU, 2,137 load, 705 flow, and 32 store operations. The capacity-only lower bound for this instruction mix remains 1,093 cycles. This experiment does not establish optimality.

## Verification

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
ruff check perf_takehome.py scripts/verify_retry.py
ruff format --check perf_takehome.py scripts/verify_retry.py
git diff --check
git diff --exit-code origin/main -- tests/
git diff --exit-code 5452f74 -- tests/ problem.py
```

Observed for the retained implementation:

- All nine unchanged frozen submission tests pass at 1,114 cycles.
- 100 random inputs, five full-width/asymmetric patterns, and eight other root-starting shapes pass the supplementary verifier.
- Scheduler-hazard examples and the corrupted-kernel negative control pass.
- Exact instruction multisets, including operands, match the archived 1,117-cycle generator.
- The performance gate rejects the archived 1,117-cycle kernel against the new 1,114-cycle target.

The earlier 1,115-cycle rollout candidate separately passed 100 random inputs, five bit patterns, and all nine unchanged submission tests with only the generator's scheduling function substituted in that process. A deliberately RAW-invalid schedule was rejected by the graph checker.

Disposable search code, schedules, and detailed results remain under `/tmp/perf-lookahead/` for near-term inspection. They are not submission dependencies and may disappear when temporary storage is cleaned.

## Decision

Keep the small load-urgency hint; do not add the rollout engine to the submission. Predictive packing helps here, but the measured benefit is modest. Larger gains still require another scheduling insight or a change in the instruction mix, not extrapolation from this three-cycle result.
