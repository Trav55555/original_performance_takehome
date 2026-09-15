# Full performance history: 147,734 to 975 cycles

[Home](../README.md) · [Architecture](architecture.md) · [Technique wiki](reference/README.md) · [Experiment index](../experiments/README.md)

The project began with a scalar starter whose recorded baseline is **147,734 cycles**. Published production now executes in **975 cycles / 1,469 scratch words**, with zero solver queries. That is 146,759 fewer simulated cycles, about 152 times faster than the recorded starter. The later 1,303 → 975 phase saved 328 cycles, or 25.2% of execution time.

This history covers the upstream setup, January vectorization and manual scheduling, the automatic scheduler, and the September compiler/research work through the 975 verification. It does not treat every experiment as a production release.

```text
147734 → 4294   SIMD, retained walker state, batching and load overlap
  4294 → 2905   Manual bundle packing, hash fusion and wider prefetch
  2905 → 1305   Automatic list scheduling and shallow cached selection
  1305 → 1303   Reuse selection arithmetic and batch initialization
  1303 → 1113   Encoded state, private temporaries and load-aware scheduling
  1113 → 1082   Predicate reuse, selective caching and instruction choice
  1082 → 1076   SSA compiler and alternative constant construction
  1076 → 1052   Hash fusion, lookup changes and cache reselection
  1052 → 1041   Startup scheduling and another cache reselection
  1041 →  981   Cache neighborhoods and joint selector balancing
   981 →  980   Small, exact, allocation-checked suffix repair
   980 →  979   Solver-free reordering plus a shorter final hash path
   979 →  975   Startup ancestry priority during forward insertion
```

The diagram follows selected milestones, not a monotonic record of every attempted change. January counts come from contemporaneous commit messages and the session log; they were not rerun for this documentation update. Later reports state their own execution, allocation and promotion gates. The current result has the [completed 975 verification evidence](../experiments/startup_ancestry_candidate_results.md). Schematics below are not measured timings unless explicitly labeled.

## Milestone ledger

Dates are Git author dates. They locate saved work, not hours spent optimizing. The January session log contains additional intermediate measurements without separate commits; those are distinguished below. Git records the next kernel-development commit after January on September 10.

| Date | Commit or source | Cycles | Scratch words | Status and change |
|---|---|---:|---:|---|
| Jan 19–21 | [Starter](https://github.com/Trav55555/original_performance_takehome/tree/f88c9458dbc5ef09d7801d961d905698e7e7cae1), [frozen checkpoint](https://github.com/Trav55555/original_performance_takehome/tree/5452f74) | 147734 | Not listed | Recorded scalar baseline; upstream setup and test-integrity guidance |
| Jan 22 | [8535c4b](https://github.com/Trav55555/original_performance_takehome/commit/8535c4b) | 4294 | Not listed | SIMD, three-batch work and software pipelining |
| Jan 22 | [9b66c24](https://github.com/Trav55555/original_performance_takehome/commit/9b66c24) | 4030 | Not listed | Batch setup, broadcasts, XOR/address work |
| Jan 22 | [b60ddb3](https://github.com/Trav55555/original_performance_takehome/commit/b60ddb3) | 3946 | Not listed | Batch remainder index operations |
| Jan 22 | [50f0c03](https://github.com/Trav55555/original_performance_takehome/commit/50f0c03) | 3765 | Not listed | Affine hash fusion and shallow arithmetic selection |
| Jan 22 | [dd47206](https://github.com/Trav55555/original_performance_takehome/commit/dd47206) | 3645 | Not listed | Explicit WIP checkpoint; six-way batching for broadcast rounds |
| Jan 22 | [e84802b](https://github.com/Trav55555/original_performance_takehome/commit/e84802b) | ~3241 | Not listed | Extend six-way batching to select/gather rounds |
| Jan 22 | [1107260](https://github.com/Trav55555/original_performance_takehome/commit/1107260) | ~2905 | Not listed | Gather loads share index-update bundles |
| Jan 22 | [4c21d2e](https://github.com/Trav55555/original_performance_takehome/commit/4c21d2e) | 1305 | Not listed | Automatic list scheduler, shallow caches and tiling |
| Jan 22 | [3ab1a17](https://github.com/Trav55555/original_performance_takehome/commit/3ab1a17) | 1323 | Not listed | Regression from skipping final index updates; next baseline restored 1305 |
| Jan 22–23 | [caffa90](https://github.com/Trav55555/original_performance_takehome/commit/caffa90), [3e2e6fb](https://github.com/Trav55555/original_performance_takehome/commit/3e2e6fb) | 1304 | Not listed | Reuse selection arithmetic; unused broadcasts removed without another cycle gain |
| Jan 23 | [46be33c](https://github.com/Trav55555/original_performance_takehome/commit/46be33c) | 1303 | Not listed | Batch initialization; January endpoint |
| Sep 10 | [b09d2a6](https://github.com/Trav55555/original_performance_takehome/commit/b09d2a6) | 1113 | See reports | Retry, load urgency and pause/store packing |
| Sep 10 | [b033825](https://github.com/Trav55555/original_performance_takehome/commit/b033825) | 1088 | See reports | Predicate reuse and selected depth-4 caches |
| Sep 10 | [d746d15](https://github.com/Trav55555/original_performance_takehome/commit/d746d15) | 1084 | See reports | Root cancellation and scheduling retune |
| Sep 10 | [8d0506a](https://github.com/Trav55555/original_performance_takehome/commit/8d0506a) | 1082 | 1536 | Scoped hash scalarization; retained legacy implementation |
| Sep 10 | [0bef02a](https://github.com/Trav55555/original_performance_takehome/commit/0bef02a) | 1076 | 1236 | [Automatic rebuilt compiler promotion](../experiments/rebuilt_promotion_results.md) |
| Sep 10 | [0accd81](https://github.com/Trav55555/original_performance_takehome/commit/0accd81) | 1052 | 1457 | [Fusion/lookup promotion](../experiments/technique_promotion_results.md) |
| Sep 11 | [5691617](https://github.com/Trav55555/original_performance_takehome/commit/5691617) | 1041 | 1458 | [Startup-policy promotion](../experiments/startup_promotion_results.md) |
| Sep 11–13 | [Published discovery trace](../experiments/promotion_980_evidence/progress.jsonl) | 1037 → 981 | Varies | Experimental cache/selector milestones, later automatically rediscovered |
| Sep 13 | [168e0f2](https://github.com/Trav55555/original_performance_takehome/commit/168e0f2) | 980 | 1465 | [Exact-repair production promotion](../experiments/promotion_980_results.md); distinct from experimental 980/1449 |
| Sep 14 | [0067321](https://github.com/Trav55555/original_performance_takehome/commit/0067321) | 980 | 1483 | [Solver-free research tie](../experiments/resource_order_results.md), not a new production result |
| Sep 14 | [2c4705b](https://github.com/Trav55555/original_performance_takehome/commit/2c4705b) | 979 | 1463 | [Solver-free production promotion](../experiments/promotion_979_results.md) |
| Sep 14–15 | `988dd9b`, `960f4c3` | 979 | 1463 | README updates only; no new performance result |
| Sep 15 | [1df789d](https://github.com/Trav55555/original_performance_takehome/commit/1df789d) | 975 | 1469 | [Startup ancestry priority; published as candidate, then fully verified](../experiments/startup_ancestry_candidate_results.md) |

Each retained compiler milestone supersedes the preceding retained implementation. Experimental rows do not. Missing scratch measurements are left blank in substance rather than inferred from the machine limit. [Production reports](../experiments/README.md#production-promotion-records) connect later promotions to verification receipts.

## What we were optimizing

There are 256 independent inputs, each taking 16 steps through a binary tree. Eight SIMD lanes make **32 groups of walkers**.

Each walker repeatedly does:

```text
       ┌──────────────────────────────────────────┐
       ▼                                          │
 fetch node → mix value → hash → choose branch ────┘
```

One walker has a dependency chain: the next address depends on the previous hash. But different walkers can run together.

The machine's per-cycle issue limits are:

```text
Scalar arithmetic:  [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ]  12
Vector arithmetic:  [ ][ ][ ][ ][ ][ ]                     6
Loads:              [ ][ ]                                 2
Stores:             [ ][ ]                                 2
Flow/select:        [ ]                                    1

Scratch storage: 1,536 words total
```

An irregular eight-lane tree gather requires eight scalar loads: **at least four cycles of load issue capacity**. That is not a four-cycle latency for each load.

The central problem became: **how do we keep the scarce engines supplied without exhausting scratch?**

## Origins: the scalar starter and frozen benchmark

The initial January 19 source used scalar arithmetic and load/store operations, with one non-debug operation per instruction bundle. Inside each round it loaded each walker's index and value, fetched a tree node, hashed the value, updated the index and wrote state back.

The [upstream submission tests at the frozen checkpoint](https://github.com/Trav55555/original_performance_takehome/blob/5452f74/tests/submission_tests.py) record `BASELINE = 147734`. Their 18,532-cycle threshold refers to a different, improved challenge starting point. It was not a measured intermediate result of this repository's optimization sequence. The model/human thresholds in the original challenge are comparison context, not commits in this history.

January 21 commits made the frozen simulator an independent file rather than a symlink and added warnings against changing tests. That boundary remains intact. The modern compiler is verified for final values from root starts while preserving non-output memory; the early records should not be read as having passed every modern promotion gate.

## 147,734 → 4,294: vectorize, retain state and overlap walkers

The [January session log](history/implementation_guide.md#progress-log) records these intermediate measurements before the first optimized commit. They are historical observations, not separately rebuilt releases:

| Recorded change | Cycles |
|---|---:|
| Original scalar baseline | 147734 |
| Basic eight-lane SIMD with two batches | 10656 |
| Software pipelining, prefetch during hash | 8496 |
| Vector copy instead of scalar copy loop | 6704 |
| Broadcast common root loads at rounds 0 and 11 | 6660 |
| Three-batch processing | 6078 |
| Replace branch selection with arithmetic | 5566 |
| Fuse index multiply/add | 5334 |
| Replace wrap selection with a masked multiply | 5054 |
| Batch broadcast rounds | 4294 |

The log also mentions a 6592-cycle vectorized result from an earlier session, without enough context to place it in this exact sequence. It is not silently inserted as another monotonic improvement.

SIMD applied the same arithmetic to eight walkers at once. Keeping indices and values in scratch across rounds avoided repeated state traffic. Processing several batches exposed independent arithmetic while the next batch's irregular node loads issued.

```text
Scalar starter:     load A → hash A → update/store A → load B → hash B
Batched SIMD:      [load group B] overlaps [hash group A]
                   [hash groups A, B, C] fills more arithmetic slots
```

These changes work together. The commit at [8535c4b](https://github.com/Trav55555/original_performance_takehome/commit/8535c4b) records 4294 cycles and lists vectorization, three-batch processing, prefetch, broadcast reuse, arithmetic branch updates and persistent scratch state. It does not provide independent ablations for every claimed component.

## 4,294 → about 2,905: improve manually packed bundles

Initialization and remainder handling left issue slots empty. January's next changes grouped constant loads, vector broadcasts, address arithmetic and remainder operations so more independent work could share each bundle.

The session log includes local 4272, 4150, 4010 and 3996 measurements while developing the 4030-cycle committed version. They were different combinations, not a steadily falling release series. Remainder index batching then produced the 3946-cycle commit.

At 3765, stages 0, 2 and 4 of the hash used affine multiply-add fusion, and rounds 1 and 12 used arithmetic selection from runtime-loaded shallow nodes. Six-way batching first reached a WIP 3645 result for broadcast rounds, then about 3241 after extending it to selection and gather rounds. Widening prefetch to share index-update bundles produced about 2905.

The six VALU slots explain the attraction of six-way batching, but do not prove six is always the best concurrency level. Gather dependencies, scratch usage and remainder handling still matter. The later scheduler replaced these manual packing choices.

Sources: commits [9b66c24](https://github.com/Trav55555/original_performance_takehome/commit/9b66c24), [b60ddb3](https://github.com/Trav55555/original_performance_takehome/commit/b60ddb3), [50f0c03](https://github.com/Trav55555/original_performance_takehome/commit/50f0c03), [dd47206](https://github.com/Trav55555/original_performance_takehome/commit/dd47206), [e84802b](https://github.com/Trav55555/original_performance_takehome/commit/e84802b) and [1107260](https://github.com/Trav55555/original_performance_takehome/commit/1107260).

## About 2,905 → 1,303: automate scheduling, then remove small costs

The large January rewrite generated a flat operation list and let a greedy scheduler pack bundles subject to physical read/write hazards and engine capacities. It cached tree levels 0 through 3 and used selection networks instead of repeated gathers. Group/round tiling controlled how much work and storage were live together.

```text
Earlier generator:  choose computation AND hand-place its bundles
Later generator:    emit operations → derive hazards → pack legal bundles
September SSA:      emit logical values → schedule → choose physical storage
```

The [4c21d2e commit](https://github.com/Trav55555/original_performance_takehome/commit/4c21d2e) records 1305 cycles. The session log's 1307 and 1304 observations describe nearby development variants; they do not replace that committed checkpoint. Its `group_size=17` and `round_tile=13` settings are historical, not today's defaults.

Removing final index updates seemed like an obvious win but regressed to 1323 at [3ab1a17](https://github.com/Trav55555/original_performance_takehome/commit/3ab1a17). The next saved baseline returned to 1305. This is an early example of less work producing a worse heuristic schedule.

Level-3 selection recomputed `idx - 7` after temporary values were overwritten. Extracting all predicate bits first removed 64 vector operations and reached 1304. Removing unused constants and broadcasts maintained that count. Batching initialization then reached 1303 on January 23.

The old logs called this the "final solution" and estimated little remaining headroom. Those estimates described a particular instruction stream and scheduler. September's graph changes demonstrate why they were not global limits.

## 1,303 → 1,117: representation and parallelism

The first large reduction came from rebuilding how traversal state and temporary values were represented.

| Checkpoint | Cycles | Main change |
|---|---:|---|
| Starting kernel | 1,303 | Existing optimized baseline |
| One-based indices | 1,265 | Simpler traversal/index arithmetic |
| Encoded values and mirrored paths | 1,258 | Cancel conversions and simplify branch updates |
| Private hash temporaries, shared selection banks | 1,170 | Support 32 active groups with fewer artificial dependencies |
| Setup cleanup and retuning | 1,159 | Batched node loads, root initialization, dead final index work removed |
| Weighted dependency scheduling | 1,130 | Better order; remove unused setup |
| Scheduler retuning | 1,126 | Improve the balance of scheduling priorities |
| Overlap decode with gathers | 1,117 | Hide independent arithmetic; separate input/output pointers |

### Change the representation so operations cancel

Let `C` be the final XOR constant in the required hash. We kept working values encoded as:

```text
encoded_value = actual_value XOR C
```

For cached nodes, we also stored `node XOR C`:

```text
(actual_value XOR C) XOR (node XOR C)
                    │
                    ▼
             actual_value XOR node
```

The two copies of `C` cancel. The hash can omit its terminal XOR with `C` and leave the next working value encoded.

Raw gathered nodes still need a decode, but that decode can run while the node loads are in flight. Final output values are decoded before storage.

Because `C` is odd, encoding flips the low bit. Mirroring the path representation makes that useful rather than adding a correction:

```text
q = 3·2^depth − 2 − original_index

next q         = 2q + (encoded_value & 1)
gather address = 3·2^depth + 5 − q
```

At a wrap back to the root, reset `q` to 1. This is the same traversal in different coordinates, not a different algorithm.

### Give independent walkers independent temporary storage

Sharing a temporary too early can serialize otherwise independent work:

```text
Shared temporary:

Walker A:  [write T] ── [finish reading T]
                                         └── Walker B may now overwrite T

Private hash temporaries:

Walker A:  [work in TA] ──────────────►
Walker B:      [work in TB] ──────────────►
Walker C:          [work in TC] ──────────────►
```

Two private hash temporaries per group, combined with shared banks for shallow selection, let all 32 groups remain active within the scratch budget.

The major lesson here was that **register layout determines how much parallelism the scheduler can see**.

Source: [retry progression](../experiments/retry_results.md).

## 1,117 → 1,113: prioritize future loads and pack the ending

At this point, instruction ordering alone still had a small payoff.

### 1,117 → 1,114: prepare loads before the load engine goes idle

A ready arithmetic operation might be unimportant now, or it might produce the address of the next gather.

```text
Less useful choice:

Arithmetic:  [unrelated work] [address work]
Loads:       [busy]          [idle]         [next gather]

Better choice:

Arithmetic:  [address work]  [unrelated work]
Loads:       [busy]          [next gather]  [next gather]
```

A rollout experiment found useful tail rearrangements. Instead of shipping the rollout search, we distilled its benefit into a small priority rule: favor operations close in dependency distance to a future load.

The retained rule reached 1,114 with **the same instruction multiset**. The last gather moved from cycle 1,103 to 1,100.

### 1,114 → 1,113: the final pause does not need its own cycle

The frozen machine commits stores in a bundle even when that bundle also pauses:

```text
Before:  ... [final store] [pause]
After:   ... [final store + pause]
```

This saved one real cycle. We checked pause-enabled execution and both engine iteration orders rather than relying on the benchmark disabling pauses.

Sources: [lookahead packing](../experiments/lookahead_packing_results.md), [pause and scheduling bounds](../experiments/scheduling_bounds_results.md).

## 1,113 → 1,082: reuse predicates, then spend the recovered space

This phase illustrates how one optimization can enable another. At 1,113 cycles, a bound on the existing physical-register graph left at most nine cycles of scheduling improvement. Reaching 1,088 required changing that graph, not violating the bound.

### 1,113 → 1,107: stop calculating the same branch bit twice

The update already computes:

```text
bit = encoded_value & 1
next_q = 2q + bit
```

A following lookup was extracting `next_q & 1`, which is exactly the existing `bit`.

Reusing it removed **192 vector operations**, plus an unused vector constant. Keeping the bit in private storage mattered: an initial shared-storage attempt was incorrect across round-tile boundaries and was rejected.

### 1,107 → 1,088: use selected depth-4 caches

The freed space helped make room for another cached tree level.

```text
Gather lookup                         Cached lookup

8 lane addresses                      16 cached node vectors
      │                                        │
      ▼                                        ▼
8 scalar loads                       binary selection tree
      │                                        │
      ▼                                        ▼
8 node values                         same 8 node values

Load-engine demand                    Flow-engine demand
```

A sixteen-way lookup costs fifteen binary selects in the original representation. Caching therefore exchanges load pressure for flow pressure and scratch use.

Caching everything lost. Caching six groups' repeated depth-4 visits won: those six lookups removed 48 gathers, with two additional preload operations, for **46 fewer loads overall**.

### 1,088 → 1,084: root cancellation finally pays

At entry:

```text
(value XOR C) XOR (root XOR C) = value XOR root
```

Folding the first root mix into initialization removed a net **255 scalar operations**. Combined with scheduler retuning, it reached 1,084.

An earlier version of this idea saved operations but no cycles. Once the graph and resource balance changed, it became useful.

### 1,084 → 1,082: move a little vector work to scalar slots

For ordinary lane-wise arithmetic:

```text
one vector operation  ⇔  eight equivalent scalar operations
```

Two selected hash invocations moved sixteen vector operations to 128 scalar operations. This relieved vector pressure enough to save two cycles.

Broad scalarization lost. The retained rule was a narrow benchmark-specific exception, not a general optimum.

Sources: [predicate reuse and caching](../experiments/cross_domain_results.md), [root folding](../experiments/domain_sweep_results.md), [scoped scalarization](../experiments/algorithmica_results.md).

## 1,082 → 1,076: a new compiler creates room for further changes

The physical-register implementation had reached **all 1,536 scratch words**. We rebuilt around single static assignment, or SSA: each logical result has its own identity before physical storage is chosen.

```text
Build logical computation
           │
           ▼
Choose instructions and schedule work
           │
           ▼
Calculate live intervals
           │
           ▼
Assign physical scratch words
           │
           ├── exceeds 1,536 words → reject
           │
           ▼
Check lanes, lower, and execute
```

This removed premature storage decisions from scheduling and allowed scratch to be reused according to actual lifetimes.

**The rebuild itself was not the whole six-cycle saving.** A rebuilt control matched 1,082. Giving constant construction another engine choice then produced the 1,076 prototype:

```text
Load engine:  constant = immediate
                     OR
Flow engine:  constant = existing_base + offset
```

In that experiment, moving 27 constants from load to flow advanced the first gather from cycle 82 to 76 and the last gather by six cycles. All base construction and lifetimes were charged.

Production then rediscovered a cache plan from scratch and delivered **1,076 cycles using 1,236 words**, leaving 300 words free.

An earlier, smaller experiment that renamed only selection temporaries had merely tied its baseline. The successful full rebuild should not be read as proof that every SSA conversion speeds up code.

Sources: [rebuilt promotion](../experiments/rebuilt_promotion_results.md), [constant-choice experiments](../experiments/algorithmica_followup_results.md).

## 1,076 → 1,052: combine algebra, lookup representation, and reselection

First, bounded engine lookahead plus an address-precomputation rewrite produced a **1,074-cycle experimental control**.

Then we audited a 1,063-cycle external implementation and reimplemented useful techniques in our own compiler. We did not adopt its generator wholesale.

The experiments branched before combining:

```text
                       1,074 control
                       /           \
             hash-stage fusion    selector/history changes
                    1,068             1,066
                       \             /
                        combined: 1,060
                               │
                         reselect caches
                               ▼
                             1,052
```

These branch savings are not additive.

### Fuse two middle hash stages

Instead of:

```text
B = 33X + C2
Y = (B + C3) XOR (B << 9)
```

use the equivalent wrapping-32-bit expression:

```text
X ──► 33X + C2 + C3 ─────────┐
                            XOR ──► Y
X ──► 16896X + (C2 << 9) ────┘
```

The two affine arms become independent multiply-adds. This is stronger than the earlier fusion within individual affine hash stages.

### Start lookup work before the newest branch bit arrives

Retaining branch history means old bits are available without reconstructing them from the current index. Permuting the lookup tree lets some selection happen earlier.

Arithmetic leaves also offer another resource exchange:

```text
select(bit, yes, no)
          ⇕
no + bit × (yes − no)       bit must be 0 or 1
```

The program computes differences from runtime-loaded nodes. There are no compile-time tree answers.

The combined changes altered which cache sites were profitable. Reselecting caches reduced 1,060 to 1,055, then 1,052.

Source: [technique-port experiments](../experiments/technique_port_results.md).

## 1,052 → 1,041: repair startup, then reselect again

A finite kernel pays for pipeline startup as well as steady-state work.

The startup policy prioritized ancestors of the first four groups' first gathers, for an initial bounded interval. It used logical dependency targets rather than saved instruction positions.

```text
Startup → steady-state load stream → final hash/store drain
   ▲
   └── accelerate the prerequisites that start this stream
```

With the old cache plan, the policy reached **1,042**. Automatic cache reselection under the new policy found **1,041**.

That last cycle matters conceptually: the integration did not just copy an experimental configuration. It reran selection under the actual production rules.

Source: [startup integration](../experiments/startup_promotion_results.md).

## 1,041 → 981: search the new cache/selector trade-off properly

Earlier production searches were deliberately small. With compile time now secondary, we explored complete cache-toggle neighborhoods repeatedly.

```text
1041 → 1037 → 1033 → 1029 → 1025 → 1021 → 1017
     → 1013 → 1009 → 1005 → 1001 → 997 → 996 → 993
```

From 1,037 to 993, twelve accepted cache additions removed 96 scalar loads. That could save 48 issue cycles if everything else stayed equal. Additional load holes reduced the actual gain to **44 cycles**.

The descent then reached a plateau:

```text
993 → 992 → 989 → 987
                   │
             no better single toggle
                   │
             swap one site for another
                   ▼
                  984
```

A swap can escape a point where neither individual change is attractive.

At 984, flow and vector arithmetic were nearly balanced. We changed how many lookup pairs use arithmetic:

| Arithmetic pairs at depths 3 / 4 | Standalone cycles |
|---|---:|
| 2 / 2 | 984 |
| 2 / 3 | 984 |
| 1 / 5 | 986 |

The tied `2 / 3` profile freed flow capacity. Adding a cache site under that profile produced **981 cycles / 1,465 words**, with 29 cache sites.

Even the initially slower `1 / 5` profile enabled a 982-cycle combination. **Rejecting every standalone non-winner would have missed useful combinations.**

Sources: [cache descent](../experiments/cache_descent_results.md), [automatically reproduced search trace](../experiments/promotion_980_evidence/progress.jsonl).

## 981 → 980: small exact suffix repair

This was the hardest cycle, not the largest gain.

Several investigations failed to beat 981:

- Broader scalarization, deeper caching, and wider forecasts often moved the bottleneck or exceeded scratch.
- Earlier output-pointer recomputation saved scratch but not cycles; explicitly delaying it made execution slower.
- GPU-trained scheduling scorers did not find a faster kernel. A 981/1449 scratch improvement arose while generating training examples, not from learned selection.
- Large coupled scheduling problems exhausted their memory budgets.
- Some equivalent rewrites shortened a local chain but worsened the overall schedule.

The productive route was to change selected late lookups and solve a **small coupled timing problem**.

```text
Generated whole-program graph
             │
       fix the early prefix
             │
       propagate dependency bounds
             │
       reject overloaded engine windows
             │
       remove fixed jobs from solver variables
             │
             ▼
     roughly 530 free issue times
             │
          exact solving
             │
             ▼
    fresh allocation + actual execution
```

### The first experimental 980

The successful experimental graph used late arithmetic conversions plus earlier scratch-saving changes. A 533-variable query found a schedule in about 47 seconds.

Here is what happened to selected outputs, using **actual zero-based issue cycles**:

| Output store | Native 981-cycle schedule | Repaired 980-cycle schedule |
|---|---:|---:|
| Group 29 | 980 | 978 |
| Group 30 | 976 | 979 |
| Group 31 | 979 | 979 |
| Whole-kernel final cycle | 980 | 979 |

The repaired schedule delays some outputs while advancing the one that determined completion. The last select moved two cycles earlier, but competing outputs limited the total improvement to one cycle.

This reached **980 cycles / 1,449 words** after allocation and full verification.

### Production took a different route to the same cycle count

A saved timing witness was not acceptable as the production answer. The compiler had to discover its configuration and schedule itself.

```text
Research route:
981/1465 → scratch-saving choices → 981/1449 → exact repair → 980/1449

Published production route:
empty-plan discovery → cache/profile search → 981/1465
                    → late lookup conversions
                    → exact repair                  → 980/1465
```

Production needed **527 free variables** for its successful query. It uses neither the saved ordinal scheduling edits nor the experimental final-XOR rewrite.

Three cold builds independently reproduced the same 980-cycle program. The price is **17 to 19 minutes of cold compilation**; an in-process cached build takes about **6.6 ms**.

Sources: [experimental 980 verification control](../experiments/promotion_980_evidence/archived_980_control.json), [published promotion](../experiments/promotion_980_results.md).

## Historical outcome at the 980-cycle release

```text
                         Cycles    Scratch words
Published compiler         980        1,465
Experimental witness       980        1,449
Attempted next target      979        not established
```

The 979-cycle query that completed after promotion exhausted its 2 GiB memory cap after about **16 hours 52 minutes**. That is **unknown**, not proof that 979 is impossible.

For the published instruction stream, the simplest capacity bound is:

```text
Loads:       ceil( 1888 /  2) = 944
Flow:        ceil(  945 /  1) = 945
Vector ALU:  ceil( 5800 /  6) = 967  ← largest
Scalar ALU:  ceil(11524 / 12) = 961
Stores:      ceil(   32 /  2) =  16
```

Being thirteen cycles above 967 does not mean thirteen cycles are recoverable. Dependencies, startup, completion tails, and scratch constraints also matter. Earlier bounds ceased to apply when we changed their instruction graphs.

Throughout the progression, the target remained the same root-starting computation on the unchanged one-core machine. The final promotion passed all nine frozen tests, full-width and asymmetric input checks, memory-preservation checks, mutation controls, fresh allocation checks, and source-only reproduction.

## 980 → 979: change resource order and shorten the last path

Research continued after the exact-repair promotion. Tensor/Mobius lookup forms, coefficient sharing, slope-select and geometric/event scheduling gave useful local changes but no faster complete kernel in their declared screens. The [research wiki](reference/search-and-research.md) preserves those distinctions and the source-availability limits. None of those failures proves that every variant of the technique is unhelpful.

A resource-order pilot then tried genuine backward/forward justification. On the unchanged native 981-cycle graph, one pass filled a late gather hole and produced a solver-free 980-cycle program. It moved 8587 jobs earlier and 955 later. Allowing some jobs to move later changed resource order in ways the earlier compactor could not.

That experimental tie used 1483 words, versus the then-production solver-based program's 1465. It was not itself a faster production release. Extra passes did not improve cycles, and the tested resource-deadline candidates exceeded scratch before lowering.

Final-hash rewriting supplied the next step:

```text
(u XOR (u >> 16)) XOR C = (u XOR C) XOR (u >> 16)

                                      Reordered native     Final-hash pair
Last gather issue                            968                  968
Last block's gather-to-store path              11                   10
Final store and pause issue                  979                  978
Complete execution cycles                    980                  979
```

Both schedules keep 1816 gathers continuous at two per cycle from 61 through 968. The rewrite makes the constant XOR and shift independent and changes the shift's preferred engine. It shortens the final path without reducing the per-engine instruction counts.

Some final-hash graphs had worse native timing spans, 984 to 989, but became 979-cycle programs after reordering and fresh allocation. A 979 timing assignment needing 1537 words was not legal and was rejected. The paired rewrite fit 1463 words. These are coupled graph/scheduling/allocation effects, not independent savings that can be added to any kernel.

### From selected experiment to automatic production

The production compiler retained automatic cache and selector discovery. It used necessary-window preflight ranking to choose a generated seed, tried two scheduling orders, and derived two late terminal blocks from the better legal schedule. Singleton and paired rewrites under those orders added at most eight schedule scores. The discovered blocks were 29 and 31, not saved winner IDs supplied to the search.

The build used 1959 scores under a 4096 limit and made zero solver queries. It reproduced the experimental program through the public builder and two isolated source-only cold builds, then passed the full promotion gates. Each cold build took about 16 minutes; a warm call took about 6.5 ms. Those host costs are separate from the 979 emitted execution cycles.

Sources: [resource-order pilot](../experiments/resource_order_results.md), [979 promotion](../experiments/promotion_979_results.md), [receipt](../experiments/promotion_979_receipt.json) and [automatic discovery trace](../experiments/promotion_979_evidence/discovery_progress.jsonl). The earlier selected final-hash pilot is cataloged as local-only evidence in the wiki; it is not a fresh-clone dependency.

## 979 → 975: advance the gather startup

The third backward/forward order gives the dependency ancestry of the first 26 logical gathers a forty-cycle priority boost during forward insertion. Dependencies and native engine assignments stay fixed. Discovery tests this order alongside native and dependence-tail orders, then selects the final-hash rewrite for block 31 alone.

| Measured event | 979 release | 975 release |
|---|---:|---:|
| First gather issue | 61 | 55 |
| Last gather issue | 968 | 964 |
| Empty gather cycles inside that interval | None | 67, 68 |
| Final store and pause issue | 978 | 974 |
| Scratch words | 1463 | 1469 |

Instruction counts are unchanged. The earlier start more than offsets the two empty gather cycles. Blocks 30 and 31 both store at cycle 974. Automatic discovery used 1963 score entries, and two isolated source-only rebuilds reproduced the same program digest. The submission, supplementary, optimizer and full compiler verifiers all passed.

Source: [975 verification report and preserved logs](../experiments/startup_ancestry_candidate_results.md).

## Current endpoint and what remains unknown

Commit `1df789d` published **975 cycles / 1469 scratch words** as a candidate on September 15. The remaining verification completed that day against the committed sources. The older 979 solver OOM remains unknown for its own graph and constraints. It is not retroactively a successful query, and it does not conflict with the later constructive results.

The capacity-only bound for the current instruction stream remains 967. No global optimum or real-hardware speedup has been established. Earlier "final" results and scoped lower bounds remain historical evidence, not current limits.

**The recurring lesson: optimize the complete dependency graph under its resource limits. Fewer instructions, more caching, more SIMD, or a shorter local chain are useful only when the fully executed kernel gets faster.**

For current code, read the [architecture map](architecture.md). For methods and negative results, use the [technique wiki](reference/README.md). For exact verification commands and costs, use the [verification guide](verification.md).
