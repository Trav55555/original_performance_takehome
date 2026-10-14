# Earlier scheduling regions and scratch reallocation

## Decision

Retain **981 cycles / 1,465 scratch words**. Four cases preserving physical version order were ruled out by cheap certificates. Two bounded reallocation probes passed those prechecks but exhausted the solver's 2 GiB address-space budget. Their status is **unknown**, not infeasible.

The next useful experiment is a smaller encoding, initially with fixed engine assignments and shared time variables for vector instructions. Increasing the search window or time allowance alone does not address this memory failure.

## Scope and controls

The [preceding investigation](coupled_scheduling_results.md) proved a 981-cycle floor when the original graph's prefix through cycle 615 is fixed. It also found a final-XOR reassociation that shortened the tail but produced a slower 985-cycle greedy schedule.

This program tested both graphs with first movable cycles 597 and 469, always targeting 980. The windows were 384/512 cycles for the original and 388/516 for the rewrite. These are different native schedules; matching cycle boundaries do not imply identical prefix contents.

The first four cases retained physical read/write version ordering and allowed eligible vector binaries to choose either one vector ALU instruction or eight scalar ALU instructions. Preserving version order is stricter than merely retaining scratch addresses: alternative orderings of independent lifetimes are outside this model.

The conditional probes retained true data dependencies but removed register-reuse ordering. They fixed logical issue times and engine assignments before cycle 469 and bounded later movement to ±8 native cycles. Any SAT witness would require global scratch allocation, lane checks and frozen execution. A witness rendered with stale physical addresses would not be executable.

Controls passed for both graphs:

- native digests and frozen cycle counts reproduced;
- native assignments satisfied both physical and relaxed encodings;
- SSA reconstruction and allocation reproduced each native program exactly, at 1,465 words;
- independent lane ownership checks passed;
- executable toys demonstrated both reassignment directions improving four cycles to three;
- corrupted dependencies and engine assignments were rejected;
- extracted read-version edges matched all 110,409 true SSA edges exactly, including binary operand-width checks.

One preparation command hit a 45-second tool timeout during construction of the rewrite's relaxed witness control. Its completed physical-control stage was preserved, and only the unfinished stage was resumed within 180 seconds. No optimization case was repeated.

## Four physical-version cases

All four were rejected before an optimization solver call.

| Graph | First movable cycle | Binary groups eligible | Result |
|---|---:|---:|---|
| Original 981 | 597 | 1,782 | Capacity contradiction |
| Original 981 | 469 | 2,389 | Capacity contradiction |
| Rewritten 985 | 597 | 1,781 | Dependency contradiction |
| Rewritten 985 | 469 | 2,389 | Dependency contradiction |

For the original graph:

- Starting at 597 still forces forty loads into cycles 937–955: only 38 slots. Flow and weighted arithmetic cuts also overflow.
- Starting at 469 forces 872 loads into cycles 521–955: only 870 slots. A weighted arithmetic cut also overflows.

For the rewrite, independent path certificates place a terminal store no earlier than cycle 981 with the 597 boundary, or cycle 980 with the 469 boundary. A 980-cycle program ends at cycle 979, so both cases fail the target even without considering capacity.

An independent heap-based propagation checker validated the cuts and paths. Corrupted work totals, capacities and path edges were rejected. These are certificates for the specified constraints, not challenge-wide lower bounds.

## Two conditional reallocation probes

Both used the 469 boundary, ±8-cycle displacement and up to 2,389 binary engine choices. Neither had a difference-constraint or tested capacity-window contradiction.

| Graph | Capacity literals | Model construction | Solver time | Result |
|---|---:|---:|---:|---|
| Original | 408,515 | 24.76 s | 23.39 s | Unknown: out of memory |
| Rewrite | 407,603 | 24.65 s | 22.63 s | Unknown: out of memory |

Each model had 22,021 free atom times with domains of at most seventeen cycles. Each optimization solver had sixty seconds, a 180-second child wall limit and a 2 GiB address-space limit. Memory, not either time limit, ended these probes.

The original relaxed model is especially tight on loads: its remaining 1,000 loads must fit in the 1,000 slots from cycles 469 through 968. That is a necessary condition, not a constructed schedule.

No SAT search witness was returned. Therefore no new candidate was allocated or executed, and no faster-kernel full verification suite was run. Allocation was exercised only by the successful native reconstruction controls.

## Next test

Reduce the formulation before widening it:

1. Keep native engine assignments initially.
2. Represent each vector instruction with one issue-time variable rather than eight lane variables connected by constraints.
3. Retain lane-level dependencies where scalar issue genuinely needs them.
4. Consider pinning a compacted load order as a separate, explicitly restricted hypothesis.

The fixed-engine reallocation problem remains untested. Passing prechecks does not establish feasibility, and any future SAT result still needs legal allocation and full execution gates.

## Artifacts and preservation

Workspace: `/tmp/perf-earlier-coupling.ajTJlT/`. It contains the protocol, both models, six case receipts, source hashes, independent certificate checks, SSA-edge checks and decision. A compact [receipt](earlier_coupling_certificate.json) preserves results and scope; detailed models remain in the temporary workspace.

```sh
python /tmp/perf-earlier-coupling.ajTJlT/check_receipts.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-earlier-coupling.ajTJlT/check_ssa_edges.py original
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-earlier-coupling.ajTJlT/check_ssa_edges.py rewrite
```

The case driver refuses to overwrite existing results. Repeating optimization queries requires a fresh declared program, not deletion of receipts.

Production stays at commit `5691617`, with a 1,041-cycle default. Production code, tests, simulator and prior reports were preserved. No commit, push, cloud job, package installation or external submission occurred.
