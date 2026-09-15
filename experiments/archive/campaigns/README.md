# Research campaign code

[Experiment index](../../README.md) · [Prototype archive](../README.md) · [Evidence method](../../../docs/reference/evidence-and-experiments.md)

This collection keeps readable Python sources, reports and protocols for four research campaigns. It does not contain workspace bundles, generated graphs, saved programs, timing files or large result receipts. Production discovery does not use this code.

## Start with the implementation

| Campaign | Main code | Historical result | Records |
|---|---|---|---|
| Final-hash ordering | [Backward/forward scheduler](finalhash-order/code/schedules.py), [driver](finalhash-order/code/run.py) | Experimental 979 cycles / 1463 scratch words | [Report](finalhash-order/records/report.md), [protocol](finalhash-order/records/protocol.md) |
| Mathematical models | [Lookup and arithmetic variants](mathematical-models/code/math_variants.py), [event scheduler](mathematical-models/code/event.py), [driver](mathematical-models/code/run.py) | Five-arm screen; best 981 cycles | [Report](mathematical-models/records/report.md), [protocol](mathematical-models/records/protocol.md) |
| Model combinations | [Combination driver](mathematical-models-mix/code/mix.py), [shared variants](mathematical-models-mix/code/math_variants.py) | Favorable interactions, but no new cycle winner | [Report](mathematical-models-mix/records/report.md), [protocol](mathematical-models-mix/records/protocol.md) |
| Slope/select | [Coefficient reuse](slope-select/code/linear_coefficients.py), [lookup variants](slope-select/code/math_variants.py), [driver](slope-select/code/run.py) | Sixteen candidates; best 981 cycles / 1473 words | [Report](slope-select/records/report.md), [protocol](slope-select/records/protocol.md) |

Each `code/` directory also retains the compiler, checker and helper snapshots used by that campaign. `original/kernel_compiler.py` is its historical control compiler. The 51 Python files preserve their original bytes rather than silently adopting today's implementation.

## Scope and provenance

These are historical sources for reading and comparison, not supported standalone runners. Drivers and audit scripts still reference former repository paths, temporary directories and data files that are not included. A syntax check does not establish that those scripts can run in this layout. Running another search requires a new scope and budget; all recorded budgets remain closed.

The sources came from the campaign captures in commit `b909b97e7e81c66254f69dd329f7721ae5232b40`, retaining their `workspace/` relative paths beneath `code/`. Their bytes were checked against the captured member hashes. Reports and protocols remain unchanged, including historical paths, links and creation-time status. References inside those records to receipts or saved artifacts are provenance, not claims that the current directory contains them. Use this index for navigation.

The workspace bundles, generated receipts and saved-program replay tools have been removed from the current layout. They remain in the earlier Git revision; this cleanup does not rewrite published history. No campaign, solver or cold compiler build was rerun for the code-only conversion.

For maintained compiler verification, use the [verification guide](../../../docs/verification.md). The separate [979 production promotion](../../promotion_979_results.md) documents automatic source-only discovery under its own gates. Neither an archived script nor its historical report replaces those gates.
