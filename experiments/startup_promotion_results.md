# Startup-policy integration

## Result

The normal `KernelBuilder.build_kernel` entry point now produces **1,041 cycles / 1,458 scratch words**. This improves on the preceding production result by eleven cycles and on the [startup prototype](load_gap_results.md) by one cycle and one word.

The 1,042-cycle policy reproduced exactly with the previous cache plan. Running automatic cache selection with that policy active found the additional cycle. No new tuning sweep was needed.

This integration was verified locally before the user authorized committing it and the research reports. No push or external challenge submission was requested in that publication step.

## Implementation

`kernel_compiler.py` records each walker's first uncached gather by logical value, then finds the dependency ancestry of the first four walkers' targets after dead-code removal. For the first 48 cycles, it subtracts 2,560 scheduler priority units from those ancestors. It restores ordinary priorities earlier if any targeted gather starts. Real issue and lookahead forecasts share the same priority list.

The targets come from the emitted graph, not saved operation positions. Changing cache sites can change which gather is first without invalidating the targets. All 32 walker contexts remain available. The block count, priority strength, and cutoff are benchmark-tuned rules, not a demonstrated general scheduling policy.

The cheaper 1,076-cycle planner still starts from no depth-4 caches. The advanced stage evaluates its two toggle neighborhoods with startup priority enabled. It scores 350 plans in total and retains fourteen sites. Relative to the preceding 1,052 cache plan, it removes `(8,15)` and `(15,4)` and adds `(3,15)` and `(7,15)`. No winning cache-site list or saved instruction stream is embedded in production.

`compile_benchmark(startup=False)` regenerates the preceding 1,052 implementation, including its own automatic selection, for verification. The cache can retain both startup modes; each result remains immutable and each builder gets fresh mutable bundles. The benchmark/default-knob dispatch and legacy fallback are unchanged.

## Verification

The integrated sources passed:

```sh
python tests/submission_tests.py
python scripts/verify_retry.py
python scripts/verify_compiler.py
ruff check perf_takehome.py kernel_compiler.py kernel_lookahead.py scripts/verify_retry.py scripts/verify_compiler.py
ruff format --check perf_takehome.py kernel_compiler.py kernel_lookahead.py scripts/verify_retry.py scripts/verify_compiler.py
git diff --check
git diff --exit-code 5452f74 -- tests/ problem.py
```

All nine frozen tests reported 1,041 cycles. Supplementary verification covered 100 generated inputs, five asymmetric patterns, nine other shapes, three non-benchmark performance ceilings, scheduler hazards, and pause/store completion.

The compiler verifier covered 100 additional full-width inputs, lane ownership, dependency/constant/selector mutations, three explicit-override fallbacks, and cached-program isolation. Fresh hash-seed-0 and hash-seed-17 builds reproduced the same digest. The latter copied only four production source files, with no tests, configs, or temporary modules, and forbade runtime-data and reference helpers during compilation.

The common 1,041-cycle gate rejected the executed 1,082 legacy program, 1,076 baseline, 1,052 previous production program, and 1,042 startup prototype. The previous production and prototype instruction digests reproduced exactly.

The old flow-mutation locator expected the address multiplier -2 to use flow. The new schedule assigns it to load, so that locator failed before the full verification run. The corrected check selects a hash constant actually assigned to flow and requires `Incorrect output values`, not an unrelated crash.

The supplementary oracle now also checks memory length and the suffix after output. A separate padded-image control passed, and an appended store that corrupted its sentinel failed with `Modified non-output memory`. An actual 64-site plan requiring 1,719 words was rejected before lowering or execution.

## Costs and limits

| Measurement | Observed |
|---|---:|
| Initial normal-path build | 74.239 seconds |
| Compiler verifier's cold build | 75.967 seconds |
| Fresh hash-seed-0 build | 74.661 seconds |
| Fresh source-only hash-seed-17 build | 71.798 seconds |
| Memoized build | 0.0034 seconds |
| Fresh-process peak resident memory | 68,052 / 68,180 KiB |
| Scored plans | 350 |

Compilation remains roughly 72 to 76 seconds cold on this host. These observations do not establish a compilation-speed improvement. The search limit remains 1,049 scored plans, with at most 921 in the baseline stage and 128 in the advanced stage.

The complete stream has 2,008 load, 781 flow, 5,793 VALU, 11,475 ALU, and 32 store instructions. Its first gather is at cycle 60 and last at 1,029. The capacity-only bound is 1,004 cycles for this stream. Neither its 37-cycle gap nor any earlier bound establishes recoverable savings or challenge-wide optimality.

The contract remains root starts and final values on the benchmark. Other tested shapes use the legacy generator; arbitrary starting indices, final-index equivalence, and generality of the startup policy are not established. The complete compiler is not formally proved.

Instruction SHA-256:

```text
817c213e13db64ca7ffacad403de35f1fc57974909ce5e974b0751efb8e2f43b
```

Logs and the extra failure controls are in `/tmp/perf-promote-1042.IQW0av/`, including `normal_build.json`, `compiler.json`, `submission.log`, `supplementary.log`, and `extra_checks.py/.json`. The temporary artifacts are not production dependencies. The normal verification commands remain runnable from the repository alone.

`tests/`, `problem.py`, `perf_takehome.py`, and `kernel_lookahead.py` remain unchanged. The user subsequently authorized a commit. No push or external challenge submission was performed.
