# Research archives

[Home](../../README.md) · [Experiment index](../README.md) · [Historical notes](../../docs/history/README.md)

The [preserved campaign collection](campaigns/README.md) contains selected final-hash, mathematical-model and slope/select evidence, with hash manifests and a saved-program replay command. It distinguishes replayable artifacts from workspace captures whose reexecution is unverified.

## Root-level prototypes

The following files were relocated from the repository root without changing their contents. They are historical artifacts, not supported runners or current verification commands. Relocation did not repeat any sweep, compiler experiment or performance measurement.

| File | Role and limits |
|---|---|
| [param_sweep.py](param_sweep.py) | Old group/tile sweep driver. It does not pass its sweep parameters to the builder and contains an old absolute import path. |
| [param_sweep_results.txt](param_sweep_results.txt) | Historical recorded output. It cannot establish parameter optimality given the driver's limitation. |
| [perf_takehome_experiment1.py](perf_takehome_experiment1.py) | Early standalone generator variant, not the public builder |
| [radical_experiment.py](radical_experiment.py) | Exploratory scalar-node-storage prototype. Its opening claims are not validated conclusions. |

The [retry report](../retry_results.md) documents the old sweep's parameter bug. No behavior fixes were folded into this move. Other archived imports and commands also retain assumptions about the old layout and source revision.

To reproduce historical behavior, first identify the relevant commit, required inputs and verification contract. Starting another search requires a new scope and budget. Use the [maintained verification guide](../../docs/verification.md) to check current production.
