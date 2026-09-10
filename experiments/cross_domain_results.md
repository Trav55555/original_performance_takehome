# Cross-domain optimization experiments

## Result

The retained kernel now runs in **1,088 cycles**, down 25 cycles from commit `b09d2a6` at 1,113. It also beats the old dependency graph's 1,104-cycle lower bound because it changes the computation graph.

The new graph's derived scheduling interval is **1,074 through 1,088 cycles**. This is neither an exact optimum nor a challenge-wide lower bound. Scratch now uses all **1,536 words**.

The useful connection was between predicate reuse, register lifetimes, and selective caching. None of these changes helps much in isolation if it merely moves work onto another saturated engine.

## 1. Reuse a branch decision instead of extracting it again

The index update computes `b = v & 1` and then `q_next = 2*q + b`. Therefore `q_next & 1` is exactly the already-computed `b`, including under 32-bit wrapping arithmetic.

The shallow lookups extracted that same bit again. Removing those extractions saves 192 vector operations across the benchmark. Removing the unused vector constant saves another operation and eight scratch words.

The first attempt moved parity into shared selection scratch. It was incorrect across round-tile boundaries because another block could overwrite the cached bit. That candidate failed the frozen output check and was rejected. Restoring boundary recomputation fixed correctness, but the default schedule regressed to 1,133 cycles. Even nine selection banks only reached 1,110 cycles while consuming all scratch.

The better allocation was to leave parity in its existing private register and change its consumers. Swapping temporary roles in the selection trees lets the final leaf selection overwrite parity only after its last read. The private register also survives round-tile boundaries without recomputation.

Result: **1,107 cycles and 1,408 scratch words**, with no extra predicate arithmetic or new registers.

## 2. Cancel representation conversions at entry

Initially encoding values with `C`, then XORing the root encoded with the same `C`, performs two scalar XORs where one would suffice. A prototype mixed the actual root into initial values directly and skipped the first root XOR. It used an otherwise unused preload word for the raw root and preserved zero-round behavior.

This removed 255 scalar operations but did not improve cycles: 1,113 alone, or 1,107 alongside private predicate reuse. The scalar engine was not the limiting resource after those changes.

Decision: do not retain this extra initialization path merely because its instruction count is smaller.

## 3. Spend spare flow capacity on a few late lookups

Predicate reuse freed eight scratch words. Together with the previous spare space, this made room for sixteen additional cached node vectors, exactly filling scratch.

The new cache covers depth 4. Its scalar preload staging reuses the existing sixteen-word buffer after the shallow broadcasts consume it. Selection uses the existing five working vectors, carries parity through all eight leaf pairs, and rematerializes upper masks after their previous uses. A scalar mask avoids allocating another vector constant.

Full or early cache use is expensive: a sixteen-node selection takes fifteen flow slots. The winning policy caches only the first six blocks' repeated depth-4 visits. The first depth-4 frontier still gathers normally. This is a static policy over public block/round positions, not a prediction about runtime data or random seeds.

| Screened variant | Cycles |
|---|---:|
| Committed baseline | 1,113 |
| Private predicate reuse | 1,107 |
| Cache first four blocks on the first depth-4 visit only | 1,163 |
| Cache first four blocks on repeated visits only | 1,093 |
| Cache first five blocks on repeated visits only | 1,089 |
| Cache first six blocks on repeated visits only | **1,088** |
| Cache first eight blocks on repeated visits only | 1,097 |

Identical lookup counts can behave differently depending on where they occur. More caching is not automatically better.

### Resource exchange

| Engine | Committed baseline | Retained |
|---|---:|---:|
| VALU | 6,556 | 6,397 |
| ALU | 12,304 | 12,273 |
| Load | 2,137 | 2,091 |
| Flow, including pause | 705 | 796 |
| Store | 32 | 32 |

Six cached vector lookups remove 48 scalar gathers; two preload operations make the net reduction 46. The added flow work is the price of that reduction. The scheduler policy itself is unchanged.

## Verification and search limits

The local screening budget was 48 attempts, including repeated controls and the rejected incorrect prototype. No cloud jobs, solver installation, or input-dependent program generation were used.

The final prototype and cleaned production code emit identical benchmark instructions. Production passes:

- All nine unchanged frozen submission tests at 1,088 cycles.
- 100 random inputs, five full-width/asymmetric patterns, and the supplementary verifier's eight additional shapes.
- Another 88 pause-enabled shape combinations across heights 3, 4, 5, and 10; batches 8 and 64; and round counts through 30.
- Register-hazard and pause/store checks, plus rejection of a deliberately corrupted kernel.
- A performance negative control: the updated gate rejects the committed 1,113-cycle generator.
- Ruff lint/format checks and immutable-file checks for `tests/` and `problem.py`.

The regional bound calculation adds 320 implied constraints. Its strongest subset has 1,968 loads, earliest issue bound 78, and completion-tail bound 13:

```text
78 + 13 + ceil(1968 / 2) - 1 = 1,074
```

All constraints were checked against the retained schedule. The bound implementation also passes its separate exhaustive small-graph checks. This remains a derived bound, not an exact solver result.

Rerun retained checks:

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
ruff check perf_takehome.py scripts/verify_retry.py
ruff format --check perf_takehome.py scripts/verify_retry.py
git diff --check
git diff --exit-code origin/main -- tests/
git diff --exit-code 5452f74 -- tests/ problem.py
```

Disposable source transformations and results are in `/tmp/perf-crossdomain/`: `program.md`, `screen.py`, `tune.py`, `private.py`, `cache.py`, and their JSON results. They describe the pre-promotion baseline and are not production dependencies. They may disappear with temporary storage cleanup. The regional analysis remains under `/tmp/perf-bounds/`.

## Next hypotheses, not measured results

- A different basis for the final XOR/right-shift could move conversion work across round boundaries. It needs an actual reduction in the full hash/index computation, not just relocation of the same operations.
- Speculative sibling fetches could hide address latency, but per-lane selection and scratch use can consume the gain. Full-depth speculation would exceed current flow capacity in the straightforward implementation.
- Bit-sliced node tables exchange loads for shifts and reconstruction. Arbitrary 32-bit node values prevent treating this as a small packed-value lookup for free.

Keep the measured predicate and late-cache changes. The next large improvement needs another instruction-mix change; scheduling this new fixed graph has at most fourteen cycles of headroom under the current bound.
