"""Deterministic compile-time configuration discovery; no persisted search inputs.

Only instruction scheduling and allocation determine scores. Neither the runtime
machine nor tree/input values are available to this module.
"""

from dataclasses import dataclass, replace
import kernel_compiler as compiler
from problem import SCRATCH_SIZE, VLEN

MAX_EVALUATIONS = 4096


@dataclass(frozen=True, order=True)
class Plan:
    sites: tuple
    pairs: tuple = (2, 2)
    final_blocks: tuple = ()
    selector_sites: tuple = ()


@dataclass(frozen=True)
class Cost:
    cycles: int
    scratch: int
    plan: Plan

    @property
    def feasible(self):
        return self.scratch <= SCRATCH_SIZE

    @property
    def rank(self):
        return (not self.feasible, self.cycles, self.scratch, self.plan)


def analyze(plan):
    ir = compiler._build_ir(
        plan.sites,
        advanced=True,
        pairs=plan.pairs,
        final_blocks=plan.final_blocks,
        selector_sites=plan.selector_sites,
    )
    logical, starts, ends = compiler._schedule(ir, lookahead=True, startup=True)
    addresses, scratch = compiler._allocate(ir, starts, ends)
    cycles = len(logical) + bool(any(e == "flow" for _, e, _, _ in logical[-1]))
    return Cost(cycles, scratch, plan), (ir, logical, addresses)


class Discovery:
    def __init__(self, observer=None):
        self.scores = {}
        self.observer = observer
        self.seed_evaluations = 0
        self.schedule_reservations = set()

    @property
    def evaluations(self):
        return (
            self.seed_evaluations + len(self.scores) + len(self.schedule_reservations)
        )

    def reserve_schedule(self, plan, tie):
        if self.evaluations >= MAX_EVALUATIONS:
            raise RuntimeError("Compilation evaluation budget exhausted")
        key = (plan, tie)
        if key in self.schedule_reservations:
            raise RuntimeError("Duplicate schedule reservation")
        self.schedule_reservations.add(key)

    def evaluate(self, plan):
        if plan not in self.scores:
            if self.evaluations >= MAX_EVALUATIONS:
                raise RuntimeError("Compilation evaluation budget exhausted")
            self.scores[plan] = analyze(plan)[0]
        return self.scores[plan]

    def report(self, phase, cost):
        if self.observer:
            self.observer(phase, cost, self.evaluations)

    def cache_plan(self):
        seed = compiler._compile_seed()
        self.seed_evaluations = seed.evaluations
        best = self.evaluate(Plan(seed.cache_sites))
        self.report("automatic-seed", best)
        universe = tuple(
            (b, r)
            for b in range(compiler._BATCH // VLEN)
            for r in range(compiler._ROUNDS)
            if r % (compiler._HEIGHT + 1) == 4
        )
        swapped = False
        for step in range(24):
            current = set(best.plan.sites)
            singles = {
                s: self.evaluate(replace(best.plan, sites=tuple(sorted(current ^ {s}))))
                for s in universe
            }
            candidate = min([best, *singles.values()], key=lambda r: r.rank)
            if candidate.cycles < best.cycles and candidate.feasible:
                best = candidate
                self.report("cache-toggle", best)
                continue
            if swapped:
                break
            proposals = []
            for old in sorted(current):
                for added in universe:
                    if added in current:
                        continue
                    estimate = singles[old].cycles + singles[added].cycles - best.cycles
                    excess = max(
                        0,
                        singles[old].scratch
                        + singles[added].scratch
                        - best.scratch
                        - SCRATCH_SIZE,
                    )
                    sites = tuple(sorted((current - {old}) | {added}))
                    proposals.append((estimate, excess, sites))
            proposals.sort()
            selected, remaining = proposals[:96], proposals[96:]
            count = min(32, len(remaining))
            selected += [remaining[i * len(remaining) // count] for i in range(count)]
            swaps = [self.evaluate(replace(best.plan, sites=p[2])) for p in selected]
            swapped = True
            candidate = min([best, *swaps], key=lambda r: r.rank)
            if candidate.cycles >= best.cycles or not candidate.feasible:
                break
            best = candidate
            self.report("cache-swap", best)
        profiles = [
            self.evaluate(replace(best.plan, pairs=(a, b)))
            for a in range(5)
            for b in range(9)
        ]
        alternatives = sorted(
            (
                r
                for r in profiles
                if r.plan.pairs != best.plan.pairs
                and r.feasible
                and r.cycles <= best.cycles + 4
            ),
            key=lambda r: r.rank,
        )[:2]
        joint = []
        for profile in alternatives:
            current = set(profile.plan.sites)
            joint.extend(
                self.evaluate(replace(profile.plan, sites=tuple(sorted(current ^ {s}))))
                for s in universe
            )
        best = min([best, *profiles, *joint], key=lambda r: r.rank)
        self.report("selector-cache-coupling", best)
        return best
