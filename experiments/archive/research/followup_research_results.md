# Follow-up result: 980 cycles, fully verified

The small exact-repair pilot found a complete executable kernel at **980 cycles / 1,449 scratch words**, improving the previous verified best by one cycle without increasing scratch. It passed the full verification gates. Production remains at the local 1,041-cycle implementation.

The [approved plan](followup_research_plan.md) targeted the two unused flow slots in the A graph. One query on its smallest admitted suffix succeeded. No conditional-arm candidates ran, and no optimization worker remains active.

A durable [source-plus-timing reproducer](followup_980/README.md) and [research receipt](followup_research_receipt.json) preserve the result. This is an experimental kernel, not automatic production schedule discovery.

## Baselines and preflights

Both H and A reproduced their exact 981-cycle / 1,449-word instruction digests. Metadata instrumentation preserved the generated instructions. Fresh SSA reconstruction and allocation also reproduced both native programs.

The model uses one job per native instruction, fixed native engines and true data dependencies. Independent physical-read reconstruction matched its SSA edges: 54,080 for H and 54,154 for A. It contains no physical scratch-reuse ordering or added lane-order constraints.

All six target-980 preflights ran:

| Graph | Movable suffix | Free variables | Membership terms | Result |
| --- | ---: | ---: | ---: | --- |
| H | 32 cycles | 515 | 5,518 | Load and flow overloads |
| A | 32 cycles | 533 | 5,909 | Admitted and selected |
| H | 64 cycles | 1,189 | 17,540 | Flow overload |
| A | 64 cycles | 1,207 | 18,047 | Admitted, not queried |
| H | 128 cycles | 2,535 | 40,222 | Flow overload; also above size caps |
| A | 128 cycles | 2,551 | 40,456 | Above size caps |

For H's smallest suffix, 16 mandatory loads need 14 slots in cycles 962–968, and 21 mandatory flow operations need 20 slots in cycles 949–968. The wider H flow windows exceed capacity by one operation. These are scoped obstructions, not global optimality claims.

Independent fixed-point propagation reproduced the release/deadline bounds. A separate recount checked all 30 reported engine windows. Projection controls compared full and reduced constraints on 11,328 assignments across 200 small graphs, including 28 inconsistent cases.

## The exact query

The single optimization query used A with:

- Prefix cycles 0–948 fixed; later jobs restricted to cycles 949–979.
- At most eight cycles of displacement from each native issue time.
- Native engines fixed, load order unpinned, and the final pause charged at 979.
- 533 free issue-time variables, 831 free-to-free edges and 636 checked boundary edges.
- 19,663 fixed jobs removed from the variable model, with their occupancy retained.
- 5,909 potential membership terms; 5,902 terms in encoded capacity constraints.
- A 2 GiB address-space cap and no solver, CPU or wall deadline.

Z3 returned **SAT in 46.58 seconds**. The complete timing witness was saved before allocation. Expansion passed the full-model constraints; fresh allocation fit in 1,449 words. The frozen machine then executed the reconstructed program in 980 cycles.

This is stronger than an independent-capacity pass or a timing-only witness: allocation, execution and full verification all succeeded. It does not prove that 979 is impossible.

## What changed in the ending

The trace confirmed that A's empty flow slots were waiting for operands. For block 29's final cached lookup, predicate arrivals by selector layer were **959, 945, 914 and 900**. The newest predicate entered the first layer even though it arrived last. Six of its ALU lanes were ready at 957 but issued at 958.

The exact schedule moved all eight predicate lanes to cycle 956, making them available at 957. It filled the two old gaps with first-layer selects that previously issued at 959 and 962.

| Observation | Native A | Retimed A |
| --- | ---: | ---: |
| Last select | 969 | 967 |
| Block 29 output store | 980 | 978 |
| Block 30 output store | 976 | 979 |
| Block 31 output store | 979 | 979 |
| Final charged cycle | 980 | 979 |
| Complete cycles | 981 | 980 |

The result moved 415 jobs, including the pause: 32 load, 102 VALU, 243 ALU, 12 flow and 26 store jobs. The physical prefix through cycle 948 remained identical after fresh allocation. Instruction counts did not change.

The last select improved by two cycles, but competing outputs limited the complete improvement to one. The global interval after the last select grew from 11 to 12 cycles. This supports coordinated scheduling of producers and outputs, not merely minimizing the final selector's issue time.

## Verification and provenance

Completed gates include:

- 100 full-width seeds and five asymmetric patterns, with non-output memory preservation.
- Independent semantic coverage, dependency, lane-owner and engine-capacity checks.
- Three deterministic reconstructions of the candidate.
- Rejection of dependency, duplicate-lane, constant and selector corruptions.
- All nine unchanged frozen submission tests.
- Supplementary 100 standard seeds, five patterns, nine other shapes, three legacy performance ceilings, fallback and pause/store controls.
- Injected 1,537-word and historical 1,545-word failures, both rejected with zero lowering calls and no execution.
- Isolated source-plus-timing generation at hash seeds 0 and 17 with runtime/oracle APIs blocked.
- Executed H/A controls at 981 and the previous production recipe at 1,041.
- A second 100-seed/five-pattern verification through the archived reproducer.

The reproducer takes a selected configuration and semantic timing assignment. It regenerates SSA, validates coverage and dependencies, allocates fresh scratch and lowers instructions. It does not use saved physical instructions, scratch addresses or runtime answers. Selected timing replay is not a self-contained production selection algorithm.

## Budget and implementation defects

The run used seven ordinary control construction/reconstruction reservations, all six preflights, six solver-validation queries and one optimization query. Full verification replays were separate. Conditional candidate evaluations: **zero**.

Diagnostics selected arm O and preparation began in an isolated source copy. No candidate manifest was screened. Once the exact witness passed the full gate, the success rule closed that arm and expired its unused budget. Its draft code was not used in the winner.

Two implementation defects need to remain visible:

1. After saving SAT, the worker's reconstruction import could not locate `problem.py`. The worker exited with code 1. A separate process established the existing repository import path, reconstructed the saved witness and completed verification. No solver restart, retargeting or second query occurred.
2. The original launcher checked source hashes before spawning but checked/reserved optimization budget inside the worker, before solver entry. The closing audit added an explicit pre-spawn budget check and tested the actual launcher with exhausted-budget and changed-source cases; both started zero workers. The original launcher is preserved. No budget overrun occurred.

## Decision

**Retain 980 / 1,449 as the verified experimental incumbent.** Stop this approved program rather than spend the remaining heuristic budget.

The next separate decision is production integration: reproduce the graph and schedule through deterministic discovery, without embedding this experimental site list or timing table as the production answer. Global optimality and any wider search remain open.

No production changes, commits, pushes, installations or external submissions occurred. The detailed workspace is `/tmp/perf-followup.k1MXNr/`; the winning generation sources and assignment also live in the repository archive linked above.
