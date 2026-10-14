# Below 980: the load stream, not another late flow gap

The verified incumbent remains **980 cycles / 1,449 words**. This exploration ran twelve static preflights and a three-candidate early-address pilot. It found no improvement and launched no exact query.

The useful result is a more precise bottleneck: the incumbent issues **1,816 gather loads continuously, two per cycle, from cycle 61 through 968**. Another local reshuffle cannot create a missing load slot. To finish earlier, we need an earlier start, less load work, or a shorter dependency path after the last loads.

## Six checks on the existing graph

We tested targets 979 and 978 at fixed starts 949, 917 and 853. Native A's original 981-cycle schedule remained the displacement anchor, with native engines, a fixed prefix, unpinned loads and a radius of eight. We did not re-anchor on the retimed winner to gain extra movement.

All six failed necessary capacity checks:

| Target | First movable cycle | Mandatory loads | Available load slots | Other obstruction |
| --- | ---: | ---: | ---: | --- |
| 979 | 949 | 16 in 961–967 | 14 | None reported |
| 979 | 917 | 104 in 917–967 | 102 | None reported |
| 979 | 853 | 232 in 853–967 | 230 | None reported |
| 978 | 949 | 16 in 961–966 | 12 | One excess flow operation |
| 978 | 917 | 104 in 917–966 | 100 | One excess flow operation |
| 978 | 853 | 232 in 853–966 | 228 | One excess flow operation |

Independent repeated propagation reproduced the bounds, and separate interval counts checked the reported overloads. These certificates rule out those scoped repairs, not 979 globally.

In the smallest 979 case, the sixteen loads are exactly the final gathers of blocks 30 and 31. Block 30 cannot load before 961 under the fixed-prefix dependency chain; block 31 cannot load before 964. All sixteen need to issue by 967. Waiting longer on an exact solver cannot satisfy sixteen operations in fourteen slots.

## Three early-address candidates

The existing rewrite can precompute `D - 2*q` before the hash finishes, leaving only subtraction of the new branch bit on the address path. That made it a specific test of the observed release delay.

The historical early-address screen tested fifteen blocks and stopped at block 26. It omitted blocks 30 and 31. We therefore evaluated only these additions to A, retaining its existing early site `(0,3)`:

| Configuration | Executed cycles | Scratch words | Target-979 preflights at 949 / 917 |
| --- | ---: | ---: | --- |
| Verified selected-timing control | 980 | 1,449 | Not a new graph |
| Native A control | 981 | 1,449 | Existing obstruction |
| Add `(30,14)` | 986 | 1,505 | Both fail |
| Add `(31,14)` | 981 | 1,513 | Both fail |
| Add both | 985 | 1,497 | Both fail |

All three candidates fit scratch and passed independent lane/capacity checks and a full-width frozen-reference smoke execution, including non-output memory preservation. No slower candidate received full promotion gates.

The rewrite did not advance the actual gathers. Block 30's native first gather was 961; it moved to 967 with its own rewrite and to 966 with both rewrites. These were normal greedy compilations, so operation ordering and engine choices could change. The results do not isolate urgency demotion as the sole cause.

Each new graph also failed both declared preflights. Their timing anchors were their own native schedules, not A's saved instruction positions. There is no eligible exact query from this pilot.

## What the complete load stream reveals

The saved winner has 1,888 load instructions in total: 72 setup/input loads and 1,816 gathers. It leaves fifty load slots unused before the first gather, then fills every load slot from 61 through 968.

Most final-round gathers have an eleven-edge data-dependency path to an output store. A gather at 968 on one of those paths cannot store before 979, requiring 980 complete cycles.

There is one important exception: **block 14's eight final gathers have a ten-edge path**, because that block already uses the final-XOR rewrite. They currently issue at 913–916. The existing narrow displacement bounds prevent moving them to the end of the load stream.

That gives three distinct ways to attack 979:

1. **Shorten the last gather's output path.** Apply the already proved final-XOR rewrite to block 30, block 31, or both. The important comparison is now the actual final gather deadline, not a generic native-schedule speedup. A ten-edge tail permits a load at 968 to store at 978. Capacity feasibility still needs to be checked.
2. **Compress the prologue by one cycle.** Attempt to advance the first gather from 61 to 60 and shift the verified body earlier. The dependency-only earliest first gather is 48; that is a relaxation, not a feasible coupled start time. A small prefix model would need checked boundary constraints for the shifted body.
3. **Put short-tail work last.** Move some of block 14's final gathers to the end while pulling eleven-edge-tail gathers earlier. This deliberately changes the old displacement scope and could increase scratch lifetimes. It is not covered by the negative suffix certificates.

## Recommended next decision

Start with the smallest semantic change: retain block 14's rewrite and test final-rewrite block sets **`[14,30]`, `[14,31]`, and `[14,30,31]`**, using the existing ALU/VALU/VALU profile. Include native A and the verified 980 timing control. Do not add a priority-restoration factorial initially.

A proposed budget is five constructions including controls, six target-979 preflights on the three new graphs, and at most one conditional exact query on the smallest admitted scope. Keep the 2 GiB/no-deadline policy and current variable/membership caps. Require native reconstruction and same-encoding controls before that query, then fresh allocation and full verification for any apparent win.

This next pilot is a proposal, not a launched run. Earlier final-XOR screens do not establish its result on these graphs and this endpoint bottleneck.

## Evidence and limits

Workspace: `/tmp/perf-below980.N2cfEi/`. The [receipt](below_980_exploration_receipt.json) records the exact cases, scopes, source hashes and candidate outcomes.

The two controls reproduced their expected digests. The freshly captured A graph matched the previous model's jobs, edges, operations, widths and native digest. Candidate sources and manifest were frozen before evaluation. The run used five construction/evaluation attempts, twelve static preflights and zero solver queries.

Production, the archived 980 winner and previous reports remain unchanged. No commits, pushes, installations or submissions occurred. The additional candidate results are smoke-verified research evidence, not new fully verified incumbents.
