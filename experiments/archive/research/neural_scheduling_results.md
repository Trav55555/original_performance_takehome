# GPU-trained scheduling policies did not beat 981 cycles

Keep the existing 981-cycle, 1,465-word experiment. A 400,513-parameter transformer trained and ran successfully, but did not improve the overall best kernel. Production remains at the local 1,041-cycle commit `5691617`. Nothing was committed, pushed, installed or submitted.

The neural experiment ran beside the untimed solver in `/tmp/perf-unlimited-scheduling.irTPtT/`. That solver remained active at the closing check, approximately 2 hours 36 minutes after its launch. It was not stopped, restarted or given a deadline. This is a status observation, not a solver result.

## Question and controls

The question was whether a small model could learn better ready-operation priorities than the existing scheduler. The experiment compared a linear model, a multilayer perceptron and a two-layer transformer. The transformer used width 128, four attention heads and no positional embeddings.

A copied compiler exposed up to 32 ready candidates. The policy could move one of the first four candidates to the first eligible position. It could not introduce operations, omit operations or issue instructions directly. Existing readiness, engine-selection and capacity checks remained authoritative. Allocation had to fit within 1,536 words before lowering or execution.

Inputs described compiler state, including critical paths, priority gaps, readiness and pressure. They did not contain runtime tree contents, kernel answers or instruction-ID embeddings. The `ready_fraction` input is a width-normalized readiness-mask encoding. Non-lane operations use the scheduler's readiness sentinel, rather than a physical fraction of ready lanes.

No-op callbacks reproduced six native programs exactly. These included the retained 981-cycle program and the previously rejected 985-cycle final-XOR rewrite. A constructed permutation control exercised a changed order. An out-of-range action was rejected.

## Data and GPU execution

Four training graphs supplied 128 states. Two separate cache-removal graphs supplied 32 held-out states. Each state had three alternative first choices. Each alternative changed one decision in an otherwise native scheduling rollout.

The run measured 480 counterfactuals, of which 466 fit scratch and passed a frozen-simulator smoke test. The other 14 were rejected without lowering or execution. Six native baselines brought the optimization-evaluation count to 486. Trace-reconstruction controls were additional checks, not additional search configurations.

Only four of 372 feasible alternative training labels improved their own baseline, all by one cycle on the slower rewrite. Another 348 labels were ties. No teacher schedule beat 981 cycles. This provided little positive training evidence for improving the original graph.

All models trained for 600 GPU updates with batches of 64 states. Candidate-order permutations also permuted labels and masks. The loss regressed measured cycle deltas, clipped to 16 cycles in either direction for training. Held-out data did not select checkpoints or enter gradient updates. This was supervised learning from rollouts, not reinforcement learning.

The existing environment was `/home/travers/projects/ai-research/arc-gpu-env/bin/python`, with PyTorch `2.3.1+rocm5.7`. A real GPU optimizer step and transformer backward pass succeeded. The device was the RX 7900 XT, identified by `gfx1100`, approximately 20 GiB memory and `rocminfo`. The older library's missing `amdgpu.ids` file caused a generic display name. It did not prevent execution.

| Model | Parameters | GPU training seconds | Training mean squared error | Held-out mean squared error |
| --- | ---: | ---: | ---: | ---: |
| Linear | 28 | 0.64 | 0.962 | 0.771 |
| Multilayer perceptron | 20,225 | 0.70 | 0.930 | 0.910 |
| Transformer | 400,513 | 1.63 | 0.677 | 1.659 |

Errors are in squared cycles and use unclipped labels for reporting. Training times exclude process startup, data generation and final evaluation. Peak transformer allocation was 51,096,064 bytes under a GPU allocation cap of approximately 4 GiB. CPU and GPU held-out predictions differed by at most 0.0000062 cycles. This does not establish identical scheduling decisions across hardware.

Up to three CPU workers generated examples while the existing solver used its own core. Closed-loop evaluation used single-threaded CPU inference for the small sequential policy calls. The supervised run and scheduling screen finished in approximately 140 seconds, including supervisor polling. No phase had a wall-clock cutoff.

## Actual scheduling results

The screen compared checkpoint-only and every-cycle application after startup. Predicted-improvement thresholds were 0, 0.5 and 1.5 cycles. These were score thresholds, not calibrated confidence estimates.

The table shows the best scratch-feasible result for each model that actually changed an ordering decision. Every selected active result used threshold zero.

| Policy | Original graph: cycles / words | Rewrite graph: cycles / words |
| --- | ---: | ---: |
| Native control | 981 / 1,465 | 985 / 1,465 |
| Linear | 981 / 1,465 | 985 / 1,465 |
| Multilayer perceptron | 981 / 1,513 | 985 / 1,513 |
| Transformer | 985 / 1,465 | 984 / 1,465 |

The transformer changed 418 decisions on the original graph and 427 on the rewrite when applied every cycle. Its checkpoint-only original-graph variant needed 1,545 words and was rejected. The scratch rejection was not the every-cycle configuration that improved the rewrite.

Across 36 training-graph screens and six held-out screens, 41 candidates fit scratch and passed frozen smoke checks. All three models selected threshold 0.5 for the held-out screen based on their combined original/rewrite results. Those held-out policies made zero changes and exactly reproduced both 988-cycle native programs. These results are not evidence of useful learned generalization.

The transformer fit the training labels better but predicted held-out labels worse than the simpler models. The small dataset and single-decision labels limit the conclusion. Better training fit did not produce a better overall kernel.

## Verification and decision

The active 984-cycle transformer rewrite passed:

- 100 full-width random seeds and five input patterns.
- Independent lane-owner, dependency and issue-capacity checks.
- Three deterministic reconstructions from the learned weights.
- Dependency, constant and selector corruption rejection.

Its digest was `3fdcfb2dc23dcd84871d2595ba0df98566da9872a17c5814b3b35dca909f2168`.

An instrumented replay of the 1,545-word rejection made zero lowering calls and produced no executable program. Policy controls rejected nonfinite scores and kept a one-candidate state within its legal action set. Independent receipt checks matched every dataset label to its measured counterfactual, checked run counts, and confirmed unchanged protected sources and search code.

No candidate qualified for promotion. Full frozen-suite, supplementary and source-only production gates were not run for the slower 984-cycle program. The existing 981-cycle experiment remains the best verified result; the production compiler remains unchanged.

Archive this supervised experiment. More transformer capacity is not justified by these results. A possible follow-up would first seek useful multi-decision training examples and measure their value before another training run. No follow-up search or additional training was launched.

## Artifacts

Workspace: `/tmp/perf-neural-scheduler.N9QSYM/`.

- `program.md`, `graphs.json`, `prototype_sources.json`: declared scope and source hashes.
- `gpu_smoke.json`, `transformer_smoke.json`, `hook_checks.json`: preflight controls.
- `teacher_manifest.json`, `teacher_rows.jsonl`, `dataset.json`: measured labels and graph splits.
- `training.json`, `linear.pt`, `mlp.pt`, `transformer.pt`: training results and weights.
- `screen_results.json`, `selected_settings.json`, `best.json`: measured outcomes and retained baseline.
- `check_results.py`, `checks.json`, `checks.log`: behavioral and receipt checks.
- `supervisor.py`, phase logs and `status.json`: persistent execution record.

The adjacent `neural_scheduling_receipt.json` retains results and artifact hashes. Rerun the completed checks without repeating the search:

```sh
PYTHONDONTWRITEBYTECODE=1 HIP_VISIBLE_DEVICES=0 OMP_NUM_THREADS=1 \
  /home/travers/projects/ai-research/arc-gpu-env/bin/python \
  /tmp/perf-neural-scheduler.N9QSYM/check_results.py
```
