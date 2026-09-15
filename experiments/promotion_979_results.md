# Automatic 979-cycle compiler promotion

The normal `KernelBuilder` path now discovers and executes **979 cycles / 1463 scratch words**, without a solver query. Three cold builds reproduced the same program: the public builder and two isolated source-only builds at hash seeds 0 and 17. The full verification driver passed in 2941.31 seconds.

This improves on production 980/1465 by one cycle and two words. It matches the preceding selected experimental result, but no experimental configuration or timing was a production search input.

## Source-only discovery

The compiler retains automatic cache and selector discovery. It then uses necessary-window preflight ranking to select one generated refinement seed. This preflight is a heuristic for choosing a seed, not a feasibility bound on global reordering.

The new `kernel_justify.py` performs one fixed-engine backward/forward pass. Jobs may move later than their original times and cross original cycle boundaries. Exact lane dependencies remain fixed, and each resulting schedule gets fresh allocation.

The compiler evaluates two tie orders, derives the two latest terminal store blocks from the better legal schedule, then evaluates their singleton and paired final-hash rewrites under both orders. This is at most eight additional scores. Reservation occurs before graph construction, and scratch overflow is rejected before lowering or execution.

The discovered blocks were 31 and 29. Those identities are results of terminal-store ranking, not literal winning block lists in production. The cache and selector choices are also discovered from source. The final pair uses dependence-tail tie order.

| Stage | Cumulative scores |
|---|---:|
|Cache and arithmetic-profile discovery|1763|
|Native rewrite frontier|1951|
|Backward/forward and final-hash neighborhood|1959|

Compilation remains capped at 4096 scores. Reconstruction checks add work beyond the score count. The default path invokes no solver and fails explicitly if its finite policy cannot meet 979 cycles. The existing pinned dependency and assertion requirements remain in place for compatibility.

## Measured result

All three builds produced this digest:

```text
d71b7cc458e45d9ae400faf7cbd525bafa531d5c23d6f10d84f3706d60143848
```

| Build | Seconds | Cycles | Scratch | Solver queries |
|---|---:|---:|---:|---:|
|Cold public builder|953.884|979|1463|0|
|Isolated source-only, hash seed 0|962.886|979|1463|0|
|Isolated source-only, hash seed 17|954.343|979|1463|0|

Warm construction took 0.00647 seconds. The compiler verifier's own `cold_seconds` field was a warm call because the driver had already built the kernel. The cold public measurement above comes from the separate first-build receipt.

The 1816 gathers remain continuous at two per cycle from 61 through 968. The rewritten block 31 final computation reduces the gather-to-store path from 11 to 10 cycles. Its store and the final pause issue at 978, giving 979 complete execution cycles. Instruction counts remain 1888 loads, 945 flow instructions including pause, 5800 VALU instructions, 11524 ALU instructions and 32 stores.

## Verification

The full driver used the public builder, not a replay adapter. It checked:

- Nine frozen submission tests, 100 full-width inputs, 100 supplementary generated inputs, five asymmetric patterns and nine other root-starting shapes.
- Independent lane ownership, exact dependencies, duplicate-lane and timing mutations, and fresh deterministic allocation.
- Output values, all non-output memory, complete charged execution, scheduler hazards and co-issued pause/store behavior.
- Three explicit override fallbacks, legacy and historical performance controls, and cached-program copy isolation.
- Rejection of corrupted constants and swapped selector branches.
- Rejection of injected 1537/1545-word allocations, a natural 1719-word graph, and a naturally overflowing 1537-word retimed schedule before lowering.
- Budget exhaustion before construction and duplicate schedule reservation rejection. A small executable toy improved from six to five cycles under both tie orders while moving work later.
- Actual execution and rejection of the 980-cycle control by the new 979-cycle performance gate. The native 981-cycle control and five older controls also executed as expected.
- Two source-only rebuilds without tests, configurations or saved schedules in their build directories. Named simulator/reference entry points and solver entry points were blocked. Both builds matched the executed public program.

Separate controls rejected missing or wrong pinned dependencies and disabled assertions before discovery, with zero kernel constructions. The supplementary verifier retained its existing standalone 980 default ceiling; the public-build and full-width compiler gates enforced 979, and supplementary execution reported 979.

Formatting, Ruff F/E9 checks, compilation and whitespace checks passed. The assurance scanner reported zero errors and three complexity warnings. These were reviewed as bounded DAG traversals and finite search loops. An independent subagent review was unavailable because its request failed before work; no independent review is claimed.

Tests and `problem.py` stayed unchanged. The supported contract remains root-starting traversals, final values only, and preservation of other memory. These checks do not establish arbitrary non-root or final-index equivalence or global optimality.

## Evidence and status

The [receipt](promotion_979_receipt.json) records source hashes, the public build, controls and the two isolated rebuilds. Detailed evidence is in `promotion_979_evidence/`. The run workspace is `/tmp/perf-promote979-run.atLGjV/`; its `full_verification_status.json` reports `passed`, and its supervisor recorded exit zero. No build was restarted.

The production source and verifier files can reproduce the discovery without the research workspaces. The normal standalone verification commands are documented in the README; each fresh process starts a new compiler cache.

This promotion changes the local working tree only. No commit or push was made. Historical research workspaces and unrelated untracked files were preserved.
