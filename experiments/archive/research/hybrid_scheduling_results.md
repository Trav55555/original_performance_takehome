# Hybrid search found a lower-scratch 981-cycle tie

The combined heuristic and GPU search finished with **981 cycles / 1,449 scratch words**. That saves 16 words against the previous 981-cycle experiment, but does not improve runtime. The selected program passed the full experimental verification gates. Production remains unchanged at commit `5691617`, with a 1,041-cycle default.

One new exact-repair query remains running alongside the original untimed solver. Neither has a wall-clock deadline. The exact arm is unfinished; its preflight results are not a coupled scheduling solution.

## Selective algebra and joint rebalancing

The final-XOR identity allows each output block to use either terminal expression:

```text
Original:   (u XOR (u >> 16)) XOR C
Rewritten:  (u XOR C) XOR (u >> 16)
C = 0xB55A4F09
```

A symbolic check proved equivalence for 32 independent values with arbitrary per-block choices. Independent terminal-IR checks covered 36 masks, including mixed representations, and rejected invalid block indices. Earlier rounds retained their encoded representation. Only the final hash and corresponding output store changed.

The algebra screen tested every single-block rewrite, all pairs among the eight latest-storing native blocks, and cumulative late-block masks. The joint screen then varied final-operation engine preferences, cache sites and nearby arithmetic-selector counts around retained candidates.

| Stage | New evaluations | Scratch-feasible | Best cycles / words |
| --- | ---: | ---: | ---: |
| Original and global-rewrite controls | 2 | 2 | 981 / 1,465 |
| Selective rewrites | 67 | 65 | 981 / 1,473 |
| Final-operation engine preferences | 14 | 14 | 981 / 1,473 |
| Cache neighbors | 128 | 118 | 984 / 1,465 |
| Nearby selector profiles | 8 | 8 | 986 / 1,505 |
| Multi-decision training and held-out labels | 240 | 218 | 981 / 1,449 |
| Model-selected and random pool plans | 60 | 52 | 981 / 1,457 |
| Total | 519 | 477 | 981 / 1,449 |

Configuration deduplication removed repeated controls and the final engine recheck. All 477 feasible candidates passed frozen-simulator smoke execution. The other 42 exceeded scratch and did not reach lowering or execution. These are finite neighborhoods, not an exhaustive joint search.

## Multi-decision learning

The A/B search retained the original graph for overall cost and a selective-rewrite graph for the best nonempty mask. Before C began, the existing C budget was split evenly between these two graphs. The change is recorded in `C_addendum.md`; it did not increase evaluations or training updates.

Each graph supplied 64 native scheduling snapshots. Proposals requested two to four local ordering changes, including at least one at cycle 615 or earlier. Each change could move a candidate from the first four eligible ready operations to the first eligible position. Existing issue legality and capacity checks remained authoritative. Unavailable requests became recorded no-ops.

The experiment generated 192 training plans, 48 held-out plans and an unmeasured pool of 384 plans. These sets were disjoint. The held-out split was by plans, not unseen graph families. Native-state inputs were proposal approximations: an earlier change could alter the ready operations encountered by a later request.

The GPU trained linear, multilayer-perceptron and transformer plan scorers for 600 updates each. The models used 180 feasible training plans. None had a negative cycle delta against its 981-cycle graph baseline. Thus the data taught avoidance of regressions without demonstrating a faster target.

| Model | Parameters | Training error | Held-out error |
| --- | ---: | ---: | ---: |
| Linear | 37 | 8.643 | 7.901 |
| Multilayer perceptron | 21,377 | 7.991 | 6.279 |
| Transformer | 401,665 | 3.389 | 7.039 |

Errors are mean squared errors in cycles on unclipped labels. The loss clipped training deltas to 16 cycles in either direction. Final checkpoints were fixed at 600 updates; held-out labels did not tune the models. GPU and CPU predictions agreed within 0.0000037 cycles on the held-out set. The existing ROCm environment performed the training; no packages were installed.

Each model selected eight pool plans per graph. A seeded random control did the same. Overlap reduced 64 selection credits to 60 actual compilations.

| Selection method | Feasible / selected | Best cycles / words |
| --- | ---: | ---: |
| Linear | 16 / 16 | 981 / 1,465 |
| Multilayer perceptron | 13 / 16 | 981 / 1,465 |
| Transformer | 13 / 16 | 981 / 1,465 |
| Random | 14 / 16 | 981 / 1,457 |

No model beat the random control on these measured best costs. The 1,449-word result came from generating training examples, not learned proposal selection. Two training plans reached that resource tie, one with four changes on the original graph and one with three changes on the selective graph.

## Verified retained tie

Deterministic ranking retained the three-change selective program. It combines:

- The final-XOR rewrite on zero-based block 14.
- ALU preference for its final shift, then VALU preferences for the early constant XOR and final combine.
- Moving the third eligible ready candidate first at zero-based cycles 179, 339 and 703.

Its selective graph without those ordering changes used 1,473 words at 981 cycles. The combined plan reduced that to 1,449 words. Compared with the original 1,465-word graph, the net saving is 16 words. Its instruction counts match the original 981 stream: 1,888 load, 947 flow, 5,797 VALU, 11,516 ALU and 32 store operations.

The selected program passed:

- 100 full-width random seeds and five asymmetric patterns.
- Independent lane ownership, dependency and issue-capacity checks.
- Three deterministic compilations.
- Dependency, constant and selector corruption rejection.
- All nine unchanged frozen submission tests.
- The supplementary verifier, including 100 standard random inputs, nine other shapes, legacy performance ceilings and pause/store controls.
- Fresh hash-seed-0 and hash-seed-17 source-only generation from the selected experimental configuration, with runtime and oracle helpers blocked.
- Executed rejection of the 1,041-cycle control at the 981-cycle ceiling.

The previous 981-cycle program remains a valid speed tie. It was not falsely classified as a performance failure. The source-only checks establish kernel generation from the selected configuration, not automatic production discovery of its cache plan, rewrite or ordering choices.

Instruction digest:

```text
bb9d4d571efe957980370c8ec758ff3b914b6309d146d80e9ab8dfc4ea73e6b5
```

## Exact repair is still running

The new solver uses the selective block-14 graph before the three ordering changes. Its seed is 981 cycles / 1,473 words. The goal is 980 cycles with fixed native engine modes, true-data dependencies, a displacement radius of eight cycles and fresh global SSA allocation after any SAT result. Physical scratch-reuse ordering is not imposed.

Preflight eliminated suffix widths 32, 64, 128 and 256 through mandatory resource overloads. For example, the 256-cycle suffix forced 245 flow operations into 244 slots. The 512-cycle suffix, starting at cycle 469, passed the difference and capacity checks. Passing these checks does not prove a complete schedule exists.

Only that first passing scope launched an optimization solve. It has no load pins and no wall/CPU deadline, with a 2 GiB address-space cap. The altered graph distinguishes it from previous original-graph queries. Native reconstruction, same-encoding satisfiability, SSA edge equality, corruption controls and an executable store/pause shortening control passed first.

An independent checker recomputed the window propagation and recounted every recorded cut. A future SAT result will still require allocation within 1,536 words before lowering or execution. The worker saves its timing witness before allocation and runs additional candidate checks if allocation succeeds. Full promotion gates remain necessary for any new result.

At the closing observation, worker `1674125` was still solving. The original worker `1059154` also remained running. Neither was restarted or reconfigured.

## Decision and artifacts

Retain the verified lower-scratch tie as an experiment. Do not claim a runtime improvement or copy its explicit ordering plan into production. The extra 16 words may permit other combinations, but the saving must be remeasured after any cache or selector change.

The declared heuristic and learning budgets are closed. No additional search, retraining, memory increase or production integration was started. The authorized exact repair continues independently. Nothing was committed, pushed or submitted.

Workspace: `/tmp/perf-hybrid-search.R8glwM/`.

The workspace retains `program.md`, `C_addendum.md`, source hashes, `rows.jsonl`, data splits, GPU weights, method selections, `hybrid_best.json`, `verification.json`, `verified_program.json`, `audit.json` and phase logs. Exact-work status is separate in `exact_solver_status.json`, `exact.heartbeat.json`, and eventual result or failure files. The adjacent `hybrid_scheduling_receipt.json` retains the measured search results, checks and a solver-status snapshot.
