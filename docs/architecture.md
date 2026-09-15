# Current compiler architecture

[Home](../README.md) · [Verification](verification.md) · [Full history](performance-progression.md) · [Technique wiki](reference/README.md)

This map describes the [979-cycle source release at `2c4705b`](https://github.com/Trav55555/original_performance_takehome/tree/2c4705b73038b723b1021ff65943d54b5d1fe842). Unverified working-tree changes are outside this reference baseline. Historical prototypes and fixed-configuration controls are not its default execution path.

## Start at the public entry point

[`KernelBuilder.build_kernel`](../perf_takehome.py) dispatches by public shape and tuning arguments:

```text
KernelBuilder.build_kernel
  │
  ├─ height=10, nodes=2047, batch=256, rounds=16
  │  default tuning, VLEN=8, one core
  │       │
  │       ▼
  │  kernel_compiler.compile_benchmark
  │       → assertion and pinned-dependency checks
  │       → Discovery.cache_plan
  │       → refinement.finish
  │       → immutable CompiledKernel
  │       → materialize fresh mutable bundles for this builder
  │
  └─ other shapes or explicit tuning overrides
          → KernelBuilder._build_legacy_kernel
```

The legacy generator remains necessary for fallback behavior and historical controls. Its benchmark result is 1082 cycles. Passing through that branch does not establish support for arbitrary dimensions or non-root inputs.

## Read the modules in this order

| File | Responsibility and useful symbols |
|---|---|
| [`perf_takehome.py`](../perf_takehome.py) | Public builder, dispatch, legacy generator and its physical-register scheduler |
| [`kernel_compiler.py`](../kernel_compiler.py) | `_IR`, `_build_ir`, native `_schedule`, lifetime `_allocate`, instruction `_lower`, `CompiledKernel`, `compile_benchmark` |
| [`kernel_optimizer.py`](../kernel_optimizer.py) | Immutable `Plan`, schedule/allocation `Cost`, memoized `Discovery`, cache/profile neighborhoods and score budget |
| [`kernel_refinement.py`](../kernel_refinement.py) | `candidates`, `finish`, `justify_finals`; late selector/final-hash choices and orchestration |
| [`kernel_justify.py`](../kernel_justify.py) | One fixed-engine backward/forward `schedule`, under native or dependence-tail tie order |
| [`kernel_retime.py`](../kernel_retime.py) | Lane-job graph capture/validation, necessary-window preflight and fresh retiming allocation; also retained exact-solver tools |
| [`kernel_checks.py`](../kernel_checks.py) | `lane_identity`, an independent check of physical scratch ownership |
| [`kernel_lookahead.py`](../kernel_lookahead.py) | Bounded engine-choice forecasts used by native scheduling; not an unrestricted global reorderer |

[`problem.py`](../problem.py) defines the local machine, hash and input model. [`tests/frozen_problem.py`](../tests/frozen_problem.py) is the frozen execution/reference oracle. Neither is an optimization target.

## Follow the representations

1. **Plan.** Cache sites, arithmetic profiles, selector sites and final-hash blocks describe compiler choices. They contain no runtime tree values or precomputed answers.
2. **Logical IR.** Each result has a single-assignment identity and width. Operands refer to a value and lane offset, not a physical scratch address.
3. **Native schedule.** Logical operations receive issue cycles and engines. Vector arithmetic may use scalar lanes where legal. Gather lanes can become ready separately.
4. **Retiming graph.** `capture` reconstructs exact lane-level jobs and dependencies, including the terminal pause. `schedule` changes order and times while keeping engines fixed for that graph.
5. **Physical allocation.** The new timing determines fresh live intervals and scratch addresses. An old address table is not valid merely because the operation graph is unchanged.
6. **Instruction bundles.** Only a legal allocation reaches instruction lowering. The frozen machine then supplies actual complete execution and correctness evidence in verification.

Do not confuse compiler scoring with simulator execution. Discovery scores generated schedules and allocations; it does not run the input-dependent computation on the host.

## Where choices and checks live

`Discovery.cache_plan` searches cache toggles, a bounded swap neighborhood, arithmetic profiles and coupled cache/profile alternatives. `finish` adds final-hash and late-selector proposals. Its necessary-window preflight ranks a refinement seed; admission is not proof of global scheduling feasibility.

`justify_finals` tries two orders on that seed, derives the two latest output blocks from the better legal schedule, then tries their singleton and paired final-hash rewrites. That is at most eight schedule scores. `reserve_schedule` checks the combined 4096-score budget before constructing each new proposal. The promoted build used 1959 scores.

`kernel_retime.lower` validates times, rebuilds lifetimes and allocates. If scratch exceeds 1536 words, it returns no program before calling the instruction lowerer. A feasible result must also pass lane ownership. `finish` raises if its finite search cannot meet 979 cycles; there is no silent slower fallback for the default benchmark.

## What remains of exact solving

Production still calls `kernel_retime.capture`, `preflight`, `validate` and `lower`. It does **not** call `solve`, `repair` or the exact worker. The pinned `z3-solver==4.15.4.0` check remains intentional compatibility behavior. Retained workers have a 2 GiB address-space cap and no wall-clock/CPU deadline; they are research tools, not routine verification commands.

## Cache and maintenance boundaries

`compile_benchmark` caches immutable results in process. `materialize` creates a new mutable instruction structure for each builder. A cold process performs discovery again; there is no disk cache.

Production does not read `experiments/`, receipts, saved site lists or saved timings. Some verifiers deliberately construct historical controls; that is separate from production discovery.

Historical notes are in [docs/history](history/README.md), prototype code in [experiments/archive](../experiments/archive/README.md), and the viewer in [tools/trace](../tools/trace/README.md). The root intentionally retains the submission API, simulator and production compiler modules.

Keep those root module paths stable during documentation work. The [source-only verifier](../scripts/verify_compiler.py) copies an explicit source-file list into an isolated directory. Moving code requires updating that contract and rerunning the affected verification, not just fixing Markdown links.
