# Final-gather tail pilot: one exact query running

This is a launch snapshot, not a new performance result. The verified incumbent remains **980 cycles / 1,449 words**. The user approved the pilot proposed in [the below-980 exploration](below_980_exploration.md).

## Completed screening

The pilot retained A's block-14 final-XOR rewrite and ALU/VALU/VALU profile, then tested exactly three additional block sets. Cache sites, selector conversions, early sites, ordinal edits and priority flags were unchanged as configuration inputs. Their actual scheduling decisions could still change.

| Final rewrite blocks | Native executed cycles | Scratch | Preflight start 949 | Preflight start 917 |
| --- | ---: | ---: | --- | --- |
| `[14,30]` | 986 | 1,497 | Load and flow overload | Flow overload |
| `[14,31]` | 985 | 1,505 | Load overload | Pass |
| `[14,30,31]` | 985 | 1,489 | Load and flow overload | Flow overload |

The native A control reproduced 981 / 1,449. The selected-timing control reproduced the verified 980 / 1,449 digest. Each candidate passed independent lane/capacity checks and a full-width frozen-reference smoke execution, with non-output memory preservation. No candidate is a new verified incumbent.

All six target-979 preflights used fixed starts 949 or 917 and a radius of eight from that candidate's native schedule. Independent repeated relaxation reproduced the bounds, and separate counts checked each reported resource window.

Only `[14,31]` at start 917 passed. Its mandatory load window has **104 loads in 104 slots**, cycles 917–968. By contrast, unchanged A needed those 104 loads by 967, which offered only 102 slots. The rewrite removed that particular obstruction; it did not establish coupled feasibility.

## The authorized query

The selected native graph finishes in 985 cycles. Fixing its prefix through cycle 916 leaves a 68-cycle native suffix; the anchor is not the old 981-cycle graph or the retimed 980 witness.

- Target: **979 complete cycles**, final pause charged at cycle 978.
- Native engines fixed; movement at most eight cycles.
- Load order unpinned; no physical scratch-reuse or added lane-order constraints.
- 1,207 free timing variables and 17,141 potential membership terms.
- 17,117 encoded capacity terms, 1,955 free-to-free edges and 1,309 checked boundary edges.
- 18,989 fixed jobs projected out, with their occupancy retained.
- **2 GiB address-space cap; no solver, CPU or wall deadline.**

At the last observation for this snapshot, worker **1607760** was running. Supervisor **1607752** records its heartbeat and exit. These process IDs are historical identifiers once the files report completion; use actual status rather than assuming liveness.

## Controls and budget

Completed: five construction/evaluation attempts (two controls and three candidates), six preflights, and five solver-validation queries. Exactly one optimization query was reserved before spawning its worker. No retries, wider scopes, new variants or memory increases are authorized.

The selected native program reconstructed exactly through fresh allocation and through source-plus-timing replay. Same-encoding native-witness, capacity SAT/UNSAT, fixed-boundary and zero-lag store/pause controls passed. The executable pause/store control shortened a charged three-cycle toy to two cycles.

Missing-edge and wrong-lane corruptions were rejected. An injected 1,537-word allocation caused zero lowering calls. Tests of the actual launch function rejected source changes and exhausted budget before spawning any worker.

## Completion handling

A separate monitor waits for this worker; it cannot launch another solver. If the query returns SAT, the worker saves the witness before fresh allocation. Overscratch results remain timing-only evidence and are not executed.

For an allocation-feasible SAT result, the monitor automatically runs the full verification gates: 100 full-width seeds, five patterns, nine frozen tests, supplementary shapes and legacy ceilings, lane/dependency/capacity checks, non-output memory preservation, deterministic reconstruction, corruption controls and isolated source-plus-timing generation. Those gates are **pending**, not completed, at this snapshot.

The monitor writes `completion_status.json` and, when applicable, `verification.json`. If it encounters a failure, it records the failure rather than retrying the search. A verified result remains experimental selected-timing replay, not automatic production discovery.

## Inspectable evidence

Workspace: `/tmp/perf-finaltail.frSOx0/`.

- `program.md`, `authorization.json`, `manifest.json`: approved scope and fixed cases.
- `rows.json`, `selection.json`: candidate results and admission.
- `solver_controls.json`, `launch_guard_controls.json`: validation evidence.
- `runtime_hashes.json`, `verification_hashes.json`: frozen generation/query and completion code.
- `exact_attempts.jsonl`, `exact_launch.json`, `exact_status.json`, `heartbeat.json`: query state.
- `exact_solver_result.json`, `exact_result.json`, `exact.exit.json`: terminal evidence when available.
- `completion_status.json`, `verification.json`: post-solve verification state.

The [launch receipt](final_gather_tail_launch_receipt.json) preserves this snapshot. Read the workspace status files for later results.

Production, previous reports and the archived 980 winner remain unchanged. No commits, pushes, installations or submissions occurred.
