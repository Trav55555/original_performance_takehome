# From 1,303 to 980 cycles

We saved **323 cycles: 24.8% less execution time, or about 1.33× faster**.

The story was not one clever scheduling trick. We repeatedly changed the representation, exposed more independent work, moved work between execution engines, and then reconsidered the schedule. A change that failed early sometimes became useful after another bottleneck moved.

```text
1303 → 1113   Representation, temporary storage, and pipeline scheduling
1113 → 1082   Predicate reuse, selective caching, and instruction choice
1082 → 1076   Rebuilt compiler and alternative constant construction
1076 → 1052   Hash fusion, lookup changes, and cache reselection
1052 → 1041   Startup scheduling and another cache reselection
1041 →  981   Deeper cache search and joint selector balancing
 981 →  980   Small, exact, allocation-checked suffix repair
```

This history covers the work from the 1,303-cycle baseline through release `168e0f2` and the subsequent completed 979-cycle query.

Below, the cycle counts are measured checkpoints. The diagrams are schematic unless marked with actual issue times. Some checkpoints were experiments rather than separately published releases.

## 1. What we were optimizing

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

## 2. 1,303 → 1,117: representation and parallelism

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

## 3. 1,117 → 1,113: prioritize future loads and pack the ending

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

## 4. 1,113 → 1,082: reuse predicates, then spend the recovered space

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

## 5. 1,082 → 1,076: a new compiler creates room for further changes

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

## 6. 1,076 → 1,052: combine algebra, lookup representation, and reselection

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

## 7. 1,052 → 1,041: repair startup, then reselect again

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

## 8. 1,041 → 981: search the new cache/selector trade-off properly

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

## 9. 981 → 980: the last cycle required coordinated scheduling

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

## 10. Outcome at the 980-cycle release

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

**The recurring lesson: optimize the complete dependency graph under its resource limits. Fewer instructions, more caching, more SIMD, or a shorter local chain are useful only when the fully executed kernel gets faster.**
