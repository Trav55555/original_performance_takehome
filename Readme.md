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
- **1076 cycles**: This repo (self-contained SSA compiler, automatic depth-4 cache selection, lane-ready instruction selection, load/flow constant choices, and post-schedule scratch allocation; previously 1082 cycles)
- **??? cycles**: Best human performance ever is substantially better than the above, but we won't say how much.

While it's no longer a good time-limited test, you can still use this test to get us excited about hiring you! If you optimize below 1487 cycles, beating Claude Opus 4.5's best performance at launch, email us at performance-recruiting@anthropic.com with your code (and ideally a resume) so we can be appropriately impressed, especially if you get near the best solution we've seen. New model releases may change what threshold impresses us though, and no guarantees that we keep this readme updated with the latest on that.

Run `python tests/submission_tests.py` to see which thresholds you pass.

## Current implementation and verification

The default kernel takes **1,076 cycles** for height 10, 2,047 tree nodes, batch size 256, and 16 rounds. Scratch usage is **1,236 of 1,536 words**, on one core with eight SIMD lanes. This saves six cycles from the preceding implementation and 227 cycles from the 1,303-cycle baseline, a 17.4% reduction.

`kernel_compiler.py` selects caches from an empty plan, schedules logical values with lane readiness, chooses execution engines, then allocates physical scratch. It uses no saved configurations, prototype imports, or runtime input inspection. Selection currently evaluates 222 plans. Cold builds took 23 to 25 seconds on this host; memoized builds in the same process took about 5 ms. Only the immutable compiled result is cached, with fresh mutable bundles for each builder.

The rebuilt path applies only to the benchmark with default tuning parameters. Other shapes and explicit overrides retain the legacy generator. Its original 1,082-cycle benchmark implementation remains available as `KernelBuilder._build_legacy_kernel`.

The current instruction stream has a capacity-only lower bound of 1,047 cycles. The earlier 1,074-to-1,082 graph bound belongs to the legacy implementation and does not transfer here. Neither establishes a challenge-wide optimum. See [the promotion receipt](experiments/rebuilt_promotion_results.md), [the preceding instruction-selection experiment](experiments/algorithmica_results.md), and [the optimization history](experiments/retry_results.md).

Verification through the normal entry point covers all nine frozen submission tests, 100 generated inputs, 100 additional full-width inputs, five asymmetric bit patterns, and nine additional root-starting shapes. Three non-benchmark performance gates remain in place. Compiler checks cover lane identities, constant/dependency mutations, explicit-override fallback, cached-program isolation, and deterministic source-only builds. Supplementary checks cover register hazards and co-issued pause/store completion. The benchmark performance gate rejects results above 1,076 cycles.

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
python scripts/verify_compiler.py
git diff --exit-code 5452f74 -- tests/ problem.py
```

`tests/` and `problem.py` remain unchanged. The kernel assumes root-starting traversals and writes final values only, not indices. The verification does not establish support for non-root starts or arbitrary dimensions.

## Prototype history and rejected experiments

See [the Algorithmica follow-up lessons](experiments/algorithmica_followup_results.md) for measured tradeoffs, graph-bound limits, and source references.

The original rebuilt prototype reached **1,076 cycles using 1,253 scratch words** on the same benchmark. Its approach is now integrated. The production compiler independently reselects cache sites and reaches the same cycle count with 1,236 words, without importing the old configuration.

The rebuilt generator schedules logical values before assigning scratch addresses and can choose between scalar and vector arithmetic. Its latest improvement moves 27 constant instructions from the load engine to flow-engine `add_imm` instructions using an existing base. This saves six cycles against the preceding rebuilt candidate. All initialization, instructions, scratch lifetimes, stores, and the final pause count toward the result.

The selected 1,076-cycle program passed all nine frozen submission tests and the supplementary verifier through a test adapter. It also passed 100 full-width random cases, five bit patterns, physical scratch-lane checks, and dependency and corrupted-constant controls. Those historical checks validated a selected program. The promotion receipt above adds normal-entry-point and automatic-selection verification. A compact port of constant selection to the retained generator only tied 1,082 cycles.

Other experiments did not improve the 1,076-cycle result. Tested arithmetic lookup selectors, progressive depth-5 selection, and equivalence-checked hash rewrites lost to their controls. Startup and tail scheduling changes did not beat the winner. Exact solving found no one-cycle reduction in its tested 16-, 32-, or 64-cycle suffixes with the prefix, physical registers, and instruction choices fixed. These suffix results are local. The legacy graph's 1,074-cycle lower bound does not transfer to the rebuilt graph.

### Retaining versus recomputing output pointers

Twelve policies tested whether regenerating output pointers could reduce scratch lifetimes enough to pay for the extra instructions.

| Policy | Cycles | Scratch words |
|---|---:|---:|
| Retain pointers, rebuilt control | 1,076 | 1,253 |
| Best freely scheduled regeneration | 1,076 | 1,241 |
| Regenerate near stores | 1,081 to 1,093 | 1,241 |

Simply placing regeneration near stores in source order did not keep it late in the schedule. The scheduler moved many constants early. Explicitly delaying regeneration shortened pointer lifetimes but made execution slower. Even the best tie saved only twelve words, so pointer regeneration is not selected for integration.

Each policy passed three full-width frozen executions with identical cycle counts across runs, plus physical scratch-lane checks. The best tie also passed twenty additional full-width cases, five patterns, and a corrupted-pointer control. The measurements include every added instruction and retained base-pointer lifetime.

Self-contained integration and normal-entry-point verification are now complete. The [bounded research follow-up](experiments/research_followup_results.md) records the preceding cache and regional-scheduling experiments. Further runtime improvements remain unproven; the current tradeoff is slower cold compilation in exchange for six fewer simulated cycles.

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
