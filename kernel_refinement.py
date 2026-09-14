"""Discover local rewrites and repair a small suffix of the chosen graph."""

from dataclasses import dataclass, replace
from itertools import combinations
import kernel_compiler as compiler
from kernel_optimizer import analyze
import kernel_retime as retime
from kernel_checks import lane_identity
from problem import SCRATCH_SIZE

MAX_SOLVER_QUERIES = 4


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


def finish(discovery, best, target=980):
    rows = candidates(discovery, best)
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
                discovery.seed_evaluations + len(discovery.scores),
                0,
                None,
            )
        if cost.cycles - target > 8:
            continue
        model = retime.capture(ir, logical)
        for width in (32, 64):
            start = max(0, target + 1 - width)
            preflight = retime.preflight(model, start, target)
            if preflight["admitted"]:
                eligible.append(
                    ((-start, cost.rank, preflight["membership_terms"]), cost, start)
                )
    eligible.sort(key=lambda entry: entry[0])
    queries = 0
    for _, cost, start in eligible:
        if queries == MAX_SOLVER_QUERIES:
            break
        repeated, (ir, logical, addresses) = analyze(cost.plan)
        assert repeated == cost
        model = retime.capture(ir, logical)
        # Fail before spending solver work if native reconstruction is not exact.
        native, words, _, _ = retime.lower(
            ir, model, [j["time"] for j in model["jobs"]]
        )
        assert (
            native == compiler._lower(ir, logical, addresses) and words == cost.scratch
        )
        queries += 1
        discovery.report("exact-query", cost)
        answer = retime.repair(model, start, target)
        if answer["status"] == "unknown":
            raise RuntimeError(
                ("Exact compiler returned unknown", answer.get("reason"))
            )
        if answer["status"] != "sat":
            continue
        program, scratch, logical, addresses = retime.lower(ir, model, answer["times"])
        if program is None:
            continue
        assert scratch <= SCRATCH_SIZE and len(program) <= target
        final = replace(cost, cycles=len(program), scratch=scratch)
        discovery.report("executable-repair", final)
        return Result(
            final,
            program,
            logical,
            addresses,
            ir,
            discovery.seed_evaluations + len(discovery.scores),
            queries,
            {k: v for k, v in answer.items() if k != "times"},
        )
    raise RuntimeError(
        ("No allocation-feasible repair within compiler budget", queries, len(eligible))
    )
