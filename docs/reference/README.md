# Technique and research reference

[Home](../../README.md) · [Full history](../performance-progression.md) · [Architecture](../architecture.md) · [Verification](../verification.md) · [Experiment index](../../experiments/README.md)

Use this wiki to look up a method, its assumptions and what happened when we tested it. Use the performance history for chronology and the architecture guide for today's call path. Current production is 975 cycles / 1469 scratch words at `1df789d`, with [completed verification](../../experiments/startup_ancestry_candidate_results.md).

## Topic pages

| Page | Topics |
|---|---|
| [Representation and algebra](representation-and-algebra.md) | SIMD, mirrored indices, XOR encoding, root folding, hash fusion, final-XOR reassociation, parity, modular inverses and invalid bit shortcuts |
| [Memory and lookups](memory-and-lookups.md) | Retained state, independent temporaries, shallow caches, arithmetic selectors, branch history, tensor/Mobius forms, slope-select, coefficient sharing and rematerialization |
| [Scheduling and allocation](scheduling-and-allocation.md) | Manual packing, list scheduling, SSA, lane readiness, startup priorities, engine selection, backward/forward justification, event graphs, deadlines and scoped bounds |
| [Search and research catalog](search-and-research.md) | Cache neighborhoods, plateau escape, interaction tests, exact-model progression, neural/GPU work, external sources and local-only research records |
| [Evidence and experiment method](evidence-and-experiments.md) | Proof versus execution, full-cost accounting, scratch-before-lower, reproducibility, finite budgets, negative controls and artifact provenance |

## Status vocabulary

- **Production:** used in the current generated compiler path. This does not make it optimal for another machine or workload.
- **Historical retained:** used by an earlier saved implementation; later replaced or generalized.
- **Experimental:** tested in an isolated configuration or screen, not necessarily through automatic production discovery.
- **No improvement:** no faster complete executable program in the stated experiment. It is not an impossibility theorem.
- **Rejected:** a candidate failed equivalence, allocation or another required gate; its attractive timing is not an executable result.
- **Unknown:** the solver exhausted time or memory, or the question was not tested. Neither means UNSAT.

An algebraic identity can be exact while its implementation remains experimental. A production technique can have earlier failed variants. Keep the graph, scheduler, allocation policy and comparison baseline attached to each conclusion.

## Quick technique finder

| Question | Start here |
|---|---|
| Can a coordinate change remove work? | [Mirrored indices and XOR encoding](representation-and-algebra.md#mirrored-indices-and-xor-encoding) |
| Can 2047 nodes replace bounds checks with masking? | [Perfect-tree geometry](representation-and-algebra.md#perfect-tree-geometry) |
| Why can more caching be slower? | [Cache selection](memory-and-lookups.md#shallow-caches-and-selected-depth-4-lookups) |
| Why did a scratch-saving rewrite not help? | [Rematerialization](memory-and-lookups.md#pointer-rematerialization) |
| What exactly does tensor lookup mean here? | [Tensor and Mobius forms](memory-and-lookups.md#tensor-and-mobius-lookup-forms) |
| Why let an instruction move later? | [Backward/forward justification](scheduling-and-allocation.md#backwardforward-justification) |
| Did a lower bound prove optimality? | [Bounds and their scope](scheduling-and-allocation.md#bounds-and-their-scope) |
| What did the neural and exact searches find? | [Solver and learned scheduling research](search-and-research.md#solver-and-learned-scheduling-research) |
| Can I reproduce a report from a fresh clone? | [Artifact availability](evidence-and-experiments.md#artifact-availability-and-historical-status) |

## Machine and semantic boundary

The benchmark has height 10, 2047 nodes, 256 inputs, 16 rounds, one core and eight lanes. Scratch is limited to 1536 words. Per-cycle capacities are 12 scalar ALU, six vector ALU, two loads, two stores and one flow operation. Arithmetic is on unsigned 32-bit words.

The verified output contract is final values from root-starting traversals, with other memory preserved. All runtime-dependent table construction, constants, broadcasts, loads, stores and pause are charged. Compilation may depend on the public shape and generated graph, not runtime tree/input values.

These are simulator results. Caches, variable latency, spills, branches and instruction availability differ on real hardware. The credible transfer is a method for measuring coupled decisions, not a prediction of CPU/GPU speedup.
