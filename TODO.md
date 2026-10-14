# To do

Open work, most important first. Remove an item when it is done or dropped.

## 1. Decide whether to keep the exact-solver tools

The production build never calls a solver, but the compiler still checks for `z3-solver` because the retained exact-scheduling tools need it, and some solver plumbing in the compiler is unused. Removing both shrinks the build path. The cost is losing the ability to rerun the old exact-scheduling experiments. `scripts/verify_equivalence.py` would still need Z3 as a verification-only dependency.

Oracle for any removal: the program digest stays `861864c85979d75993f9e07187b6bde2035b9d4085b9f6d2acb81622ad67138b`, and all verifiers pass.

## 2. Simplify lifetime bookkeeping in the allocator (optional)

Deferred during the September refactor because `_allocate` may depend on dict insertion order. Attempt it only with the digest as the oracle. The benefit is small.

## 3. Add a cold-build CI job (optional)

The `Checks` workflow proves the saved program but never builds it, so it cannot show that the current compiler still emits that program. A job that runs `python scripts/verify_equivalence.py` without `--program` would build, prove and report the digest in about 20 minutes. Run it on demand or on a schedule, not on every push.

## 4. Research: close the gap between 975 and 967 cycles

967 cycles is a lower bound from the 5,800 VALU operations on six slots. It ignores dependencies and may be unreachable. Figure 5 of the [summary page](https://trav55555.github.io/original_performance_takehome/) shows the slack in the first ~75 and last ~25 cycles, where load, flow and VALU use drop. Progress needs fewer VALU operations or less startup and tail slack. This is open-ended research, not cleanup.
