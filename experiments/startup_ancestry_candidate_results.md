# Verified 975-cycle startup ancestry scheduling

## Result

A bounded startup-priority policy produced a verified **975-cycle / 1,469-word** kernel, improving the 979/1,463 compiler by four cycles while using six more scratch words. It uses the same instruction graph family and native engine assignments. No solver ran.

All outstanding verification completed successfully on September 15, 2026. The full compiler verifier ran against a clean archive of `1df789d`; two isolated source-only rebuilds reproduced the exact public program digest. Submission, supplementary and optimizer checks also passed. The filename retains the original candidate-report path so published links remain valid.

## Mechanism

The backward/forward scheduler now tests a third order. During forward insertion, it gives the dependency ancestry of the first 26 logical gather operations a forty-cycle priority boost. Targets are derived from the generated graph; no saved instruction IDs, timings or runtime values are inputs.

The previous 979 schedule issued 1,816 gathers continuously from cycle 61 through 968. The 975 schedule starts at 55, has empty gather cycles 67 and 68, and ends at 964. Blocks 30 and 31 both store at cycle 974, alongside the terminal pause, for 975 complete cycles.

The final refinement retains only block 31's final-hash rewrite. Engine counts are unchanged: 1,888 load, 945 flow including pause, 5,800 VALU, 11,524 ALU and 32 store instructions.

## Discovery and measurements

The source compiler independently rediscovered the same cache and selector plan, evaluated three scheduling orders across the graph-derived final-hash neighborhood, and selected:

- arithmetic profile `(2, 3)`;
- final-hash block `(31,)`;
- selector sites `(22,15,0,6)` and `(29,15,0,7)`;
- 1,963 score entries;
- zero solver queries.

The standalone cold public build took 911.96 seconds. Its program digest is:

```text
861864c85979d75993f9e07187b6bde2035b9d4085b9f6d2acb81622ad67138b
```

## Evidence

Passed:

- `python tests/submission_tests.py`: nine unchanged tests, 975 cycles in every case, 909.64 seconds.
- A fresh reconstruction from the selected plan matched the public-build digest, passed dependency and independent lane-ownership checks, fit in 1,469 words, and passed 100 full-width inputs plus five asymmetric patterns while preserving all non-output memory.
- `python scripts/verify_justify.py`: three scheduling modes, executable toy, missing-edge rejection, budget and duplicate-reservation controls.
- Python compilation, Ruff F/E9 checks, Ruff formatting, `git diff --check`, and `git diff --exit-code 5452f74 -- tests/ problem.py`.

The following checks were pending when `1df789d` was published and have now passed:

- `python scripts/verify_compiler.py`: public-path execution on 100 full-width inputs; lane ownership; three explicit override fallbacks; historical slower controls; dependency, constant and selector mutations; cached-program isolation; and two isolated source-only rebuilds at hash seeds 0 and 17.
- `python scripts/verify_optimizer.py`: duplicate-lane and missing-dependency rejection, illegal-timing rejection, fresh allocation, scratch-before-lower rejection, exhausted-budget rejection, native 981 execution and executed 980-control rejection.
- `python scripts/verify_retry.py --max-cycles 975`: 100 random inputs, five patterns, nine other shapes, three non-benchmark ceilings, scheduler hazards, co-issued pause/store and a corrupted-kernel control.

The full verifier completed in about 45 minutes 49 seconds, including cold builds of 944.77, 880.23 and 868.39 seconds. All three produced 975 cycles, 1469 words and the digest above. The two isolated builds reported zero solver queries; named runtime-data, reference and solver entry points were blocked during construction.

Raw logs, exit markers, timestamps, the public-build record and source hashes are preserved in [promotion_975_evidence/manifest.json](promotion_975_evidence/manifest.json). These are verification artifacts, not production inputs. The manifest records their origins and hashes. Exploratory sweeps and replay programs remain temporary artifacts under `/tmp/perf-978-candidate/` and `/tmp/perf-975-program.json`; they are not required to reproduce the compiler.

## Decision

Mark the 975 implementation as verified production. No verification jobs remain pending for this change. The supported contract is root-starting traversal, final values and preservation of other memory. These checks do not prove arbitrary non-root or final-index equivalence, global optimality, or real-hardware speedup. No independent code review or formal proof is claimed. No external challenge submission occurred.
