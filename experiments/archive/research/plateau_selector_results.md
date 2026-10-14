# Escaping cache plateaus and rebalancing selectors

## Result

The best verified candidate is **981 cycles / 1,465 scratch words**, twelve cycles faster than the [993-cycle candidate](../../cache_descent_results.md) and sixty faster than the committed 1,041-cycle default.

During this work, the user authorized committing the existing integration and reports. That checkpoint is `5691617`; it was not pushed. The new experiments did not change production. The goal is lower verified cycle count, with compilation cost secondary.

## Cache plateau and escape

Starting from 993 cycles, the next four full single-site neighborhoods produced:

| Change | Cycles | Scratch |
|---|---:|---:|
| Starting candidate | 993 | 1,426 |
| Remove `(4,15)` | 992 | 1,473 |
| Add `(13,4)` | 989 | 1,433 |
| Add `(14,4)` | 987 | 1,433 |
| Complete next neighborhood | No faster plan | |
| Swap out `(5,15)`, in `(27,4)` | 984 | 1,417 |

The swap screen tested 128 proposals: 96 ranked by combined single-toggle deltas and 32 sampled across the remaining ranked list. Those estimates only selected experiments; complete scheduling and execution decided the result. Of the 128 proposals, 121 were new. The whole stage added 369 plans to the prior 810-plan archive. One exceeded scratch; all 368 feasible plans passed frozen smoke execution. The stage took 51.57 seconds.

The swapped plan then received its own complete single-toggle neighborhood. Sixty-two plans were new and passed smoke checks. None improved on 984 cycles. This established a single-toggle cycle plateau for that fixed selector profile, not a global optimum.

## Joint selector/cache balance

The 984 plan's instruction bounds were almost tied: 964 cycles for VALU and 963 for flow. More caching could move the bottleneck rather than remove it.

The next screen parameterized how many first-layer leaf pairs use multiply-add selection instead of flow selection. It tested all 45 count pairs: zero through four arithmetic leaves at depth 3, and zero through eight at depth 4. Stored branch history, reversed depth-3 bit order, eager shared differences, startup priority, and lookahead stayed fixed. The original `(2,2)` profile reproduced the 984 program exactly.

Thirty-nine profiles fit scratch; six did not and were never executed. The best alternatives were not standalone speed wins:

| Arithmetic leaves at depths 3 / 4 | Cycles | Scratch |
|---|---:|---:|
| 2 / 2, control | 984 | 1,417 |
| 2 / 3 | 984 | 1,457 |
| 1 / 5 | 986 | 1,505 |

The two best eligible non-control profiles each received one full 64-site cache neighborhood. Eligibility allowed up to four cycles of standalone regression as a proposal heuristic, not a prediction of additive savings. Of 128 joint candidates, 119 fit scratch and passed smoke execution; nine exceeded scratch.

The winner uses **two arithmetic leaves at depth 3 and three at depth 4**, then adds cache site `(22,15)`. It reaches 981 cycles / 1,465 words with 29 cache sites. The initially slower `(1,5)` profile also produced a 982-cycle candidate after a cache addition. Rejecting every standalone non-winner would have missed both useful combinations.

Profile `(2,3)` shifts 28 flow operations to arithmetic across the 28 cached lookups in its control. The extra cache then spends some of that freed flow capacity. All setup, remaining operations, and lifetimes are charged; no runtime values are inspected during compilation.

## Check the new plateau and forecast policy

A complete single-toggle neighborhood around the 981 plan produced 63 new plans, 56 feasible. No neighbor was faster. This is a measured local plateau for the fixed `(2,3)` profile; it does not cover swaps, other leaf identities, or other profiles at every cache plan.

A final twelve-configuration screen varied forecast horizon over one or two cycles, width over 8, 16, or 32 operations, and decisions over one or two per cycle. The original one-cycle/eight-operation/one-decision policy reproduced 981 exactly. Every alternative was slower, ranging from 984 to 988 cycles. All twelve fit scratch and passed smoke execution. The best alternative took 984 cycles and 1,505 words, so no wider forecast was retained.

The following counts exclude reused cache scores and separate baseline replays. Profile and forecast rows include their controls.

| Stage | New cache plans or profile rows | Feasible smoke passes |
|---|---:|---:|
| Cache descent and sampled swaps | 369 | 368 |
| Neighborhood after the swap | 62 | 62 |
| Selector profiles | 45 | 39 |
| Joint selector/cache neighbors | 128 | 119 |
| Neighborhood at 981 | 63 | 56 |
| Forecast variants | 12 | 12 |

There were no compilation exceptions, timeouts, or feasible correctness failures. Four local workers ran the screens. The declared limits were twenty seconds per compilation, or sixty seconds for the forecast screen because compilation speed was not its objective.

## Final program and verification

The 981 program emits 1,888 load, 947 flow, 5,797 VALU, 11,516 ALU, and 32 store instructions. Its first gather is at cycle 61 and last at 969. Empty load slots split into 50 at startup, two between gathers, and 22 after the last gather.

Capacity-only bounds are load 944, flow 947, VALU 967, and ALU 960 cycles. The 967 bound belongs to this stream. The fourteen-cycle gap is not guaranteed recoverable, and no challenge-wide optimum has been established.

Both the 984 and 981 finalists passed 100 full-width seeds, five asymmetric patterns, lane ownership, three deterministic compiles, and dependency/constant/selector mutations. Both passed all nine unchanged frozen tests and the supplementary verifier through experimental adapters. Other shapes retained unchanged legacy generation. The 981 gate rejected the executed 984 and 1,041 controls exactly as `((984, 981),)` and `((1041, 981),)`.

Fresh hash-seed-17 generation with runtime-data and reference helpers forbidden reproduced both digests. Z3 proved the normalized pair-difference identity; a wrong difference expression produced a counterexample. An independent structural check covered 184 mixed-leaf/permuted-tree cases across depths 3 and 4. These checks are not a formal whole-compiler proof.

The 981 finalist's repeat selected-plan compilations took 0.482 and 0.497 seconds. Full automatic selection under the new profile has not been integrated or timed. The selected program depends on experimental configuration files, not a self-contained production selection rule.

Instruction SHA-256:

```text
8801c539f3a3f66babc875f7b082c4395406fc98ffe732d492f535833049c13e
```

## Artifacts and remaining directions

Cache plateau and swap artifacts are in `/tmp/perf-cache-plateau.RvU1Ta/`. Selector, joint-cache, and forecast artifacts are in `/tmp/perf-selector-balance.EYPqZY/`. Both retain protocols, source snapshots, configs, rows, controls, verification logs, hashes, and decisions.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-cache-plateau.RvU1Ta/search.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/follow_cache.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/selectors_screen.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/joint_descent.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/forecast_screen.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/verify_winner.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-selector-balance.EYPqZY/probe.py
```

Replay needs the temporary sources/configurations. The saved 981 checkpoint is retained separately as `verified_981.json` and `program_981.json` for the follow-up screens.

Further reduction should target coupled representation and scheduling choices, not assume more caches or wider forecasts always help. This screen varied leaf counts but always chose the first leaf pairs. Which pairs receive arithmetic, profile changes at the final cache plan, and larger coordinated cache exchanges remain open.

The committed default stays at 1,041 cycles. No additional commit, push, production promotion, cloud work, or external submission occurred after checkpoint `5691617`.
