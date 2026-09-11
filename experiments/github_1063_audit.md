# Audit of the public 1,063-cycle fork

## Verdict

This audit preceded the [technique ports](technique_port_results.md) and their [1,052-cycle promotion](technique_promotion_results.md).

**Verified for the official benchmark.** The pinned fork executes in 1,063 cycles on our unchanged frozen machine. That is 11 cycles faster than our verified 1,074-cycle prototype. The audit found no benchmark-path test manipulation, debug dependence, runtime-input specialization, or hidden host-side computation of input-dependent results.

It is not a general-purpose replacement for our generator. Repeated tree wraps and non-vector-sized batches expose correctness failures. Its scheduler also returns incomplete programs on allocation failure instead of raising an error. These findings do not invalidate the reproduced benchmark result.

Source: [rubinownz111/1063-cycles-original-performance-takehome](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/tree/3b312194d61d22d71bd73127d8f3a70c422a445e), commit `3b312194d61d22d71bd73127d8f3a70c422a445e`.

## Reproduction and isolation

The fork's `problem.py`, `tests/frozen_problem.py`, and `tests/submission_tests.py` match ours byte-for-byte. The 3,176-line compiler was read before execution.

The foreign compiler ran inside Bubblewrap with a private network namespace, read-only source/system mounts, no home directory, a cleared environment, and CPU, memory, and wall-time limits. The sandbox mounted our tests and simulator, not the fork's copies. Its normal `KernelBuilder.build_kernel` entry point passed all nine frozen tests at 1,063 cycles.

For the independent checks, the compiler exported JSON instructions. A separate trusted process loaded those instructions and our frozen reference implementation without importing the foreign compiler. Compilation also succeeded with simulator construction, tree/input generation, reference execution, memory-image construction, and common random APIs replaced by throwing stubs. Fresh compiles under Python hash seeds 0 and 17 produced identical instructions.

| Measurement | Observed result |
|---|---:|
| Benchmark shape, height / batch / rounds | 10 / 256 / 16 |
| Cycles | 1,063 |
| Allocator peak and distinct scratch words touched | 1,465 |
| Scalar / vector pool words | 41 / 1,424 |
| Highest physical scratch address | 1,535 |
| Selected-program compilation, two fresh processes | 0.750 / 0.776 seconds |

The allocator places its pools at opposite ends of the scratch array. This is not a compact layout that can run in an array of only 1,465 words. Every address was within the actual 1,536-word machine limit. Compilation timings are local observations for the fork's fixed tuning choices, not measurements of its earlier optimization search.

Instruction SHA-256:

```text
6943d765e35dc1d4cf75bb15c3597bd28680cfa3a6d7dd2a4ffde382ffc14af9
```

The stream contains 1,991 load, 798 flow, 11,964 ALU, 5,999 VALU, and 32 store instructions. Its capacity-only bound is 1,000 cycles. This is not an optimality proof.

## Correctness and failure sensitivity

The independently executed benchmark passed:

- 100 full-width random tree/value inputs and 100 standard generated inputs.
- Five asymmetric bit patterns, with root-starting indices.
- Final-value comparison and preservation of every non-output memory region.
- Execution with debug disabled, pause handling enabled, and reversed engine iteration order.
- Instruction whitelist, slot-capacity, address-bound, and duplicate-write checks.

An instrumented compile attached logical writer/lane provenance to each physical instruction, including retroactive ALU expansions. It produced exactly the uninstrumented program. An independent checker then verified each read against its expected logical writer before committing that cycle's writes. Only scratch address 0 relied on an initial value.

Corrupted hash constants and swapped selector branches both failed with `output mismatch`. Moving a vector load ahead of its address definition failed the lane checker and actual execution. Poisoning the checker's initial-zero identity also failed. These controls demonstrate that the checks can reject relevant errors.

Z3 4.15.4 proved the default fused hash stages 2 and 3, normalized pair-difference selection, overflow-to-root constant fusion, and unsigned parity modulo 2 over wrapping 32-bit values. A wrong fused multiplier produced a counterexample, `X = 4158051080`. These are expression proofs; the complete compiler and allocator are not formally verified.

## Legality details

The [allocator reserves scratch word 0](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L739-L765) as a zero source. The frozen machine explicitly initializes scratch to zero, and the lane audit confirmed that this word is not overwritten. Using that defined initial state is not a simulator modification.

As a conservative check, prepending an explicit `const 0` instruction produced a 1,064-cycle program. It passed three full-width seeds and five patterns, still beating our 1,074 result even with that extra initialization cycle charged.

Table loads, pair differences, broadcasts, hash constants, and stores all execute as ordinary machine instructions. Compile-time specialization uses the public shape, fixed memory layout, and block/round positions. It does not use tree or value contents. Hardcoded strategy masks are benchmark tuning, not precomputed answers.

The comparison is limited to root starts and final values, matching our benchmark contract. Neither arbitrary starting indices nor final-index equivalence was established. Non-default experimental flags in the fork were not exhaustively audited.

## Findings outside the benchmark

Shapes below are written as height / rounds / batch. Seven of eleven supplementary shapes passed three full-width seeds each. Four failed:

| Shape | Observed failure |
|---|---|
| 3 / 9 / 64 | Compiler assertion |
| 4 / 12 / 128 | Incorrect output values |
| 10 / 23 / 256 | Incorrect output values |
| 10 / 16 / 257 | Incorrect output values |

1. **Repeated wraps are unsupported without a guard.** [`_round_depth`](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L2694-L2696) subtracts `height + 1` only once rather than taking modulo. Depths become wrong after the second wrap. This accounts for the first three failing shapes.
2. **Batch tails are silently dropped.** [`num_groups = batch_size // V`](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L2776-L2786) has no remainder path or rejection. The 257-element test leaves an element unprocessed.
3. **Scheduling failure returns a partial program.** The [stuck branch breaks, then returns the accumulated instructions](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L1338-L1370). A constructed operation needing at least nine scratch words with only eight available returned an empty program without raising. Its log still said `Scheduled 1 ops -> 0 cycles`. This did not occur in the benchmark, but makes instruction count alone an unsafe search score.

The seven passing shapes were 3/0/8, 3/1/8, 3/4/32, 4/5/32, 8/18/128, 10/11/256, and 10/22/256. They are bounded compatibility checks, not a generality claim.

## What is worth studying

The fork uses [two multiply-adds and XOR for hash stages 2 and 3](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L2572-L2610), [mixed multiply-add/vselect table leaves](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L2165-L2220), and [retroactive ALU packing](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L1063-L1140). Its [default concurrency cap is 20 groups](https://github.com/rubinownz111/1063-cycles-original-performance-takehome/blob/3b312194d61d22d71bd73127d8f3a70c422a445e/perf_takehome.py#L130), unlike our 32-context experiments.

Those are candidates for isolated experiments, not individually measured causes of the 11-cycle advantage. The audit ran no performance ablations and made no ports. Retain our production fallback rather than importing this compiler wholesale.

## Receipt and replay

Artifacts are in `/tmp/perf-1063-audit/`: `provenance.json`, `sandbox.sh`, `submission.log`, `export.py`, `export.json`, `seed17.json`, `slots.py`, `verify.py`, `verification.json`, `shapes.json`, `proofs.py`, `proofs.json`, `explicit_zero.json`, and `failure_probe.json`.

```sh
bash /tmp/perf-1063-audit/sandbox.sh tests/submission_tests.py
bash /tmp/perf-1063-audit/sandbox.sh /audit/export.py > /tmp/perf-1063-audit/export.json
AUDIT_HASHSEED=17 bash /tmp/perf-1063-audit/sandbox.sh /audit/export.py plain > /tmp/perf-1063-audit/seed17.json
bash /tmp/perf-1063-audit/sandbox.sh /audit/export.py shapes > /tmp/perf-1063-audit/shapes.json
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-1063-audit/verify.py
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-1063-audit/proofs.py
bash /tmp/perf-1063-audit/sandbox.sh /audit/failure_probe.py
```

Replay depends on those temporary files, the pinned clone, and the isolated solver environment. The compiler and machine files remained unchanged. Our then-uncommitted four-frontier report was preserved. No code adoption, commit, push, or external submission occurred during the audit.
