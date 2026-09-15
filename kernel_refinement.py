"""Discover local rewrites, then justify a graph-derived final-hash neighborhood."""

from dataclasses import dataclass, replace
from itertools import combinations
import kernel_compiler as compiler
from kernel_optimizer import Cost, analyze
import kernel_retime as retime
from kernel_justify import schedule
from kernel_checks import lane_identity
from problem import SCRATCH_SIZE


@dataclass
class Result:
    cost: object
    program: list
    logical: list
    addresses: dict
    ir: object
    evaluations: int
    solver_queries: int
    solver_receipt: dict | None


def candidates(discovery, best):
    # A block is selected by measured cost, never by its previously saved ID.
    finals = [
        discovery.evaluate(replace(best.plan, final_blocks=(b,)))
        for b in range(compiler._BATCH // compiler.VLEN)
    ]
    feasible = [r for r in finals if r.feasible]
    seeds = [best]
    if feasible:
        seeds.append(min(feasible, key=lambda r: r.rank))
    proposals = set(r.plan for r in seeds)
    for seed in seeds:
        cost, (ir, logical, _) = analyze(seed.plan)
        assert cost == seed
        issue = {i: c for c, bundle in enumerate(logical) for i, _, _, _ in bundle}
        stores = {
            op.block: issue[i] for i, op in enumerate(ir.ops) if op.kind == "vstore"
        }
        successors = [[] for _ in ir.ops]
        for i, op in enumerate(ir.ops):
            for value in {v for v, _ in op.args}:
                successors[ir.producer[value]].append(i)
        critical, distance = [0] * len(ir.ops), [4] * len(ir.ops)
        for i in reversed(range(len(ir.ops))):
            critical[i] = (4 if ir.ops[i].kind == "gather" else 1) + max(
                (critical[j] for j in successors[i]), default=0
            )
            distance[i] = (
                0
                if compiler._engine_cost(ir.ops[i], ir.widths)[0] == "load"
                else min((distance[j] + 1 for j in successors[i]), default=4)
            )
        leaves = [
            i
            for i, op in enumerate(ir.ops)
            if op.site is not None and op.kind == "select"
        ]
        late = sorted(
            leaves,
            key=lambda i: (
                -issue[i],
                -stores[ir.ops[i].site[0]],
                -critical[i],
                ir.ops[i].site,
            ),
        )[:8]
        tail = max(issue[i] for i, op in enumerate(ir.ops) if op.kind == "select")
        boundary = tail
        while boundary and any(e == "flow" for _, e, _, _ in logical[boundary - 1]):
            boundary -= 1
        remaining = [i for i in leaves if i not in late]
        early = sorted(
            remaining,
            key=lambda i: (abs(issue[i] - boundary), distance[i], ir.ops[i].site),
        )[:4]
        sites = [ir.ops[i].site for i in late + early]
        for size in (1, 2):
            for subset in combinations(sites, size):
                proposals.add(replace(seed.plan, selector_sites=tuple(sorted(subset))))
        discovery.report("rewrite-seed", seed)
    return [discovery.evaluate(plan) for plan in sorted(proposals)]


def finish(discovery, best, target=979):
    rows = candidates(discovery, best)
    # This necessary-window test selects a seed; it is not a feasibility bound
    # on unrestricted backward/forward scheduling. No solver is invoked.
    feasible = [r for r in rows if r.feasible]
    if not feasible:
        raise RuntimeError("No feasible refinement frontier")
    anchor_target = min(r.cycles for r in feasible) - 1
    eligible = []
    for cost in sorted(rows, key=lambda r: r.rank):
        if not cost.feasible:
            continue
        repeated, (ir, logical, addresses) = analyze(cost.plan)
        assert repeated == cost
        if cost.cycles <= target:
            lane_identity(ir, logical, addresses)
            program = compiler._lower(ir, logical, addresses)
            return Result(
                cost,
                program,
                logical,
                addresses,
                ir,
                discovery.evaluations,
                0,
                None,
            )
        if cost.cycles - anchor_target > 8:
            continue
        model = retime.capture(ir, logical)
        for width in (32, 64):
            start = max(0, anchor_target + 1 - width)
            preflight = retime.preflight(model, start, anchor_target)
            if preflight["admitted"]:
                eligible.append(
                    ((-start, cost.rank, preflight["membership_terms"]), cost, start)
                )
    eligible.sort(key=lambda entry: entry[0])
    if not eligible:
        raise RuntimeError("No admitted refinement seed within compiler budget")
    seed = eligible[0][1]
    discovery.report("justification-seed", seed)
    result = justify_finals(discovery, seed.plan)
    if result.cost.cycles > target:
        raise RuntimeError(
            ("No allocation-feasible refinement within compiler budget", target)
        )
    return result


def justify_finals(discovery, plan):
    """Eight schedules at most: two orders and two graph-derived terminal blocks."""
    evaluated = {}

    def evaluate(proposal, tie):
        key = (proposal, tie)
        if key not in evaluated:
            discovery.reserve_schedule(proposal, tie)
            _, (ir, logical, _) = analyze(proposal)
            model = retime.capture(ir, logical)
            times = schedule(model, tie=tie)
            program, words, logical, addresses = retime.lower(ir, model, times)
            cost = Cost(max(times) + 1, words, proposal)
            discovery.report("justify-" + tie, cost)
            evaluated[key] = (
                Result(cost, program, logical, addresses, ir, 0, 0, None)
                if program is not None
                else None
            )
        return evaluated[key]

    seeds = [evaluate(plan, tie) for tie in ("native", "tail")]
    legal = [r for r in seeds if r is not None]
    if not legal:
        raise RuntimeError("No allocation-feasible justification seed")
    base = min(legal, key=lambda r: r.cost.rank)
    stores = {
        base.ir.ops[i].block: t
        for t, entries in enumerate(base.logical)
        for i, engine, _, _ in entries
        if engine == "store"
    }
    blocks = sorted(stores, key=lambda b: (-stores[b], b))[:2]
    for size in (1, 2):
        for subset in combinations(blocks, size):
            proposal = replace(
                plan, final_blocks=tuple(sorted(set(plan.final_blocks) | set(subset)))
            )
            for tie in ("native", "tail"):
                result = evaluate(proposal, tie)
                if result is not None:
                    legal.append(result)
    best = min(legal, key=lambda r: r.cost.rank)
    assert best.cost.scratch <= SCRATCH_SIZE
    best.evaluations = discovery.evaluations
    discovery.report("executable-justification", best.cost)
    return best
