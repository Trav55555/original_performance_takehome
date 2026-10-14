# What the experiments taught us, and where to look next

The best verified result remains **981 cycles / 1,449 scratch words**. The local searches found no better cost, and both untimed exact searches ended without an answer. Neither result establishes optimality.

My recommendation is to test a **small exact repair on the new arithmetic-selector graph**, rather than restart either large query. Inspection of the saved programs gives a specific reason: the new graph has unused flow slots at cycles 957 and 958, where the previous incumbent had none. A focused repair may be able to use those slots to advance the ending. Dependencies and other engines may still prevent it.

This document records completed evidence and proposes future work. No new compiler run, optimization query, training run or installation accompanied it.

## What we know

| Observation | What it supports | What it does not establish |
| --- | --- | --- |
| Restoring critical urgency recovered a selective rewrite from 991 to 981 cycles. Both programs passed full checks. | Priority and lookahead scoring can suppress the benefit of a valid rewrite. | That urgency restoration alone beats 981, or explains every rewrite regression. |
| Two per-lookup conversions removed two flow operations but added two VALU and 16 ALU operations. Completion stayed at 981. | Fewer flow instructions are not enough; their readiness and downstream work matter. | That flow reduction is useless, or that all per-lookup conversions have been tested. |
| The restored block-29 rewrite ended with an 11-cycle tail rather than its original 10-cycle tail. | Another output path can determine completion after one path improves. | Which set of changes will advance all competing outputs together. |
| The selector-first cache search and 16 combinations found no better cost. | The previous scratch saving did not produce a gain in these declared neighborhoods. | That scratch headroom has no value under other schedules or rewrites. |
| Both exact queries exhausted 2 GiB after about ten hours. | The formulations eventually ran out of memory, despite fitting initially. | That 980 is impossible, or that more memory would guarantee an answer. |

The four-arm program recorded 988 unique configurations. Of these, 954 passed allocation, independent legality checks and frozen execution; 28 exceeded scratch and six were incompatible. Full verification covered selected representative programs, not every screen candidate. See the [results](breakthrough_research_results.md) and [receipt](breakthrough_research_receipt.json).

Retain H, the earlier 981 / 1,449 configuration. Archive the new A graph as a verified equal-cost alternative with different resource usage. The search's lexical tie-break is not a reason to prefer its extra arithmetic work.

## Both exact searches are now terminal

Earlier reports correctly described the workers as running at their observation times. This section and the adjacent [terminal evidence](untimed_solver_outcomes.json) record their later outcomes without rewriting those snapshots.

| Query | Native program | Restricted search | Solver time | Outcome |
| --- | --- | --- | ---: | --- |
| Original | 981 / 1,465 | Fixed native engines; prefix before 469 fixed; later movement within eight cycles; pinned loads; ordered lanes | 38,281 seconds, about 10h 38m | Unknown, out of memory |
| Hybrid selective | 981 / 1,473 | Fixed native engines; prefix before 469 fixed; later movement within eight cycles; loads unpinned; no added lane ordering | 37,841 seconds, about 10h 31m | Unknown, out of memory |

Both targeted 980 cycles, used true-data dependencies without physical scratch-reuse ordering, and retained a 2 GiB address-space cap. Neither had a solver or CPU deadline. Neither produced an executable candidate. A normal worker exit code means the failure was recorded successfully, not that the optimization succeeded.

The original query had 9,471 free issue times and 118,496 capacity literals. The hybrid query had 10,576 free times and 177,176 capacity literals. Neither searched the new two-conversion A graph. The hybrid seed also lacked H's three ordering changes.

Simply waiting longer cannot resume these terminated runs. A larger memory allowance could postpone the same failure. It is an option for a separately approved experiment, not the default next step.

## A new observation from the saved programs

No schedules were regenerated for this comparison. The evidence file preserves the program hashes and per-cycle counts.

| Recorded program | Non-pause flow operations in cycles 949 through 969 | Empty flow slots in that interval |
| --- | ---: | --- |
| H, previous 981 / 1,449 incumbent | 21 | None |
| A, new verified 981 / 1,449 tie | 19 | 957 and 958 |

For an illustrative requirement to issue those operations by cycle 968, there would be 20 slots starting at 949. The count changes from 21 operations to 19. This explains why an old overload argument cannot simply be copied onto A.

This is **not** a new feasibility certificate. Each operation's deadline must be derived from A's actual dependencies and native engine assignments. Operand availability, arithmetic capacity, stores and allocation can still make a 980-cycle repair impossible within the selected scope.

A's instruction digest is:

```text
504932cb0e5bb31fff4e4fbc57af8d61d7c90c2aaea9d7cd7601b8d4b7162024
```

## Ranked research directions

### 1. Repair the new graph's ending with a much smaller exact model

**Hypothesis:** A's two freed flow slots permit a local retiming that the forward heuristic missed.

Start by reconstructing A's true-data graph and the actual final-output dependencies. Run cheap deadline and mandatory-capacity checks for suffix widths 32, 64 and 128, with H as the comparison graph. For a 981-cycle native program, the 32-cycle suffix begins at 949.

Unlike the earlier large queries, eliminate fixed jobs from the variable model. Account for their occupied slots and boundary dependencies explicitly. Fix the prefix before each suffix and initially allow later jobs to move at most eight cycles from their native times. Keep native engine modes, leave load order unpinned, and do not impose old physical allocation ordering. Add lane-order constraints only if their lossless-normalization conditions have been checked on this graph.

Only the first A scope that passes preflight should qualify for an optimization query. First require native-981 satisfiability, exact reconstruction and corruption controls in the same encoding. A target-980 SAT result would still need fresh allocation and full execution gates.

The strongest opposing case is that the gaps are unusable because the required operands arrive too late, or because arithmetic work occupies the necessary slots. Passing separate engine windows cannot settle that question.

**Stop rule:** if all declared small scopes fail preflight, record their specific obstructions. Do not automatically return to a 512-cycle suffix or raise memory. This would be a scoped negative result, not global optimality.

### 2. Choose branch-bit order per critical lookup

**Hypothesis:** put the last-arriving branch predicate near the end of a selection tree, so less selector work remains after it becomes available.

The current advanced generator reverses bit order at depth 3 but keeps normal order at depth 4. Arrival-aware ordering would act at individual lookups, instead of changing one global order for every walker. Leaf-table permutation must change with the bit order so the lookup still returns the same node.

First inspect the recorded availability times of all four predicates at late depth-4 lookups. If the latest predicate currently feeds the first layer, moving it later has a plausible dependency benefit. If predicate arrival is not limiting, stop before a permutation sweep.

Earlier work already tested global history/bit-order variants. The proposed distinction is a small, trace-selected set of individual lookups on the current graphs. Audit those old variants before claiming a genuinely new case.

Use controls that separate bit order from arithmetic-leaf placement. Recompute and charge any new pair differences. Re-identify converted sites by predicate and operand meaning, not an old pair number whose meaning changed with the table permutation.

The strongest opposing case is that earlier partial selections increase live scratch or merely move flow contention elsewhere. A shorter path from the latest predicate is a hypothesis about timing, not a speed result.

### 3. Schedule against output deadlines rather than only path length

**Hypothesis:** a deadline-driven or bidirectional schedule advances the competing outputs more effectively than rewarding long paths and early emission positions.

A true backward construction would place consumers near a target finish and work toward their producers while respecting resource slots. A less invasive version would use latest-issue slack in forward selection. Neither is the same as the already-tested restoration of baseline critical-path scores.

Start with all 32 output stores. Record when each required value becomes ready, whether a ready operation had capacity, and whether the policy deferred it despite capacity. Separate true data dependencies from resource ordering observed in one schedule. Observed order is not automatically a mandatory edge.

The allocator runs after scheduling. Distinguish its later scratch rejection from the scheduler's live-word pressure heuristic; do not label both as a physical-register stall.

The strongest opposing case is that backward scheduling creates long live ranges or delays loads enough to erase the ending's gain. Rebuild and allocate every candidate. Do not freeze a prefix already known to force 981 and then expect a different priority score to escape that bound.

**First gate:** identify which actual stalls a deadline policy could change. If all late stalls follow mandatory dependencies or fully occupied resources, another priority formula has little justification without a graph change.

### 4. Replace selected four-way selector groups, not only leaves

**Hypothesis:** moving a complete two-level selector group to arithmetic can remove a higher-layer flow operation while preserving two levels of selector dependency.

For arbitrary 32-bit leaves `a,b,c,d` and normalized predicate bits `s,t`, consider this candidate form, with wrapping arithmetic:

```text
u = multiply_add(s, b-a, a)
v = multiply_add(s, d-c-b+a, c-a)
y = multiply_add(t, v, u)
```

It selects `a,b,c,d` for predicate combinations `00,10,01,11`. The first two multiply-adds can be independent once their inputs are ready. Swapping predicate roles and permuting the leaves may let the earlier predicate drive those two operations.

Machine-check the identity and predicate assumptions before implementing it. Construct all coefficients from runtime-loaded values with charged instructions. Reuse valid differences when available, but count new subtraction, broadcast and storage costs.

This differs from A's first-layer-only conversions: it can remove the parent flow select too. It does not remove the cost of preparing its coefficients. Some groups already contain arithmetic leaves, so the marginal resource trade must be counted against their actual baseline, not three hypothetical flow operations.

The strongest opposing case is higher arithmetic demand and extra live vectors. Test only groups identified by the output-dependency analysis. A broad global conversion is not justified by the present evidence.

## Recommended next decision

Approve a small diagnostic and repair pilot, not another thousand-case search:

1. Reproduce H and A from source and reconstruct their final-output graphs.
2. Inspect predicate arrivals, readiness stalls and competing output deadlines.
3. Preflight the three declared suffix sizes on both graphs, six cases total.
4. If A has a passing scope, permit at most one new target-980 exact query under the existing 2 GiB, no-deadline policy.
5. If it does not, use the failed constraints to choose between per-lookup bit order, deadline scheduling and four-way arithmetic selection.

These are proposed limits for a future run, not current execution authority. The highest-confidence recommendation is to avoid rerunning the two unchanged large queries. Confidence that any listed mechanism will beat 981 is lower; no candidate has demonstrated that yet.

Larger neural models, wider undirected priority sweeps and blanket memory increases remain lower priorities. The next experiment should answer a specific question about the final outputs, or test a work-changing rewrite tied to that evidence.

All future candidates must include charged setup, stores and pause, stay within 1,536 words before lowering, and pass the existing full verification gates before becoming a new best. Source-only generation from a selected experimental configuration is still not automatic production integration.
