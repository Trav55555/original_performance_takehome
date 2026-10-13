# Anthropic's original performance take-home

This kernel runs the benchmark in **975 cycles** and uses 1,469 of the 1,536 scratch words. The compiler that produces it calls no solver. Commit `1df789d` passed the unchanged nine-test submission suite and every supplementary verifier. Two isolated rebuilds from source alone produced the same program digest. The [975 report](experiments/startup_ancestry_candidate_results.md) and the [evidence manifest](experiments/promotion_975_evidence/manifest.json) hold the details.

The benchmark walks a height-10 tree of 2,047 nodes with a batch of 256 inputs for 16 rounds. It runs on one simulated core with eight SIMD lanes. The recorded scalar baseline takes 147,734 cycles, so 975 is about 152 times faster.

## Where to look

| Goal | Read |
|---|---|
| Build and check the result | [Build and run](#build-and-run), then the [verification guide](docs/verification.md) |
| Understand the current code | [Architecture and module map](docs/architecture.md) |
| Follow the project from 147,734 to 975 | [Performance history and milestone ledger](docs/performance-progression.md) |
| Look up a technique or a research result | [Technique and research wiki](docs/reference/README.md) |
| Inspect reports and raw evidence | [Experiment index](experiments/README.md) |

Historical notes live in [`docs/history/`](docs/history/README.md). Archived prototype code and old analysis scripts live in [`experiments/archive/`](experiments/archive/README.md). The trace viewer lives in [`tools/trace/`](tools/trace/README.md). None of these are current compiler or verification guidance.

The repository root holds the submission entry point, the simulator, the production `kernel_*.py` modules and the environment files. The submission and the source-only rebuild both import these modules by their flat names, so they stay at the root.

## Build and run

Keep Python assertions enabled.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tests/submission_tests.py
```

The first build takes 15 to 16 minutes. The compiler keeps no disk cache, so every new Python process searches again. A second build inside the same process takes about 4 ms. The emitted kernel does not use Z3. The compiler still checks for `z3-solver==4.15.4.0`, because the retained exact-scheduling tools need it.

To run the supplementary checks:

```sh
python scripts/verify_retry.py --max-cycles 975
python scripts/verify_compiler.py
python scripts/verify_optimizer.py
python scripts/verify_justify.py
git diff --exit-code 5452f74 -- tests/ problem.py
```

Each command starts a cold build except `verify_justify.py` and the `git diff`. `verify_compiler.py` runs two more isolated cold builds and takes about 46 minutes. The [verification guide](docs/verification.md) lists what each command covers.

## How the compiler reaches 975

The compiler searches over two choices. It picks the cache sites, which serve tree lookups from scratch instead of gathering them. It also picks which lookup selectors to replace with arithmetic. It schedules each candidate graph backward, then forward, and keeps every instruction on its native engine. The forward pass tries three orders. One of them promotes the ancestry of the first 26 gathers. From the best schedule, the compiler finds the two blocks that finish last and tries final-hash rewrites on each block and on the pair.

Every choice comes from a generated graph and its measured schedule length. The compiler reads no saved configuration, timing table or physical program, and it never sees runtime input values. Each schedule gets a fresh scratch allocation. Setup, constants, broadcasts, loads, stores and the final pause all count.

The verified build scored 1,963 candidates out of a budget of 4,096. If the search finds no legal program at 975 cycles or fewer, compilation fails. It never returns a slower kernel.

Each cycle offers two load slots, six vector-arithmetic slots and one flow slot. Caching swaps gathers for selection work. Arithmetic selectors move work from flow to vector arithmetic. Removing instructions from one engine often adds contention on another, so only the complete schedule says whether a change helps.

Other tree shapes and explicit tuning overrides fall back to the legacy generator. On the benchmark shape that generator takes 1,082 cycles.

## What the checks prove

The verifiers built the kernel through the public `KernelBuilder` and checked:

- The nine frozen submission tests, 100 generated inputs, 100 full-width inputs, five asymmetric patterns and nine other root-starting shapes.
- Lane ownership and dependencies. Mutations that drop a dependency, duplicate a lane, corrupt a constant or swap a selector branch all fail.
- Scratch limits. The compiler rejects an over-limit allocation before lowering, including a natural 1,537-word retimed allocation.
- Fallback for explicit overrides, isolation between cached program copies, scheduler hazards and a pause co-issued with the final stores.
- Three performance ceilings on non-benchmark shapes, and two source-only rebuilds at hash seeds 0 and 17.

The 975-cycle gate rejected executed controls at 980, 1,041, 1,042, 1,052, 1,076 and 1,082 cycles.

The checks have limits. The kernel assumes traversals start at the root. It writes final values and leaves every other memory word unchanged, but it does not write final indices. The checks do not cover non-root starts or arbitrary dimensions.

Nobody has proven 975 optimal either. The current instruction stream has 5,800 vector-arithmetic operations, which need at least 967 cycles on six slots. That bound ignores dependencies, so 967 may be out of reach. An exact search for 979 on an older graph ran out of its 2 GiB memory cap after 16 hours 52 minutes without an answer.

## From 147,734 to 975 cycles

The [full history](docs/performance-progression.md) covers the upstream starter, the January vectorization and scheduling work, and the September compiler research. The September phase took the kernel from 1,303 to 975 cycles, a 25.2% cut.

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

Changes in one row interact, so their savings don't add up in other combinations. The January counts come from commit and session measurements. They were not rerun under the current gates.

## About the original challenge

Anthropic's original take-home allowed four hours. After Claude Opus 4 beat most human results, Anthropic switched to a two-hour version that started at 18,532 cycles. This repo uses that version's extra instructions and debugging tools, with the starter code reset to the slow baseline. Anthropic changed the starting point again after Opus 4.5.

Anthropic reported these model results from the 18,532-cycle start. The runs had different lengths, and this repo's 975 is not a two-hour attempt.

| Cycles | Reported run |
|---:|---|
| 2,164 | Claude Opus 4 after many hours |
| 1,790 | Opus 4.5 casual run, about the best human result in two hours |
| 1,579 | Opus 4.5 after two hours |
| 1,548 | Sonnet 4.5 after many hours |
| 1,487 | Opus 4.5 after 11.5 hours |
| 1,363 | Opus 4.5 with an improved test setup |

Anthropic did not publish its best human result. The original README invited solutions below 1,487 cycles to performance-recruiting@anthropic.com. It also warned that the threshold could change with new models. This repo makes no hiring promise.

### Leave the tests alone

Anthropic reported that every first-day submission below 1,300 cycles was invalid, because the agents had edited the tests. If you use an agent, tell it not to touch `tests/` or the simulator.

Before you report a score, run both commands and say that you ran them. The `git diff` must print nothing.

```sh
git diff 5452f74 -- tests/ problem.py
python tests/submission_tests.py
```

The challenge disables multicore on purpose. Raising `N_CORES` changes the benchmark. It is not an optimization.
