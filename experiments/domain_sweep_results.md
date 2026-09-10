# Domain sweep after 1,088 cycles

Follow-up: [benchmark-tuned instruction selection](algorithmica_results.md) moved two positional hash groups to the ALU engine and reached 1,082 cycles. It is scoped to the measured benchmark configuration, not a general selection policy. This record documents the preceding 1,084-cycle result.

## Result

A bounded sweep across scheduling, algebra, instruction selection, caching, register pressure, and output conversion produced a compact retained kernel at **1,084 cycles**. The previous committed result was 1,088.

The retained changes are:

1. Increase the critical-path priority weight from 80 to 100 and the four-cycle load-urgency bonus from 200 to 300. This changes only scheduling.
2. Fold the first root mix into input initialization. Reuse the now-dead scalar constant for hash stage zero to hold the actual root, so this needs no scratch.

The current fixed dependency graph has a derived interval of **1,074 through 1,084 cycles**. This does not prove the exact optimum or bound other legal implementations.

A screen-only 1,083-cycle candidate moved one block-round's eight non-fused hash operations from VALU to 64 scalar ALU operations. It was not promoted. The one-cycle result depends on choosing a narrow source position, adds a benchmark-specific instruction-selection exception, and did not receive the full promotion suite. It is evidence for joint instruction selection and scheduling, not retained production code.

## Research protocol

The sweep used generated modules under `/tmp/perf-domain-sweep/`. Production stayed unchanged until a compact candidate passed the frozen oracle.

The first bounded pass contained 64 candidates:

- 24 VALU-to-ALU resource-exchange variants.
- 14 placements for the six cached depth-4 lookups.
- 25 scheduler policies, including five refined neighbors.
- One baseline control.

Follow-ups tested four root-fold policies, twelve narrow scalarization windows, four tail scalarizations, five live-context reductions, one vectorized output decode, and two whole-hash windows. Every transformation used public compile-time positions. None inspected runtime tree values, input values, random seeds, or reference outputs.

Screens used a fixed random input and a full-width asymmetric pattern. Strict improvements advanced to the full verifier.

## Exact operation decomposition

The retained benchmark emits 21,333 body operations plus the terminal pause:

| Engine | Operations | Capacity-only bound |
|---|---:|---:|
| VALU | 6,397 | 1,067 |
| Load | 2,091 | 1,046 |
| ALU | 12,018 | 1,002 |
| Flow, including pause | 796 | 796 |
| Store | 32 | 16 |

The major components are:

### VALU

- Hash core: 512 block-rounds times 11 operations = **5,632**.
- Index updates: 480.
- Shallow/cache selection masks: 210.
- Constants, node broadcasts, and root index initialization: 75.

The hash is 88% of all VALU work. Three affine add/left-shift stages already use `multiply_add`. The other stages expose independent arms to the scheduler before their combining operation. The minimum dependency depth of the current eleven-operation hash implementation is nine cycles.

### Load

- Scalar tree gathers: **2,000**.
- Input pointers and input vector loads: 64.
- Constants and contiguous node preloads: 27.

Scalar gathers are 96% of load work. They remain the strongest regional constraint.

### ALU

- Gather address, decode, and node mix: 6,000.
- Branch parity extraction: 3,584.
- Non-initial shallow node mixing: 1,792.
- Input/root mix: 256.
- Final decode: 256.
- Cached lookup mask and node mix: 96.
- Initialization: 34.

### Flow

- Shallow selection: 704.
- Six cached depth-4 selections: 90.
- Cache address setup and pause: 2.

A sixteen-way lookup needs fifteen binary `vselect` operations in the current selection representation. Caching exchanges eight scalar gathers for that flow chain. Six late cached lookups are the measured balance point.

## Findings by adjacent domain

### Queueing theory and bottleneck accounting

Simple capacity balancing was misleading. Replacing one vector operation with eight scalar operations often improved aggregate engine bounds but lengthened dependency chains or competed with gather work.

Broad scalarization regressed from 1,088 to between 1,092 and 1,160 cycles. After root folding freed ALU capacity, small windows reached 1,083 to 1,087, but the useful choices were position-sensitive. This makes alternative engine assignment a joint scheduling problem, not a global ratio adjustment.

### Partial evaluation and algebraic cancellation

The old entry sequence performed 256 XORs to encode input values, followed by 256 XORs with the encoded root. The encoding constants cancel:

```text
(value XOR C) XOR (root XOR C) = value XOR root
```

The retained version initializes each lane with `value XOR root` and skips only round zero's root mix. Later root visits remain unchanged. One scalar operation reconstructs the actual root into storage whose previous constant is dead. Net reduction: **255 ALU operations**.

This tied at 1,113 before selective caching changed the graph. In the current graph it improves 1,088 to 1,085 under the old scheduler policy and to 1,084 with the retained policy. The result is a reminder that dead-work elimination can be latent until another bottleneck moves.

### List scheduling

The unchanged operation multiset reached 1,087 under four nearby policies. Weight 100, load horizon four, and urgency bonus 300 were retained because the values are round and lie inside a tied neighborhood.

The load engine issues its last gather at cycle 1,071. The remaining twelve cycles drain hash and output dependencies. The regional load bound remains 1,074, leaving ten cycles between the derived lower bound and the retained schedule.

### Cache placement and knapsack allocation

Moving the same six cached lookups did not improve the prefix placement. Contiguous placements later in source order took 1,091 to 1,109 cycles. Interleaved placements tied or regressed by one cycle. The cache policy is balancing two queues, not predicting branch coherence.

All 1,536 scratch words now have owners:

- Index and value state: 512.
- Two private vectors for 32 active blocks: 512.
- Shared selection banks: 96.
- Input pointers: 32.
- Constants, scalar staging, and cached vectors: 384.

Reducing live contexts is a pebble-game trade. Group sizes 31, 30, 28, and 24 freed 16 to 128 words but regressed to 1,098 through 1,189 cycles. Reducing selection banks from four to three freed 24 words and regressed to 1,098. Latency hiding is currently worth more than the recovered space.

Arbitrary cached node values cannot be losslessly compressed below their information content. Storing sixteen raw nodes would need only sixteen words, but `vselect` takes fixed vector operands; the current direct selector therefore replicates them across lanes in 128 words. A bit-sliced or reconstructed representation would save scratch only by adding shifts, masks, or loads. This remains a possible trade, not a free compression.

### Liveness and output conversion

After the final traversal, a node vector is dead. Reusing it to broadcast the encoding constant replaces 256 scalar output XORs with one broadcast and 32 vector XORs at no scratch cost. It regressed to 1,095 because VALU, not ALU, is the limiting engine. Dead-register reuse was valid; the engine exchange was wrong.

Targeting only the observed tail also failed. Scalarizing one to eight final simple vector operations produced 1,084 to 1,086 cycles.

### Integer-mix circuit structure

The fixed hash is a reversible chain of additions, XORs, and shifts. Thomas Wang's discussion of integer hashes emphasizes both reversibility and executing independent shift arms in parallel. The current DAG already exposes that parallelism, and its three affine stages already use the target's fused multiply-add.

Replacing the fixed mix with another published integer hash would violate semantics. The remaining legitimate route is exact 32-bit expression synthesis with equivalence proof and this machine's scheduled-cycle cost. No equivalent shorter circuit was established in this sweep.

Source: [Thomas Wang, Integer Hash Function](https://web.archive.org/web/20060507103516/http://www.cris.com/~Ttwang/tech/inthash.htm).

### Integrated code generation

Constraint-based code generation and Unison-style work treat instruction selection, register assignment, and scheduling together. That matches the observed 1,083 screen: a profitable VALU-to-ALU choice exists, but naive broad conversion loses.

Useful references:

- [Constraint-based Code Generation](https://hjort.dev/publications/documents/castaneda_lozano-et-al-2013-constraint-based_code_generation.pdf)
- [Unison](https://unison-code.github.io/)

A next experiment should expose each simple vector operation as either one VALU operation or eight parallel ALU operations, then choose mappings under schedule/resource constraints. Hardcoding source offsets is not the right production interface.

## Verification

The retained 1,084-cycle production generator exactly matched the fully verified prototype's instructions and scratch usage. It passes:

- All nine unchanged frozen submission tests.
- 100 random inputs and five full-width/asymmetric patterns.
- The supplementary eight shapes plus 88 additional pause-enabled root-starting shapes.
- Scheduler hazards, co-issued pause/store behavior, and the corrupted-kernel negative control.
- Ruff lint/format and immutable-file diff checks.

The regional-bound prototype found 320 stronger implied constraints and checked them against the executable schedule. Its strongest resource subset still yields 1,074 cycles.

Rerun:

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
ruff check perf_takehome.py scripts/verify_retry.py
ruff format --check perf_takehome.py scripts/verify_retry.py
git diff --check
git diff --exit-code origin/main -- tests/
git diff --exit-code 5452f74 -- tests/ problem.py
```

Artifacts and machine-readable results remain under `/tmp/perf-domain-sweep/`. They are not production dependencies and may disappear when temporary storage is cleaned.

## Revised problem breakdown

There are now three distinct problems:

1. **Schedule the current graph.** At most ten cycles remain between the derived bound and retained schedule. Exact or stronger regional scheduling is appropriate.
2. **Reduce the hash circuit.** This dominates VALU work. Any replacement must be exactly equivalent for every 32-bit input and judged by full scheduled cycles.
3. **Replace critical gathers.** Direct cache selection has a fifteen-flow-operation cost and consumes all scratch. Progress needs a different lookup representation, fewer live vectors, or a schedule that makes more of the existing cache profitable.

The highest-value next test is integrated alternative-resource scheduling on a small late region, with proof-preserving VALU/ALU alternatives and no source-position special cases. The strongest alternative is exact scheduling of the unchanged graph, which can improve no more than ten cycles under the current bound.
