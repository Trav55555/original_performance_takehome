# Mathematical bounds and bit-level algebra

## Decision

Keep the verified **981-cycle / 1,465-word** candidate. This investigation found stronger, checkable bounds but no faster executable program:

| Model | Established lower bound | What remains possible |
|---|---:|---|
| Current logical operations, aggregate engine reassignment | 965 | Dependency and timing restrictions ignored |
| Current logical dependencies, eligible engine reassignment | **967** | Global rescheduling, different allocation |
| Current logical dependencies and current engine assignments | **969** | Global rescheduling, different allocation |
| Current prefix, engines and physical registers; last 16/32/64 cycles movable | **981** within each restricted model | Changes outside those restrictions |
| Problem-wide worst case, using a valid all-zero tree | 16, from input reads | Far too weak to estimate the optimum |

The 967 and 969 bounds do not apply after changing the computation graph. Neither bound is an attainable guarantee. Full-graph feasibility at 980 remains unresolved. Production stays at commit `5691617`, 1,041 cycles.

## Resource certificates

The earlier weighted-resource argument is valid. The logical graph contains 4,518 vector binaries, 36 scalar binaries, 2,660 vector multiply-adds and 54 broadcasts. A vector binary may use one VALU instruction or eight ALU instructions. Assign eight accounting units to each retained vector arithmetic operation and one to each scalar binary:

```text
W = 8*(4518 + 2660 + 54) + 36 = 57,892
capacity = 8*6 VALU slots + 12 ALU slots = 60 units/cycle
T >= ceil(57,892 / 60) = 965
```

These are credits for retained operations, not intrinsic complexity of the hash function. A rewrite can change the required credits.

Exact rational primal and dual certificates agree at `14473/15` cycles for the aggregate relaxation. Dual prices are `1/60` for ALU and `8/60` for VALU, zero for other engines. A matching fractional assignment places `15376/5` vector binaries on VALU and the remainder on ALU; other resource constraints also fit. This proves optimality of that aggregate relaxation, not of a machine schedule. Relative to the current assignment, it shifts 7.8 vector binaries toward ALU.

## Dependency-window certificates

Two graphs were built from the reproduced 981 program:

- Fixed-engine SSA instructions: 20,179 nodes, 54,157 data edges. Physical-register reuse constraints are omitted.
- A deliberately relaxed lane graph: 67,478 atoms, 161,200 edges. Vector operations may split into lanes for dependency analysis; constant alternatives omit their anchor dependency. These relaxations avoid inventing barriers that could overstate the bound.

Both have a dependency-only critical path of 197 cycles. That alone is much weaker than resource throughput.

For each node, compute an optimistic release cycle `r_i` and tail length `q_i`, including its issue cycle. Nodes with `r_i >= r` and `q_i >= q` must fit in cycles `r` through `T-q`. If their required resource work is `W` and capacity is `C`, then:

```text
T >= r + q - 1 + ceil(W/C)
```

The strongest relevant certificates are:

| Scope/resource | r | q | W | C | Bound |
|---|---:|---:|---:|---:|---:|
| Fixed engine: VALU | 1 | 2 | 5,797 | 6 | 969 |
| Reassignment-safe arithmetic credits | 1 | 2 | 57,892 | 60 | 967 |
| Gather loads, either model | 48 | 12 | 1,816 | 2 | 967 |

The gather certificate is particularly concrete: the retained graph has 227 eight-lane gathers. None of their 1,816 scalar loads can occur before cycle 48 in the relaxed graph, and each needs at least eleven following cycles. Even perfect two-load issue then requires `48 + 908 + 11 = 967` cycles.

For arithmetic, the two-cycle strengthening is justified by actual windows: all retained arithmetic occurs no earlier than cycle one, and its results require a later consumer. It is not an arbitrary startup/drain surcharge.

Independent arithmetic checking verified every selected cut. All relaxed atoms, dependencies and credits were also checked against the IR. The bound formula passed 200 small DAGs whose optimal schedules were computed exhaustively. Corrupted certificates, incorrect resource capacities, and an unjustified whole-vector completion barrier were rejected by controls. An initial certificate serialization error was caught by the independent checker, corrected, and the artifacts regenerated.

## Where these relaxations stop helping

A separate earliest-deadline allocator produced resource-window witnesses at 969 for the fixed model and 967 for the relaxed model. Their immediately lower horizons failed. Both independent-resource window models admit 980.

These witnesses are **not executable schedules**. They allocate resource work independently and do not enforce the coupled placement of every dependency, engine mode, vector instruction and scratch lifetime. They show that the current family of window constraints cannot establish 981 as optimal. A stronger model must add coupling, rather than merely rerun the same resource sums.

## Exact tail scheduling

Z3 tested whether the current program could finish in 980 cycles with three suffix sizes. Prefix instructions, engine assignments and physical scratch addresses were fixed. The model preserves read/write hazards, issue capacities and terminal pause placement.

| Movable suffix | Suffix instructions | Result | Solver time |
|---|---:|---|---:|
| 16 cycles | 176 | UNSAT | 0.071 s |
| 32 cycles | 517 | UNSAT | 0.401 s |
| 64 cycles | 1,190 | UNSAT | 2.611 s |

No query timed out. The original 981 schedule satisfied the modeled dependencies. A positive control found and executed a legal three-to-two-cycle pause/store packing improvement.

These are solver-backed negatives for restricted scheduling problems. They do not rule out a 980-cycle solution with an earlier change, another engine assignment, another allocation or another graph. A full joint 980-cycle model was not solved; only the independent-resource whole-graph relaxation was checked.

## Modular arithmetic and 2-adic structure

Ten bounded Z3 queries established seven identities and rejected three false claims.

All six hash stages are bijections on 32-bit words:

- Stages 0, 2 and 4 have odd multipliers 4097, 33 and 9, hence modular inverses modulo `2^32`.
- The right-XOR-shift stages have bit-linear inverses. For shifts 19 and 16, applying the XOR shift twice cancels it, after removing the constant.
- Stage 3, `y = (x+C3) XOR (x<<9)`, has a useful 2-adic description. Starting from `z=0`, iterate `z = (y XOR (z<<9)) - C3` modulo `2^32`. Each iteration fixes nine more low bits. Four iterations recover the original word. Z3 proved this identity for all 32-bit inputs.

This is real number-theoretic structure, but an inverse is not a cheaper forward implementation. Carries also prevent treating the entire hash as one linear transformation over bits: a solver counterexample rejected even GF(2)-affinity of the first word-affine stage.

The final encoded parity identity is exact:

```text
(u XOR (u >> 16)) & 1 = (u & 1) XOR ((u >> 16) & 1)
```

Ignoring the high half is wrong; `u = 65536` is a counterexample. The split does not save instructions when the complete encoded value is still needed: the current code extracts its parity with one AND, while independent extraction needs two ANDs and an XOR.

## One applicable reassociation, tested

The second candidate moves next-address work before the branch bit is ready:

```text
D - (2*q + p) = (-2*q + D) - p       modulo 2^32
```

The compiler already uses this idea at one earlier visit. At a penultimate visit followed by an uncached final visit, the mirrored-index update can become dead, so the reassociation need not add a multiply-add. It changes readiness rather than guaranteeing fewer operations.

After proving the identity, sixteen configurations were tested: the unchanged control and this additional placement at the first fifteen eligible penultimate visits. All fit scratch and passed full-width frozen smoke execution. No speed win: the best alternative tied 981 but used 1,513 words; others took 982–988 cycles. The control's digest remained identical. No new candidate was promoted, and no full winner-verification claim is made for these smoke-only alternatives.

## A genuinely problem-wide, but weak, bound

For an all-zero tree, each output is `H^16(x)` regardless of traversal path. The stage inverse proofs imply that this mapping is bijective. Direct exact evaluation gives `H^16(0) = 0xbd30e3b4`, so it is not the identity.

The in-place output layout matters. Entropy alone would not force loads for an identity function: the answers would already be in memory. Here, however, a program that never reads an independent input word can only leave that word unchanged or overwrite it with a value independent of its original contents. Neither behavior implements a nonidentity permutation for all possible values. Overwriting an unread original would destroy information that exact computation needs.

Thus every one of the 256 independent input words must be read on this valid input family. At most eight words arrive per load and two loads issue per cycle, giving a universal read-work bound of sixteen cycles. This deliberately weak bound does not count hashing, tree access, address setup or final stores. It neither predicts a sixteen-cycle implementation nor places the global optimum near 981.

A useful challenge-wide bound would need stronger word-circuit or memory-query arguments valid across representations, caching policies and recomputation. Fixed-DAG bounds alone cannot supply that result.

## External grounding and limits

- [Boyd and Vandenberghe, duality lectures](https://web.stanford.edu/class/ee364a/lectures/duality.pdf), sections 5.3–5.5: dual feasible points provide lower bounds. The local rational certificate was checked directly, not inferred from the source.
- [Hong and Kung, *I/O Complexity: The Red-Blue Pebble Game*](https://eecs.harvard.edu/~htk/publication/1981-stoc-hong-kung.pdf), sections 2–3: fixed computation graphs, memory limits and partition-based I/O bounds. A mapping to this vector ISA would still need to charge instruction capacities and legal storage behavior.
- [Demaine and Liu, SPAA 2018](https://erikdemaine.org/papers/PebblesRedBlue_SPAA2018/paper.pdf), introduction: optimizing general graph pebbling tradeoffs can be hard. That does not prove this particular instance intractable or establish its cycle minimum.
- [Brucker and Knust, 2000](https://ideas.repec.org/a/eee/ejores/v127y2000i2p355-362.html): bibliographic confirmation of related LP/constraint-propagation scheduling work. Publisher access returned 403, and the accessible record has no abstract; detailed methods were not verified.

The source review supports the mathematical approaches, not any published bound for this challenge. A delegated reasoning attempt failed with a provider credit error; the investigation was completed directly with existing tools and the isolated Z3 installation. No packages were installed.

## Artifacts and next step

The compact [certificate receipt](math_bounds_certificate.json) preserves the numbers, scopes and configuration. Full graphs, certificates, window assignments, solver scripts and logs are in `/tmp/perf-math-bounds.N7I1Pd/`.

```sh
python /tmp/perf-math-bounds.N7I1Pd/bounds.py
python /tmp/perf-math-bounds.N7I1Pd/check_certificates.py
python /tmp/perf-math-bounds.N7I1Pd/check_lane_model.py
python /tmp/perf-math-bounds.N7I1Pd/window_relaxation.py
/tmp/perf-five-arms/solver-env/bin/python /tmp/perf-math-bounds.N7I1Pd/run_exact.py
/tmp/perf-five-arms/solver-env/bin/python /tmp/perf-math-bounds.N7I1Pd/algebra.py
python /tmp/perf-math-bounds.N7I1Pd/rewrite_screen.py
```

The highest-value next step is a more strongly coupled scheduling model, allowing engine reassignment and moving decisions before the frozen 64-cycle suffix. Alternatively, change the operation graph to escape these bounds. More checks of the same independent-resource relaxation cannot close the remaining gap.

All production sources, frozen tests, simulator and pre-existing reports were preserved. No commit, push, cloud job or external submission occurred.
