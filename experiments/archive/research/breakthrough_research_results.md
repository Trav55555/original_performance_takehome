# Breakthrough research results

The approved four-arm program did not beat **981 cycles / 1,449 scratch words**. Keep the previous H configuration as the experimental incumbent. A new selector variant tied both costs, but added arithmetic work and did not earn promotion.

The useful finding was narrower: restoring critical-path urgency recovered a selective rewrite from 991 to 981 cycles. Both programs passed full verification. This supports the suspected priority-demotion effect, but does not improve the incumbent.

## Budget and coverage

The run used 989 counted compilations against a maximum of 1,012. These comprised 977 new search attempts and 12 control compilations. One control injected an oversized allocation, so the registry contains 988 unique configurations. Verification replays were separate and did not generate new proposals.

Of those configurations, 954 passed allocation, independent lane/capacity checks and frozen execution. Another 28 exceeded scratch and never reached lowering. Six proposals removed a cached lookup required by an explicit selector conversion; the generator rejected them without silently dropping the conversion.

| Arm | New configurations | Executed | Scratch rejected | Incompatible | Best screened cycles / words |
| --- | ---: | ---: | ---: | ---: | --- |
| A, per-lookup selectors | 308 | 308 | 0 | 0 | 981 / 1,449 |
| B, rewrite-aware priorities | 49 | 49 | 0 | 0 | 981 / 1,465 for an active change |
| C, selector-first cache search | 604 | 570 | 28 | 6 | 981 / 1,505 |
| D, cross-arm combinations | 16 | 16 | 0 | 0 | 981 / 1,473 |

A covered all 312 declared single/pair configurations; four had already run as controls. B covered 56 distinct configurations from its nominal 64-case factorial, with seven control results reused. Some B settings reproduced the original 981 / 1,449 instructions exactly. The table names the best active B variant instead of presenting a no-op as progress.

C used all 12 profile evaluations, 576 cache toggles and 16 swaps. D used all 16 combination slots. Unused budget expired. No further tuning, training or optimization solver jobs followed.

## A removed flow work, but did not finish earlier

The strongest A tie added per-use arithmetic conversion at these zero-based selector locations:

```text
block 22, round 15, layer 0, pair 6
block 29, round 15, layer 0, pair 7
```

It retained H's block-14 final-XOR rewrite, ALU/VALU/VALU preferences and ordering choices at cycles 179, 339 and 703. Every extra difference operation was charged.

| Engine | Previous H | New A tie |
| --- | ---: | ---: |
| Load | 1,888 | 1,888 |
| Flow | 947 | 945 |
| VALU | 5,797 | 5,799 |
| ALU | 11,516 | 11,532 |
| Store | 32 | 32 |

Two flow operations disappeared, at a cost of two VALU operations and 16 ALU operations. The last select still issued at cycle 969, followed by 11 cycles through the final store. The late uninterrupted flow run began at cycle 959 rather than 616. Removing flow work created gaps without moving completion earlier.

All 312 A configurations were scratch-feasible. Their complete cycle counts ranged from 981 to 992, with 33 speed ties. This rejects the declared 12-site, single/pair neighborhoods as a route to a faster measured kernel. It does not cover all lookup sites or larger coordinated sets.

New tie instruction digest:

```text
504932cb0e5bb31fff4e4fbc57af8d61d7c90c2aaea9d7cd7601b8d4b7162024
```

## B confirmed a priority effect

The implementation matched operations through semantic context and recursive operand identity, not instruction numbers. It restored critical-path urgency, emission-position priority, or both. Scheduling and lookahead used the same adjusted values. No execution dependencies or instructions were added by these switches.

The strongest paired recovery used the final-XOR rewrite on block 29 with ALU/VALU/VALU preferences and no ordering overrides:

| Priority policy | Cycles | Scratch words | Last select | Following cycles |
| --- | ---: | ---: | ---: | ---: |
| Current priorities | 991 | 1,465 | 980 | 10 |
| Restored critical urgency only | 981 | 1,465 | 969 | 11 |

Restoring urgency moved the last select earlier, but the final schedule again ended with an 11-cycle tail. The shortened block-29 tail no longer determined completion. The result returned to the incumbent's speed rather than beating it.

Separately, restoring both priority terms on the block-14 selective graph tied 981 cycles while reducing scratch from 1,473 to 1,465 words. Its match covered 8,542 unchanged operations. An independent audit checked their 20,292 operand edges.

## C and D did not convert the findings into a gain

C used H, the new A tie and the active B representative as its three seeds. It tested neighboring selector profiles before cache changes. It expanded the native profile and both flow-reducing neighbors even when they were slower alone. Oversized parents could generate child proposals, but could not be lowered or executed.

The best new C configuration swapped cache location `11,4` for `18,4` on the A seed. It tied 981 cycles but required 1,505 words. All 16 D combinations also ran in 981 cycles; the smallest used 1,473 words.

The lower-scratch schedule therefore did not enable a better result in these declared neighborhoods. Neither the memory saving nor the priority effect was assumed to transfer between graphs.

## Verification and safeguards

The four original controls reproduced their exact instruction digests. Metadata-only changes and no-rewrite priority switches were no-ops. Symbolic checks proved the selector identity for arbitrary 32-bit operands with normalized predicates and found a counterexample when the predicate was two.

Full verification covered the A tie, the block-14 B representative, and both sides of the block-29 recovery. Each passed:

- 100 full-width seeds and five asymmetric patterns.
- Independent lane, dependency and capacity checks, plus non-output memory preservation.
- Three deterministic compilations and dependency, constant and selector corruption controls.
- All nine unchanged frozen submission tests.
- Supplementary random, pattern, other-shape, legacy and pause/store checks.
- Source-only generation at hash seeds 0 and 17 with runtime/oracle access blocked.
- Executed comparisons against N, H and the slower 1,041-cycle control.

The previous H program remained a valid speed and scratch tie. It was not incorrectly rejected as a failed speed control. A recorded 1,545-word failure also replayed with zero lowering calls and no execution.

The audit reconciled manifests, budgets, deduplication, actual execution status and the selected program digest. Budget-overrun and source-hash corruption probes started zero workers. Production, tests, the simulator and prior reports remained unchanged.

The initial foreground preflight had a 120-second tool-call limit and completed without interruption. This differed from the protocol's blanket no-deadline wording. Screening workers had no wall/CPU deadlines, and neither existing exact solver was affected. No timeout occurred.

## Decision and artifacts

Archive these completed neighborhoods. Keep H as the incumbent rather than replacing it with the lexicographically selected A tie. The tests support a real priority effect, but not a new best cost or a claim of optimality.

At the closing snapshot, the original and hybrid exact workers were still running. Their original no-timeout policies and 2 GiB address-space limits remained intact. Their eventual results are separate from this completed search.

Workspace: `/tmp/perf-breakthrough.nxDOHi/`.

It retains the approved protocol, generator changes, manifests, append-only results, source hashes, independent audit, paired comparisons, verification logs and programs. The [machine-readable receipt](breakthrough_research_receipt.json) records counts, configuration identities, verification and the solver snapshot. The [research plan](breakthrough_research_plan.md) remains unchanged as the historical proposal.

Nothing was integrated, committed, pushed or submitted.
