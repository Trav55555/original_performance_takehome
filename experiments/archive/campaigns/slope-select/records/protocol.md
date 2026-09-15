# Slope-select and algebraic coefficient pilot

## Authority and scope

The user approved the proposed sixteen-configuration pilot. Work is isolated here. Production remains 980 cycles /1465 words; its automatically discovered plan is an experimental control, not a new production search input. Previous research budgets remain closed. No solver, installation, cloud work, production changes, commit, push, materialization sweep, or cache reselection is allowed.

## Hypotheses

H1: Selecting a slope before the late Boolean bit changes a binding flow dependency without the full tensor form's extra online VALU instruction.
H2: Canonical modular linear forms expose coefficient reuse that identical-operand subtraction matching misses, especially the mixed difference across swapped axes.

Primary outcome is actual complete frozen-machine cycles. Scratch must not exceed1536 words. Secondary diagnostics are charged engine work, final gathers, targeted lookup operand/operation timing, and coefficient recipes. Fewer instructions, earlier local nodes, or a necessary bound alone are not wins.

## Fixed matrix and budget

Sites are (30,14,0) and (31,14,0), the prior A18/A16 tiles. Cross tensor/slope shape, natural/reversed bit order, and structural/algebraic coefficient reuse:2*2*2*2=16 candidates. Structural tensor is the previous shared implementation unchanged. No adaptive candidates or retries.

Four control reservations: symbolic algebra and failure sensitivity; original native981; isolated native981; published980 logical replay with fresh allocation. At most two conditional reconstruction reservations, for the best feasible candidate with cycles<=980. No other full-kernel constructions are permitted. Symbolic micro-IR fixtures do not schedule, lower, execute, or search full kernels and have a fixed coverage matrix defined below.

Reserve before full construction. Hash-guard production and isolated sources; lock an append-only reservation ledger; reject duplicates, exhausted arms, and restarts. On an unexpected failure, preserve the partial ledger and stop. Unused slots expire when the run closes.

## Algebra and implementation boundary

All coefficients are derived from runtime-loaded encoded node words, not inspected input data. Bits must already be normalized0/1. Tensor computes a+s(b-a)+t[(c-a)+s(d-c-b+a)]. Slope computes base=a+s(b-a), slope=select(s,d-b,c-a), result=base+t*slope. Every difference and broadcast is charged.

Structural sharing matches existing scalar subtraction operands and broadcast operands. Algebraic sharing uses coefficient maps modulo2^32 over encoded-node references. It scans only scalar +/- definitions and broadcasts, never distributes XOR, divides, assumes input sparsity, or changes data-dependent behavior. For each target it considers existing forms, one-step +/- combinations of known forms, and a fixed finite catalogue of factorizations. Choose by additional scalar DAG nodes, then recipe order. No whole-IR CSE, rematerialization, or lane-zero scalar policy is added.

## Gates and controls

1. Run the actual coefficient/codelet emitter through an independent symbolic interpreter. Cover two node-ID layouts, two native-pair availability conditions, both shapes, both orders, both sharing policies, and all four Boolean corners:128 checks. Polynomial coefficient equality after wrapping proves equality for arbitrary node words for these fixtures. Add a wrong-slope mutation and demand a corner mismatch. Test swapped-axis mixed-difference reuse and algebraic substitution from existing native pair differences.
2. Original and isolated native generation must exactly agree at981/1465. Replay the published control timing only on the unchanged freshly generated graph; require980/1465 and the published digest. Execute control programs against the unchanged frozen reference.
3. Inject1537/1545 allocations and ensure lowering is never called. Exhausted-budget reservation must fail without appending or constructing. Corrupt the executed encoding constant and require an output mismatch. Solver entry points are patched to fail if called.
4. Each feasible candidate receives three fixed full-width seeds and five asymmetric patterns. Reconstruct native dependencies, validate capacities and lane ownership, and allocate freshly before lowering. Overflow rejects before lower/execute. Preserve every result, including regressions.
5. Best candidate<=980, if any:100 full-width seeds, five patterns, two new deterministic reconstructions, independent graph/lane checks and the same digest. This is extended experimental validation, not production discovery/promotion or the complete incumbent gate suite. Otherwise do not run this gate.

## Decision and stopping

Report paired shape/reuse effects, whether target flow timing really moved, and complete cycles. Do not treat a favorable local dependency or980 tie as a new fully verified production incumbent. Close all budgets after the fixed matrix and conditional gate. Scalar/vector materialization remains a separately proposed follow-up.

Artifacts: source manifests, selection.json, attempts.jsonl, results.jsonl, pure_checks.json, artifacts per feasible candidate, screen_result.json, independent audit and decision/receipt. Preserve original sources and prior workspaces.
