# Resource-order pilot: a solver-free match at 980 cycles

Backward/forward reordering matched 980 cycles without a solver. All eight variants passed execution screens. Best was B03 at 980 cycles /1483 scratch words, using the unchanged native graph, dependence-tail tie order and one right/left pass.

Production remains 980/1465. B03 uses eighteen more scratch words and has not passed the complete production promotion suite. It is an extended-validated experimental alternative, not a new cycle incumbent.

The complementary slope pair regressed to 985 cycles. Every deadline candidate exceeded scratch and was rejected before lowering or execution. All budgets are closed.

## Fixed program and results

The [protocol](resource_order_program.md) declared two paired-slope candidates, eight backward/forward candidates and eight deadline candidates. The [receipt](resource_order_receipt.json) contains the complete matrix, source hashes, control results, timing diagnostics and audit. The tested scheduling implementation is preserved in [resource_order_scheduler.py](resource_order_scheduler.py).

| Arm | Candidates | Executed / rejected | Best actual cycles / words |
|---|---:|---:|---|
|Complementary slope pair|2|2 /0|985 /1473|
|Backward/forward reordering|8|8 /0|980 /1483|
|Resource-tail deadline scheduling|8|0 /8|None, all over scratch|

Each feasible candidate passed three full-width seeds and five asymmetric patterns. B03 additionally passed 100 full-width seeds, five patterns and two fresh deterministic reconstructions. These reconstructions ran in the same process and each passed another seed. No cold source-only discovery run or full submission suite was claimed.

## Backward/forward reordering

For every candidate, the driver generated a fresh native IR and schedule. It retained the native engine assignment and individual scalar lanes. It did not load a saved candidate graph or timing as search input.

The right pass moved each job toward its successors without extending the current horizon or exceeding issue capacity. The forward pass used the resulting order to insert jobs at their earliest feasible times. This permits work to move later than its original issue time and permits order changes across original cycles. The previous fixed-chain compactor did not permit that full class of changes.

| ID | Base | Tie order | Passes | Actual cycles | Scratch words |
|---|---|---|---:|---:|---:|
|B01|Native|Native|1|980|1499|
|B02|Native|Native|2|980|1500|
|B03|Native|Dependence tail|1|980|1483|
|B04|Native|Dependence tail|2|980|1491|
|B05|Paired slope|Native|1|980|1499|
|B06|Paired slope|Native|2|980|1499|
|B07|Paired slope|Dependence tail|1|980|1491|
|B08|Paired slope|Dependence tail|2|980|1515|

B03 moved 8587 native jobs earlier and 955 later, including the charged pause in the job count. The audit checked concrete cross-cycle order reversals against the saved native model and candidate timing. Two passes did not improve cycles and sometimes increased scratch.

The best result did not require either slope rewrite. Its engine counts are unchanged from the native control:

| Engine | Instructions |
|---|---:|
|Load|1888|
|Flow, including pause|945|
|VALU|5800|
|ALU|11524|
|Store|32|

### The one-cycle mechanism

The native schedule issued its first gather at61 and its last at969. Cycle965 contained no gathers and no other loads. That was a two-slot hole in the gather stream.

B03 kept the first gather at61 and moved the last to968. Its1816 gather instructions occupy both load slots continuously from61 through968. The independent artifact audit checked this count and interval directly.

| Event | Native | B03 |
|---|---:|---:|
|First gather issue|61|61|
|Last gather issue|969|968|
|Store29 issue|980|975|
|Store31 issue|980|979|
|Pause issue|980|979|
|Complete execution cycles|981|980|

Issue times are zero-based. The result closes the late gather hole rather than starting the gather stream earlier. It does not establish that980 is a global lower bound.

B03 program digest:

```text
61b77f7620d82be1edc1765406cabc5d490eba1408ac99b6016e2972bdb695be
```

## The complementary slope effects did not compose

In the preceding pilot, the block30 reversed slope edit advanced store31, while the block31 edit advanced store29. Combining the two edits under native scheduling lost those separate effects:

| Schedule | Store29 issue | Store31 issue | Actual cycles |
|---|---:|---:|---:|
|Native control|980|980|981|
|Prior block30-only slope|980|979|981|
|Prior block31-only slope|979|980|981|
|Paired slope|981|984|985|

Structural and algebraic sharing tied at985/1473. The paired graph used11533 ALU instructions, nine more than native, with the other engine counts unchanged. Counts reflect actual native engine selection, not only source-expression counts.

Backward/forward reordering recovered the paired graph to980, but it did not beat the unchanged graph in cycles or best scratch. Complementary terminal effects are a useful hypothesis filter, not evidence that improvements add.

## The deadline approximation was too weak where needed

This arm used a derived resource-tail heuristic, not the complete clustered-VLIW scheduling algorithm. Each tail combined dependence depth with capacity lower bounds on the set of unique proper descendants. Flow demand included the separate pause cycle. Successor bounds propagated backward. Deadlines were then used as priorities, either directly or blended with native issue times.

The descendant-work bound strengthened118 jobs in each base graph. It strengthened no job originally scheduled at or after900. The largest improvement was at an early shared producer, whose path tail197 became a resource tail966. Thus the added bound mostly described early shared work rather than distinguishing late competitors.

All eight resulting allocations exceeded1536 words. Scratch ranged from1553 to2666. The pure dependence-tail comparison also overflowed. Their timing lengths are recorded only as abstract schedule diagnostics; none was lowered or executed.

This rejects the tested approximation and storage-insensitive serial priorities as an immediate solution. It does not reject resource-aware deadlines generally. A more useful version would need to account for competing work outside each job's descendant set and control live storage.

## Verification receipt

- Four full control reservations passed: symbolic/guard checks, original native981, isolated native981, and the published980 timing replay. Original and isolated native programs agreed exactly. Published replay used a freshly generated unchanged graph, fresh allocation and the published digest.
- Algebra checks covered128 symbolic corners, cross-axis coefficient reuse, the scalar reduction from three new differences to two, and a wrong-slope mutation.
- Resource tails passed all1133 feasible assignments among6144 enumerated assignments for24 deterministic four-job DAGs. A fan-out control separated resource tail4 from path tail2. An overstated bound failed its control.
- A fully charged executable toy improved from six to five cycles while moving one job later. Missing-edge, dependency-time and capacity mutations were rejected.
- Both native and retiming allocation paths rejected injected1537/1545-word results before lowering. Zero budget rejected before construction. Corrupting the encoding constant failed actual output comparison.
- Every executed candidate passed independent graph, capacity and lane-owner checks with fresh allocation. Frozen execution checked outputs, all non-output memory, and complete charged cycle counts.
- Screens comprised30 seed executions and50 pattern executions. B03's conditional gate added107 executions. Full-kernel controls added14 successes; the scheduling toy added two. The expected corrupted-program failure is separate.
- The read-only audit checked all18 candidate timings, ten allocated programs, eight pre-lower rejections, saved model/timing projections, addresses, lane ownership, program digests, engine counts, pause placement and genuine order reversals.

The run took53.755 seconds, including controls and conditional verification. This timing excludes automatic production plan discovery. The run used the published discovered configuration as an experimental control, so it does not establish a replacement production compilation time.

The process used a2GiB address-space cap. There were zero solver queries, no installation, and no production changes. All24 reservations were consumed: four controls, eighteen candidates and two conditional reconstructions. There were no retries or reopened historical budgets.

## Decision

Retain the backward/forward scheduler for further research. Do not add more passes merely because the first pass helped. The first pass already matched980 across both tested graph families, and a second pass did not reduce execution time.

A future finite program could test this scheduling method on graphs with a shorter final hash path. That would test a different combination than restarting the old979 solver query. This program did not authorize or run that follow-up. Production integration also needs its separate source-only discovery and full verification gates.

Workspace: `/tmp/perf-resource-order.HM8PpA/`. Read-only audit: `python /tmp/perf-resource-order.HM8PpA/audit.py`. Full models, timings, addresses, programs and driver sources remain there. The repository preserves the scheduler implementation and result provenance, but not a self-contained full-run archive.

No commit or push was made.
