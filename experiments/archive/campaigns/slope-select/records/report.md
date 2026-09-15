# Slope-select pilot: useful local changes, no cycle incumbent

The sixteen-case pilot completed without a candidate at 980 cycles. Best was 981 cycles and 1473 scratch words. Published production remains 980/1465, and the unchanged native experimental control remains 981/1465. No production change or solver query ran.

Slope-select improved one matched tensor configuration from 984 to 981 cycles. In reversed order, it retained 981 cycles while reducing scratch from 1481 to 1473 words. Algebraic coefficient reuse removed one scalar instruction from each reversed tensor configuration, but changed neither cycles nor scratch.

## Scope and results

The fixed matrix used blocks 30 and 31, round 14, tile 0. It crossed tensor/slope evaluation, natural/reversed bit order, and structural/algebraic coefficient reuse. All sixteen configurations were feasible and passed three full-width seeds plus five asymmetric patterns each.

Both reuse policies produced the same cycles and scratch in every row below. The complete sixteen-row matrix and source hashes are in the [receipt](slope_select_receipt.json). The [protocol](slope_select_program.md) fixes the budget and gates.

| Block | Bit order | Tensor cycles / words | Slope-select cycles / words | Slope cycle delta |
|---|---|---|---|---:|
|30|Natural|984 /1481|985 /1481|+1|
|30|Reversed|981 /1481|981 /1473|0|
|31|Natural|984 /1481|981 /1481|-3|
|31|Reversed|981 /1481|981 /1473|0|

The reversed structural tensor configurations exactly reproduced the prior S+A18 and S+A16 programs, including their digests, engine counts, cycles and scratch. The new comparison therefore measures changes against the previous implementation rather than a shifted baseline.

## What changed in the computation

For normalized bits s,t and arbitrary runtime-loaded encoded node words a,b,c,d, the new lookup evaluates:

```text
h     = b-a
v0    = c-a
v1    = d-b
base  = FMA(s,h,a)
slope = SELECT(s,v1,v0)
y     = FMA(t,slope,base)
```

Every difference and broadcast is charged. The online evaluation uses two VALU instructions and one flow instruction. The select operates on coefficients before the final FMA, rather than selecting the final result.

The algebraic pass recognizes signed linear forms modulo2^32. For example, it can replace `(d-b)-(c-a)` with `(d-c)-(b-a)` using native pair differences. It considers existing forms, one-step combinations, and five fixed mixed-difference recipes. It does not inspect node values, distribute XOR through addition, change broadcast placement, or optimize the whole IR.

For reversed tensor at block 31, structural versus algebraic sharing changed scheduled ALU work from 11527 to 11526 instructions. VALU work remained 5803. Relative to native, both tensor variants used 944 flow instructions instead of 945. Both completed in 981 cycles. Block 30 likewise lost one scalar instruction, from 11535 to 11534, with no timing or scratch change. The raw sharing-hit counters have different meanings between implementations and are not compared.

## Timing explains the limit

Cycle labels below are zero-based issue times. All four coefficient operands were ready by cycle17 in every candidate. Their construction was not waiting on late data.

For natural-order slope-select at block31:

```text
first bit ready              920
slope SELECT issues          922
second bit ready             932
base FMA issues              942
final FMA issues             943
native final SELECT issued   944
```

The flow instruction moved earlier, but the base FMA waited22 cycles after its operands were ready. The final result moved only one cycle earlier than native. Complete execution tied the native981 result, while improving the matched natural tensor result by three cycles.

At block30, natural-order slope-select also moved its select early, to913. Its base FMA did not issue until943, despite its bit arriving at912 and coefficients being ready by14. The final result issued at944 and the complete program regressed to985. This rejects the idea that moving the select early is sufficient by itself. The reason for the scheduler's delay was not established by this pilot.

Reversing the bits changes which input really arrives first. In reversed block31 slope-select, s was ready at931 and t at920. The slope select issued at939 and the final FMA at940, four cycles earlier than native. Completion still remained981. The label "first bit" denotes evaluation order, not an assumed arrival advantage.

Earlier local work also hit a later limit. Reversed block30 tensor and slope variants moved the last gather from native969 to968. Block31's store moved from980 to979, but block29 still stored at980. Reversed block31 slope-select instead left block31's final store at980. These are observed schedules, not proofs that a different scheduler cannot improve them.

Engine counts can shift between VALU and scalar ALU after a graph change. For example, reversed block30 slope-select used5800 VALU and11533 ALU instructions, while reversed block31 used5801 and11525. Both used945 flow instructions. Comparing only the source expression's operation count would miss that exchange.

## Verification and limits

- 128 symbolic corner checks covered two source-ID layouts, two native-pair availability states, both shapes, both bit orders and both reuse policies. The independent interpreter checked all eight output lanes. Sharing controls confirmed cross-axis mixed-coefficient reuse and the scalar reduction from three new differences to two. A wrong-slope mutation failed equivalence.
- Original and isolated native builds agreed exactly at981/1465. The published timing replay used a fresh unchanged graph and fresh allocation, produced980/1465 with the expected digest, and passed three seeds plus five patterns. Saved timing was used only for this control.
- Every candidate passed independent native dependency/capacity validation, fresh allocation and lane ownership checks before execution. The frozen reference checked outputs and preservation of all non-output memory.
- Candidate executions totaled48 seed cases and80 pattern cases. Controls added14 successful executions. A corrupted encoding constant failed the actual output comparison.
- Injected1537/1545-word allocations failed before lowering. A zero-budget reservation failed before construction and did not append to the ledger. Solver entry points were patched to fail if called.
- A read-only audit checked20 unique reservations, the complete matrix, source hashes, artifact digests, physical capacities, scratch addresses, pause placement and matched comparisons. It constructed and executed no new kernels.

Runtime was 22.809 seconds for the fixed run. All sixteen candidates were feasible; none qualified for the conditional<=980 verification gate. The two unused reconstruction slots expired. No100-seed winner gate, frozen submission suite, source-only production discovery or promotion was run for these variants.

## Decision

Keep slope-select as an experimental lookup option and retain the algebraic coefficient normalizer. Neither is justified as a production change by these results. The next useful question is why ready base FMAs wait 22 to 31 cycles, and whether a change can advance the actual last stores without disturbing other walkers. A materialization sweep, broader site search or another scheduling program needs a new finite authorization.

Workspace: `/tmp/perf-slope-select.SzgnoH/`. Read-only audit: `python /tmp/perf-slope-select.SzgnoH/audit.py`. The source manifest covers the isolated generator and original controls. Full programs and logical schedules remain in that temporary workspace; the repository receipt preserves results and provenance, not a self-contained executable archive.

All budgets are closed. No commit or push was made.
