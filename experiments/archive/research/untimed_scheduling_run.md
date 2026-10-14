# Untimed scheduling launch record

At the user's explicit request, the next solver run has **no solver timeout and no child wall deadline**. This file records the launch, not a terminal outcome.

- Case: original 981-cycle graph, fixed native engines, ordered lanes, pinned native-order loads.
- Target: 980 cycles; prefix before cycle 469 fixed; later retiming within ±8 cycles.
- Scratch reallocation remains mandatory before execution; limit 1,536 words.
- Worker address-space cap remains 2 GiB. Memory exhaustion is an unknown outcome, not proof of infeasibility.
- Worker PID at launch: `1059154`; supervisor: `1059153`.
- Workspace: `/tmp/perf-unlimited-scheduling.irTPtT/`.

Inspect `status.json` and `heartbeat.json` for current state, `worker.log` for diagnostics, and `result.json` or `failure.json` for a terminal outcome. The worker saves a SAT assignment before allocation and automatically runs full-width/pattern/reconstruction checks for a legal improvement. The remaining promotion gates must still pass before calling it a strongly verified new best.

The process runs outside the interactive tool lifetime and stops on a terminal solver result, resource failure or explicit cancellation. It does not automatically launch other cases or raise the memory limit.

Production and all prior reports remain unchanged. No commit, push, package installation, cloud job or external submission.
