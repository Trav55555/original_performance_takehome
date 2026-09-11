# Porting techniques from the 1,063-cycle fork

## Decision at experiment close

The candidate below has since been [integrated and verified through the normal entry point](technique_promotion_results.md). The following records the preceding experiment.

Keep a verified **1,052-cycle, 1,457-word prototype** as the next integration candidate. It is 22 cycles faster than our [1,074-cycle prototype](four_frontiers_results.md) and 11 faster than the [audited 1,063-cycle fork](github_1063_audit.md).

The winner combines global hash-stage fusion, mixed arithmetic/select lookup trees, stored branch bits, and a bounded cache reselection. Retroactive ALU packing is not retained. Production remained at 1,076 cycles in commit `0bef02a` during this experiment; no production code, tests, or simulator files changed.

## Bounded screens

All arms began from the same 1,074-cycle control: tile-12 ordering, its twelve cache sites, one-cycle/eight-operation engine lookahead, and address precomputation at block 0, round 3. The control and the older 1,076 program both reproduced their instruction digests exactly.

| Arm | Screen rows | Scratch-feasible frozen passes | Best actual change, cycles / words |
|---|---:|---:|---:|
| Fused hash stages | 87 | 87 | 1,068 / 1,313 |
| Selectors, history, and bit order | 85 | 72 | 1,066 / 1,488 |
| Retroactive ALU packing | 15 | 15 | 1,074 / 1,263 |
| Matched combinations | 24 | 24 | 1,060 / 1,456 |
| Cache reselection under the new costs | 128 | 128 | 1,052 / 1,457 |

There were 339 screen rows, including repeated controls, and 326 feasible frozen smoke passes. Each feasible row executed on a full-width input using seed 461. Thirteen selector configurations exceeded 1,536 words and were not executed. The fastest of those schedules was 1,060 cycles but required 1,913 words. There were no compilation exceptions, timeouts, or feasible smoke failures.

Screens used at most four local workers and a 20-second compilation cap per configuration. The declared arm budgets were respected. No cloud jobs or external submissions ran.

## Hash-stage fusion

For zero-based hash stages 2 and 3, replace:

```text
B = 33*X + C2
Y = (B + C3) XOR (B << 9)
```

with:

```text
A = 33*X + (C2 + C3)
B = 16896*X + (C2 << 9)
Y = A XOR B
```

All operations wrap to 32 bits. The two affine expressions become parallel multiply-adds. New constants and broadcasts are emitted and charged. This is a fresh implementation of the audited identity in our compiler, not an import of the foreign generator.

Global application won the placement screen at 1,068 cycles. Applying it to the first eight rounds reached 1,069; the final eight reached 1,070. The earlier negative affine-rewrite experiment used a different generator and schedule, so its result did not rule out this port.

## Mixed selectors and earlier branch bits

For a normalized bit, a lookup leaf can use `base + bit*(other-base)` instead of a flow select. The program computes differences between runtime-loaded, encoded node values with scalar subtraction, then broadcasts the differences. It shares those tables across lookups.

The selector screen also tested two separable changes:

- Retain normalized branch bits rather than recovering older bits from the current index.
- Permute leaves and consume earlier branch bits first, allowing partial selection before the latest branch bit is ready.

The ablations matter. These are joint results, not gains attributable to arithmetic selection alone:

| Change relative to the 1,074 control | Cycles | Words |
|---|---:|---:|
| Stored branch history only | 1,072 | 1,333 |
| History plus reversed bit order at depth 2 | 1,069 | 1,473 |
| Reversed depth-2 order without history | 1,075 | 1,257 |
| One arithmetic leaf at depth 3, without history | 1,092 | 1,247 |
| That arithmetic leaf with history | 1,070 | 1,334 |
| That leaf with history and reversed depth-2 order | 1,066 | 1,488 |

Aggressive early selection often exceeded scratch. All 32 logical walker contexts remained available; the foreign compiler's 20-group concurrency cap was not imported.

After combining with hash fusion, the best profile changed: use two arithmetic leaf pairs at depths 3 and 4, stored history, and reversed bit order only at depth 3. With the original cache sites, this reached 1,060 cycles and 1,456 words.

## Retroactive packing

The port tries to place all eight lanes of a ready operation into preceding ALU holes, with windows up to eight cycles. It checks each lane's operand-ready time and recomputes lifetimes from the final virtual schedule before physical allocation. Optional broadcast expansion uses scalar `x OR x` copies, without a new zero constant.

Zero-window mode reproduced the control exactly. Two constructed positive controls moved eight lanes and executed one cycle faster: four cycles to three for binary work, and three to two for a broadcast. The implementation therefore could make a real move.

Binary-only policies made no moves on the benchmark. Policies allowing broadcasts moved four lanes of one operation into the previous cycle, but stayed at 1,074 cycles and used 1,263 words instead of 1,240. The twelve matched combination pairs also tied with retroactive packing enabled or disabled; that pass made no moves in those combinations.

This narrow, late full-operation pass added no speed benefit to our existing lane-ready scheduler. It does not rule out other backfilling policies. It is excluded from the winner.

## Reselecting caches under the changed costs

The 1,060 combination changed the resource balance, so cache selection was revisited rather than inheriting the old plan without testing it.

The 128-plan budget covered the control, all 64 depth-4 site toggles, and 63 new toggles around the best first result. Adding `(8, 15)` reached 1,055 cycles and 1,462 words. Also adding `(15, 4)` reached 1,052 and 1,457. No old site was removed.

The final fourteen sites, written as block/round pairs, are:

```text
(2,15), (4,15), (5,4), (5,15), (6,4), (6,15), (7,4),
(8,4), (8,15), (9,4), (11,4), (15,4), (17,15), (29,15)
```

These are search outputs based on scheduled cycles and allocation, not input-specific answers. The final program performs 512 fused hashes and 156 arithmetic selection leaves using four shared difference tables. Difference setup is eager. The prior engine lookahead and single address rewrite remain enabled.

The first gather moved from cycle 76 in the 1,074 control to 68; the last moved from 1,061 to 1,040. These are whole-program observations. They do not isolate a single instruction's causal contribution.

## Verification and limits

Five finalists, one from each arm including the actual retroactive-packing tie, each passed 100 full-width inputs, five patterns, three deterministic compiles, and logical lane-identity checks. The lane checker covers partial broadcast expansion. Dependency, constant, and selector mutations were rejected for every finalist.

The winner also passed all nine unchanged frozen tests and the supplementary verifier through an experimental adapter. The supplementary run covered 100 generated inputs, five patterns, nine other shapes, three shape-specific performance ceilings, and corruption rejection. Other shapes use our unchanged legacy generator. Those tests do not establish generality of the new benchmark-only passes.

The same supplementary 1,052-cycle ceiling rejected the executed 1,074 control exactly as `((1074, 1052),)` and the audited foreign instruction stream as `((1063, 1052),)`. The foreign compiler was not executed during that comparison.

Z3 checked the hash and pair-selector identities and the scalar-OR broadcast copy. A wrong hash multiplier produced a counterexample. Structural checks exhausted 4,282 branch-history/permutation cases through depth 5. A fresh process under Python hash seed 17 reproduced the winner's digest with runtime-data and reference helpers replaced by throwing stubs. These checks are not a formal proof of the complete compiler.

| Engine | Instructions | Capacity-only cycle bound |
|---|---:|---:|
| Load | 2,003 | 1,002 |
| Flow | 786 | 786 |
| VALU | 5,794 | 966 |
| ALU | 11,499 | 959 |
| Store | 32 | 16 |

The 1,002 bound applies only to this instruction stream. It establishes neither attainability nor global optimality.

Selected-program compilation took 0.436 seconds in the screen and 0.407 and 0.418 seconds in repeat checks. These measurements exclude cache search and production integration. The prototype uses temporary configuration files and is not yet a self-contained replacement for the normal entry point.

Instruction SHA-256:

```text
ca588b18f9790385cc509caf5bc5c57b85bff1ab01029766195a48cdd07b4a76
```

## Artifacts and next step

The experiment is in `/tmp/perf-technique-port.272nNK/`. It contains `program.md`, the local compiler and IR changes, `retro.py`, `lane_checker.py`, screen configs/results, `proofs.json`, structural and retroactive positive controls, `verification.json`, `winner.json`, `winner_program.json`, frozen/supplementary logs, comparison gates, and `purity.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/screens.py fusion
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/screens.py selectors
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/screens.py retro
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/combine.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/cache_followup.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/verify_finalists.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/probe.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/probe.py control
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-technique-port.272nNK/probe.py external
```

Replay requires those temporary sources/configs; the external comparison additionally needs the earlier audit export. This report preserves the conclusions, not a portable implementation.

Stop the bounded search here. If promotion is requested, integrate the winning rules and deterministic selection, measure complete compilation cost, and rerun the normal entry point. Do not copy a saved instruction stream or carry the unsuccessful retroactive pass into production. No commit, push, or external submission occurred during the experiment.
