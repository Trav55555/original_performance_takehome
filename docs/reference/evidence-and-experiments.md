# Evidence and experiment method

[Wiki](README.md) · [Verification commands](../verification.md) · [Research catalog](search-and-research.md) · [Production reports](../../experiments/README.md#production-promotion-records)

A candidate becomes an optimization result only after its complete legal execution is checked. An experiment becomes production only after the normal builder discovers it under the intended rules.

## Keep the evidence levels separate

| Evidence | Establishes | Does not establish |
|---|---|---|
| Algebraic identity | Equivalent expressions under stated arithmetic/predicate assumptions | Correct emitter wiring, a useful schedule or storage fit |
| Capacity/dependency bound | Necessary cost within a specified graph/model | Attainability or a bound after arbitrary graph changes |
| SAT timing witness | A solution to the encoded constraints | Omitted constraints, physical allocation or runtime correctness |
| Legal logical schedule | Dependencies, lanes and engine capacities fit | Scratch fit after new lifetimes |
| Allocation and lane-owner check | Required storage fits; physical reads refer to intended logical values | Full algorithm/reference equivalence |
| Frozen execution | Checked outputs, memory preservation and complete cycles for the tested inputs | All possible inputs, arbitrary shapes or automatic discovery |
| Source-only cold rebuild | Reproducible generation without saved answers or research artifacts under the tested controls | Global optimality or independent code review |
| Promotion campaign | Public-path verification under the declared contract | Universal correctness or real-hardware speedup |

## Charge the whole computation

Measure initialization, runtime tree loads, coefficient construction, constants, broadcasts, arithmetic, stores and final pause. Do not report a consumer moving earlier as the whole-kernel gain. Another output may still determine completion.

The frozen machine's engine capacities and scratch limit define feasibility. Never lower or execute an over-scratch candidate. A shorter abstract schedule requiring 1537 words cannot beat a legal 979/1463 program on a 1536-word machine.

Report host compilation separately. A selected-config pilot, warm compiler call and cold automatic discovery perform different work. The public 979 cold build took about 16 minutes; the eight-case pilot took 36.749 seconds without automatic discovery. Their times are not interchangeable.

## Use controls that can fail

Useful controls in this project included:

- Missing/spurious data dependencies, duplicate lane writes and illegal timing.
- Corrupted hash constants and swapped selector branches.
- Injected and naturally occurring scratch overflow, rejected before lowering.
- An exhausted budget rejected before candidate construction.
- A valid 980-cycle program rejected by both the earlier 979 and current 975 performance gates.
- A small scheduling example that really becomes shorter while moving an operation later.
- Named simulator, input-generation and reference entry points blocked during source-only construction.

A negative control should fail for the intended reason. Catching any exception and calling that success can hide a broken test. The [fork audit](../../experiments/github_1063_audit.md) also found a generator that returned a partial program when scheduling failed, demonstrating why instruction length alone is unsafe.

## Bound the experiment before running it

Define the hypothesis, comparison graph, allowed transformations, candidate budget, controls and conditional verification gate. Reserve attempts before construction. A scratch rejection or failed attempt still consumes its declared reservation where the protocol specifies it.

Keep alternative experiments isolated from production and from one another. A control may explicitly replay a published timing; candidates and production discovery must not silently inherit that saved answer. Record whether reconstruction was same-process, cold-process or isolated source-only.

Closing a manifest closes its unused slots too. OOM does not permit automatic retries, larger RAM or transferred budget. Timeout and OOM remain unknown. An UNSAT result must retain its graph, prefix, engine and allocation restrictions.

For a new result, preserve both a decision and a receipt. The decision explains what was learned, what was rejected and what remains uncertain. The receipt identifies sources, parameters, limits, outputs, digests and actual checks. Do not replace either with a winning number alone.

## Artifact availability and historical status

The [975 evidence manifest](../../experiments/promotion_975_evidence/manifest.json) records the verified commit, commands and source/artifact hashes. Adjacent raw logs preserve the completed compiler, optimizer, supplementary and submission results. The [979 evidence directory](../../experiments/promotion_979_evidence/) and [receipt](../../experiments/promotion_979_receipt.json) remain unchanged historical records. Current compiler source and standalone verifiers reproduce production without the temporary workspaces.

The [campaign code collection](../../experiments/archive/campaigns/README.md) preserves final-hash, mathematical-model and slope/select sources, reports and protocols. It does not include generated graphs, saved programs or replay tooling. The source files match their historical capture bytes, but the collection is not a self-contained experiment reproduction.

Other reports point to `/tmp` drivers and graphs that may not survive. The [research catalog](search-and-research.md#local-only-records) explicitly identifies untracked local records. A fresh clone does not contain them. Summarizing their findings in this wiki is not the same as archiving all their artifacts.

Reports and receipts describe their creation-time state. A statement that no commit occurred may be followed by a later published promotion. An old status observation that a solver was running may be followed by an OOM closure. Preserve the original record; link its successor from the maintained index or history.

Likewise, old source-hash guards may fail against today's compiler because the source intentionally changed. Do not rewrite old hashes to make a historical audit appear current. Use its pinned revision and artifacts, or record that reconstruction is unavailable.

## Maintaining this wiki

For each new technique, add its mechanism, assumptions, comparison result, verification level and source. Label hypotheses and untested extensions. Add the measured milestone to the [history](../performance-progression.md#milestone-ledger) only with its production/experimental status intact.

Prefer links to a canonical report over copying entire matrices into several pages. Keep raw evidence unchanged. Review links and status when a technique is later promoted; do not turn an earlier negative result into an impossibility claim or erase it because a later combination worked.

Use the [verification guide](../verification.md) for current commands. This wiki does not authorize new experiments, solver runs, publication or changes to the frozen benchmark.
