# A 975-Cycle Kernel for Anthropic's Original Performance Take-Home

## Summary

This repository holds a kernel for Anthropic's original performance take-home that runs the benchmark in 975 cycles. The recorded scalar baseline takes 147,734 cycles, so the kernel is about 152 times faster. It uses 1,469 of the 1,536 scratch words.

A search-based compiler produces the kernel without calling a solver. Commit `1df789d` passed the unchanged nine-test submission suite and every supplementary verifier. Two isolated rebuilds from source alone reproduced the same program digest. A proof with the Z3 satisfiability-modulo-theories (SMT) solver shows that the emitted program matches the reference for every tree and input value on the benchmark shape, with traversals starting at the root.

Nobody has shown that 975 cycles is optimal. A resource bound gives at least 967 cycles for the current instruction stream, but that bound ignores dependencies.

## 1. Introduction

Anthropic's original take-home gave candidates four hours to speed up a tree-walking kernel on a simulated very long instruction word (VLIW) machine with single-instruction, multiple-data (SIMD) vector units. After Claude Opus 4 beat most human results, Anthropic switched to a two-hour version that started at 18,532 cycles. This repository uses that version's extra instructions and debugging tools, with the starter code reset to the slow baseline. Anthropic changed the starting point again after Opus 4.5.

Table 1 lists the model results Anthropic reported from the 18,532-cycle start. The runs had different lengths. The 975-cycle result in this repository is not a two-hour attempt.

**Table 1.** Model results reported by Anthropic.

| Cycles | Reported run |
|---:|---|
| 2,164 | Claude Opus 4 after many hours |
| 1,790 | Opus 4.5 casual run, about the best human result in two hours |
| 1,579 | Opus 4.5 after two hours |
| 1,548 | Sonnet 4.5 after many hours |
| 1,487 | Opus 4.5 after 11.5 hours |
| 1,363 | Opus 4.5 with an improved test setup |

Anthropic did not publish its best human result. The original README invited solutions below 1,487 cycles to performance-recruiting@anthropic.com and warned that the threshold could change with new models. This repository makes no hiring promise.

Table 2 points each reader goal to the relevant document.

**Table 2.** Document map.

| Goal | Document |
|---|---|
| See the result at a glance | [Technical summary page with diagrams](https://trav55555.github.io/original_performance_takehome/) |
| Build and check the result | [Appendix A](#appendix-a-build-and-verification-procedure), then the [verification guide](docs/verification.md) |
| Understand the current code | [Architecture and module map](docs/architecture.md) |
| Follow the project from 147,734 to 975 cycles | [Performance history and milestone ledger](docs/performance-progression.md) |
| Look up a technique or research result | [Technique and research wiki](docs/reference/README.md) |
| Inspect reports and raw evidence | [Experiment index](experiments/README.md) |

Historical notes are in [`docs/history/`](docs/history/README.md). Archived prototype code and old analysis scripts are in [`experiments/archive/`](experiments/archive/README.md). The trace viewer is in [`tools/trace/`](tools/trace/README.md). None of these are current compiler or verification guidance.

The repository root holds the submission entry point, the simulator, the production `kernel_*.py` modules and the environment files. The submission and the source-only rebuild import these modules by their flat names, so they stay at the root.

## 2. Symbols and Abbreviations

| Term | Meaning |
|---|---|
| ALU | Scalar arithmetic engine, 12 slots per cycle |
| VALU | Vector arithmetic engine, 6 slots per cycle |
| Load, store | Memory engines, 2 slots each per cycle |
| Flow | Control and selection engine, 1 slot per cycle |
| Bundle | The set of instructions issued in one cycle |
| Cache site | A tree lookup served from scratch instead of gathered from memory |
| Selector | The operation that picks a cached tree value; it runs on the flow engine or as VALU arithmetic |
| Scratch | The 1,536-word register file |
| SIMD | Single instruction, multiple data |
| VLIW | Very long instruction word |
| Z3 | The SMT solver used for the equivalence proof and the retained exact-scheduling tools |

## 3. Problem Description

The benchmark walks a height-10 tree of 2,047 nodes. A batch of 256 inputs takes 16 rounds. In each round, every input hashes its value with the current node's value, then moves to a child chosen by the hash. After a leaf it returns to the root. The kernel runs on one simulated core with eight SIMD lanes.

Each cycle offers the slots listed in Section 2. Within a cycle, every instruction reads the state from the start of the cycle, and writes land at the end. The challenge disables multicore on purpose. Raising `N_CORES` changes the benchmark and is not an optimization.

## 4. Method

The compiler searches over two choices for each candidate program:

1. Cache sites, which replace memory gathers with selection work.
2. Selectors to convert from flow operations to VALU arithmetic.

The compiler schedules each candidate graph backward, then forward, and keeps every instruction on its native engine. The forward pass tries three priority orders; one of them promotes the ancestors of the first 26 gathers. From the best schedule, the compiler finds the two blocks that finish last and tries final-hash rewrites on each block and on the pair. Each schedule receives a fresh scratch allocation.

Every choice comes from a generated graph and its measured schedule length. The compiler reads no saved configuration, timing table or physical program, and it never sees runtime input values. Setup, constants, broadcasts, loads, stores and the final pause all count toward the cycle total.

Removing instructions from one engine often adds contention on another. Caching trades gathers for selection work, and arithmetic selectors move work from flow to VALU. Only the complete schedule shows whether a change helps.

If the search finds no legal program at 975 cycles or fewer, compilation fails rather than return a slower kernel. Other tree shapes and explicit tuning overrides fall back to the legacy generator, which takes 1,082 cycles on the benchmark shape.

## 5. Results

The verified build scored 1,963 candidates out of a budget of 4,096 and emitted a 975-cycle program that uses 1,469 scratch words. A cold build took 15 to 16 minutes, because the compiler keeps no disk cache and every new Python process searches again. A second build in the same process took about 4 ms. The emitted kernel does not use Z3.

The current instruction stream has 5,800 VALU operations. On six VALU slots these need at least 967 cycles. That bound ignores dependencies, so 967 cycles may be out of reach. An exact search for 979 cycles on an older graph ran out of its 2 GiB memory cap after 16 hours 52 minutes without an answer.

Table 3 summarizes the progress from the baseline. The [full history](docs/performance-progression.md) covers the upstream starter, the January vectorization and scheduling work, and the September compiler research. The September phase cut the cycle count from 1,303 to 975, a reduction of 25.2%.

**Table 3.** Cycle count by development stage.

| Cycles | Main changes |
|---|---|
| 147,734 → 4,294 | SIMD, persistent walker state, batching and software pipelining |
| 4,294 → about 2,905 | Manual bundle packing, affine hash fusion and a wider prefetch window |
| About 2,905 → 1,303 | Automatic list scheduling, shallow selection caches, predicate reuse and initialization cleanup |
| 1,303 → 1,113 | One-based and mirrored indices, XOR encoding, private hash temporaries, load-aware scheduling and final store/pause packing |
| 1,113 → 1,082 | Reused branch predicates, cached depth-4 lookups, a folded root mix and selected vector work moved to scalar slots |
| 1,082 → 1,076 | A single-static-assignment graph, scratch allocation after scheduling and some constants built on the flow engine |
| 1,076 → 1,052 | Fused hash stages, retained branch history, arithmetic lookup leaves, engine lookahead and cache reselection |
| 1,052 → 1,041 | Earlier startup gather dependencies and cache reselection under that policy |
| 1,041 → 981 | Cache neighborhood search, a swap to escape a plateau and arithmetic selectors tuned with the cache choices |
| 981 → 980 | Two late selectors converted to arithmetic, the final schedule repaired with Z3 and scratch allocated again |
| 980 → 979 | Continuous gathers from backward/forward scheduling, a shorter final hash path and scratch allocated again |
| 979 → 975 | Early gather ancestry first, only block 31's final-hash rewrite kept and scratch allocated again |

Changes in one row interact, so their savings do not add up in other combinations. The January counts come from commit and session measurements and were not rerun under the current gates.

## 6. Verification

The verifiers built the kernel through the public `KernelBuilder` and checked the following:

- The nine frozen submission tests, 100 generated inputs, 100 full-width inputs, five asymmetric patterns and nine other root-starting shapes.
- Lane ownership and dependencies. Mutations that drop a dependency, duplicate a lane, corrupt a constant or swap a selector branch all fail.
- Scratch limits. The compiler rejects an over-limit allocation before lowering, including a natural 1,537-word retimed allocation.
- Fallback for explicit overrides, isolation between cached program copies, scheduler hazards and a pause co-issued with the final stores.
- Three performance ceilings on non-benchmark shapes, and two source-only rebuilds at hash seeds 0 and 17.
- A Z3 proof over the emitted 975-cycle bundles. For every tree and every input value on the benchmark shape, each final value equals the reference, every other memory word stays unchanged, and every scratch and memory access stays in range. The proof uses none of the compiler's code.

The 975-cycle gate rejected executed controls at 980, 1,041, 1,042, 1,052, 1,076 and 1,082 cycles. The [975 report](experiments/startup_ancestry_candidate_results.md) and the [evidence manifest](experiments/promotion_975_evidence/manifest.json) hold the details.

## 7. Limitations

- The kernel assumes traversals start at the root.
- The kernel writes final values and leaves every other memory word unchanged, but it does not write final indices.
- The checks, including the proof, do not cover non-root starts or arbitrary dimensions.
- Optimality is unproven (Section 5).

## 8. Concluding Remarks

A solver-free search compiler reaches 975 cycles on the benchmark, about 152 times faster than the scalar baseline. Independent rebuilds reproduce the program, and a Z3 proof establishes its equivalence to the reference within the limits of Section 7. The gap to the 967-cycle resource bound remains open.

## Appendix A. Build and Verification Procedure

> **Caution:** Do not modify `tests/` or `problem.py`. Anthropic reported that every first-day submission below 1,300 cycles was invalid because the agents had edited the tests. If you use an agent, tell it not to touch `tests/` or the simulator.

Keep Python assertions enabled throughout.

1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `. .venv/bin/activate`
3. Install the pinned dependencies: `python -m pip install -r requirements.txt`
4. Run the submission suite: `python tests/submission_tests.py`

The compiler checks for `z3-solver==4.15.4.0`, because the retained exact-scheduling tools and the equivalence proof need it.

To run the supplementary checks, run each command in Table A1.

**Table A1.** Supplementary checks.

| Command | Duration |
|---|---|
| `python scripts/verify_retry.py --max-cycles 975` | One cold build |
| `python scripts/verify_compiler.py` | About 46 minutes, including two isolated cold builds |
| `python scripts/verify_optimizer.py` | One cold build |
| `python scripts/verify_justify.py` | Seconds |
| `python scripts/verify_random_graphs.py` | Seconds |
| `python scripts/verify_equivalence.py` | One cold build, then about a minute of proof; `--program` checks a saved program without building |
| `git diff --exit-code 5452f74 -- tests/ problem.py` | Seconds |

The [verification guide](docs/verification.md) lists what each command covers.

Before you report a score, run both of the following commands and state that you ran them. The `git diff` must print nothing.

```sh
git diff 5452f74 -- tests/ problem.py
python tests/submission_tests.py
```
