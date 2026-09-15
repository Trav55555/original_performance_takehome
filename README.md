# Anthropic's original performance take-home

**979 cycles, 1,463 scratch words, no solver queries.** This result was promoted in `2c4705b`. The public builder and two isolated source-only rebuilds produced the same program. The figures and compiler description below refer to this verified release. See the [verification report](experiments/promotion_979_results.md) and [receipt](experiments/promotion_979_receipt.json).

This repo optimizes Anthropic's original performance take-home. The benchmark uses a height-10 tree with 2,047 nodes, a batch of 256 inputs and 16 rounds. It runs on one core with eight SIMD lanes and a 1,536-word scratch limit.

The latest change saved one cycle and two scratch words over the previous 980-cycle implementation. Other shapes and explicit tuning overrides still use the legacy generator, whose benchmark implementation takes 1,082 cycles.

## Find your way around

| Goal | Read |
|---|---|
| Build and check the current result | [Setup below](#build-and-run), [verification commands and costs](docs/verification.md) |
| Understand the current code | [Architecture and module map](docs/architecture.md) |
| Follow the whole project | [147,734 → 979 history and milestone ledger](docs/performance-progression.md) |
| Look up a technique or research result | [Technique and research wiki](docs/reference/README.md) |
| Inspect reports and raw evidence | [Experiment index](experiments/README.md) |

Historical notes live in [`docs/history/`](docs/history/README.md), archived prototype code in [`experiments/archive/`](experiments/archive/README.md), and the trace viewer in [`tools/trace/`](tools/trace/README.md). They are separate from current compiler and verification guidance.

The root keeps the submission entry point, simulator, production `kernel_*.py` modules and environment files. Their flat import paths are part of the submission and source-only verification contract.

## Build and run

Keep Python assertions enabled. The default compiler no longer calls a solver, but it still checks for `z3-solver==4.15.4.0` for compatibility with the retained exact-scheduling tools. The emitted kernel has no Z3 dependency.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tests/submission_tests.py
```

Expect the first build to take about 16 minutes on the host used for verification. The three measured cold builds took 15.9 to 16.0 minutes; a cached build took about 6.5 ms. There is no disk cache, so each new Python process starts over. Within a process, the compiler caches immutable tuples and gives each builder its own mutable instruction bundles.

Run the additional checks with:

```sh
python scripts/verify_retry.py --max-cycles 979
python scripts/verify_compiler.py
python scripts/verify_optimizer.py
python scripts/verify_justify.py
git diff --exit-code 5452f74 -- tests/ problem.py
```

These commands have separate compiler caches. `verify_compiler.py` also runs two isolated cold rebuilds; `verify_justify.py` uses small scheduling tests without benchmark discovery.

## How the compiler reaches 979

The compiler searches for cache choices and arithmetic replacements for lookup selectors. It then schedules the generated graph backward and forward, keeping each instruction's native engine assignment. From that schedule it finds two late terminal blocks and tests final-hash rewrites for each block and the pair, under two tie orders.

All choices come from generated graphs and measured schedule costs. The compiler reads no saved configurations, timing tables, physical programs or runtime input values. Each new schedule gets a fresh scratch allocation. Setup, constants, broadcasts, loads, stores and the final pause all count toward execution time.

The successful build used 1,959 score entries. The limit is 4,096, including at most eight backward/forward schedules. Reconstruction checks add compilation work beyond that score count. If the search cannot find a legal result at or below 979 cycles, compilation fails rather than returning a slower kernel.

The machine has two load slots, six vector-arithmetic slots and one flow slot per cycle. Caching replaces gathers with selection work; arithmetic selectors move work from flow to arithmetic. Fewer instructions on one engine can mean more contention on another. Only the complete schedule decides whether a change helps.

The [previous 980-cycle compiler](experiments/promotion_980_results.md) used Z3 to repair a 32-cycle native suffix with 527 free issue-time variables. The current path uses no solver. The old exact workers remain available with a 2 GiB address-space cap and no wall-clock or CPU deadline.

An earlier selected-timing experiment reached 980 cycles with 1,449 words. The current compiler is faster but uses 14 more words than that separate experiment. That saved timing is not an input to production discovery.

### What is verified

Verification through `KernelBuilder` passed:

- All nine frozen submission tests, 100 generated inputs, 100 full-width inputs, five asymmetric patterns and nine other root-starting shapes.
- Lane-ownership and dependency checks, plus mutations that introduce missing dependencies, duplicate lanes, corrupted constants and swapped selector branches.
- Scratch rejection before lowering, including a natural 1,537-word retimed allocation.
- Explicit-override fallback, isolation between cached program copies, scheduler hazards and co-issued pause/store completion.
- Three non-benchmark performance ceilings and two source-only rebuilds at hash seeds 0 and 17.

The 979-cycle performance gate rejected an executed 980-cycle control. The native 981-cycle control and the older 1,041, 1,042, 1,052, 1,076 and 1,082 controls also ran as expected.

`tests/` and `problem.py` are unchanged. The kernel assumes root-starting traversals and writes final values only, not indices. It preserves all other memory. These checks do not establish support for non-root starts or arbitrary dimensions.

The current instruction stream has a capacity-only lower bound of 967 cycles. That does not mean 967 is attainable. An older attempt to solve for 979 exhausted 2 GiB after about 16 hours 52 minutes and returned **unknown**. It used a different graph and scope from the successful implementation. Neither result proves global optimality.

## From 147,734 to 979 cycles

The recorded scalar baseline is 147,734 cycles. The current result is a roughly 151× speedup in simulated execution. The [full illustrated history](docs/performance-progression.md) covers the upstream starter, January vectorization and scheduling, September compiler research, and the final promotion. The later 1,303 → 979 phase alone saved 324 cycles, or 24.9% of execution time. The [979 report](experiments/promotion_979_results.md) supplies the current verification evidence.

| Cycles | Main changes |
|---|---|
| 147,734 → 4,294 | SIMD, persistent walker state, batching and software pipelining |
| 4,294 → about 2,905 | Manual bundle packing, affine hash fusion and a wider prefetch window |
| About 2,905 → 1,303 | Automatic list scheduling, shallow selection caches, predicate reuse and initialization cleanup |
| 1,303 → 1,113 | One-based and mirrored indices, XOR encoding, private hash temporaries, load-aware scheduling and final store/pause packing |
| 1,113 → 1,082 | Reuse branch predicates, cache selected depth-4 lookups, fold the root mix and move selected vector work to scalar slots |
| 1,082 → 1,076 | Build a single-static-assignment graph, allocate scratch after scheduling and construct some constants on the flow engine |
| 1,076 → 1,052 | Fuse hash stages, retain branch history, use arithmetic lookup leaves and engine lookahead, then reselect caches |
| 1,052 → 1,041 | Advance startup gather dependencies and reselect caches under that policy |
| 1,041 → 981 | Search cache neighborhoods, escape a plateau with a swap and tune arithmetic selectors alongside cache choices |
| 981 → 980 | Convert two late selectors to arithmetic, repair the final schedule with Z3 and allocate scratch again |
| 980 → 979 | Keep gathers continuous with backward/forward scheduling, shorten the final hash path and allocate scratch again |

The savings in each row include interactions between changes. They are not independent gains that can be added in other combinations. January counts are historical commit/session measurements, not fresh executions under every modern promotion gate.

### Experiments worth keeping

The original rebuilt prototype reached 1,076 cycles with 1,253 scratch words. Automatic cache reselection later matched that speed with 1,236 words, without importing the old configuration. Moving 27 constant instructions from load to flow-engine `add_imm` saved six cycles against the preceding rebuilt candidate.

The selected prototype passed nine frozen tests through an adapter, 100 full-width cases, five patterns, physical lane checks and dependency/constant corruption controls. Those checks validated a selected program. The production reports add automatic discovery and verification through the normal builder. A smaller port of constant selection to the legacy generator only tied 1,082 cycles.

Early tests of arithmetic selectors, progressive depth-5 selection, equivalent hash rewrites, and startup/tail scheduling did not beat the 1,076-cycle control. Later combinations did. Exact searches also found no one-cycle gain in the tested 16-, 32- and 64-cycle suffixes when the prefix, physical registers and instruction choices stayed fixed. Those results apply to those graphs and constraints, not every rewrite. The legacy graph's 1,074-cycle lower bound does not apply to the rebuilt graph.

Twelve output-pointer policies tested whether recomputing pointers could reduce their scratch lifetimes:

| Policy | Cycles | Scratch words |
|---|---:|---:|
| Retain pointers, rebuilt control | 1,076 | 1,253 |
| Best freely scheduled regeneration | 1,076 | 1,241 |
| Regenerate near stores | 1,081 to 1,093 | 1,241 |

Putting regeneration near stores in source code did not keep it late in the schedule. The scheduler moved many constants early. Forcing later regeneration shortened lifetimes but slowed execution. The best tie saved only twelve words, so it was not integrated. Each policy passed three full-width cases and physical lane checks; the best also passed twenty more cases, five patterns and a corrupted-pointer control. All added work and retained base-pointer lifetimes were counted.

The [Algorithmica follow-up](experiments/algorithmica_followup_results.md) records the resource tradeoffs and source references. The [bounded research follow-up](experiments/research_followup_results.md) covers the earlier cache and regional-scheduling work. Later [frontier experiments](experiments/four_frontiers_results.md) reached 1,074 cycles. An [audit of a public fork](experiments/github_1063_audit.md) reproduced 1,063, and [isolated technique ports](experiments/technique_port_results.md) reached 1,052 before integration. [Load-gap profiling](experiments/load_gap_results.md) produced a 1,042-cycle policy; cache reselection reduced it to 1,041 through the normal builder.

## About the original challenge

Anthropic's original take-home allowed four hours. After Claude Opus 4 surpassed most human results, Anthropic switched to a two-hour version starting at 18,532 cycles, 7.97 times faster than the slow baseline. This repo uses that version's extra instructions and debugging tools, with the starter code reset to the slow baseline. Anthropic changed the starting point again after Opus 4.5.

Anthropic reported these model results using the 18,532-cycle starting point. The run lengths differ, and this repo's 979-cycle result is not a two-hour attempt.

| Cycles | Reported run |
|---:|---|
| 2,164 | Claude Opus 4 after many hours |
| 1,790 | Opus 4.5 casual run, roughly matching the best human performance in two hours |
| 1,579 | Opus 4.5 after two hours |
| 1,548 | Sonnet 4.5 after many hours |
| 1,487 | Opus 4.5 after 11.5 hours |
| 1,363 | Opus 4.5 with an improved test setup |

Anthropic did not publish its best human result. The original README invited solutions below 1,487 cycles to performance-recruiting@anthropic.com, with code and preferably a resume. It also warned that the hiring threshold could change with new model releases. That invitation is historical context, not a current hiring guarantee from this repo.

### Do not change the test to improve the score

Anthropic reported that none of the first-day submissions below 1,300 cycles were valid. The agents had changed the tests. If you use an agent, tell it to leave `tests/` and the simulator alone and to verify with `tests/submission_tests.py`.

For a submission, run these commands and report that you ran them:

```sh
# This should be empty.
git diff origin/main tests/
python tests/submission_tests.py
```

Multicore is intentionally disabled. Changing `N_CORES = 1` to make the score better changes the benchmark; it is not an optimization.
