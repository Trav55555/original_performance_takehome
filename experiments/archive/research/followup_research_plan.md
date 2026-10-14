# Follow-up research plan: make the final outputs finish earlier

Status: proposed. This document does not authorize execution. The earlier search budgets are closed, and both earlier exact workers have terminated.

The [machine-readable contract](followup_research_plan.json) records budgets and gates. The execution driver must implement and test its guards before launch.

## Goal and scope

Find a complete, legally executed kernel in **980 cycles or fewer**, with at most **1,536 scratch words**. The incumbent is 981 / 1,449. Compilation speed is secondary. Memory-only gains and abstract timing witnesses are not speed breakthroughs.

Run a small diagnostic pilot, at most one exact repair, and at most one evidence-selected heuristic or rewrite arm. Do not run all three fallback arms or repeat the previous thousand-case grid.

The [lessons](research_lessons_and_directions.md) motivate this plan. The [terminal evidence](untimed_solver_outcomes.json) records why the two previous exact searches stopped: memory exhaustion, not infeasibility.

## Baselines

Use the copied generator in `/tmp/perf-breakthrough.nxDOHi/`, with explicit configurations rather than helper defaults.

| ID | Configuration source | Cycles / words | Role |
| --- | --- | ---: | --- |
| H | `baselines.json`, key `H` | 981 / 1,449 | Existing incumbent |
| A | `verified_best.json`, field `config` | 981 / 1,449 | Two per-use selector conversions; new repair graph |

Expected instruction digests:

```text
H bb9d4d571efe957980370c8ec758ff3b914b6309d146d80e9ab8dfc4ea73e6b5
A 504932cb0e5bb31fff4e4fbc57af8d61d7c90c2aaea9d7cd7601b8d4b7162024
```

A has empty flow slots at cycles 957 and 958. H has none in cycles 949 through 969. Those observations do not establish that another operation can legally occupy either gap.

Abort preparation if source artifacts are missing or either baseline fails to reproduce. Preserve production, frozen tests, the simulator and previous reports.

## Budgets and authority

| Work | Maximum |
| --- | ---: |
| Benchmark control compilations, including fault-injection controls | 12 |
| Diagnostic target-980 preflights | 6 |
| Solver validation queries, including any symbolic rewrite checks | 12 |
| Target-980 optimization queries | 1 |
| Conditional-arm candidate evaluations | 64 |
| Conditional arms selected | 1 |

The maximum ordinary screening/control compilation budget is **76**. Preflights are model analyses, not additional candidate schedules. Final verification replays and reconstruction of the single solver witness are separate, explicitly logged categories. They must not hide new proposal searches.

Use at most two compiler workers and one optimization worker at once. Give the exact worker a 2 GiB address-space cap. No solver, CPU, subprocess, supervisor or foreground tool deadline may wrap the authorized exact run. Use persistent supervision so the interactive session need not wait for its completion.

These are proposed resource limits, not estimates that guarantee completion. Unused budget expires. No automatic retries, widening, memory increases, installations, GPU training, cloud work or external submissions.

## Phase 0: reproduce and validate the observation path

Reproduce H and A, including charged setup, stores and pause. Metadata-only instrumentation must preserve their exact instructions.

Export fresh SSA dependencies and native engine assignments. Validate operation/lane coverage against the compiler, then reconstruct the native program through allocation. Do not derive executable schedules by moving instructions with stale physical scratch addresses.

Required controls include:

- Exact native reconstruction and independent lane/capacity checks.
- Rejection of a missing dependency and a wrong lane mapping.
- Scratch rejection before any call to lowering.
- A same-encoding native timing witness.
- Small capacity/boundary counterexamples and an executable store/pause shortening control.
- Rejection of source-hash and budget violations before workers start.

Reserve the finite solver-validation catalogue before invoking it. Use fixed native witnesses or small toys, not additional benchmark optimization attempts disguised as tests. Any conditional rewrite must reserve its symbolic proof queries within the same validation budget.

A failing correctness, identity, boundary-accounting or provenance control stops the phase. Fix and record an implementation defect before proceeding; do not reinterpret it as a failed research hypothesis.

## Phase 1: explain the gaps and competing endings

Analyze both graphs and all 32 output stores. A target of 980 means the final charged bundle is cycle 979. Derive operation-specific latest issue times from the actual dependency graph; do not assign every select a deadline of 968 just because one ending has 11 cycles.

For each operation contributing to a late output, record:

1. Native issue time and the completion times of required input lanes.
2. Earliest readiness under the recorded schedule.
3. Latest allowed issue time under the target's dependency relaxation.
4. Native engine and occupied slots when it could have issued.
5. The operations that received those slots instead.
6. Which outputs depend on it and when those outputs currently finish.

At cycles 957 and 958, identify missing operands of the next relevant flow operations and trace their producers backward. The greedy scheduler normally issues a ready select when flow capacity exists. An empty slot is therefore not evidence of deliberate deferral. The producer's scheduling may be the real issue.

Record readiness and capacity at the decision point as well as the final cycle occupancy. A full engine explains one schedule's contention; it does not prove its chosen ordering is mandatory.

The allocator runs afterward. Keep allocation rejection distinct from the scheduler's live-word pressure score. Track every output after changes, since improving one ending can expose another.

Deliver `gap_blockers.json`, `output_deadlines.json` and an interpretation naming the strongest supported blocker. These diagnostics are proposal evidence, not proof of an attainable makespan.

## Phase 2: six preflights, at most one exact repair

**Hypothesis:** A's changed instruction mix permits a small retiming that the forward scheduler missed.

Preflight both H and A at each scope below. All starts refer to the native 981-cycle program.

| Suffix width | First movable cycle | Fixed prefix |
| --- | ---: | --- |
| 32 | 949 | 0 through 948 |
| 64 | 917 | 0 through 916 |
| 128 | 853 | 0 through 852 |

Use fixed native engines, true-data dependencies and no physical scratch-reuse ordering. A movable job's domain is the intersection of the suffix, native time plus or minus eight cycles, and target cycles 0 through 979. Model the final pause at 979 and charge its flow slot. Leave load order unpinned. Do not add lane-order constraints in this pilot.

Propagate release/deadline constraints and check mandatory resource windows. Independent checks must recount any reported overload. H is a comparison, not a requirement to manufacture an expected UNSAT result.

For fixed jobs, carry their resource occupancy into residual capacities and their edges into boundary release/deadline constraints. Check fixed-to-fixed edges and reject negative residual capacities. Preserve a mapping back to the full schedule for independent validation. Keep data-dependency lag one separate from zero-lag ordering or control relations; do not reuse a validator that assumes every edge type has the same lag.

The previous compact solver already used constant terms for singleton domains. Do not claim that replacing those with constants is a new optimization. The main changes are the A graph and smaller free scopes. Explicit boundary projection must demonstrate its additional reduction and equivalence.

### Admission and selection

Select the smallest A suffix that:

- passes difference and mandatory-capacity checks;
- has at most 2,048 non-singleton issue-time variables;
- needs at most 32,768 potential job/cycle membership terms before capacity encoding.

Count membership terms as the sum of domain sizes for free jobs. These conservative structural caps are proposed admission rules, not a memory guarantee. Record why each scope fails. Do not solve H, grow beyond 128 or raise the caps automatically.

Before the one target-980 query, require native-981 witness acceptance and boundary controls in the same reduced encoding. Passing preflight is not coupled feasibility.

### Outcomes

- **SAT:** persist the complete timing witness first. Expand fixed jobs and lanes, validate all full-model constraints, then allocate fresh scratch. Lower and execute only if allocation fits. Complete full verification before claiming a new best.
- **UNSAT:** report the graph, engines, prefix and displacement scope. Do not infer global optimality or automatically try the next suffix.
- **Unknown or out of memory:** preserve the direct reason and stop exact work. No restart or memory increase.
- **No admitted scope:** launch no optimization query. Use the obstruction evidence to select a conditional arm.
- **SAT but allocation fails:** retain a timing-only witness. It is not an executable result; no allocator search or second solve is included.

## Phase 3: select one conditional arm

Freeze the selected arm, sites, variants and controls before its first screen. Selection uses Phase 1 evidence, not an urge to spend the remaining budget. It can proceed while the one admitted exact worker runs, in a separate source copy. No change may retarget that live query.

If the evidence is ambiguous or supports none of these mechanisms, stop with that finding rather than test all three. If more than one qualifies, prefer a directly observed avoidable predicate delay, then producer scheduling deferral, then a work-changing quartet rewrite. Record the opposing explanation.

### Arm O: arrival-aware order at individual lookups

Choose this when a late predicate enters early in a critical depth-4 selection tree and leaves avoidable selector depth afterward.

For each baseline, select at most four relevant cached lookups. Compare the native order with three deterministic alternatives: move the latest-ready predicate last, sort predicates by observed readiness, and swap the latest-ready predicate with the last position. Deduplicate equivalent orders.

Cross each order with two scoped arithmetic policies: all-flow leaves and the existing mixed-leaf policy. Include each policy's native-order control to separate order effects from arithmetic changes. The cap is `2 graphs * 4 lookups * 4 orders * 2 policies = 64` evaluations.

Permute leaves consistently. Prove all predicate-to-leaf mappings with symbolic leaves. Charge new differences and broadcasts. Preserve A's conversions by semantic meaning; reject a combination if that cannot be done, rather than silently changing what an old pair number names.

Promotion evidence is earlier actual predicate-to-node completion without worsening the complete program. If bit order changes but readiness or finishing time does not, close the arm. This pilot does not include multi-lookup combinations.

### Arm S: deadline-driven producer scheduling

Choose this when a producer of a late value was ready but lost useful slots to movable work with more finish-time slack. Do not gate solely on empty flow capacity.

Use fixed native engine assignments to isolate scheduling from engine reassignment. Compare forward least-slack construction and backward latest-placement construction. For each direction, test four deterministic tie policies: native order, load-enabling work first, downstream fanout, and estimated live-word pressure. Keep the primary deadline rule unchanged.

This is at most `2 graphs * 2 directions * 4 tie policies = 16` evaluations. Unused slots from the common 64-case ceiling expire. Record each heuristic's exact tie rules before running it.

A heuristic that fails to construct a legal schedule reports packing failure, not UNSAT. An abstract schedule is not a result until independently validated, freshly allocated and executed. Stop if the measured producer delays remain or merely transfer to another output.

### Arm Q: four-way arithmetic selection

Choose this when a two-level cached selector group contributes serial flow work and its coefficients can plausibly be prepared before its predicates are needed.

Initially limit groups to four runtime-loaded cache leaves, so the coefficient costs and opportunities for sharing are explicit. Prove this wrapping 32-bit identity for normalized bits `s,t`, including a counterexample outside that domain:

```text
u = multiply_add(s, b-a, a)
v = multiply_add(s, d-c-b+a, c-a)
y = multiply_add(t, v, u)
```

Test up to four groups per graph, both predicate orientations, and shared-scalar versus per-use-vector coefficient construction. This gives at most 32 single-group configurations. Test all six pairs of the four groups per graph with both coefficient policies, adding at most 24 configurations. For pair cases, put the earlier-ready predicate first, chosen from diagnostics rather than a single-case speed win.

The maximum is 56 evaluations. Pairs remain eligible even when neither single wins. Reject overlapping groups explicitly. Count all coefficient work and compare against the group's actual mix of flow and arithmetic instructions.

Stop if preparation latency, arithmetic demand or scratch pressure erases the observed benefit. Equal selector depth assumes coefficients are ready; it is not a guarantee about the full dependency graph.

## Common screen and promotion gates

The driver must enforce budgets, canonical deduplication and source hashes outside the optimizing policy. Record rejected and failed proposals, not just successful rows. Preserve an append-only attempt log and terminal status files.

For each scratch-feasible candidate, check logical coverage, dependencies, lanes and capacities independently, then execute against the frozen reference. Every rejected allocation must have zero lowering calls. Do not drop constants, setup, stores, pause or non-output memory checks to improve the score.

Before calling any result a new best, require:

- 100 full-width seeds and five asymmetric patterns.
- All nine frozen submission tests, supplementary inputs and other shapes.
- Legacy performance ceilings, fallback and pause/store checks.
- Three deterministic compilations or reconstructions.
- Dependency, constant and selector corruption sensitivity.
- Source-only generation at hash seeds 0 and 17 with runtime/oracle access blocked.
- Executed comparison with H and A; distinguish a speed win from a memory-only tie.

Source-only generation from a selected configuration or a saved exact timing assignment is not automatic production discovery. Keep these provenance categories separate. An exact witness must never reuse stale physical addresses, and its replay must not be described as self-contained compiler selection.

If a result passes the full gate below 981, stop queuing new heuristic candidates. Let in-flight work finish and preserve its results. Do not cancel, restart or retarget an active untimed exact worker without explicit authorization.

## Closing decision and artifacts

Create an isolated workspace only after approval. Retain the protocol, approval record, source hashes, baseline traces, diagnostics, six preflights, admission decisions, validation controls, optional exact query and witness, conditional manifest, attempts, results and verification receipts.

Finish with one of: verified speed improvement, verified memory-only improvement, scoped negative result, or unresolved exact query. If the heuristic arm ends while the exact worker remains active, report partial completion and its actual status. Do not promise an ETA.

No production integration, commit, push, package installation or submission belongs to this plan. A wider search, another fallback arm or a second exact query requires a new decision.
