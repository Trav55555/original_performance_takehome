# Mathematical models: five-arm research results

## Decision

Keep the published **980-cycle / 1,465-word** compiler. This program tested 74 full-kernel candidates across five mathematical approaches. None beat the 981-cycle native control. The published 980 timing was separately reconstructed, freshly allocated and executed as a control, without another solver query.

The useful negative result is specific. Broad recursive lookup factorization reduces flow work and sometimes scratch, but adds too much arithmetic. Small tensor tiles remain a representation hypothesis worth revising, not a demonstrated kernel improvement.

The [program](mathematical_models_program.md) declares the arms, budgets and gates. The [receipt](mathematical_models_receipt.json) includes all candidate rows, source hashes, selected configurations and the post-run audit. Full working artifacts remain in `/tmp/perf-math-program.Z3q77s/`.

## Results

Only scratch-feasible, executed candidates appear in the best-result columns. Over-scratch schedule lengths are not execution results.

| Arm | Candidates | Executed / scratch-rejected | Best cycles / words | Decision |
|---|---:|---:|---:|---|
| A: two-bit tensor tiles | 24 | 24 / 0 | 981 / 1497 | Revise coefficient sharing before a further test |
| B: recursive Mobius lookups | 12 | 10 / 2 | 1003 / 1377 | Archive these broad conversions |
| C: radix and parity projection | 8 | 8 / 0 | 981 / 1465 | No gain at the tested sites |
| D: geometric scheduling | 18 | 11 / 7 | 987 / 1482 | Archive these priority families |
| E: max-plus event schedules | 12 | 12 / 0 | 981 / 1465 | Retain as a diagnostic, not an optimizer win |

The screen took 84.04 seconds on this host, excluding implementation and the later audit. It used 74 candidate reservations and four controls. The eight conditional combination slots and eight validation reconstruction slots remained unused. No arm strictly improved the native control, so the declared combination gate did not open. No candidate qualified for full winner verification below 980.

## A. The tensor toy win did not transfer directly

A four-node table can use the coefficients `a`, `b-a`, `c-a`, and `d-c-b+a`. For normalized bits `s` and `t`:

```text
u = a + s*(b-a)
v = (c-a) + s*(d-c-b+a)
result = u + t*v
```

The first two multiply-adds are independent. The representation replaces a three-select tree with three multiply-adds, after runtime coefficient construction. The earlier toy probe saved three cycles against mixed selection at reuse counts eight and thirty-two.

This program selected twelve late two-bit tiles from the native graph and tested both bit orders. All 24 passed three full-width smoke seeds. Only A18 tied 981 cycles, with 32 more scratch words. It uses the reversed tile order at block 30, round 14, tile zero. This identity is a research result, not a production lookup table.

Relative to the native control, A18 has:

| Quantity | Native | A18 |
|---|---:|---:|
| Flow instructions, including pause | 945 | 944 |
| Vector arithmetic instructions | 5800 | 5804 |
| Scalar arithmetic instructions | 11524 | 11536 |
| Last gather completion cycle | 969 | 968 |
| Complete execution cycles | 981 | 981 |
| Scratch words | 1465 | 1497 |

Advancing the final gather did not advance completion. The extra arithmetic and live coefficients matter in this kernel, even though the toy workload benefited.

There is also an implementation limit. The experimental coefficient cache shares coefficients among new tensor uses, but does not merge them with the compiler's existing node broadcasts and pair differences. For example, coefficient `a` receives a new broadcast even when another lookup still needs the old broadcast of that same scalar. The allocator can reuse storage after last use, but does not eliminate duplicate computations. The next useful comparison would remove those duplicates before changing more scheduling policy. That implementation was not screened here.

## B. Recursive structure changes the arithmetic bill

The full Boolean Mobius transform uses the same finite-difference operation recursively. This is the higher-dimensional form of the two-bit tile. Its triangular transform is invertible modulo `2^32`, and its matrix support has a recursive Sierpinski-like pattern. It does not imply that arbitrary node values or their coefficients are sparse.

Twelve variants covered depth three, depth four, or both; all visits or repeated-traversal visits only; and natural or reversed bit order. Ten were feasible. Two required 1540 and 1571 scratch words and were rejected before lowering or execution.

The fastest feasible case, B03, converts repeated depth-three visits. It saves 88 scratch words but takes 1003 cycles. Flow work falls from 945 to 785 instructions. Vector arithmetic rises to 5937 instructions and scalar arithmetic to 11784.

This has a stronger obstruction than a poor greedy schedule. Its vector capacity bound alone is 990 cycles. Even allowing the usual exchange of one retained vector binary for eight scalar binaries, arithmetic credits give:

```text
work = 8*5937 + 11784 = 59280
capacity = 8*6 + 12 = 60 credits/cycle
lower bound = 59280/60 = 988 cycles
```

That bound assumes these retained computations, with eligible scalar/vector binary exchanges. It does not apply after eliminating or rewriting operations. All ten feasible recursive variants have credit bounds at least 988, so ordinary reassignment and retiming of their retained arithmetic cannot beat 980.

The smallest scratch result was B02 at 1305 words, but it took 1027 cycles. Scratch savings alone do not meet the objective.

## C. Digit coordinates preserve carries, not speed

Four late round-14 branch sites were selected from the native graph: blocks 31, 29, 30 and 27. Each received two alternatives while retaining the complete output hash.

The radix variant splits the last affine stage into base-65536 coordinates. It explicitly computes the carry from the low half and includes that carry in branch parity. Its best result was 984 cycles / 1489 words at block 31.

The projection variant uses the low-bit identity of `9*x + 0xfd7046c5`. Its low bit is `x_low_bit XOR 1`, so branch parity can use `x XOR 1` and the existing final right shift instead of waiting for the complete final XOR. The block-31 case tied 981 / 1465; the other cases were slower. Correctness does not imply a shorter useful dependency path once the added instructions are scheduled.

The new helper implementations passed 2064 full-width and boundary-value comparisons before the full-kernel cases. The old carry-omission counterexample, GF(2) nonlinearity results and 2-adic inverse proofs were not rerun as new discoveries. The wrapping Walsh-Hadamard shortcut remains rejected by its previously demonstrated information-losing collision.

## D. Geometry was too coarse for this schedule

Operations received origin coordinates for walker, round and hash stage. Eighteen variants tested wavefront group sizes four, eight and sixteen; Morton ordering; Gray-code walker ordering; and bit-reversed walker ordering. Each used priority interpolation strengths one-eighth, one-half and one. The scheduler retained its lane-readiness, capacity, scratch-pressure and startup rules.

The weakest four-walker wavefront bias was the best result at 987 / 1482. Seven variants exceeded scratch and were never lowered or executed. The rejected range reached 2077 words.

These tests show that the declared structural priorities did not help this graph and scheduler. They do not rule out piecewise-affine scheduling with different regions, learned parameters, or a changed computation graph. Existing engine-choice heuristics remained active, so these are scheduling-policy comparisons, not experiments with every engine assignment fixed.

## E. Max-plus timing made some instructions earlier, but not completion

This arm constructed capacity chains for the existing native-engine jobs. A chain has one instruction per cycle; the number of chains equals the engine capacity. Data dependencies and chain edges form an event graph. Earliest times follow the recurrence `t[j] = max(t[i] + lag[i,j])`, with fixed-prefix release times where applicable.

Six within-cycle orderings were tested over the whole graph and over the final 128 cycles. All twelve tied 981 / 1465. Whole-graph versions moved 72 to 124 jobs earlier. All six fixed-prefix suffix versions moved zero jobs.

A second longest-path calculation checked the least timing for each constructed event graph. Frozen execution and the lane checker checked the resulting programs. A small nine-cycle model compacted to a three-cycle program, which executed correctly, so the implementation was capable of producing a shorter legal program.

The equal 981 results are scoped to those capacity-chain orders. The published 980 schedule already demonstrates that different ordering choices can do better. No unrestricted optimality or impossibility claim follows.

## Verification and control boundaries

The isolated native compiler produced exactly the same physical program as the original native compiler at 981 / 1465. The published logical timing then reconstructed to 980 / 1465 with the expected digest:

```text
c17788082bd3757c95f02bd743582ff1acd3f55c56e3326d9fc72e65da7ba5bc
```

Saved timing was used only for that control. All candidate searches began from the newly generated native graph, not the saved timing or physical program.

The 65 feasible candidates passed 195 paired full-width seed executions. The best feasible member of each arm also passed five asymmetric patterns, for 25 additional executions. Checks included exact logical lane coverage and dependencies, independent physical lane identity, engine capacities, final outputs, non-output memory preservation and actual cycle count.

The new representation helpers passed 3072 recursive-lookup comparisons, 512 two-bit-tile comparisons and 2064 branch comparisons. A corrupted encoding constant failed the real full-kernel output check. Injected scratch sizes 1537 and 1545 produced zero lowering calls. A zero-budget reservation failed before any construction or ledger append.

Nine over-scratch candidates were rejected before lowering and execution. No solver ran. The program did not repeat the nine-test submission suite, 100-seed winner gate or oracle-blocked cold builds because no candidate improved on 980. These are screened research results, not fully verified new incumbents.

## Next decision and artifacts

The most focused follow-up is tensor coefficient reuse with existing broadcasts and pair differences. Broad recursive conversion would need to reduce its arithmetic workload, rather than merely find a different schedule. The strict isolated-improvement combination gate also leaves coupled plateau-breaking choices untested; earlier research showed that such interactions can matter.

No follow-up was started. All budgets for this program are closed, including unused slots. Production sources and frozen tests are unchanged. There were no installations, cloud jobs, commits, pushes or submissions.

The workspace contains the frozen source snapshot, `program.md`, `baseline_plan.json`, `selection.json`, `attempts.jsonl`, `results.jsonl`, `screen_result.json`, `pure_checks.json`, `research_sources.json`, `protected_sources.json`, and saved finalist configurations, logical schedules and physical programs under `artifacts/`.

For a read-only audit of the saved artifacts:

```sh
python /tmp/perf-math-program.Z3q77s/audit.py
```

`run.py` refuses to restart an already-used manifest. A future rerun or expansion requires a new authorized workspace and budget. Temporary source and program artifacts are not durable once `/tmp` is removed; the repository report, protocol and receipt preserve the decisions and all result rows.
