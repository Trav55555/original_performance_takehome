# Ordered-lane scheduling: no witness within budget

## Decision

Retain **981 cycles / 1,465 scratch words**. Adding the verified lane-order constraints did not resolve any of the four sixty-second queries. Every result remains **unknown: timeout**. No new schedule, allocation or executable candidate was produced.

This closes the declared budget. Rather than repeat a similar solver run, the next recommended experiment is a small measured heuristic search on the shortened-tail graph, such as changing the engine preferences of its two final XOR operations while keeping the cache plan fixed. That is a hypothesis, not a demonstrated improvement.

## What was tested

The [compact models](compact_scheduling_results.md) fix native engine assignments, preserve true data dependencies and logical issue times before cycle 469, and allow at most ±8 cycles of later retiming. The target is 980. Scratch must be reallocated before any search witness can execute.

This experiment added only the proved normalization:

```text
issue_time[lane 0] <= ... <= issue_time[lane 7]
```

The structural requirements were rechecked: homogeneous engine costs within each family, uniform matching-lane or complete-barrier dependencies, and monotone native and per-lane bounds. The normalization preserves feasibility within these models; it does not make their fixed-engine or displacement restrictions disappear.

The original graph received 11,634 ordering edges and the final-XOR rewrite 11,627. Many concern fixed prefix work or follow from existing bounds. Between 5,236 and 6,155 required explicit solver inequalities in each query.

## Results

| Graph | Load order | Active ordering inequalities | Solver time | Peak RSS | Result |
|---|---|---:|---:|---:|---|
| Original 981 | Free | 6,155 | 60.62 s | 1.31 GiB | Unknown: timeout |
| Rewritten 985 | Free | 6,150 | 60.60 s | 1.31 GiB | Unknown: timeout |
| Original 981 | Pinned | 5,236 | 60.24 s | 0.84 GiB | Unknown: timeout |
| Rewritten 985 | Pinned | 5,240 | 60.24 s | 0.83 GiB | Unknown: timeout |

The pinned variants compact remaining loads in native relative order, assigning two slots per cycle from 469. This remains an additional restriction.

Each query had a sixty-second solver limit, a 180-second child wall limit and a 2 GiB address-space limit. Model construction took 5.55–7.58 seconds. No memory failure or child wall timeout occurred. Peak RSS is a separate measurement from the address-space limit.

The time bounds, capacity literals and preflight cuts were identical to the corresponding unordered cases. Ordering was nevertheless active: a targeted witness was SAT without ordering and UNSAT with it. The negative result is therefore not caused by an unused configuration flag.

## Verification and limits

Both native assignments satisfied the new encoding and reconstructed to their exact original digests, scratch usage and frozen cycle counts. Independent lane ownership checks passed. Executable store/pause and corrupted-dependency controls also passed.

The verification receipt confirms that:

- only ordering edges changed the saved models;
- those edges exactly match the certified lane families;
- ordered and unordered propagated bounds agree;
- preflight cut memberships and capacity literal counts match the prior cases;
- a witness violating only ordering is rejected.

No benchmark SAT witness was returned. Consequently, no new candidate received scratch allocation or the full promotion suite. These timeouts prove neither infeasibility nor global optimality. They also do not establish that ordering never helps; it did not produce a result under this budget.

## Artifacts and preservation

Workspace: `/tmp/perf-ordered-scheduling.slYEcL/`. It contains the protocol, models, four case receipts, native controls, structural checks, ordering checks, source hashes and decision. The compact [receipt](ordered_scheduling_receipt.json) preserves the key results.

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-ordered-scheduling.slYEcL/verify_ordering.py
```

Production remains at commit `5691617`, with a 1,041-cycle default. Production sources, tests, simulator and prior reports were preserved. No commit, push, package installation, cloud job or external submission occurred.
