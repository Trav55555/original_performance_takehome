# Final-hash plus backward/forward scheduling pilot

## Authority and objective

The user approved the proposed eight-case final-hash pilot. Seek actual complete execution below980 cycles, under1536 scratch words. Production remains980/1465. The solver-free research control is980/1483 with one dependence-tail-ordered justification pass. Previous budgets remain closed. No solver, installation, cloud work, production edit, commit or push is authorized by this pilot.

## Fixed matrix and budget

Four graph configurations: no final rewrite, block31, block29, and blocks29+31. For each, run one right/left pass with native or dependence-tail tie order. Eight candidate reservations only. No slope tiles, cache changes, extra passes or additional sites.

Four control reservations cover the existing symbolic/guard fixtures, original native981, isolated native981 and published980 replay. Add the declared final-XOR algebra check to the symbolic control. The no-rewrite candidates must reproduce the previous B01/B03 results and digests exactly.

At most two conditional fresh reconstructions, only for the best feasible candidate strictly below980. All specifications and source hashes are frozen before construction. Reserve before each construction. No retries, budget transfers or automatic extensions; an unexpected failure stops and closes the run. Address-space cap2GiB. Solver entry points must fail if called.

## Hypothesis and implementation

The exact identity is `(u ^ (u >> 16)) ^ C == (u ^ C) ^ (u >> 16)` for32-bit words. Moving the constant XOR to a parallel branch can shorten the final data-dependence path. The existing compiler's final_blocks parameter already implements this transformation and changes the final shift's preferred engine. Reuse that implementation; do not change hash semantics or add a new algebraic transform.

Every candidate graph and its native engine assignment are generated afresh from the experimental published control plan, with only final_blocks overridden. Run the unchanged tested double-justification implementation, then allocate freshly. Do not use saved candidate timings or programs as optimization inputs. The published timing replay and prior result hashes are controls only.

## Gates

1. Recheck the inherited symbolic/mutation, scheduling-toy, graph, budget and scratch guards. For the final-XOR identity, check zero and all32 basis words. Both expressions are affine over GF(2); these33 checks characterize the identity for all32-bit inputs. A mutation shifting the XOR-adjusted operand must fail. Full-kernel tests check the actual compiler wiring and all wrapping arithmetic.
2. Original and isolated native controls must match981/1465. Published replay must match980/1465 and its existing digest. All setup, broadcasts, loads, stores and final pause remain charged.
3. Each candidate gets exact native graph/dependency/capacity validation and fresh allocation. Reject scratch>1536 before lowering or execution. For feasible programs, run independent lane-owner checks, three fixed full-width seeds and five asymmetric patterns, with non-output memory preservation.
4. Record all store times, the final gather stream, and the graph distance from each selected block's final gather lanes to its store when that final gather exists. A shorter dependency path is not proof of a shorter complete execution.
5. For the best candidate<980 only:100 full-width seeds, five patterns, two fresh deterministic reconstructions with named simulator/reference entry points blocked during generation, and one additional seed per reconstruction. Run the unchanged nine-test frozen submission suite through an explicitly labeled replay adapter using the verified candidate program. Check observed cycles, not only threshold passes. This is experimental validation, not automatic production discovery, public-builder integration, or the complete production promotion suite.

## Decision

A result>=980 is not a new cycle incumbent. A sub980 result must be labeled by the gates actually passed, with production left unchanged. Do not restart the old979 solver query. If no candidate qualifies, expire both validation slots and stop. Preserve source manifests, reservation ledger, rows, models, timings, addresses, programs, conditional verification evidence, and a read-only audit. Write a concise decision and receipt.
