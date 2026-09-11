# Promotion of the rebuilt 1,076-cycle kernel

## Result

The normal `KernelBuilder.build_kernel` entry point now produces **1,076 cycles with 1,236 scratch words** for the default benchmark. This leaves 300 words free and saves six cycles over the retained legacy implementation.

The compiler is self-contained in `kernel_compiler.py`. It imports machine constants from `problem.py`, uses only the Python standard library, and never executes the simulator or examines runtime tree/input values during generation. No saved site list, emitted program, temporary import, solver package, or test adapter is required.

## Automatic cache selection

The production selector starts with no depth-4 caches. It evaluates candidate sites using full scheduling and allocation costs. Candidates that exceed scratch cannot win. Each admission scan stops early after a candidate saves four cycles, the issue budget of one eight-lane gather on the two-slot load engine. This is a heuristic stopping rule, not a bound on possible gains.

The selector permits at most sixteen admissions, followed if needed by exchanges between a block's first and repeated depth-4 visits. It stops after reaching the 1,076-cycle target. Canonical site scores are memoized within the search; complete programs for rejected candidates are not retained. The implementation bounds the search at 921 unique plans.

The current search evaluates 222 plans and recompiles its winner once for emission. Its twelve selected sites are:

```text
(2,15), (4,15), (5,4), (5,15), (6,4), (6,15),
(7,4), (8,4), (9,4), (11,4), (17,15), (29,15)
```

These positions are outputs of the selector, not hardcoded generator inputs. Scheduler policy and search limits are benchmark-tuned, and the new path is explicitly scoped to that benchmark.

A preliminary exhaustive-admission selector recovered 1,076 cycles in 1,233 scored plans, including general swaps. A singleton-shortlist variant stopped at 1,080. The retained early-stop variant recovered 1,076 in 222 plans without a saved seed configuration. The preliminary variants remain disposable experiments; their options are not included in production.

## Compiler and entry point

The compiler retains the prototype's encoded values, mirrored indices, fused affine hash stages, lane-ready ALU/VALU choices, and load/flow constant alternatives. It schedules single-assignment values before coloring scalar and vector lifetime intervals. Lifetimes include partial writes and final consuming lanes. Reads precede cycle-end writes, so a last read may share a cycle with reuse of its storage.

The compiler conservatively reserves the scalar-seven dependency for both constant forms before greedy instruction selection. Actual immediate loads do not read that anchor. The independent lane checker distinguishes the two forms. All runtime initialization and selection work remains in the emitted program.

Only height 10, 2,047 nodes, batch 256, and 16 rounds with default tuning knobs use the new path. Other shapes and explicit overrides call the existing generator. `KernelBuilder._build_legacy_kernel` retains the 1,082-cycle benchmark implementation unchanged.

The completed compilation is cached as immutable tuples. Every builder gets new instruction dictionaries and slot lists. Mutating one builder cannot alter the cached result or another builder's program.

## Build cost

| Measurement | Observed result |
|---|---:|
| Cold build, verifier process | 25.457 seconds |
| Cold build, fresh process | 23.450 seconds |
| Cold build, source-only directory | 23.903 seconds |
| Cached build in the same process | 0.0047 seconds |
| Peak resident memory, fresh processes | 63,068 KiB |

Cold compilation is substantially slower than the preceding generator. This cost is paid once per process and is separate from the 1,076 simulated cycles. There is no persistent disk cache. These measurements describe this host and a few observed runs, not portable timing guarantees.

Both fresh processes produced the same instruction digest despite different Python hash seeds. The isolated directory contained only `perf_takehome.py`, `kernel_compiler.py`, and `problem.py`. Generation also succeeded with runtime input-generation, simulator construction, and the legacy module's reference-kernel entry points replaced by functions that raise on use.

Instruction SHA-256 for the verified result:

```text
a1cedda0acceb4eada28ae1b14aad2898e768370e2028ca5febe9f3ea377ddbe
```

## Verification receipt

The production entry point passed:

- All nine unchanged frozen submission tests at 1,076 cycles.
- The supplementary verifier with its default ceiling tightened to 1,076.
- One hundred generated inputs, five asymmetric bit patterns, nine other shapes, and three non-benchmark performance ceilings.
- One hundred additional full-width random inputs against the frozen reference, including pause-enabled execution.
- Physical lane ownership, address bounds, capacity checks, and dependency-corruption rejection.
- Frozen rejection of a corrupted flow constant; the supplementary load-constant mutation also remained effective.
- Explicit fallback tests for group size, round tile, and selection-bank overrides.
- An executed legacy control at 1,082 cycles, rejected by the stricter promotion ceiling.
- Fresh-process determinism, source-only generation, and cached-program mutation isolation.
- Ruff lint/format checks, diff checks, and immutable simulator/test checks.

The supplementary scheduler-unit checks still target the legacy physical scheduler. `scripts/verify_compiler.py` independently checks lane identities for the new compiler. Deterministic output hashes are supporting evidence, not the correctness oracle; the frozen simulator/reference remains the execution oracle.

Rerun from the repository:

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
python scripts/verify_compiler.py
ruff check perf_takehome.py kernel_compiler.py scripts/verify_retry.py scripts/verify_compiler.py
ruff format --check perf_takehome.py kernel_compiler.py scripts/verify_retry.py scripts/verify_compiler.py
git diff --check
git diff --exit-code 5452f74 -- tests/ problem.py
```

The compiler verifier deliberately performs three cold builds. Its running time is therefore longer than a single submission-suite run. Raw development receipts are under `/tmp/perf-promote.xgMSA5/`; the rerunnable checks do not depend on that directory.

## Limits

The contract remains root-starting traversals and final values only. Arbitrary non-root starts and final-index equivalence are not supported. The selector is bounded and heuristic, not an optimal joint scheduler/allocator.

The emitted stream contains 2,019 load, 912 flow, 6,280 VALU, 12,527 ALU, and 32 store instructions. Its largest capacity-only bound is 1,047 cycles. The legacy graph's 1,074-cycle bound does not apply to this graph, and neither bound proves challenge-wide optimality.

No frozen tests or simulator files changed. The accompanying experiment notes preserve the pre-promotion results and link to this receipt. No external challenge submission was made.
