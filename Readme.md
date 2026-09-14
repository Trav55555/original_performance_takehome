# Anthropic's Original Performance Take-Home

This repo contains a version of Anthropic's original performance take-home, before Claude Opus 4.5 started doing better than humans given only 2 hours.

The original take-home was a 4-hour one that starts close to the contents of this repo, after Claude Opus 4 beat most humans at that, it was updated to a 2-hour one which started with code which achieved 18532 cycles (7.97x faster than this repo starts you). This repo is based on the newer take-home which has a few more instructions and comes with better debugging tools, but has the starter code reverted to the slowest baseline. After Claude Opus 4.5 we started using a different base for our time-limited take-homes.

Now you can try to beat Claude Opus 4.5 given unlimited time!

## Performance benchmarks 

Measured in clock cycles from the simulated machine. All of these numbers are for models doing the 2 hour version which started at 18532 cycles:

- **2164 cycles**: Claude Opus 4 after many hours in the test-time compute harness
- **1790 cycles**: Claude Opus 4.5 in a casual Claude Code session, approximately matching the best human performance in 2 hours
- **1579 cycles**: Claude Opus 4.5 after 2 hours in our test-time compute harness
- **1548 cycles**: Claude Sonnet 4.5 after many more than 2 hours of test-time compute
- **1487 cycles**: Claude Opus 4.5 after 11.5 hours in the harness
- **1363 cycles**: Claude Opus 4.5 in an improved test time compute harness
- **980 cycles**: This repo, using automatic cache/selector discovery and exact suffix scheduling. Previously 1041 cycles.
- **??? cycles**: Best human performance ever is substantially better than the above, but we won't say how much.

While it's no longer a good time-limited test, you can still use this test to get us excited about hiring you! If you optimize below 1487 cycles, beating Claude Opus 4.5's best performance at launch, email us at performance-recruiting@anthropic.com with your code (and ideally a resume) so we can be appropriately impressed, especially if you get near the best solution we've seen. New model releases may change what threshold impresses us though, and no guarantees that we keep this readme updated with the latest on that.

Install the build dependency below, then run `python tests/submission_tests.py` to see which thresholds you pass.

## Current implementation and verification

The default kernel takes **980 cycles** for height 10, 2,047 tree nodes, batch size 256, and 16 rounds. Scratch usage is **1,465 of 1,536 words**, on one core with eight SIMD lanes. This saves 61 cycles from the preceding 1,041-cycle implementation.

The compiler discovers its cache choices, lookup conversions, and instruction timing from source. It does not read saved configurations, timing tables, physical programs, or runtime input values. The measured build used 1,951 score entries and one optimization query. Reconstruction checks add compilation work beyond that score count.

Cold builds took **17 to 19 minutes** on this host. A memoized build took about **6.6 ms**. Compiled programs are immutable tuples, and each builder receives fresh mutable bundles. There is no disk cache. The earlier selected-timing experiment reached the same 980 cycles using 1,449 words, but this production compiler discovers a different schedule using 16 more words.

The new path applies only to the benchmark with default tuning parameters. Other shapes and explicit overrides retain the legacy generator. Its 1,082-cycle benchmark implementation remains available as `KernelBuilder._build_legacy_kernel`.

### From 1,303 to 980 cycles

The full progression saved **323 cycles, or 24.8% of execution time**. Read the [illustrated walkthrough](docs/performance-progression.md) for the intermediate checkpoints, dependency diagrams, algebra, failed experiments, and the distinction between experimental and production results.

| Measured progression | Main changes |
|---|---|
| 1,303 → 1,113 | One-based and mirrored indices, XOR encoding, private hash temporaries, load-aware scheduling, and final store/pause packing |
| 1,113 → 1,082 | Reuse branch predicates, selectively cache depth-4 lookups, fold the root mix, and move selected vector work to scalar slots |
| 1,082 → 1,076 | Rebuild around single static assignment, allocate scratch after scheduling, and construct some constants on the flow engine |
| 1,076 → 1,052 | Combine hash-stage fusion, retained branch history, arithmetic lookup leaves, engine lookahead, and cache reselection |
| 1,052 → 1,041 | Advance startup gather dependencies and reselect caches under that policy |
| 1,041 → 981 | Search complete cache neighborhoods, escape a plateau with a swap, and rebalance arithmetic selectors with cache choices |
| 981 → 980 | Convert two late selectors to arithmetic, then jointly repair the final schedule with Z3 and allocate scratch afresh |

The machine has only two load slots, six vector-arithmetic slots, and one flow slot per cycle. Caching exchanges gathers for selection work; arithmetic selectors move work from flow to arithmetic. Those exchanges help only when the complete schedule improves. The phase totals above include interacting changes, not independent additive savings for each technique.

The final production query repairs a 32-cycle native suffix with 527 free issue-time variables. Earlier instruction times and native engine choices remain fixed. All constants, setup, loads, stores, and the final pause are charged. No saved timing table or ordinal scheduling edits are production inputs.

The current instruction stream has a capacity-only lower bound of 967 cycles, not a proof that 967 is attainable. The 979-cycle query that completed after promotion exhausted its 2 GiB memory cap after about 16 hours 52 minutes. Its result was **unknown**, not proof that 979 is impossible.

### Build and verification

The exact scheduler requires pinned `z3-solver==4.15.4.0` at build time. The emitted kernel has no Z3 dependency. Solver workers have a 2 GiB address-space cap and no wall-clock or CPU deadline. Compilation is bounded by 4,096 score entries and four optimization queries; unknown results fail explicitly rather than silently returning a slower kernel. Keep Python assertions enabled.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tests/submission_tests.py
python scripts/verify_retry.py
python scripts/verify_compiler.py
python scripts/verify_optimizer.py
git diff --exit-code 5452f74 -- tests/ problem.py
```

Separate commands start separate compiler caches. Allow time for cold compilation; `verify_compiler.py` also performs two isolated cold rebuilds.

Verification through `KernelBuilder` passed all nine frozen submission tests, 100 generated inputs, 100 full-width inputs, five asymmetric patterns, and nine other root-starting shapes. Three non-benchmark performance ceilings remain in place. Checks cover lane ownership, missing dependencies, duplicate lanes, corrupted constants and selectors, scratch rejection before lowering, explicit-override fallback, cached-program isolation, and co-issued pause/store completion. Both source-only rebuilds reproduced the same program at hash seeds 0 and 17.

The 980-cycle ceiling rejects the executed native 981-cycle control and the 1,041, 1,042, 1,052, 1,076, and 1,082 controls. See [the promotion results](experiments/promotion_980_results.md) and [machine-readable receipt](experiments/promotion_980_receipt.json).

`tests/` and `problem.py` remain unchanged. The kernel assumes root-starting traversals and writes final values only, not indices. These checks do not establish support for non-root starts or arbitrary dimensions.

## Prototype history and rejected experiments

See [the Algorithmica follow-up lessons](experiments/algorithmica_followup_results.md) for measured tradeoffs, graph-bound limits, and source references.

The original rebuilt prototype reached **1,076 cycles using 1,253 scratch words** on the same benchmark. The first promotion independently reselected cache sites and reached the same cycle count with 1,236 words, without importing the old configuration.

The rebuilt generator schedules logical values before assigning scratch addresses and can choose between scalar and vector arithmetic. That prototype moved 27 constant instructions from the load engine to flow-engine `add_imm` instructions using an existing base. This saved six cycles against its preceding rebuilt candidate. All initialization, instructions, scratch lifetimes, stores, and the final pause count toward the result.

The selected 1,076-cycle program passed all nine frozen submission tests and the supplementary verifier through a test adapter. It also passed 100 full-width random cases, five bit patterns, physical scratch-lane checks, and dependency and corrupted-constant controls. Those historical checks validated a selected program. The promotion receipt above adds normal-entry-point and automatic-selection verification. A compact port of constant selection to the retained generator only tied 1,082 cycles.

Earlier bounded experiments did not improve the 1,076-cycle result. Their tested arithmetic lookup selectors, progressive depth-5 selection, and equivalence-checked hash rewrites lost to their controls. These negatives did not rule out the later joint hash/selector improvements. Startup and tail scheduling changes did not beat the winner. Exact solving found no one-cycle reduction in its tested 16-, 32-, or 64-cycle suffixes with the prefix, physical registers, and instruction choices fixed. These suffix results are local. The legacy graph's 1,074-cycle lower bound does not transfer to the rebuilt graph.

### Retaining versus recomputing output pointers

Twelve policies tested whether regenerating output pointers could reduce scratch lifetimes enough to pay for the extra instructions.

| Policy | Cycles | Scratch words |
|---|---:|---:|
| Retain pointers, rebuilt control | 1,076 | 1,253 |
| Best freely scheduled regeneration | 1,076 | 1,241 |
| Regenerate near stores | 1,081 to 1,093 | 1,241 |

Simply placing regeneration near stores in source order did not keep it late in the schedule. The scheduler moved many constants early. Explicitly delaying regeneration shortened pointer lifetimes but made execution slower. Even the best tie saved only twelve words, so pointer regeneration is not selected for integration.

Each policy passed three full-width frozen executions with identical cycle counts across runs, plus physical scratch-lane checks. The best tie also passed twenty additional full-width cases, five patterns, and a corrupted-pointer control. The measurements include every added instruction and retained base-pointer lifetime.

The [bounded research follow-up](experiments/research_followup_results.md) records the preceding cache and regional-scheduling experiments. Later [frontier experiments](experiments/four_frontiers_results.md) reached 1,074 cycles. An [independent audit](experiments/github_1063_audit.md) reproduced a public fork at 1,063, and [isolated technique ports](experiments/technique_port_results.md) reached 1,052. Those techniques were integrated at 1,052 cycles. [Load-gap profiling](experiments/load_gap_results.md) then led to a 1,042-cycle startup policy. Its integration reselected caches and reached 1,041 cycles through the normal entry point. The cache, selector, and exact-scheduling work above subsequently reduced that to 980.

## Warning: LLMs can cheat

None of the solutions we received on the first day post-release below 1300 cycles were valid solutions. In each case, a language model modified the tests to make the problem easier.

If you use an AI agent, we recommend instructing it not to change the `tests/` folder and to use `tests/submission_tests.py` for verification.

Please run the following commands to validate your submission, and mention that you did so when submitting:
```
# This should be empty, the tests folder must be unchanged
git diff origin/main tests/
# You should pass some of these tests and use the cycle count this prints
python tests/submission_tests.py
```

An example of this kind of hack is a model noticing that `problem.py` has multicore support, implementing multicore as an optimization, noticing there's no speedup and "debugging" that `N_CORES = 1` and "fixing" the core count so they get a speedup. Multicore is disabled intentionally in this version.
