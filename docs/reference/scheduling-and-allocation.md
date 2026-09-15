# Scheduling and allocation

[Wiki](README.md) · [Architecture](../architecture.md) · [Search research](search-and-research.md) · [Evidence](evidence-and-experiments.md)

The objective is complete charged execution under issue and scratch limits. Instruction count, an early consumer or a feasible abstract schedule is not the objective by itself.

## Manual packing and automatic list scheduling

**Historical progression.** January's generator hand-packed batches, broadcasts, remainders and prefetch loads. Replacing that approach with a flat operation list and automatic greedy bundle packing produced the 1305-cycle checkpoint.

The legacy scheduler tracks physical read/write hazards. True dependencies and reuse of the same scratch location both constrain it. Changing a temporary's lifetime can therefore change visible parallelism even when the mathematical computation stays the same.

Later priority rules considered critical paths, distance to future loads and changes in live storage. Favoring ready ancestors of a gather helps prevent the load engine from waiting for an address. These are heuristics, not proofs that the resulting order is best.

Sources: [full history](../performance-progression.md), [load-aware packing](../../experiments/lookahead_packing_results.md).

## SSA, lane readiness and fresh allocation

**Production.** The compiler gives each logical result a unique identity, schedules before choosing physical scratch addresses, then allocates from actual lifetimes. This removes false constraints from premature reuse.

A gather writes lanes separately. Scalarized vector operations also require exact lane accounting. Assuming all vector lanes become available together can invent a barrier; ignoring a partial write can omit a real dependency.

`kernel_retime.capture` constructs the logical job graph. `validate` checks dependencies, coverage, timing and capacity. `lower` rebuilds lifetimes, allocates and rejects scratch overflow before instruction lowering. `kernel_checks.lane_identity` checks that each physical read observes the intended logical lane, using reads before cycle-end writes.

Sources: [rebuilt promotion](../../experiments/rebuilt_promotion_results.md), [retiming implementation](../../kernel_retime.py), [lane checker](../../kernel_checks.py).

## Engine selection and bounded lookahead

**Production.** A lane-wise vector binary can sometimes use one VALU instruction or eight scalar ALU instructions. An immediate can sometimes use a load `const` or flow `add_imm` from an existing base. Both choices affect contention, dependencies and storage.

Moving 27 constants to flow advanced the rebuilt first gather from 82 to 76 and saved six complete cycles in that comparison. Broad scalarization often lost; narrowly selected work helped. The native scheduler's bounded lookahead forecasts engine choices, not arbitrary global instruction order.

Sources: [constant experiments](../../experiments/algorithmica_followup_results.md), [scoped scalarization](../../experiments/algorithmica_results.md), [lookahead code](../../kernel_lookahead.py).

## Startup and the final pause

**Production.** Startup scheduling temporarily prioritizes ancestors of the first four groups' first gathers. It reached 1042 with an old cache plan; reselection produced the 1041 promotion.

The final store can share a bundle with `pause` when the flow slot is available. The machine commits that store before stopping. This saved a real cycle and was checked with pause enabled and different engine iteration orders. Omitting pause or relying on the benchmark disabling it would be a different claim.

Sources: [startup experiments](../../experiments/load_gap_results.md), [promotion](../../experiments/startup_promotion_results.md), [pause/store verification](../../experiments/scheduling_bounds_results.md).

## Backward/forward justification

**Production, after a successful research tie.** Right-justify instructions within a horizon, derive a new order, then insert them forward at their earliest legal positions. Some instructions must move later to change how resource slots are shared.

The current implementation preserves each graph's native engine assignments and exact lane dependencies. It tests native and dependence-tail tie orders. Allocation is a separate subsequent gate.

On the unchanged experimental native graph, one pass moved 8587 jobs earlier and 955 later, closing the load hole at cycle 965 and improving complete execution from 981 to 980. Extra passes did not improve cycles and sometimes increased scratch. Combining one pass with final-hash rewriting later produced 979/1463 through automatic discovery.

This differs from compaction that retains broader original-cycle order. The [ALNS RCPSP example](https://alns.readthedocs.io/en/latest/examples/resource_constrained_project_scheduling_problem.html) illustrates right-then-left justification for resource-constrained project scheduling. Our ISA adaptation additionally needs lane, pause and physical allocation checks; its numerical results do not transfer from that example.

Sources: [resource-order pilot](../../experiments/resource_order_results.md), [production scheduler](../../kernel_justify.py), [979 promotion](../../experiments/promotion_979_results.md).

## Event graphs, geometric priorities and deadlines

**Experimental, no faster incumbent in the tested families.** Fixed capacity chains can turn a chosen resource order into an event graph. Earliest issue times follow `t[j] = max(t[i] + lag[i,j])`. The longest path solves that chosen graph, not the problem of selecting all resource orders. Tested event compactions moved some jobs earlier but retained 981 cycles.

Wavefront, Morton, Gray-code and bit-reversed priorities provided coarse structural orderings. The tested geometric families were slower or exceeded scratch. A resource-tail deadline approximation strengthened 118 jobs but none originally issued at or after cycle 900. Its eight full-kernel variants required 1553 to 2666 words and were rejected before lowering.

Observed saturation is also limited evidence. A busy window can explain why an operation would have to displace other work, but does not show that those same jobs must occupy that window in every legal schedule.

Sources: [resource-order report](../../experiments/resource_order_results.md), local mathematical-model records in the [research catalog](search-and-research.md#local-only-records).

## Bounds and their scope

For fixed instruction counts, a capacity-only bound is:

```text
T >= max(ceil(engine_count / engine_capacity))
```

The current stream's largest such bound is `ceil(5800/6) = 967`. It does not prove attainability. Dependencies, startup, tails and scratch may require more cycles; different instruction choices change the counts.

Historical models added dependency windows and weighted arithmetic credits. One earlier graph had aggregate bound 965, reassignment-safe dependency bound 967 and fixed-engine dependency bound 969. These are different relaxations of that graph, not interchangeable machine optima.

For jobs forced into a window by optimistic release `r` and remaining tail `q`, a resource argument can take the form `T >= r + q - 1 + ceil(W/C)`. The release, tail and required work must be justified, not inferred from one observed ordering.

A suffix UNSAT result applies only with its prefix, engines, graph and other declared constraints fixed. A necessary-window admission is not a jointly executable schedule. The default compiler uses old preflight machinery to rank a seed for global justification, not to prove that global justification is feasible or impossible.

Sources: [early scheduling bounds](../../experiments/scheduling_bounds_results.md), [current counts](../../experiments/promotion_979_results.md), local bound/certificate records listed in [search research](search-and-research.md).
