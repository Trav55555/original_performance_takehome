# Selection virtual-register prototype

## Decision

**Do not promote the prototype. Keep the 1,117-cycle kernel.**

Removing early physical assignments for the shared selection temporaries did not improve the best cycle count in the tested search. It reduced the register requirement of one tied schedule, but did not justify adding SSA conversion and an allocator to the submission generator.

This experiment does not prove the existing schedule optimal, or rule out renaming other temporaries. It tests the specific proposed seam: the shared shallow-selection banks.

## Controlled comparison

Starting generator content hash: `a3fbf5fa166348e4dadb213a5001b7e2514dbd0b`.

The production kernel, simulator, and tests were not changed during this experiment. The baseline frozen submission suite passed all nine tests at 1,117 cycles. Existing uncommitted changes from the earlier retry were preserved.

Held constant:

- Root-starting benchmark: height 10, 2,047 nodes, 256 inputs, 16 rounds.
- Hash and traversal representation, operations, and engine assignments.
- One core, fixed slot limits, vector length eight, 1,536-word scratch capacity.
- Frozen simulator and reference implementation.

Changed only:

- Shared selection definitions became 384 distinct virtual vector values.
- Their storage could be assigned after scheduling, or during bounded scheduling.
- Dependency priorities and round tiling were compared explicitly.

The selection pool had at most 27 available physical vectors: twelve original selection vectors plus fifteen vectors from unused scratch. Other scratch locations retained their original ownership. Candidate operation counts were checked against the unmodified instruction stream.

## Results

| Comparison | Result |
|---|---|
| Original dependencies + SSA lowering and interval allocation | 1,117 cycles, ten peak selection vectors |
| Remove selection alias edges | Dependency edges decreased from 87,426 to 86,622 |
| Recompute critical-path priorities on relaxed graph, original weight 80 | 1,152 cycles; twelve peak vectors |
| Retune relaxed-graph priorities, including original-priority controls | Best tied 1,117; no improvement |
| Online scheduling with a hard register budget | Best tied 1,117; eight peak vectors |

The original-dependency control demonstrates that conversion and allocation can preserve the baseline result. Removing constraints also changes heuristic priorities; it must not be confused with improving the heuristic's output.

### Bounded scheduling search

324 configurations were executed on the unchanged frozen machine:

- Round tiles: 11, 12, 13.
- Physical selection budgets: 8, 10, 12, 16, 20, 27 vectors.
- Priority weights: 10, 20, 40, 60, 80, 100.
- Priority critical-path sources: original graph, relaxed graph, or an equal blend.

Every configuration fit its enforced budget and passed the seed-zero differential check. None beat 1,117 cycles.

The selected tied prototype used tile 11, weight 100, original-graph priorities, and an eight-vector selection budget. It required ten allocation deferrals while scheduling. Eight live selection vectors do not automatically lower the production kernel's scratch high-water mark: the other fixed allocations were not compacted.

## Allocator semantics

The interval allocator allows storage reuse when the old value's final read shares a cycle with the new write. Two writes may not share a physical slot in the same cycle.

The online variant allocates from a fixed physical pool, defers definitions when no register is available, and releases values after their last scheduled consumer. It honors the same read-before-write semantics and rejects deadlock rather than spilling, increasing scratch capacity, or changing the instruction stream.

Over-budget post-scheduled variants were diagnostic only and were never executed with an enlarged simulator scratch space.

## Verification and sensitivity

- The best tied bounded prototype passed 100 random benchmark inputs and five full-width/asymmetric bit patterns against the frozen reference.
- Non-output memory remained unchanged.
- A one-vector budget was rejected before execution when scheduling could not progress.
- An intentionally invalid allocation that aliased live values to one address was rejected for incorrect output on seed zero.
- `tests/` still matches `origin/main`; `tests/` and `problem.py` still match upstream checkpoint `5452f74`.

Disposable code and detailed JSON results remain under `/tmp/perf-virtual-prototype/` for near-term inspection. They are not submission dependencies and may disappear when temporary storage is cleaned.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-virtual-prototype/prototype.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-virtual-prototype/priorities.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-virtual-prototype/bounded.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-virtual-prototype/verify.py
python tests/submission_tests.py
```

## Implication

The current twelve-vector selection reservation is not a demonstrated speed bottleneck. Do not build a full compiler on that assumption. A next experiment should target a measured startup/tail dependency or reduce the instruction mix; broader renaming would need separate evidence, especially for the private hash temporaries that this prototype intentionally left fixed.
