# Compact fixed-engine scheduling

## Decision

Retain **981 cycles / 1,465 scratch words**. The smaller formulation eliminated the previous memory failures, but all four optimization queries reached their sixty-second solver limit without a witness. Their results are **unknown**, not UNSAT.

A closing structural check identified a lossless lane-order normalization for these models. It is the next useful test; no additional optimization query was run to test it in this program.

## What changed

The [previous probes](earlier_coupling_results.md) allowed engine reassignment and exhausted a 2 GiB address-space budget. This program made two distinct changes:

- **Fixed native engine assignments**, which restricts the feasible set.
- **Collapsed each native vector instruction to one issue-time variable**, which is equivalent to the lane representation within that fixed-engine subset.

Scalar ALU and gather lanes remained separate. Both graphs kept true SSA dependencies, fixed logical issue times before cycle 469, and allowed at most ±8 cycles of retiming afterward. The target remained 980. Scratch reuse ordering was relaxed, so a SAT witness would still require allocation before execution.

| Graph | Native cycles | Instruction jobs | Dependency edges |
|---|---:|---:|---:|
| Original | 981 | 20,180 | 54,157 |
| Final-XOR reassociation | 985 | 20,173 | 54,150 |

Each graph previously used 41,761 lane atoms and 110,409 true-data edges. The reduction is not evidence that the broader engine-choice problem is solved.

## Four bounded queries

The two primary queries left load order free. After neither produced a usable winner, the two declared conditional queries pinned remaining loads in native relative order to two slots per cycle beginning at 469. This load-order policy is an additional restriction, not a dominance claim.

All four passed difference-constraint and per-engine capacity-window prechecks.

| Graph | Load order | Free times | Capacity literals | Build | Solve | Peak RSS | Result |
|---|---|---:|---:|---:|---:|---:|---|
| Original | Free | 10,576 | 177,294 | 7.36 s | 60.37 s | 1.31 GiB | Unknown: timeout |
| Rewrite | Free | 10,569 | 176,747 | 7.35 s | 60.36 s | 1.31 GiB | Unknown: timeout |
| Original | Pinned | 9,471 | 118,496 | 5.31 s | 60.23 s | 0.83 GiB | Unknown: timeout |
| Rewrite | Pinned | 9,485 | 117,097 | 5.37 s | 60.23 s | 0.83 GiB | Unknown: timeout |

Each solver had sixty seconds, a 180-second child wall limit and a 2 GiB address-space limit. Peak RSS is a separate measurement from the address-space limit. None of these queries reported memory exhaustion or hit the child wall limit.

No SAT search witness was returned. No new candidate was allocated or executed, and no faster-kernel full verification suite was run.

## Model verification

Both native assignments satisfied the compact encoding. Expanding them back to lane atoms and rebuilding through the SSA allocator reproduced the exact native digests, scratch usage and frozen cycle counts. Independent lane ownership checks passed.

An additional checker established:

- every atom maps to exactly the intended instruction job;
- collapsed edges match the fixed-mode lane dependencies;
- native per-cycle engine counts are unchanged;
- every propagated time bound matches the uncollapsed model, including pinned-load constraints;
- reported capacity cuts have the correct membership and work;
- a corrupted atom-to-job mapping is rejected.

An executable store/pause control improved from three cycles to two with charged setup. The model rejected a one-cycle target and a corrupted dependency assignment.

## A lossless symmetry reduction

The models contain 1,662 and 1,661 eight-lane instruction families respectively, including already-fixed prefix work. Within each family, lanes have the same engine cost. Across all 20,263 family-edge pairs in each graph, dependencies are either matching-lane edges or complete barriers. Native lane times and the prefix, displacement and load-pin bounds are monotone in lane number.

These properties permit sorting the eight issue times within each family:

1. A matching-lane dependency has `A[lane] + 1 <= B[lane]`. Sorting both vectors preserves this inequality rank by rank: componentwise dominance implies dominance of corresponding order statistics.
2. A complete barrier depends only on the latest source and earliest destination time. Sorting changes neither.
3. Each family keeps the same multiset of issue times on the same engine, so resource occupancy is unchanged.
4. Monotone per-lane bounds remain satisfied after sorting. The fixed prefix remains fixed.

Therefore every feasible assignment in these fixed-engine timing models has an ordered representative. Adding `t[0] <= t[1] <= ... <= t[7]` can remove equivalent assignments without sacrificing timing feasibility under the checked conditions.

The structural conditions were checked exhaustively over both graphs. One thousand generated cases also checked the order-statistic lemma. A nonuniform-edge counterexample shows why this is not a blanket rule for arbitrary graphs: with `A=[0,10]`, `B=[11,1]`, the edge `A[1] -> B[0]` is initially satisfied but fails after sorting `B`.

This normalization has **not yet been tested in an optimization solve**. It neither supplies a 980-cycle witness nor proves that one exists, and scratch feasibility remains a separate gate.

## Artifacts and next step

Add the verified lane-order constraints to the compact model before restoring engine choices or increasing the search window. First confirm that the ordering removes equivalent assignments in practice; all four current outcomes remain unknown.

Workspace: `/tmp/perf-compact-scheduling.l3Ccoq/`. It contains the protocol, copied source models, compact models, controls, four case receipts, independent model checks, lane-family lists, symmetry checks, source hashes and decision. A compact [receipt](compact_scheduling_certificate.json) preserves the key evidence.

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-compact-scheduling.l3Ccoq/check_model.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-compact-scheduling.l3Ccoq/check_symmetry.py original
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-compact-scheduling.l3Ccoq/check_symmetry.py rewrite
```

Production remains at commit `5691617`, with a 1,041-cycle default. Production sources, tests, simulator and prior reports were preserved. No commit, push, package installation, cloud job or external submission occurred.
