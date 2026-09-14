# Automatic 980-cycle compiler promotion

The normal `KernelBuilder` entry point generates a **980-cycle kernel using 1,465 scratch words** for height 10, 2,047 nodes, batch 256, and 16 rounds. The preceding production compiler used 1,041 cycles and 1,458 words. Tests and simulator sources are unchanged.

The [receipt](promotion_980_receipt.json) includes source and evidence hashes. Raw verification outputs are in [promotion_980_evidence](promotion_980_evidence/).

## What produced the gain

| Step | Cycles | Mechanism |
|---|---:|---|
| Previous automatic compiler | 1,041 | Startup-aware scheduling and earlier hash/lookup rules |
| Cache search | 984 | Compare all single-site toggles, then a bounded swap neighborhood |
| Profile/cache coupling | 981 | Select arithmetic lookup-pair counts together with a cache change |
| Late lookup conversions | 981 | Move two late selections from flow to arithmetic |
| Exact suffix repair | 980 | Solve coupled issue times, then allocate scratch afresh |

The cache search begins with the existing compiler's empty-plan discovery. It does not load the historical winning sites. The subsequent graph search selects late lookup conversions from native issue times and dependency structure. It also compares final-XOR rewrite locations, but the winning path uses no such rewrite and no ordinal scheduling edits.

For normalized branch bits, `no + bit * (yes - no)` is equivalent to selection under wrapping arithmetic. This moves work away from the single flow slot. It does not guarantee fewer cycles by itself: the selected converted graph still needs 981 cycles under greedy scheduling.

The selected exact problem repairs the 32-cycle native suffix starting at cycle 949. Earlier instruction times and native engine choices remain fixed. Timing displacement is bounded by eight cycles. Dependency propagation and mandatory engine-window checks reject impossible scopes before solving. The successful component query used 527 free variables and 5,979 potential capacity memberships. Z3 found SAT in 72.15 seconds.

The compiler validates the complete assignment, reconstructs logical instructions without deleting empty cycles, allocates fresh scratch, and checks physical lane ownership before lowering. The final store and pause are charged. A timing witness alone is not a performance result.

## Discovery versus experimental replay

An earlier selected-timing experiment reached 980 cycles with 1,449 words. This promotion uses a different graph and schedule and needs 16 more words. Its digest is:

```text
c17788082bd3757c95f02bd743582ff1acd3f55c56e3326d9fc72e65da7ba5bc
```

The development continuation read only its own newly generated cache checkpoint. That component test was not treated as proof of source-only production discovery. A later normal-entry-point cold build and two isolated cold rebuilds independently rediscovered the result without configuration or timing files. The earlier experimental program was executed separately as a verification control, not used as a compiler input.

## Verification

- All nine unchanged frozen submission tests passed at 980 cycles.
- Supplementary checks passed 100 generated inputs, five asymmetric patterns, nine other root-starting shapes, and three non-benchmark performance ceilings.
- Compiler checks passed 100 full-width inputs, explicit-override fallback, cached-program isolation, lane ownership, and dependency/constant/selector mutations.
- Repair checks passed three fresh allocations and rejected missing dependencies, duplicate lanes, and dependency-timing corruption.
- Injected 1,537- and 1,545-word allocations and a natural 1,719-word graph were rejected before lowering. A separate historical 1,545-word control also made zero lowering calls and was not executed.
- The performance gate rejected executed 981, 1,041, 1,042, 1,052, 1,076, and 1,082-cycle controls.
- Two source-only rebuilds at hash seeds 0 and 17 reproduced the same digest. Runtime/oracle entry points were blocked in the generator process. The separate solver worker consumes the generated abstract graph.
- Non-output memory preservation and co-issued store/pause completion passed.

The checks ran through `full_verify.py` in the isolated promotion workspace. It invoked the public builder, `scripts/verify_optimizer.py`, the unchanged submission suite, `scripts/verify_retry.py`, and `scripts/verify_compiler.py` in one process. The documented scripts can also run separately, at the cost of repeated cold compilation.

Local source review, targeted Ruff checks, Python compilation, source-hash checks, and diff checks completed the verification. This is tested implementation evidence, not a formal correctness proof.

## Build cost and limits

| Build | Seconds | Cycles | Scratch words |
|---|---:|---:|---:|
| Initial public cold build | 1,142.69 | 980 | 1,465 |
| Isolated cold build, hash seed 0 | 1,051.94 | 980 | 1,465 |
| Isolated cold build, hash seed 17 | 1,035.22 | 980 | 1,465 |
| Memoized build | 0.00658 | 980 | 1,465 |

The compiler used 1,951 score entries and one optimization query. Reconstruction and validation repeats add work beyond the score counter. The receipt preserves the compiler verifier's own `cold_seconds` field, but that script ran after the initial build in a warm process. The table above uses the separately recorded initial cold measurement.

The build dependency is `z3-solver==4.15.4.0`. Solver workers have a 2 GiB address-space cap and no wall-clock or CPU deadline. The compiler admits at most 4,096 score entries and four optimization queries per build. Unknown results fail explicitly. Missing or mismatched dependencies fail before search.

Actual instruction counts are 1,888 loads, 945 flow operations, 5,800 vector ALU operations, 11,524 scalar ALU operations, and 32 stores. The simple capacity-only lower bound is 967 cycles for this stream. It does not prove global optimality, nor does this promotion establish 979-cycle feasibility.

The supported semantics remain root-starting traversal and final output values. Non-root starts, final-index equivalence, arbitrary dimensions, and identical performance across other Python/platform combinations are not established.
