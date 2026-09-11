# Promotion of the 1,052-cycle compiler

## Result

The normal `KernelBuilder.build_kernel` entry point now produces **1,052 cycles using 1,457 of 1,536 scratch words**. It saves 24 cycles against the previous production compiler and reproduces the [verified technique-port prototype](technique_port_results.md) exactly.

Generation is self-contained. No saved cache sites, instruction streams, temporary modules, foreign compiler imports, or runtime tree/value inspection are used. The unchanged dispatch limits the new path to height 10, 2,047 nodes, 256 inputs, 16 rounds, one core, eight lanes, and default tuning knobs. Other shapes and explicit overrides retain the unchanged legacy generator.

## Implementation and selection

`kernel_compiler.py` shares its intermediate representation, scheduler, allocator, and lowering between two cost models. The advanced model enables fused hash stages 2/3, mixed arithmetic/select leaves at depths 3 and 4, stored normalized branch bits, reversed depth-3 bit order, and the address rewrite at block 0, round 3. `kernel_lookahead.py` adds one-cycle, eight-operation engine forecasts with at most one decision per cycle. Retroactive packing is not included.

Selection has two bounded stages:

1. The retained baseline planner starts with no depth-4 caches. Its cheaper greedy schedule evaluates 222 plans and regenerates the previous 1,076-cycle, 1,236-word program and twelve cache sites.
2. The advanced planner scores all 64 one-site toggles, then repeats around the best result. Including the control and removing duplicate plans, this evaluates 128 plans. It selects fourteen sites and emits the 1,052-cycle program.

The total is 350 scored plans, plus final emission for each cost model. The general search limits are 921 baseline and 128 advanced plans. This two-stage search is a heuristic, not a global optimization claim. The source contains the placement and selector rules, but no list of winning cache sites.

Only small scores survive candidate evaluation. Both completed programs are memoized as immutable tuples; each builder receives fresh mutable bundles. There is no disk cache. A scratch-infeasible final plan raises before lowering. A real 64-site plan requiring 1,740 words exercised that rejection without executing the invalid schedule.

## Normal-path verification

These commands passed on the integrated sources:

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
python scripts/verify_compiler.py
ruff check perf_takehome.py kernel_compiler.py kernel_lookahead.py scripts/verify_retry.py scripts/verify_compiler.py
ruff format --check perf_takehome.py kernel_compiler.py kernel_lookahead.py scripts/verify_retry.py scripts/verify_compiler.py
git diff --check
git diff --exit-code 5452f74 -- tests/ problem.py
```

The unchanged frozen suite passed all nine tests at 1,052 cycles. The supplementary verifier passed 100 generated inputs, five bit patterns, nine other shapes, three non-benchmark performance ceilings, scheduler hazards, pause/store completion, and corruption rejection.

The compiler verifier additionally checked 100 full-width inputs, logical lane ownership, slot/address limits, three explicit-override fallbacks, and cached-program isolation. Fresh source-only generation copied just `perf_takehome.py`, `kernel_compiler.py`, `kernel_lookahead.py`, and `problem.py`. It reproduced the same digest under hash seed 17 with runtime-data and reference helpers forbidden. A separate fresh build used hash seed 0.

The same 1,052-cycle gate rejected the executed 1,076 and 1,082 controls after checking their outputs. The regenerated 1,076 instruction digest is unchanged from the preceding release. Moving a vector load before its address definition failed the lane checker. A corrupted flow constant and swapped selector branches each failed with `Incorrect output values`.

The first verification attempt exposed an outdated mutation target, not a kernel failure. The old test flipped a bit in the first large flow constant. That constant is now the address multiplier -2, so the mutation caused an out-of-range load. The final test changes -2 to 0 instead, keeping the address in memory and requiring a failed value comparison. The complete compiler verifier passed after this correction.

## Cost and limits

| Measurement | Result |
|---|---:|
| Compiler verifier's initial cold build | 73.796 seconds |
| Fresh hash-seed-0 build | 74.136 seconds |
| Fresh source-only hash-seed-17 build | 74.678 seconds |
| Same-process memoized build | 0.0034 seconds |
| Fresh-process peak resident memory | 65,980 KiB |
| Simulated cycles / scratch words | 1,052 / 1,457 |

The prior production compiler took about 23 to 25 seconds cold. This promotion spends more compilation time to save 24 simulated cycles. The prototype's roughly 0.4-second selected-program compile excluded search and was not a prediction of production cold-build cost.

Instruction counts are 2,003 load, 786 flow, 5,794 VALU, 11,499 ALU, and 32 store operations. The capacity-only bound is 1,002 cycles for this stream; it does not establish attainability or challenge-wide optimality. The contract remains root starts and final values, not arbitrary starting indices or final-index equivalence. The complete compiler is not formally proved.

Instruction SHA-256:

```text
ca588b18f9790385cc509caf5bc5c57b85bff1ab01029766195a48cdd07b4a76
```

Logs are under `/tmp/perf-promote-1052/`: `normal_build.json`, `submission.log`, `supplementary.log`, `compiler.json`, `compiler.err`, and `scratch_guard.log`. They are evidence artifacts, not runtime dependencies. The production checks above remain runnable from a fresh checkout.

The user authorized promotion, commit, and push. No external challenge submission was made. `tests/`, `problem.py`, and `perf_takehome.py` remain unchanged.
