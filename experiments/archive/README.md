# Research archives

[Home](../../README.md) · [Experiment index](../README.md) · [Historical notes](../../docs/history/README.md)

The [campaign code collection](campaigns/README.md) contains readable Python sources, reports and protocols for final-hash, mathematical-model and slope/select research. It excludes workspace bundles and generated artifacts. Historical drivers are not supported standalone runners.

## Research records below 980 cycles

[`research/`](research/) holds the plans, results, receipts and certificates from the September research below 980 cycles. They sat untracked in `experiments/` until October 2026 and moved here unchanged, except one link and one path noted below. The [research wiki](../../docs/reference/search-and-research.md#research-records) summarizes each record's subject and closure. The four campaign receipts moved to their campaign's `records/receipt.json`; the campaigns' `*_program.md` and `*_results.md` files were byte-identical to the tracked `protocol.md` and `report.md` and were not kept.

[`research/followup_980/`](research/followup_980/README.md) rebuilds the experimental 980-cycle witness from source and a selected timing assignment. Its root path was updated for the new depth, and a rerun reproduced the recorded digest `759f3ecb`. It is not automatic production discovery. `plateau_selector_results.md` links to `cache_descent_results.md` at its new relative path.

## Root-level prototypes

The following files were relocated from the repository root without changing their contents. They are historical artifacts, not supported runners or current verification commands. Relocation did not repeat any sweep, compiler experiment or performance measurement.

| File | Role and limits |
|---|---|
| [param_sweep.py](param_sweep.py) | Old group/tile sweep driver. It does not pass its sweep parameters to the builder and contains an old absolute import path. |
| [param_sweep_results.txt](param_sweep_results.txt) | Historical recorded output. It cannot establish parameter optimality given the driver's limitation. |
| [perf_takehome_experiment1.py](perf_takehome_experiment1.py) | Early standalone generator variant, not the public builder |
| [radical_experiment.py](radical_experiment.py) | Exploratory scalar-node-storage prototype. Its opening claims are not validated conclusions. |

## January analysis scripts

These eleven files moved unchanged from `scripts/` to [`scripts/`](scripts/). They date from January 2026 and were not rerun after the move. Several insert an old absolute path or the working directory into `sys.path`, and three resolve the repository root as their parent's parent, which no longer points at the root.

| File | Role |
|---|---|
| `analyze_bottleneck.py`, `analyze_graph.py`, `analyze_kernel.py` | One-off analyses of the January kernel |
| `bottleneck_detector.py`, `profiler.py`, `visualize_schedule.py` | Engine-utilization and schedule-gap tools described in the [implementation guide](../../docs/history/implementation_guide.md) |
| `value_reuse_profiler.py` | Recomputation finder for the January generator |
| `breakthrough_experiments.py`, `scheduler_experiments.py`, `experiment_batching.py`, `validate_speculative.py` | Experimental drivers. They are not permission to start another search. |

The [retry report](../retry_results.md) documents the old sweep's parameter bug. No behavior fixes were folded into this move. Other archived imports and commands also retain assumptions about the old layout and source revision.

To reproduce historical behavior, first identify the relevant commit, required inputs and verification contract. Starting another search requires a new scope and budget. Use the [maintained verification guide](../../docs/verification.md) to check current production.
