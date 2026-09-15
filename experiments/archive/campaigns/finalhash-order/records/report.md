# Final-hash reordering reaches 979 cycles

The eight-case pilot produced an experimental program at **979 cycles / 1463 scratch words**, with no solver. This is one cycle faster and two words smaller than published production at 980/1465.

The best candidate, F08, rewrites the final hash for blocks 29 and 31 and applies one backward/forward pass with dependence-tail tie order. It passed 100 full-width seeds, five asymmetric patterns, two fresh oracle-blocked reconstructions, and the unchanged nine-test frozen suite through a replay adapter. An artifact audit also passed. Production was not changed, and automatic discovery and full promotion gates remain outstanding.

## Fixed matrix

The [protocol](finalhash_order_program.md) allowed eight candidates, four controls and two conditional reconstructions. Every candidate used the published discovered configuration as an experimental control. Only the final-hash block set and scheduling tie order varied. There were no cache changes, slope tiles, extra passes or solver calls.

| ID | Final-hash blocks | Tie order | Native timing span | Actual cycles | Scratch words |
|---|---|---|---:|---:|---:|
|F01|None|Native|981|980|1499|
|F02|None|Dependence tail|981|980|1483|
|F03|31|Native|984|979|1513|
|F04|31|Dependence tail|984|Not executed|1537|
|F05|29|Native|989|980|1491|
|F06|29|Dependence tail|989|980|1483|
|F07|29,31|Native|988|979|1471|
|F08|29,31|Dependence tail|988|979|1463|

Native timing spans describe the generated schedules before justification. The rewritten native schedules were not separately allocated or executed. F04 had a 979-cycle timing assignment but exceeded the 1536-word limit. It was rejected before lowering or execution and is not a legal 979-cycle result.

F01 and F02 reproduced the preceding pilot's B01 and B03 programs exactly, including cycles, scratch, instruction counts and program digests. The scheduling implementation was byte-identical to the [published experimental scheduler](resource_order_scheduler.py).

## Why the cycle disappeared

The earlier scheduler result removed the late gather hole. This pilot kept that improvement and shortened the final computation.

```text
                              F02 control       F08
First gather issue                 61            61
Last gather issue                 968           968
Block 31 gather-to-store path      11            10
Block 31 store issue              979           978
Final pause issue                 979           978
Complete execution cycles         980           979
```

Issue times are zero-based. All eight timing assignments have 1816 gathers occupying both load slots continuously from cycle 61 through 968. The seven executable programs preserve the same engine counts: 1888 loads, 945 flow instructions including pause, 5800 VALU instructions, 11524 ALU instructions and 32 stores.

The final-hash identity is:

```text
(u XOR (u >> 16)) XOR C
    = (u XOR C) XOR (u >> 16)
```

The existing compiler transformation computes the constant XOR and shift on separate branches. It also changes the final shift's preferred engine. The audit independently traced the last gather lanes through the saved graph to block 31's store. Both the dependency distance and observed tail fell from 11 to 10 cycles. Block 30 retained its 11-cycle tail and stored at 975. F08 stored block 29 at 974.

Rewriting block 29 alone did not improve cycles. In combination it improved storage enough to make the dependence-tail variant legal: F04 needed 1537 words, while F08 needed 1463. This is a measured interaction between the graph, schedule and allocation, not a general claim that this rewrite saves 74 words.

The native rewritten schedules looked worse, at 984 through 989 cycles. Screening them only on those timing spans would have missed the successful combinations. The relevant score is complete execution after reordering and fresh allocation.

## Verification and limits

The verified contract is root-starting traversal with height 10, 2047 nodes, batch 256, 16 rounds, one core and VLEN 8. Final values are the outputs; other memory is preserved. General non-root and final-index equivalence is not established.

All fourteen reservations were consumed, and the manifest is closed.

- Four controls checked original and isolated native 981/1465 programs, the published 980/1465 replay, symbolic identities, a scheduling toy, and guard sensitivity. Original and isolated native programs matched exactly. Published replay used a fresh unchanged graph and fresh allocation.
- The final-XOR proof checked zero and all 32 basis words. Both expressions are affine over GF(2), so these 33 cases characterize the identity. A mutation shifting the XOR-adjusted value failed the control. Full-kernel execution checked the actual emitter wiring.
- Inherited guards rejected missing dependencies, illegal timing, over-capacity bundles, and injected 1537/1545-word allocations before lowering. Zero budget rejected before construction. Corrupting the executed encoding constant produced an output mismatch.
- All seven feasible candidates passed three full-width seeds and five asymmetric patterns, for 56 screen executions. Each used fresh allocation and independent lane-owner checks. Execution checked complete cycle counts, output values, and preservation of all non-output memory.
- F08 passed another 100 full-width seeds and five patterns. Two new same-process reconstructions matched its program and scratch exactly and each passed an additional seed. Named simulator, input-generation and reference entry points were blocked during reconstruction, and a positive guard check confirmed the blocker was active.
- The unchanged nine-test frozen submission suite passed and observed 979 cycles. Its adapter replayed the experimental program. It did not exercise the production builder or automatic plan discovery.
- The read-only audit checked all eight timing assignments, four native graphs, seven allocated programs, the pre-lower rejection, physical lane ownership, instruction counts, digests, final pause, and final-gather ancestry and path lengths. It generated or executed no candidates.

The 36.749-second run included controls and conditional verification. It excluded automatic production plan discovery. The process had a 2 GiB address-space cap and used no solver.

The [receipt](finalhash_order_receipt.json) preserves the full matrix, reservations, control results, verification records and source/artifact hashes. F08's program digest is:

```text
d71b7cc458e45d9ae400faf7cbd525bafa531d5c23d6f10d84f3706d60143848
```

Workspace: `/tmp/perf-finalhash-order.eZag32/`. The read-only audit is `python /tmp/perf-finalhash-order.eZag32/audit.py`. Full driver sources, models, programs, timings and addresses remain in that workspace. The repository receipt is not a self-contained full-run archive.

## Decision

The pilot succeeded at its benchmark execution objective. Keep F08 as the best experimental result and stop this search. The next stage is source-only production discovery and the complete promotion suite, under separate authorization. The existing production program remains 980/1465.

The older 979 solver query remains an out-of-memory unknown for its own graph and constraints. This constructive result uses a different graph and scheduling method. It neither changes that historical solver outcome nor proves global optimality.

No historical budget was reopened. No production file, test, frozen reference or simulator changed. No commit or push was made during this pilot.
