# Load-gap profiling and startup scheduling

## Decision at experiment close

The policy below has since been [integrated with automatic cache selection at 1,041 cycles](startup_promotion_results.md). This report records the preceding experiment.

Keep a verified **1,042-cycle / 1,459-word prototype** for integration review. It saves ten cycles against [production at 1,052](technique_promotion_results.md) while using two more scratch words. Production remained unchanged at commit `0accd81` during the experiment.

The experiment followed one question: where are the unused load slots, and can a targeted scheduling change recover some of them? It did not change caches, arithmetic, traversal order, or the engine-choice policy.

## Profile before tuning

The published instruction digest reproduced exactly. The 1,052-cycle program has 2,003 load instructions and 101 unused load slots:

| Region | Unused load slots |
|---|---:|
| Before first gather, cycle 68 | 69 |
| Between first and last gathers | 10 |
| After last gather, cycle 1,040 | 22 |

The load work comprises 1,936 gather lanes, 36 vector loads, and 31 constants. Most unused capacity is therefore at startup, not scattered throughout the gather phase.

An offline checker reconstructed logical operand readiness from each lane's actual writer cycle. At every gap, none of the program's later load instructions was already ready under the scheduler's dependency model. Tracing one witness through the earliest-ready future load found 73 holes at same-cycle dependencies and six at ready work whose engine was full: four at flow selects and two at scalar AND operations. The remaining 22 had no future load.

These witnesses describe this schedule. They do not prove unavoidable latency, exclude changing engine choices, or establish a global lower bound. The model retains the compiler's conservative anchor dependency for alternative constants. A synthetic latency case and a deliberately delayed ready load checked that the profiler distinguishes these cases. Review also corrected witness tracing to require every operand lane for full-vector instructions, rather than just the traced output lane. This changed the engine attribution of two holes, not the phase totals or chosen experiment.

## One targeted mechanism

Temporarily increase priority for the complete dependency ancestry of selected walkers' first uncached gathers. Apply the same priority list to real issue and the existing one-cycle forecast. Restore ordinary priorities when a targeted gather starts, or at a cycle cutoff.

The initial screen used 56 configurations: controls, target groups of one to eight walkers, several offsets, four priority strengths, and shorter cutoffs. Its best result was 1,043 cycles / 1,456 words. A predeclared follow-up varied only that winner's priority strength across sixteen values.

All 72 rows were scratch-feasible and passed full-width seed 461. There were no compilation exceptions, timeouts, or smoke correctness failures. Forty-seven rows beat production; the complete range was 1,042 to 1,067 cycles. Counts include controls and repeated instruction streams. The screen used four local workers and a 20-second compilation limit per configuration.

The winner targets blocks 0 through 3, subtracts 2,560 priority units from their gather ancestors, and restores normal priorities at cycle 48. Priority units are scheduler scores, not cycles. This is benchmark-tuned scheduling, not a demonstrated general rule. The winning run used the full 48-cycle priority window and retained all 32 walker contexts.

Ordinary, zero-strength, and two zero-cutoff controls reproduced the published program exactly. The winner's logical operations, operands, widths, and producer graph also match the control exactly. Only scheduling, engine choices, and resulting allocation differ.

## What changed

| Measurement | Production | Winner |
|---|---:|---:|
| Cycles | 1,052 | 1,042 |
| Scratch words | 1,457 | 1,459 |
| First gather | 68 | 60 |
| Last gather | 1,040 | 1,030 |
| Startup load holes | 69 | 48 |
| Between-gather load holes | 10 | 6 |
| Drain load holes | 22 | 22 |
| Total load instructions | 2,003 | 2,008 |
| Flow instructions, including pause | 786 | 781 |
| VALU instructions | 5,794 | 5,800 |
| ALU instructions | 11,499 | 11,451 |

The winner issues five more constants through the load engine instead of flow. Gather work stays at 1,936 lanes. It runs faster despite more load instructions, so instruction count alone would have rejected the useful direction.

Total load holes fall from 101 to 76. Twenty of the 25-slot reduction comes from finishing ten cycles earlier; the other five slots hold the extra load instructions. Startup improves by eight cycles and the first-to-last gather interval by two. The drain does not improve.

An earlier first gather was not sufficient to choose the winner. Another configuration started gathers at cycle 55 but finished in 1,048 cycles. The selected four-walker policy starts at 60 and finishes six cycles sooner than that alternative.

## Verification and scope

The selected winner passed 100 full-width seeds, five asymmetric patterns, lane ownership, and three deterministic compiles. Dependency, encoding-constant, and selector mutations were rejected. A fresh hash-seed-17 process reproduced the digest with runtime-data and reference helpers forbidden.

Through an experimental adapter, it passed all nine unchanged frozen tests and the supplementary verifier at a 1,042-cycle ceiling. Supplementary coverage included 100 generated inputs, five patterns, nine other shapes, three non-benchmark performance ceilings, and pause/store checks. Other shapes use the unchanged legacy generator; this does not establish generality of the new scheduling policy.

The same supplementary ceiling rejected the executed production control exactly as `((1052, 1042),)`. Verification also checked preservation of all non-output memory for the full-width and pattern cases.

Selected-plan compilation took 0.401 seconds in the screen and 0.396 / 0.392 seconds in repeats. These exclude automatic cache selection and production integration. The new instruction-stream capacity bound is 1,004 cycles, higher than production's 1,002 despite the better execution time. The remaining 38-cycle gap is neither promised savings nor a challenge-wide bound.

Instruction SHA-256:

```text
af7f9144e670c98df1f23356683481145199dddaf2bc2f3ee2db8353eca88993
```

## Artifacts and replay

The workspace is `/tmp/perf-load-gaps.PmEoc5/`. It contains the protocol, copied compiler, `startup.py`, profiler, synthetic controls, manifests, all screen rows, winner configuration/instructions, verification receipts, and decision note. Screen-row engine counts describe the logical schedule and exclude the final pause; `winner_profile.json` records complete physical counts.

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/profile.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/controls.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/screen.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/followup.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/verify_winner.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/probe.py submission
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/probe.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-load-gaps.PmEoc5/probe.py control
```

Replay depends on the temporary sources and saved experimental cache configuration. This report preserves the conclusions, not a portable implementation. No production changes, promotion, commit, push, or external submission occurred during the experiment.

Stop the search here. If integration is requested, verify automatic cache selection under the changed schedule and measure full cold-build cost. The demonstrated gain comes from targeted startup scheduling; it does not justify a broad scheduler sweep or treating earlier gathers as the objective.
