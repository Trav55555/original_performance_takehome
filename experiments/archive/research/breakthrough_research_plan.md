# Research plan: break the 981-cycle plateau

Status: proposed, not started. Approval is required before new experiments run. The existing two untimed solvers continue under their original authorization.

## Objective and decision

Find a complete, correctly executed kernel below the current 981-cycle result. The first success threshold is **980 cycles or fewer**, with at most 1,536 scratch words. A memory-only improvement is useful research evidence, not a runtime breakthrough.

Prioritize per-lookup selector conversion. Test rewrite-aware priorities independently in parallel. Then combine promising settings with selector-first cache searches around the lower-scratch schedule. Do not start another neural-training program: the last training set contained no faster examples.

This plan allows at most **1,012 unique screening/control compilations**. Finalist verification replays are counted separately. Budgets limit configurations, not elapsed time. Unused budgets expire rather than moving silently to another arm.

| Phase | Maximum compilations |
| --- | ---: |
| Controls | 16 |
| A: per-lookup conversion | 312 |
| B: rewrite-aware priorities | 64 |
| C: selector-first cache search | 604 |
| D: cross-arm combinations | 16 |
| Total | 1,012 |

## Baselines and prior evidence

| ID | Cycles | Scratch words | Role |
| --- | ---: | ---: | --- |
| N | 981 | 1,465 | Original verified graph, no ordering overrides |
| R | 981 | 1,473 | Selective block-14 rewrite and engine preferences, no ordering overrides |
| H | 981 | 1,449 | R plus three ordering choices; current resource winner |
| G | 985 | 1,465 | Earlier global final-XOR rewrite, default preferences |

Use H as the incumbent and N as the main independent control. H has 87 unused words, 16 more than N. That saving is not assumed to survive graph changes.

Selected configurations and receipts are under `/tmp/perf-hybrid-search.R8glwM/`. N is in `winner.json`, R in `exact_seed.json`, and H in `verified_best.json`. Preserve them. Copy and hash sources before implementation; abort if a temporary artifact is missing or a control no longer reproduces.

What the previous work established:

- Global selector/cache combinations previously enabled 984 to 981, despite no standalone selector improvement.
- Global leaf-placement sweeps did not cover per-lookup selector policies.
- Shorter final dependency chains did not reliably produce faster schedules.
- The latest combined search found scratch savings, not a faster training example.
- On the original graph, retaining the prefix through cycle 615 and its remaining flow work forces at least 981 cycles. This is a scoped certificate, not a global optimum.

The earlier 965 to 969 figures were scoped lower bounds, not achieved programs or guaranteed headroom. Changed graphs require fresh bounds.

Recheck active solver results before launching. If either produces a candidate, finish its outstanding verification first. Rebase this plan only after an explicit recorded update to the incumbent and success threshold.

## Phase 0: establish controls and attribution

Budget: at most 16 control compilations, plus symbolic and structural checks.

1. Reproduce the four baseline digests, complete cycle counts and scratch allocations.
2. Add stable semantic labels for block, round, hash stage and selector location. Metadata-only changes must reproduce baseline instructions exactly.
3. Capture resource usage by cycle, selector issue times, downstream output chains, live-word estimates and actual allocation. Proposal scores are heuristics, not feasibility proofs.
4. Give transformed operations stable site keys. Do not match different graphs by raw instruction number.
5. Prove selector conversion for arbitrary 32-bit operands and predicates restricted to zero or one. Include a non-normalized-predicate counterexample.
6. Confirm the scratch guard rejects before lowering. Exercise dependency, output-corruption and invalid-site controls.

Stop before search if any identity, mapping, control digest or safety check fails.

## Arm A: per-lookup selector conversion

Hypothesis: converting a few bottleneck-critical flow selections to arithmetic removes serialized work without paying for a global selector-profile expansion.

Scope: first-layer cached selectors whose predicates are demonstrably normalized. Use the existing identity, with wrapping 32-bit arithmetic:

```text
select(p, yes, no) = no + p * (yes - no), for p in {0,1}
```

For N and H separately, freeze a manifest of up to 12 eligible sites. Allocate eight slots to late output-critical selections and four to selections near earlier flow/load bottlenecks. Rank deterministically from native compiler traces and record excluded sites. Runtime tree values are not inputs to selection.

Test two difference-construction policies:

- Shared: reuse an existing difference or construct it once per operand pair.
- Per-use: construct a separate difference for each converted lookup.

All added subtraction, broadcast or other setup instructions count. Per-use construction does not guarantee late issue; measure its actual lifetime. Deduplicate shared expressions before allocation.

For each baseline and construction policy, test all single sites and all pairs among the 12 sites. Pair tests must not depend on a single-site speed win.

Budget: `2 baselines * 2 construction policies * (12 singles + 66 pairs) = 312` evaluations maximum.

Mechanism checks: did the requested flow selections disappear, did charged arithmetic work increase as expected, and did late flow pressure or completion time improve? Check actual allocation rather than assuming one temporary costs only eight extra peak words.

Failure interpretation: no useful result rejects this declared local conversion set, not all per-lookup mixing. A slower candidate with the intended resource trade may enter the bounded combination stage.

## Arm B: preserve urgency after algebraic rewrites

Hypothesis: some rewrite benefit is lost because the current priority function demotes a shortened dependency chain or changes the ordering scores of unrelated operations.

Test a factorial comparison with two independent switches:

1. Critical-path urgency: current graph values versus restored baseline urgency for uniquely matched unchanged operations.
2. Position priority: current emission-order contribution versus baseline contribution for those operations.

Restored urgency uses the greater of current and reference critical-path values for matched unchanged operations. New or genuinely changed operations retain the current-graph rule. Build the reference graph with the same cache/selector configuration but no final rewrite. Match by semantic identity and operands, not numeric IDs. Abort ambiguous matches.

These switches alter priority only. They must not insert artificial execution dependencies or instructions. The scheduler and its lookahead must use consistent priority definitions.

Test N and H with four rewrite masks: none, all blocks, the latest-finishing native block, and the retained block-14 mask. Cross these with both final-operation preference profiles already used by N and R, and all four switch combinations.

Budget: `2 baselines * 4 masks * 2 engine profiles * 4 priority policies = 64` evaluations maximum, before deduplication.

Measure changed priorities, actual decision changes, last relevant flow issue, dependency-tail length and complete cycles. If priorities change without recovering flow timing or runtime, the hypothesis has not earned further tuning. Do not assume it caused the previous regression.

## Arm C: selector-first cache search

Hypothesis: scratch headroom and a different resource balance enable combinations missed by the previous cache-before-selector search.

Use up to three distinct seeds: H, one representative from A, and one from B. Choose each arm's seed from scratch-feasible candidates showing its intended mechanism. Prefer the lowest complete cycles, then scratch, then a stable configuration key. Do not require a standalone speed win. Skip an arm's seed if no candidate exercised its mechanism legally.

For each seed:

1. Evaluate the four neighboring global selector profiles around the current profile: `(2,2)`, `(2,4)`, `(1,3)` and `(3,3)`.
2. Retain the native profile and both flow-reducing neighbors, `(2,4)` and `(3,3)`, for cache expansion, even if they are individually slower. Confirm their selector-count reductions after local overrides.
3. Test all 64 cache toggles under each of these three profiles.

An over-scratch profile may still generate child proposals. Do not attach an executed cycle count to that abstract parent or lower it. Every child must independently pass allocation before execution. This avoids pruning a combination merely because its parent allocation failed.

This ordering is deliberate: **selector change first, cache search second**. It must not discard a slower selector profile merely because H is still the fastest standalone configuration.

For the best two resulting parent settings, also test eight cache swaps each. Select four from paired toggle estimates and four diverse swaps using a fixed seed. Predictions choose experiments; only complete execution ranks outcomes.

Budget: at most 12 profile evaluations, 576 toggles and 16 swaps, totaling **604**.

## Arm D: explicit cross-arm combinations

Budget: at most 16 evaluations.

Freeze a final manifest combining up to four A settings, two B policies and two C cache/profile contexts. Preserve semantic selector-site identities and reject incompatible proposals explicitly. Do not silently drop a requested conversion when a cache change removes its lookup.

Keep each component's uncombined result in the comparison. This distinguishes a genuine combination benefit from a component that already provided the whole gain.

## Execution and safety

A and B may run in parallel after Phase 0. Give them isolated compiler copies and freeze each copy before launching workers. Use at most three compiler workers in total, not three per arm. C waits for both; D waits for C. No additional solver workers or GPU training are authorized by this plan.

The original solver and the hybrid exact worker retain their no-timeout policies and 2 GiB address-space caps. Do not stop, restart, retarget or increase their memory. If they fail from resources, record unknown or failure, not infeasibility. Recheck process identity rather than trusting an old PID alone.

Implement the following controls in the execution driver before launch:

- Per-arm and overall budget assertions, append-only results and canonical configuration deduplication.
- Hash checks for protected sources and immutable baseline receipts.
- A scratch check outside the optimizing policy that prevents lowering above 1,536 words.
- Independent lane/capacity checks and frozen smoke execution for each feasible screen candidate.
- Phase stops on correctness, semantic mapping or provenance failures.
- Persistent progress and terminal-result files without wall/CPU deadlines.

Markdown and the adjacent manifest declare these requirements; they do not enforce them by themselves. Do not repeat old configuration/source pairs without identifying a verification replay or a genuinely changed experiment.

## Evidence and promotion gates

The primary ranking is complete executed cycles, then scratch words. Predicted cost, last-flow timing, training loss and static bounds cannot replace execution.

Before declaring a new best verified result, require:

- 100 full-width seeds, five asymmetric patterns and all nine frozen tests.
- Independent lane ownership, dependency, capacity and non-output-memory checks.
- Three deterministic compilations and corruption rejection.
- Supplementary, legacy, pause/store and fallback checks.
- Fresh source-only generation at hash seeds 0 and 17, with runtime/oracle access blocked.
- Executed comparison against N and H. Reject an old control on speed only when the new result is strictly faster.

Verify the strongest finalists at phase boundaries rather than running the full gate on every screen candidate. Stop publication or promotion on any gate failure. An isolated failing candidate does not invalidate previously verified controls.

Production integration is a separate decision. It requires deterministic automatic discovery rather than saved site lists or ordering tables, plus cold-build and integration checks. Do not modify production, tests or the simulator, install packages, commit, push, submit or deploy during this research program.

## Artifacts and closing decision

Create an isolated workspace only after approval. Retain the protocol, source hashes, candidate manifests, `results.jsonl`, stage summaries, rejected-candidate reasons, instruction digests, verification receipts and a decision note. Every row distinguishes abstract schedule length, allocation feasibility, execution and full verification.

End with one of three outcomes:

- Below 981 and fully verified: retain the experimental winner and propose integration separately.
- Memory-only or mechanism-only improvement: retain it with that narrower label; do not call it a speed breakthrough.
- No useful improvement: archive the completed scopes and report what remains untested.

Do not spend leftover budget on more random schedules or larger models. Use the measured result to decide the next hypothesis.
