# Performance challenge retry

Follow-up: [load-lookahead packing](lookahead_packing_results.md) reduced the retained kernel to **1,114 cycles**. This record documents the preceding 1,117-cycle milestone.

## Result

The unchanged frozen submission suite reports **1,117 cycles**, versus **1,303** at starting commit `0d7c637`: 186 fewer cycles (14.3%), or 1.167x faster. Scratch usage is 1,416 of 1,536 words.

Only the kernel generator and its scheduling helpers affect the submission. The simulator and `tests/` are unchanged. No runtime input values, random seeds, reference outputs, extra cores, debug behavior, or simulator modifications are used to generate the program. As before, the output is the final value array; indices are not written back. Traversals start at the root, as specified by `Input`.

## Measured progression

These are checkpoints from the retry, not additive savings estimates:

| Checkpoint | Cycles |
|---|---:|
| Original frozen-suite baseline | 1,303 |
| One-based indices | 1,265 |
| XOR encoding plus mirrored path indices, before register-layout changes | 1,258 |
| Two private hash temporaries per block; shared shallow-selection banks; 32 active blocks | 1,170 |
| Batched node loads, root initialization, dead final index updates removed; retuned | 1,159 |
| Weighted dependency scheduling and unused setup removed | 1,130 |
| Scheduling parameters retuned | 1,126 |
| Decode values while gathers execute; separate input/output pointers per block | **1,117** |

The final parameters are group size 32, round tile 12, four shallow-selection banks, and source-order/critical-path weight 80. Uniform scalarization could reach 1,115 in a local probe, but that instruction-count policy was not retained for a two-cycle gain. At this checkpoint, the retained implementation was 1,117.

## Why the representation is equivalent

Let `C = 0xB55A4F09`, the final XOR constant of the fixed hash. Store each working value as `v = actual_value XOR C`.

For shallow nodes, preload `node XOR C`. Then `v XOR (node XOR C)` equals the original hash input. For gathers, decode `v` while the memory load is pending, then XOR the loaded node. The final hash stage leaves off XOR C, maintaining the encoded representation. Decode again before storing.

C is odd, so encoded parity is the opposite of actual parity. At depth d, represent the index as `q = 3*2**d - 2 - idx`. This is the one-based index with its path bits mirrored. The reference update becomes `q_next = 2*q + (v & 1)`. Reset q to 1 at a wrap. The gather address is `3*2**d + 5 - q`, and shallow selection uses nodes reversed within each level. Hash results, branch choices, and wrap behavior are unchanged.

The scheduler models RAW and WAW dependencies with latency one, and WAR with latency zero: a read can share a bundle with a subsequent overwrite because writes take effect at cycle end. It combines critical-path priority with source order rather than assuming pure longest-path scheduling is best.

## Rejected approaches and lessons

- Pure critical-path scheduling regressed in the tested configurations; source-order weighting mattered.
- Broad scalarization usually regressed or tied. The successful encoding already moved considerable work to scalar ALUs.
- Scalarizing both operations of the last hash stage in the final round regressed to 1,130.
- Partially preloading/selecting depth-4 nodes increased scratch pressure and dependencies; no tested configuration beat the retained kernel.
- Fewer operations can still produce a worse heuristic schedule. Retune after changing instruction selection or register layout.
- The old `param_sweep.py` did not pass its group/tile arguments to the builder. Its printed results did not establish parameter optimality. Retry sweeps called `build_kernel` with the actual parameters.

## Verification

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
ruff check perf_takehome.py scripts/verify_retry.py
ruff format --check perf_takehome.py scripts/verify_retry.py
git diff --check
git diff origin/main -- tests/
git diff 5452f74 -- tests/ problem.py
```

The supplementary verifier executes the generated instructions on the frozen simulator and compares against its reference implementation. It covers 100 random benchmark inputs, five full-width/asymmetric bit patterns, eight additional root-starting shapes, and scheduler hazard examples. It also corrupts an emitted constant in a copied kernel and requires the output comparison to reject that negative control. It checks that non-output memory is preserved.

| Engine | Final operations | Capacity-only lower bound |
|---|---:|---:|
| VALU | 6,556 | 1,093 |
| ALU | 12,304 | 1,026 |
| Load | 2,137 | 1,069 |
| Flow | 705 | 705 |
| Store | 32 | 16 |

These bounds apply to this instruction stream, not to every equivalent implementation. The result is not a proof of optimality. Non-root starts and arbitrary batch sizes beyond scratch capacity are outside this verification.
