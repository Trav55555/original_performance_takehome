# Resource-order pilot

## Objective and authority

User approved continuing with the complementary reversed-slope pair, backward/forward reordering, and resource-aware deadlines. Optimize actual complete frozen execution. Production stays untouched at980 cycles /1465 scratch words. The archived published plan is an experimental control only. All previous budgets remain closed. No solver, package installation, cloud work, materialization sweep, cache search, commit or push.

## Finite matrix

Four control reservations cover the previous symbolic/guard controls, original native981, isolated native981, and published980 timing replay. Add the declared scheduling microchecks to the symbolic control; do not generate another full-kernel control.

Eighteen candidate reservations:

- Pair: two candidates, blocks30+31 / round14 / tile0 / reversed slope-select, structural versus algebraic coefficient sharing.
- Backward/forward: eight candidates. Use native and the best feasible pair as bases. Cross two tie orders, native and dependence-tail, with one or two right/left passes. If neither pair is feasible, close the pair-based slots unused.
- Deadlines: eight candidates. Same two bases. Compare pure dependence-tail priority against resource-tail deadline blended with native issue times at weights1/8,1/2,1. This is a derived necessary-resource-tail heuristic, not a full reimplementation of the clustered-VLIW paper.

At most two conditional reconstructions for the best feasible candidate with cycles<=980. All candidate specifications are declared before construction. Rank bases by cycles, scratch, then stable name. There is no adaptive expansion, retry, transfer of unused slots, or additional combination search.

## Algorithms and hypotheses

H1: The two slope edits improve different last stores individually. The pair might retain both improvements. Preserve all per-block store times; do not assume additive effects.

H2: Right-justify each native job against current successor times and available capacity without extending the current horizon. Then serially place jobs as early as possible in the order derived from that right-justified schedule. Jobs may move later than their original positions and cross original-cycle order. Test actual order changes, not merely earlier timestamps under old capacity chains. One/two passes are separate fixed cases.

H3: For each native job compute both a dependence tail and a descendant-work tail. Count each proper descendant once. With fixed native engines, every proper descendant is at least one cycle later. Therefore1+ceil(descendant engine work / engine capacity) is a necessary inclusive tail length. Proper flow descendants need one further cycle for the charged pause. A flow job itself needs at least two cycles including pause. The resource tail is the maximum of these bounds and the dependence tail, with successor bounds propagated backward through dependency lags. Deadline=T-tail; prioritize by the declared native-time/deadline blend. These estimates rank ready jobs and are not hard feasibility cuts.

Both scheduling arms retain the freshly generated native engine assignment and individual scalar lanes. They change order, not instruction selection. Shared issue capacity is global across walkers. No decomposition by walker and no saved candidate timing input. All candidate graphs come from fresh native IR construction. Published saved timing is replayed only as a control.

## Safety, oracles and stopping

Reserve before construction; enforce immutable source hashes, unique append-only reservations and a closed-manifest restart rejection. An unexpected failure stops the run and preserves the ledger. Solver entry points are disabled. Process address-space limit is2GiB; a resource failure is unknown, never UNSAT.

Before screening, rerun128 symbolic slope/tensor corner checks and mutation/sharing controls. Validate deadline bounds against all feasible time assignments in24 deterministic four-job toy DAGs. Include a fan-out case where resource tail exceeds path length, and a deliberately overstated bound. Execute a fully charged6-to-5-cycle toy demonstrating an operation moves later while total execution improves. Check missing dependency and over-capacity timing mutations.

Original/isolated native must agree at981/1465; published replay must match980/1465 and its digest. Test1537/1545 scratch rejection before lowering, zero budget before construction, and actual output corruption sensitivity.

For every full candidate: validate native graph identity/dependencies/capacities, allocate afresh, reject scratch>1536 before lowering, check physical lane ownership, and execute three fixed full-width seeds plus five asymmetric patterns. All setup, broadcasts, stores and pause count. Preserve non-output memory. A necessary bound, a timing witness or a scratch-only gain is not a cycle win.

For the best candidate<=980 only:100 seeds, five patterns, and two deterministic fresh reconstructions with execution checks. This extended experimental gate is not the complete incumbent promotion suite or source-only production discovery. Do not label it a promoted incumbent without the remaining gates.

Close all budgets after the matrix and conditional gate. Write results, source/decision receipts, terminal-store vectors, scheduling diagnostics and a read-only artifact audit. Preserve production, earlier workspaces and unrelated untracked files.
