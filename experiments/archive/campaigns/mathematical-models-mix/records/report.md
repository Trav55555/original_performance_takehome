# Mathematical-model combinations

## Decision

Keep the published **980-cycle / 1465-word** compiler. Mixing the screened mathematical approaches produced favorable interactions, but no faster complete kernel. None of the forty two-component pairs beat its better component.

Coefficient sharing did improve one experimental tensor variant from 983 / 1497 to 981 / 1481. That is a useful matched result, but it remains slower and larger than production. Do not integrate these variants on the strength of this screen.

The [protocol](mathematical_models_mix_program.md) and [receipt](mathematical_models_mix_receipt.json) preserve the selected factors, budgets, results and audit. Full code and schedules are in `/tmp/perf-math-mix.X7KVbp/`. The [previous screen](mathematical_models_results.md) supplies the component history.

## Why these combinations

The previous program required a strict standalone improvement before trying combinations. No arm met that gate. Earlier project work had already shown that tied or slightly worse choices can combine profitably, so the new program deliberately relaxed that gate.

The four tensor factors were A18, A09, A16 and A21. A18 and A16 apply the same coefficient basis at neighboring late walkers, which can amortize setup. A09 and A21 convert distinct depth-four tiles with smaller standalone scratch costs. Parity factors C02, C06 and C01 cover two projection sites and one carry-aware radix variant. Scheduling factors D01, D10 and D16 provide weak wavefront, Morton and bit-reversed priorities. E01 and E05 compact fixed native-engine event graphs using two different capacity-chain orders.

Broad recursive lookup conversion was excluded from pure scheduling crosses because its retained arithmetic bound was already at least 988 cycles. That bound does not reject new operation elimination or cache reselection, neither of which was attempted for the broad recursive forms here.

An additional factor S reuses exact existing scalar differences and broadcasts during tensor coefficient construction. It performs structural common-subexpression reuse, not value-dependent specialization or whole-compiler rewriting. All runtime coefficient work that remains is charged.

## Screen coverage

Twelve current-run component reproductions matched their earlier cycle counts, scratch sizes and program digests. Four separate controls covered native equality, the published980 timing with fresh allocation, and a small executable event model.

| Family | Evaluations | Best cycles / words |
|---|---:|---:|
| Single-component reproductions | 12 | 981 / 1465 |
| Two-component pairs | 40 | 981 / 1497 |
| Sharing on single and double tensor tiles | 10 | 981 / 1481 |
| Shared tensor plus parity | 6 | 981 / 1481 |
| Event compaction of selected pairs | 16 | 981 / 1497 |
| Tensor plus parity plus geometric order | 4 | 985 / 1522 |

All 88 profiles fit scratch and passed three full-width seed executions each. Seventeen family finalists also passed five asymmetric patterns each. The screen took 106.53 seconds, excluding implementation and audit.

The program used 92 counted attempts including four controls. No candidate reached 980, so the eight conditional validation slots remained unused. All budgets are closed. No solver ran.

## Favorable interaction is not necessarily a useful combination

For complete cycle counts, define the additive interaction:

```text
I(A,B) = T(A+B) - T(A) - T(B) + T(base)
```

Negative values mean that the combination did better than the additive prediction. They do not establish an improvement over either component or the baseline.

Among the forty pairs, nineteen had negative interaction, fourteen had zero interaction and seven had positive interaction. None ran faster than both components.

The strongest favorable pair illustrates the distinction:

| Configuration | Cycles |
|---|---:|
| Native baseline | 981 |
| A09 tensor tile | 983 |
| D01 weak wavefront priority | 987 |
| Additive prediction for A09+D01 | 989 |
| Actual A09+D01 | 985 |

The interaction is minus four cycles. Yet A09 alone is two cycles faster than the combination, and the published kernel is five cycles faster. This is a real departure from additivity, not a new performance win.

A18+C02 tied 981 / 1497. The two individually tied changes did not expose an extra cycle of improvement. Two projected parity sites, C02+C06, took 982 / 1465.

## Sharing helped selectively

Sharing was compared against the exact same unshared configurations:

| Tensor configuration | Unshared cycles / words | Shared cycles / words |
|---|---:|---:|
| A18 | 981 / 1497 | 981 / 1481 |
| A16 | 983 / 1497 | 981 / 1481 |
| A09 | 983 / 1465 | 984 / 1465 |
| A21 | 983 / 1466 | 983 / 1466 |
| A18+A21 | 983 / 1498 | 982 / 1482 |
| A16+A21 | 983 / 1498 | 982 / 1482 |
| A18+A16 | 983 / 1497 | 985 / 1481 |

For A16, sharing reused three definitions. After rescheduling, the program had one fewer vector instruction and nine fewer scalar instructions. Execution improved by two cycles and scratch by sixteen words.

The other rows prevent a blanket conclusion. A09 became a cycle slower despite removing a vector instruction. Sharing the neighboring A18+A16 pair reduced scratch but added two cycles. Reusing logical values changes lifetimes and the heuristic schedule as well as instruction counts; fewer instructions are not an automatic speed gain.

The best shared-tensor/parity combination, S+A18+C02, still tied 981 / 1481. No shared configuration beat the native control.

## Retiming and triples did not unlock another cycle

The sixteen max-plus tests used eight newly generated paired graphs, with two capacity-chain orders each. All sixteen preserved the cycle count of their unretimed counterpart. These results are scoped to those orders and selected pairs. They do not cover every shared single-tile graph or unrestricted rescheduling.

Four three-factor tests combined the two best plain tensor/parity pairs with weak wavefront or bit-reversed scheduling. The fastest was A18+C02+D01 at 985 / 1522. Its third-order interaction was zero after accounting for the measured single and pair effects. The other three third-order interactions were positive one cycle. No tested triple supplied an additional favorable higher-order effect.

## Verification and limits

Every feasible profile passed independent physical lane identity, capacity checks, complete logical dependency checks, frozen-reference outputs, non-output memory preservation and actual cycle accounting. There were 264 candidate seed executions and 85 finalist pattern executions. The controls rejected conflicting configurations, a corrupt encoding constant, over-scratch lowering and an exhausted reservation budget.

The published logical timing reconstructed to 980 / 1465 with the unchanged expected digest. It was used only as a control. Candidate schedules came from current-run native graphs; no solver or saved selected timing drove the combinations.

No profile qualified for the 100-seed/full-winner gate. The unchanged submission suite and oracle-blocked cold builds were not repeated. These are screened research comparisons, not new fully verified incumbents. The search was finite and did not include cache reselection, all tensor sites or all possible capacity-chain orders.

The strongest result to retain is selective coefficient reuse as a research technique. A larger Cartesian product of the same factors has little support from this screen. Further work should identify a concrete dependency or resource obstruction that a new change can remove, then test that change against matched controls.

## Artifacts

The workspace contains frozen sources, `program.md`, `manifest.json`, `selection.json`, unique reservations in `attempts.jsonl`, rows in `results.jsonl`, the complete comparison matrix in `screen_result.json`, and finalist programs under `artifacts/`.

Run a post-run audit without generation or execution:

```sh
python /tmp/perf-math-mix.X7KVbp/audit.py
```

`mix.py` refuses to restart an already-used manifest. Temporary code and physical programs remain subject to `/tmp` cleanup. The repository protocol, report and receipt preserve the analysis, provenance and result rows. Production and prior research sources are unchanged. No files were committed or pushed.
