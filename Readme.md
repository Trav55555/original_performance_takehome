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
- **1088 cycles**: This repo (encoded values, mirrored indices, predicate reuse, selective depth-4 caching, and dependency scheduling with load lookahead; previously 1303 cycles)
- **??? cycles**: Best human performance ever is substantially better than the above, but we won't say how much.

While it's no longer a good time-limited test, you can still use this test to get us excited about hiring you! If you optimize below 1487 cycles, beating Claude Opus 4.5's best performance at launch, email us at performance-recruiting@anthropic.com with your code (and ideally a resume) so we can be appropriately impressed, especially if you get near the best solution we've seen. New model releases may change what threshold impresses us though, and no guarantees that we keep this readme updated with the latest on that.

Run `python tests/submission_tests.py` to see which thresholds you pass.

## Current implementation and verification

The retained kernel takes **1,088 cycles** for height 10, 2,047 tree nodes, batch size 256, and 16 rounds. This saves 215 cycles from the previous 1,303-cycle baseline, a 16.5% reduction. Scratch usage is **1,536 of 1,536 words**, on one core with eight SIMD lanes.

Resource-aware bounds put the optimum for the current dependency graph between 1,074 and 1,088 cycles. This is not a bound on every legal implementation. See [the predicate and selective-cache experiments](experiments/cross_domain_results.md) for the latest changes and bound, and [the optimization history](experiments/retry_results.md) for the representation changes.

Verification covers all nine frozen submission tests, 100 random inputs, five full-width/asymmetric bit patterns, and eight additional root-starting shapes. Supplementary checks exercise register hazards, co-issued pause/store completion, and rejection of a deliberately corrupted kernel. The performance gate rejects results above 1,088 cycles.

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
git diff --exit-code 5452f74 -- tests/ problem.py
```

`tests/` and `problem.py` remain unchanged. The kernel assumes root-starting traversals and writes final values only, not indices. The verification does not establish support for non-root starts or arbitrary dimensions.

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
