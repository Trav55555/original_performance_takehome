# Resource-aware scheduling bounds

Follow-up: [predicate reuse and selective caching](cross_domain_results.md) changed the graph and reached 1,088 cycles, with a new interval of 1,074 through 1,088. This record documents the preceding 1,113-cycle kernel and its bounds.

## Result

The current kernel runs in **1,113 cycles**, one cycle below the previous 1,114. The final pause now shares the last store bundle. Arithmetic, body scheduling, instruction operands, and scratch allocation are unchanged.

For schedules preserving the current physical-register dependency graph:

```text
1,104 <= optimal total cycles <= 1,113
```

The lower bound improves on the earlier 1,093-cycle engine-capacity estimate. It leaves at most nine cycles of scheduling improvement within this model. It does not establish the best algorithm or the exact optimal schedule.

## Question and method

Could the regional bounds from [Malik, McInnes, and van Beek](https://cs.uwaterloo.ca/~vanbeek/Publications/ictai06.pdf) narrow the interval before building a full constraint solver?

The experiment captured 21,733 body operations and reconstructed 87,426 dependency edges. Read-after-write and write-after-write edges have latency one. Write-after-read edges have latency zero, matching cycle-end writes. Engine assignments and physical scratch addresses stay fixed.

For an operation `i`, compute:

- `r[i]`, a lower bound on its zero-based issue cycle.
- `q[i]`, a lower bound on total cycles minus its issue cycle. A final body operation has `q = 1`.

For one engine with capacity `c`, select all operations with `r[i] >= R` and `q[i] >= Q`. If there are `N` such operations, their issue cycles must fit between `R` and `T - Q`, inclusive. Therefore:

```text
N <= c * (T - Q - R + 1)
T >= R + Q + ceil(N / c) - 1
```

The prototype evaluates every release/tail threshold pair using a two-dimensional count table. With only ordinary dependency distances, this gives a body lower bound of 1,099 cycles.

Next, it examines lookup regions between an index definition and the following first hash multiply-add. For each reachable endpoint pair `a, b`, it takes only operations on paths from `a` to `b`. For each engine, let `d1` be the minimum weighted distance from `a` to those operations, and `d3` the minimum distance from those operations to `b`. Their count implies:

```text
issue[b] - issue[a] >= d1 + ceil(N / c) + d3 - 1
```

These are necessary distance constraints, not heuristic ordering preferences. Their derivation also permits zero-latency edges. Applying the constraints and propagating distances produced:

- 512 candidate endpoint pairs.
- 384 stronger constraints: 256 from load capacity and 128 from flow capacity.
- A final subset of 2,016 scalar gathers, each with `r >= 84` and `q >= 13`.

The strongest bound is:

```text
84 + 13 + ceil(2016 / 2) - 1 = 1,104 cycles
```

The regional analysis runs outside the production generator.

## Terminal pause correction

The first prototype reserved a separate terminal pause cycle. Under that boundary policy, the intermediate and regional bounds were 1,100 and 1,105 cycles. Those numbers include a restriction that the hardware does not require.

The frozen simulator executes every engine in a bundle and then commits writes, even if a flow instruction pauses the core. Its final store can therefore share a bundle with the pause. This works with pause handling enabled, not just with the submission suite's pause handling disabled.

`perf_takehome.py` now uses a free final flow slot. If none is available, it appends a separate bundle. On the benchmark, the last store and pause both issue at cycle 1,112, giving 1,113 counted cycles. All earlier bundles are identical to the archived 1,114-cycle generator.

The lower bound ignores the pause's resource demand, a relaxation that remains valid whether or not a candidate schedule can pack it. The upper bound comes from the executable packed-pause kernel. Keeping the old separate-pause restriction instead gives the interval 1,105 through 1,114.

## Verification

Observed checks:

- All nine unchanged frozen submission tests pass at 1,113 cycles.
- The supplementary verifier passes 100 random inputs, five full-width/asymmetric patterns, and eight other root-starting shapes.
- A pause-enabled full-kernel check passes. Small pause/store checks cover both engine-dictionary orders and resuming after the final pause.
- The pause prototype separately passed ten pause-enabled full inputs.
- Exact instruction/operand multisets and scratch usage match the previous kernel. Scratch remains 1,416 of 1,536 words.
- The updated 1,113-cycle gate rejects the archived 1,114-cycle generator. The corrupted-kernel negative control still fails as expected.
- The bound prototype checks every emitted operation, capacity, original edge, and added regional edge against the retained schedule.
- A separate exhaustive enumerator checks 120 small graphs, 52,547 feasible schedules, and 93 strengthened regional constraints. It also checks lane-offset hazards and rejects a deliberately invalid read-after-write schedule.
- Ruff lint/format checks and the immutable-file diff checks pass.

Rerun the retained implementation checks:

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
ruff check perf_takehome.py scripts/verify_retry.py
ruff format --check perf_takehome.py scripts/verify_retry.py
git diff --check
git diff --exit-code origin/main -- tests/
git diff --exit-code 5452f74 -- tests/ problem.py
```

The disposable bound experiment requires the locally available NumPy and remains under `/tmp/perf-bounds/` for near-term follow-up:

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-bounds/regions.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-bounds/verify.py
```

`regional.json` contains the selected operation IDs, release/tail arrays, and added constraints. `baseline-1114.py` preserves the previous generator. Temporary artifacts are not submission dependencies and may disappear when temporary storage is cleaned.

Generator Git blob hashes:

- Before: `3af8025d807b60e6fe428d4f6e7583663b37549a`.
- Retained: `a15bb838c3e510412e507223dfff3b8ef8114206`.

## Decision and limits

Keep the compact terminal packing rule. The resource-aware bounds narrowed the scheduling question without adding a solver dependency to production.

No full exact solver or expression-synthesis search ran in this experiment. The small-graph checks test the bound implementation; they do not prove feasibility at 1,104 or establish optimality at 1,113. The next exact scheduling search can target 1,104 through 1,112. A larger improvement must escape the current dependency model, for example through equivalent-expression changes or different scratch allocation.

The Brain-2 compiler ingest queue now links a pending task for the scheduling, Souper, modulo-scheduling, Unison, and tree-traversal papers. Their ingestion and durable synthesis remain TODO.
