# Algorithmica follow-up: measured lessons

Recorded 2026-09-10. Source: Sergey Slotin's [Algorithms for Modern Hardware](https://en.algorithmica.org/hpc/). This record separates the source's guidance from our experiments and proposals.

## Status and contract at the time of these experiments

This is a pre-promotion snapshot. The subsequent [promotion receipt](rebuilt_promotion_results.md) records the integrated 1,076-cycle, 1,236-word implementation.

At this stage the repository emitted the **1,082-cycle retained kernel**, using 1,536 scratch words. Its implementation is at `8d0506a`; `09f9dab` documents subsequent prototypes without integrating them.

A rebuilt prototype reached **1,076 cycles / 1,253 scratch words**. It is not a submission dependency or a finished integration. Both measurements use height 10, 2,047 nodes, batch 256, sixteen rounds, one core, eight SIMD lanes, and the unchanged frozen simulator. The contract is root-starting traversals and final values only. No runtime tree/value inspection occurs during generation.

## Lessons supported by experiments

### Optimize resource demand, not instruction count alone

Algorithmica's [throughput chapter](https://en.algorithmica.org/hpc/pipelining/throughput/) distinguishes critical-path latency from execution-resource throughput. Our useful transfer was to give constant construction two legal engine choices:

```text
load: const destination, immediate
flow: add_imm destination, existing_base, offset
```

The rebuilt scheduler moved 27 constants from load to flow when load slots were occupied. It included the base dependency and lifetime. Against its preceding 1,082-cycle control, first gather moved from cycle 82 to 76, last gather from 1,069 to 1,063, and the twelve-cycle drain stayed unchanged.

| Engine | Rebuilt control | Constant-choice winner |
|---|---:|---:|
| Load | 2,054 | 2,027 |
| Flow including pause | 870 | 897 |
| Vector ALU | 6,281 | 6,283 |
| Scalar ALU | 12,511 | 12,495 |
| Store | 32 | 32 |

Other engine choices changed slightly because scheduling is coupled. These totals are observations, not independent additive savings per rewrite. Twelve probes of a compact port to the retained physical-register scheduler only tied 1,082; the improvement does not transfer automatically between backends.

### Startup belongs in the objective

A finite kernel pays setup and drain costs. The latest gain advanced startup rather than shrinking the drain. Do not blindly apply advice to ignore cold initialization when initialization is inside the measured operation.

Instruction capacity is only one constraint. At minimum inspect dependencies, first/last gathers, setup, final stores/pause, and scratch feasibility alongside total engine counts.

### Reduced lifetime does not necessarily reduce peak storage or cycles

Twelve output-pointer policies compared retention, recomputation, sharing bases between groups of blocks, and explicit late recomputation.

| Policy | Cycles | Scratch words |
|---|---:|---:|
| Retain pointers | 1,076 | 1,253 |
| Best freely scheduled regeneration | 1,076 | 1,241 |
| Regenerate near stores | 1,081 to 1,093 | 1,241 |

Source placement near stores initially failed to achieve late execution: the scheduler hoisted independent pointer constants. Three bounded follow-ups delayed pointer generation until a lane of the final encoded hash was available. These ordering edges affected scheduling, but added no fictional scratch read or uncharged instruction.

Late load rematerialization reduced median regenerated-pointer lifetime to one cycle. Total scalar word-cycles fell from 33,789 to 1,076, but peak scalar allocation fell only from 53 to 41 words and execution slowed by five cycles. Late flow rematerialization also extended the base-7 lifetime from 27 to 1,084 cycles. All such lifetimes were allocated.

Decision: retain output pointers for this integration. A twelve-word saving with no speed improvement does not justify extra machinery while 283 words are already free. This does not reject rematerialization under different pressure or for different values.

### Cache and selector choices must repay their full cost

Scratch fit is necessary, not sufficient. Count table loads, address construction, encoding, broadcasts, mask normalization, selects, live intermediates, and output reconstruction.

- Arithmetic selector networks: best actual conversion was 1,092 cycles against a 1,082 rebuilt depth-4 control.
- Progressive depth-5 selection: best actual depth-5 reduction was 1,090 against its 1,086 depth-5 control. Some depth-4 variants tied 1,082 with more scratch.
- Constant construction improved the depth-5 family to 1,081, still slower than the depth-4 winner at 1,076.

These are bounded negative results for tested implementations. They do not prove that deeper caches or all alternative table representations are bad. In particular, selected depth-4 caching already improved earlier kernels, disproving a blanket cutoff at depth 3.

### Scope every graph bound and equivalence claim

The retained graph's interval is 1,074 to 1,082 cycles. It does not transfer to the rebuilt graph.

Exact tail solving tested one-cycle improvements in the final 16, 32, and 64 cycles of both the rebuilt 1,082 control and 1,076 winner. All six problems were unsatisfiable with prefix bundles, engine assignments, physical registers, and derived hazard edges fixed. A positive control found and executed a known pause/store packing improvement. This establishes only those restricted suffix results, not global optimality.

Six hash rewrites were proved equivalent over 32-bit inputs, but none beat its control in 56 scheduled screens. A deliberately invalid rewrite produced a counterexample. Finite-grammar screening rejected 77,406 programs for each of two hash stages and 266 one-operation programs for the encoded final stage. Every candidate failed a concrete witness. This excludes that grammar, not every equivalent hash circuit.

## Graph theory, compression, and memoization

| Application | Status | Decision boundary |
|---|---|---|
| Interval coloring of logical-value lifetimes | Used in rebuilt allocation | Fixed-schedule, separate scalar/vector pools; not globally optimal scheduling/allocation |
| Retain versus recompute, related to DAG pebbling | Pointer case tested above | Compare peak pressure and full cycles, not only total lifetime |
| Canonical cache-configuration memoization | Integration proposal | Saves repeated host search work, not simulated execution by itself |
| Reuse immutable traversal graph structure | Integration proposal | Recompute affected priorities/lifetimes; do not assume an old global schedule remains valid |
| Compress tables into shared bases/differences | Some pair-difference selectors tested and rejected | Runtime transformation and reconstruction must be charged |
| Compress the emitted instruction file | No measured cycle benefit | Fewer host bytes do not imply fewer executed cycles |

Independent walkers cannot share hash results merely because they visit the same node. Their incoming values differ. Any change to the required hash needs exact wrapping-32-bit equivalence, not similar statistical behavior.

## Supporting Evidence From Follow-Up Research

These sources corroborate mechanisms, not our cycle measurements:

- [Algorithmica: instruction-level parallelism](https://en.algorithmica.org/hpc/pipelining/) and [throughput computing](https://en.algorithmica.org/hpc/pipelining/throughput/) explain independent chains, latency versus throughput, and register demand. Native instruction timings are examples for specific processors, not simulator constants.
- [Algorithmica: machine code analyzers](https://en.algorithmica.org/hpc/profiling/mca/) motivates instruction/resource analysis. [LLVM's llvm-mca documentation](https://llvm.org/docs/CommandGuide/llvm-mca.html) confirms that analysis uses a target scheduling model. Do not equate a model's prediction with universally cycle-perfect hardware behavior.
- [uops.info methodology](https://www.uops.info/table_overview.html) distinguishes latency, throughput, and port use, measured by microarchitecture and input/output operand pair. Its x86 numbers are not applicable to this simulator.
- [LLVM ScheduleDAGMILive](https://llvm.org/doxygen/classllvm_1_1ScheduleDAGMILive.html) tracks live intervals and register pressure while scheduling. [LLVM Rematerializer](https://www.llvm.org/docs/doxygen/Rematerializer_8h_source.html) explicitly tracks definitions, uses, dependencies, and rematerialization locations. Neither source guarantees rematerialization is profitable here.

No modeled cache hierarchy, branch predictor, native shuffle instructions, or extra cores can be inferred from the book and added to the simulator. Transfer the reasoning method, not absent hardware features.

## Verification and provenance

Historical experiment receipts, not new runs performed for this documentation update:

- The 1,076 program passed all nine frozen tests and the existing supplementary verifier through an adapter. It separately passed 100 full-width inputs, five patterns, physical lane-identity checks, and dependency/constant mutations.
- Every pointer policy passed three fresh compiles and three full-width frozen executions with identical instructions/cycles across repeats, plus lane-identity checks. The best tie passed twenty additional full-width inputs, five patterns, and a corrupted-pointer control.
- Host compilation timings were recorded separately; no compilation-speed conclusion was drawn from small sequential samples.
- All prototype comparisons fully charge initialization, constants, storage, output, and pause. Over-budget allocation is not an executable winner.

Local detailed receipts remain disposable:

- `/tmp/perf-five-arms/decision.md`, `verification.json`, `hash_proofs.json`, `exact_tail.json`.
- `/tmp/perf-pointer-remat.bTyV4U/decision.md`, `results.json`, `program.md`.

This document preserves conclusions if those directories disappear, not runnable prototype code. Integration was still pending at this point; the subsequent promotion is documented separately.

## Decision proposed before promotion

Make the rebuilt generator and deterministic cache selection self-contained. Use canonical configuration memoization to bound repeated search work, measure compilation cost separately, and rerun the frozen oracle through the normal repository entry point. Keep the retained kernel until that integrated implementation is faster and verified. Do not carry failed pointer-rematerialization policies into it.
