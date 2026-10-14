# Arithmetic leaf placement: no cycle improvement

## Decision

Keep the original **981-cycle / 1,465-word** experimental candidate. Changing which leaf pairs use arithmetic did not improve the tested compiler policy. Production remains unchanged at commit `5691617`, with a 1,041-cycle default.

This follows the [selector-balance experiment](plateau_selector_results.md). That experiment selected two arithmetic leaf pairs at depth 3 and three at depth 4, always using the first pairs. This screen varied their identities while keeping those counts fixed.

## Screen and joint checks

The screen covered all `choose(4,2) * choose(8,3) = 336` placements at the existing 29-site cache plan. Pair numbers are zero-based positions in each depth's permuted selection table, not tree node numbers. History storage, bit order, startup priority, forecast policy, and eager difference setup stayed fixed.

The explicit prefix control reproduced the original 981 program's instruction digest. Every feasible candidate then executed full-width frozen seed 461. Scratch rejects were not lowered or executed.

| Stage | Configurations | Feasible smoke passes | Scratch rejects | Feasible cycle range |
|---|---:|---:|---:|---:|
| Leaf placements, including control | 336 | 318 | 18 | 981–991 |
| Two full cache-toggle neighborhoods | 128 | 114 | 14 | 984–1,001 |

Fourteen placements tied at 981 cycles, including the original. The two best feasible non-control placements were selected by cycles, scratch, and canonical pair order:

| Depth-3 pairs | Depth-4 pairs | Cycles | Scratch |
|---|---|---:|---:|
| `(0,1)` | `(0,1,3)` | 981 | 1,465 |
| `(0,1)` | `(0,2,3)` | 981 | 1,497 |

Each received all 64 single-cache toggles. Neither neighborhood contained an improvement or even a 981-cycle tie. These joint checks matter because the earlier selector-count experiment found gains that were absent from standalone changes.

All 464 planned configurations completed in 60.78 seconds with four local workers. There were no compilation exceptions, timeouts, or feasible correctness failures. The twenty-second per-compilation cap was not reached. Even the rejected schedules were not hidden speed winners: the fastest estimated placement reject was 986 cycles / 1,538 words; the fastest joint reject was 985 / 1,553. Neither is an executable result.

## Strong verification of a non-prefix tie

The `(0,1)` / `(0,1,3)` alternative passed:

- 100 full-width seeds and five asymmetric patterns;
- independent lane ownership and three deterministic compiles;
- dependency, constant, and selector corruption rejection;
- all nine unchanged frozen tests through the experimental adapter;
- supplementary checks, including nine other shapes and three legacy performance ceilings;
- fresh hash-seed-17 generation with runtime-data and reference helpers forbidden.

Both the original and non-prefix 981-cycle programs were executed and rejected at a deliberately tighter 980-cycle ceiling, exactly as `((981, 980),)`. The non-prefix program passed at 981. The integrated 1,041 control was rejected at 981 as `((1041, 981),)`. Thus the negative result did not rely on a performance gate that accepts everything.

Z3 proved normalized pair-difference selection and found a counterexample for the wrong difference expression. An independent structural check covered 944 mask/permutation cases: all six depth-3 masks over eight positions and all 56 depth-4 masks over sixteen positions. This is not a formal whole-compiler proof.

The verified tie has the same operation counts and gather endpoints as the incumbent: 1,888 loads, 947 flow, 5,797 VALU, 11,516 ALU, and 32 stores; first/last gather 61/969. Its instructions differ, confirming that the placement change was exercised. Repeat selected-plan compiles took 0.439 and 0.467 seconds. These are not automatic production-selection timings.

```text
Retained incumbent:
8801c539f3a3f66babc875f7b082c4395406fc98ffe732d492f535833049c13e
Verified non-prefix tie:
a728e6941e460785a58de0d550ec8b077d71e066c833d8fa69f1231b0449068c
```

## Scope and artifacts

The negative result covers all placements at fixed counts `(2,3)` and this cache plan, plus two complete joint neighborhoods. It does not cover other counts at the final cache plan, per-lookup placement policies, coordinated multi-cache moves, or a different instruction mix. The incumbent's 967-cycle capacity bound remains stream-specific, not a proven global minimum or an attainable guarantee.

Artifacts are in `/tmp/perf-leaf-placement.FfOTWK/`: protocol, compiler snapshots, manifests, rows, baseline, verification, proofs, and source hashes. `best.json` retains the original prefix winner. `finalist.json` and `winner.json` identify the strongly verified non-prefix tie; the latter is a verifier filename, not a promotion decision.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-leaf-placement.FfOTWK/screen.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-leaf-placement.FfOTWK/verify_winner.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-leaf-placement.FfOTWK/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-leaf-placement.FfOTWK/probe.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-leaf-placement.FfOTWK/probe.py candidate-tight
```

Existing sources and the prior untracked report were preserved by hash. No production changes, commit, push, cloud work, or external submission occurred in this experiment.
