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

### Techniques that reduced the cycle count

The machine can issue twelve scalar ALU operations, six vector ALU operations, two loads, two stores, and one flow operation per cycle. A shorter expression is not necessarily a faster kernel. The compiler must also expose independent work and avoid overloading an engine.

**Schedule logical values before assigning scratch addresses.** The single static assignment, or SSA, representation separates data dependencies from physical register reuse. The scheduler can interleave walkers without first imposing register-alias dependencies. A fresh allocator then reuses scratch words after their last reads. The compiler rejects candidates that exceed 1,536 words before lowering or execution.

**Simplify the repeated hash and traversal work.** Encoded values and mirrored tree indices reduce repeated transformations. Two middle hash stages become independent affine expressions followed by XOR, which exposes parallel work and uses vector multiply-add instructions. Cached nodes use the matching encoded representation, and the first round uses the raw root directly. These rules were part of the earlier improvements; their savings are not additive because each rewrite changes scheduling and register pressure.

**Trade selected gathers for cached lookups.** Shallow tree levels are loaded once. Selected depth-4 visits use lookup trees instead of eight lane gathers. More caching also costs selector operations and live scratch, so enabling every cache is not the answer. Starting from the existing automatic seed, full one-site comparisons and a bounded swap search reduced 1,041 cycles to 984. The winning site list is a search result, not a table in the generator.

**Balance lookup work across engines.** The compiler retains normalized branch bits, then mixes flow-engine `vselect` instructions with arithmetic lookup pairs. For a bit `p` equal to zero or one, `no + p * (yes - no)` selects the same value using wrapping arithmetic. Differences come from runtime-loaded nodes. Joint selection of arithmetic-pair counts and one further cache change reduced 984 cycles to 981.

**Make loads ready earlier.** Bounded engine lookahead favors work that enables upcoming gathers. Startup priority advances the first four walkers' gather dependencies. Together with cache reselection, that startup policy previously reduced 1,052 cycles to 1,041. Filling an arithmetic slot is less useful when its work does not relieve the load bottleneck.

**Repair the final schedule jointly.** The last improvement required more than greedy scheduling. The compiler selects late lookup conversions from the generated graph, checks dependency and capacity bounds, and submits a small suffix to Z3. The selected graph replaces two late flow selectors with arithmetic but still takes 981 cycles under the native scheduler. Exact repair of its 32-cycle native suffix reaches 980 while keeping the earlier instruction times and native engine choices fixed. The successful query had 527 free time variables and took about 72 seconds. Fresh allocation, lane checks, and frozen execution establish that the result is an executable kernel, not merely a timing witness.

| Measured checkpoint | Cycles |
|---|---:|
| Previous startup-aware production compiler | 1,041 |
| Automatic cache toggle/swap search | 984 |
| Joint selector-profile and cache selection | 981 |
| Late arithmetic conversions, native schedule | 981 |
| Exact suffix repair and fresh allocation | 980 |

The successful path uses neither saved ordinal scheduling edits nor the experimental final-XOR rewrite. All emitted constants, setup, loads, stores, and the final pause count toward the result. The current instruction counts give a capacity-only lower bound of 967 cycles. That is a bound for this instruction stream, not a proof of challenge-wide optimality.

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
