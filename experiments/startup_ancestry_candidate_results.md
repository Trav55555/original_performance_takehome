# Startup ancestry scheduling candidate

## Result

A bounded startup-priority policy produced a **975-cycle / 1,469-word** candidate, improving the fully promoted 979/1,463 compiler by four cycles while using six more scratch words. The candidate uses the same instruction graph family and native engine assignments. No solver ran.

This is integrated in the working tree but is not a completed promotion. Isolated source-only rebuilds, the full compiler verifier and the optimizer verifier remain outstanding.

## Mechanism

The backward/forward scheduler now tests a third order. During forward insertion, it gives the dependency ancestry of the first 26 logical gather operations a forty-cycle priority boost. Targets are derived from the generated graph; no saved instruction IDs, timings or runtime values are inputs.

The previous 979 schedule issued 1,816 gathers continuously from cycle 61 through 968. The candidate starts at 55, has empty gather cycles 67 and 68, and ends at 964. Blocks 30 and 31 both store at cycle 974, alongside the terminal pause, for 975 complete cycles.

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

Outstanding at the publication checkpoint:

- `scripts/verify_compiler.py` and its two isolated source-only cold rebuilds have not run.
- `scripts/verify_optimizer.py` and the supplementary retry verifier under the new 975 ceiling were launched; results were still pending.

The exploratory sweep and replay artifacts are under `/tmp/perf-978-candidate/`, `/tmp/perf-975-build.json`, `/tmp/perf-975-program.json`, and `/tmp/perf-975-submission.log`. Temporary artifacts are evidence for this working session, not production inputs.

## Decision

Keep the 975 implementation as a candidate. Do not call it fully promoted until the outstanding source-only and failure-sensitive gates pass. The user authorized committing and pushing the candidate with these limits documented. No external challenge submission occurred.
