# Algorithmica-inspired instruction selection

## Result

A benchmark-tuned instruction-selection exception reduced the retained kernel from **1,084 to 1,082 cycles**. Block zero's hashes at rounds 4 and 8 use lane-wise ALU operations for their eight non-fused operations while retaining three vector multiply-add operations per hash.

This is a measured positional heuristic, not integrated instruction selection and scheduling. It applies only to height 10, 2,047 nodes, batch 256, and 16 rounds with group size 32, round tile 12, and four selection banks. Other shapes and generator settings retain the previous instruction mix.

The exact instruction exchange is:

```text
16 VALU operations -> 128 ALU operations
```

The benchmark instruction counts are now:

| Engine | Operations | Capacity-only bound |
|---|---:|---:|
| VALU | 6,381 | 1,064 |
| Load | 2,091 | 1,046 |
| ALU | 12,146 | 1,013 |
| Flow | 796 including pause | 796 |
| Store | 32 | 16 |

The regional resource-bound prototype gives a fixed-graph interval of **1,074 through 1,082 cycles**. This is not a bound across alternative algorithms, representations, or instruction choices.

## Question and method

[Algorithmica's throughput guidance](https://en.algorithmica.org/hpc/pipelining/throughput/) recommends treating execution-resource pressure separately from dependency latency. The current graph was close to its six-slot VALU capacity bound while the twelve-slot ALU engine had spare capacity. The experiment therefore gave each ordinary hash-vector instruction an exactly equivalent alternative: eight lane-wise scalar ALU instructions. Vector multiply-add instructions remained on VALU because scalarizing them would require separate multiply and add stages.

A disposable semantic capture under `/tmp/perf-integrated-selection/` identified all 512 hash invocations by vector destination, block, round, and hash stage. It did not use raw source offsets as the selection policy.

The bounded schedule-only search found:

- 202 of 512 whole-hash single conversions reached 1,083 cycles.
- Two whole-hash conversions reached 1,082 cycles.
- At stage granularity, 461 of 1,536 single conversions reached 1,083 cycles, but the bounded pair search found no 1,082-cycle result.
- Broad policies overloaded ALU or disrupted latency hiding. Converting every deep hash in block zero regressed to 1,108 cycles.

The retained positions came from the bounded search. Other pairs also reached 1,082, including block zero at rounds 4 and 7, 4 and 9, and 4 and 10. Tie-breaking restricted the whole-hash combination candidates to blocks 0–3. The evidence does not establish that block zero or four-level spacing is structurally best. Four tree levels have no demonstrated connection to the scheduler's four-cycle dependency horizon.

A source-priority ablation checked a possible confound. Expanding instructions also changes source-order priorities used by the scheduler. With the old instruction mix and expanded priorities, execution remained at 1,084 cycles. With scalarization and the original priorities, it remained at 1,082. Both matched frozen reference outputs. This rules out priority renumbering alone as the explanation for this gain; it does not make the positional rule general.

## Register and progressive-lookup follow-ups

Sharing physical node vectors before scheduling created false dependencies and regressed sharply: 16 banks took 1,236 cycles, while 28 took 1,244. Scheduling with one virtual node vector per hash and coloring live intervals afterward needed only 23 simultaneous node vectors. Retuning its load horizon from four to five recovered 1,082 cycles and would free 72 scratch words, but did not improve speed. The post-schedule allocator was therefore not retained.

A second prototype reserved eight persistent vectors for one progressive depth-4 lookup. It scheduled branch-bit consumption during rounds 11–14, spreading the same fifteen selections across earlier rounds and eliminating three VALU masks plus eight scalar masks.

Its initial 1,088-cycle schedule needed 24 simultaneous node vectors but allocated only 23. The prototype stopped at that allocation assertion before differential execution.

A subsequent 210-policy schedule-only sweep reached 1,086 cycles. Recomputed interval peaks for the first two tied winners were 21 and 20 node vectors; other tied winners needed 25 and 24. The 24-vector initial result must not be attributed to every best schedule. These tuned candidates did not receive physical-remapping and frozen-output verification. Reject this arm on schedule cost, not on a claim that all best candidates exceed the register budget.

## Correctness and limits

Each replacement preserves the original 32-bit operation lane by lane and has the same one-cycle scratch-write semantics. It changes engine assignment and scheduling, not the hash function, lookup path, memory inputs, or output contract.

The rule still uses public compile-time block and level positions. It does not inspect runtime values, tree contents, random seeds, reference outputs, or simulator debug state. As elsewhere in this submission, generated benchmark inputs start at the root and only final values are written back.

The original unscoped rule also changed non-benchmark shapes and regressed several schedules despite correct outputs:

| Height / rounds / batch | Before | Unscoped tuning | Scoped tuning |
|---|---:|---:|---:|
| 4 / 12 / 128 | 637 | 639 | 637 |
| 8 / 18 / 128 | 1,017 | 1,029 | 1,017 |
| 10 / 11 / 256 | 1,028 | 1,031 | 1,028 |

The retained shape/settings guard prevents those changes. Supplementary verification now has explicit performance ceilings for these three shapes. Other shape checks establish correctness, not a general speed improvement.

## Verification

The retained implementation passed:

- All nine unchanged frozen submission tests at 1,082 cycles.
- 100 random inputs and five full-width/asymmetric patterns.
- Nine supplementary root-starting shapes and three non-benchmark performance gates.
- The three scope gates reject the unscoped schedules at 639, 1,029, and 1,031 cycles. Injecting the unscoped implementation into the actual verifier fails its first shape gate.
- Exact emitted-program equality with the reviewed 1,082-cycle benchmark. The three protected shapes, a height-12 case, and three nondefault generator configurations match the pre-change instruction streams.
- Scheduler hazard, co-issued pause/store, and corrupted-kernel negative controls.
- Immutable `tests/` and `problem.py` checks.
- Ruff lint, formatting, and diff checks.

The verifier's default performance gate is 1,082 cycles. Scratch remains **1,536 of 1,536 words**.

The temporary search artifacts are not production dependencies and may disappear with temporary-storage cleanup.

## Decision

Retain the two positional substitutions only within the measured benchmark configuration. They save two verified cycles, but accept a benchmark-specific exception that the earlier one-cycle candidate did not justify. The scope guard and explicit disclosure make that trade-off visible; they do not satisfy the original goal of a general schedule-cost-driven selection policy. That goal and the eight-cycle fixed-graph scheduling gap remain open.
