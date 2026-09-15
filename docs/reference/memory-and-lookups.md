# Memory, lookup representation and scratch

[Wiki](README.md) · [Algebra](representation-and-algebra.md) · [Scheduling and allocation](scheduling-and-allocation.md)

A lookup optimization exchanges load work, arithmetic, flow instructions and live storage. Include table construction and broadcasts in the cost. Cached nodes are runtime-loaded data, not compile-time constants or saved answers.

## Retain state and expose independent work

**Production, evolved from January batching.** Keep walker state in scratch across rounds rather than loading and storing it on every step. Eight SIMD lanes make 32 groups for batch 256. Enough independent groups hide one walker's hash-to-next-address dependency behind another's work.

Private hash temporaries avoid false serialization through shared storage. During the retry, two private hash temporaries per group plus shared shallow-selection banks enabled 32 active groups. More private storage is not always better; it competes with cached node vectors and other live values.

The early `group_size=17`, `round_tile=13` settings are historical. The current public defaults and benchmark dispatch are described in [architecture](../architecture.md).

## Shallow caches and selected depth-4 lookups

**Production.** Preload shallow tree levels and select from them instead of issuing repeated lane gathers. A full sixteen-way depth-4 selection tree uses fifteen binary selects in its original form, trading load demand for flow demand and scratch.

At the 1088 checkpoint, six cached repeated depth-4 visits removed 48 gathers but added two preload operations. Net load reduction was 46, not 48. Caching every visit was worse.

The profitable sites changed after fusion, branch-history changes and scheduler changes. Production therefore discovers sites using full schedule/allocation scores, rather than importing the earlier winning list. Later toggle neighborhoods, swaps and profile coupling reached the 981 native plan that underlies the final refinements.

Sources: [cross-domain experiments](../../experiments/cross_domain_results.md), [cache neighborhood](../../experiments/cache_neighborhood_results.md), [descent](../../experiments/cache_descent_results.md), [discovery implementation](../../kernel_optimizer.py).

## Arithmetic selectors and branch history

**Production, with earlier unsuccessful variants.** For a normalized bit:

```text
SELECT(bit, yes, no) = no + bit*(yes - no)
```

The program computes the difference from loaded node values and broadcasts it as needed. This moves online work from flow to vector arithmetic. It is invalid to apply this form to an arbitrary nonzero predicate without normalization.

Retaining branch history and permuting lookup order can start partial selection before the newest predicate arrives. Changing bit order requires the corresponding leaf permutation. Selection shape, arithmetic-leaf count and cache admission must be evaluated together.

A tied `2/3` arithmetic-pair profile enabled a cache addition that improved the earlier `2/2` configuration. Pairwise gains are not additive. Sources: [technique ports](../../experiments/technique_port_results.md), [published profile/cache trace](../../experiments/promotion_980_evidence/progress.jsonl).

## Tensor and Mobius lookup forms

**Experimental; no production cycle win in the declared screens.** For four arbitrary words and normalized bits `s,t`:

```text
c00 = a
c10 = b - a
c01 = c - a
c11 = d - c - b + a
u = FMA(s, c10, c00)
v = FMA(s, c11, c01)
y = FMA(t, v, u)
```

This selects `a,b,c,d` for `00,10,01,11`. The first two FMAs are independent. It replaces a three-select tree with three arithmetic operations after charged coefficient setup. A successful toy amortization result did not transfer directly to the complete kernel.

Recursive Boolean Mobius conversion applies these finite differences across more bits. The transform is triangular and invertible modulo `2^32`; it does not compress arbitrary data or imply sparse coefficients.

In the 74-candidate mathematical screen, the best two-bit tile tied 981 cycles at 1497 words. Broad recursive conversion's best feasible result was 1003/1377. All ten feasible recursive variants had retained-arithmetic credit bounds of at least 988 cycles. Ordinary retiming or scalar/vector reassignment could not beat 980 without changing that retained work.

The source records are local-only, identified in the [research catalog](search-and-research.md#local-only-records). These were screens, not new production promotions.

## Slope-select and coefficient sharing

**Experimental.** A different four-way evaluation uses two FMAs and one select:

```text
h = b-a
v0 = c-a
v1 = d-b
base = FMA(s, h, a)
slope = SELECT(s, v1, v0)
y = FMA(t, slope, base)
```

This selects a coefficient rather than the final value. The chosen evaluation bit is not necessarily the earliest-arriving bit. In the sixteen-case pilot, a natural-order block-31 case improved its matched tensor version from 984 to 981 cycles. Reversed variants tied 981 while reducing scratch from 1481 to 1473. None reached then-production 980.

Sharing exact existing differences and broadcasts sometimes helped. One tensor variant improved from 983/1497 to 981/1481, but other sharing choices slowed execution. Longer shared lifetimes and changed scheduling can offset fewer definitions.

The identity `(d-b)-(c-a) = (d-c)-(b-a)` allows cross-axis coefficient reuse. The tested algebraic normalizer removed one scalar instruction in reversed tensors without changing cycles or scratch. It did not distribute XOR through addition or inspect node values.

These results are scoped to the tested sites and schedulers. Broader materialization placement, cache reselection and all-site conversion were not covered by those pilots.

## Pointer rematerialization

**Tested, no runtime improvement.** Recompute an output pointer near its consumer instead of keeping it live for much of the kernel. Count the recomputation's dependencies, including any retained base address.

Twelve policies compared against 1076/1253. Best freely scheduled regeneration tied 1076 with 1241 words. Explicit near-store variants took 1081 to 1093 cycles. Source placement alone did not keep the instruction late; the scheduler hoisted work.

One variant reduced total scalar word-cycles from 33789 to 1076 while reducing peak scalar allocation only from 53 to 41. Another prolonged the base-seven lifetime. Integrated lifetime, peak allocation and runtime are different objectives.

Source: [Algorithmica follow-up](../../experiments/algorithmica_followup_results.md). The twelve-word saving did not meet that experiment's integration threshold.

## Other storage approaches and legality

Selection-only virtual-register allocation tied 1117 and was not promoted. The later full SSA compiler removed more premature physical decisions and enabled a different result. Progressive/deeper selection networks and alternative bank arrangements did not establish a better retained program in their tested scopes.

A foreign allocator touched 1465 distinct words but used physical address 1535, requiring the full 1536-word array. Count the required allocation/address range, not just words touched by one run. Sources: [selection-only prototype](../../experiments/virtual_register_results.md), [fork audit](../../experiments/github_1063_audit.md).

Every reschedule needs fresh allocation and lane checking. A 979 timing using 1537 words is rejected before execution, regardless of how attractive its lookup representation looks.
