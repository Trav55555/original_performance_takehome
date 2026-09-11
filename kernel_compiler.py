"""SSA compiler for the public (height=10, batch=256, rounds=16) benchmark.

All input/tree data is loaded by emitted instructions. Host-side selection uses
only scheduled cycles and scratch allocation, never a simulator or input values.
Other shapes and explicit tuning overrides retain the legacy generator.
"""

from dataclasses import dataclass
from functools import lru_cache
import heapq

from problem import HASH_STAGES, SCRATCH_SIZE, SLOT_LIMITS, VLEN

_C = 0xB55A4F09
_HEIGHT, _BATCH, _ROUNDS = 10, 256, 16
_TARGET_CYCLES = 1076
Ref = tuple[int, int]  # Logical value and lane offset.
Site = tuple[int, int]  # Walker block and round, not runtime data.
Bundle = dict[str, list[tuple]]


@dataclass
class _Op:
    kind: str
    code: str | int
    dst: int | None
    args: tuple[Ref, ...]
    imm: int | None
    preferred: str = "valu"


class _IR:
    def __init__(self):
        self.ops: list[_Op] = []
        self.widths: list[int] = []
        self.producer: list[int] = []
        self.constants: dict[int, Ref] = {}
        self.vconstants: dict[int, Ref] = {}

    def emit(self, kind, code="", args=(), width=VLEN, imm=None, preferred="valu"):
        dst = None
        if width:
            dst = len(self.widths)
            self.widths.append(width)
            self.producer.append(len(self.ops))
        self.ops.append(_Op(kind, code, dst, tuple(args), imm, preferred))
        return (dst, 0) if dst is not None else None

    def const(self, value: int) -> Ref:
        value &= 0xFFFFFFFF
        if value not in self.constants:
            self.constants[value] = self.emit("const", width=1, imm=value)
        return self.constants[value]

    def vc(self, value: int) -> Ref:
        if value not in self.vconstants:
            self.vconstants[value] = self.emit("broadcast", args=(self.const(value),))
        return self.vconstants[value]

    def binary(self, code, a, b, preferred="valu", width=VLEN) -> Ref:
        return self.emit("binary", code, (a, b), width, preferred=preferred)


def _build_ir(sites: tuple[Site, ...]) -> _IR:
    """Encoded values and mirrored indices; no physical scratch names yet.

    v = actual_value XOR C; q = 3*2**depth - 2 - index.
    q_next = 2*q + (v & 1); gather address = 3*2**depth + 5 - q.
    Cached nodes carry XOR C. Raw gathers require decoding v before mixing.
    """
    ir = _IR()
    blocks = _BATCH // VLEN
    selected = set(sites)
    assert all(
        0 <= b < blocks and 0 <= r < _ROUNDS and r % (_HEIGHT + 1) == 4
        for b, r in selected
    )
    preload_depth = 4 if selected else 3
    count = (1 << (preload_depth + 1)) - 1
    raw_nodes = []
    for i in range(0, count, VLEN):
        raw_nodes.append(ir.emit("vload", args=(ir.const(7 + i),)))
    cache = []
    for i in range(count):
        ref = (raw_nodes[i // VLEN][0], i % VLEN)
        encoded = ir.binary("^", ref, ir.const(_C), preferred="alu", width=1)
        cache.append(ir.emit("broadcast", args=(encoded,)))
    raw_root = ir.emit("broadcast", args=((raw_nodes[0][0], 0),))
    values, indices, bits, pointers = [], [], [], []
    nodes = (1 << (_HEIGHT + 1)) - 1
    for b in range(blocks):
        ptr = ir.const(7 + nodes + _BATCH + b * VLEN)
        pointers.append(ptr)
        values.append(ir.emit("vload", args=(ptr,)))
        indices.append(ir.vc(1))
        bits.append(None)
    for begin in range(0, _ROUNDS, 12):
        for b in range(blocks):
            for r in range(begin, min(begin + 12, _ROUNDS)):
                depth = r % (_HEIGHT + 1)
                q, v = indices[b], values[b]
                if r == 0:
                    node = raw_root
                elif depth <= 3 or (b, r) in selected:
                    entries = list(
                        reversed(cache[(1 << depth) - 1 : (1 << (depth + 1)) - 1])
                    )
                    for bit_index in range(depth):
                        bit = (
                            bits[b]
                            if bit_index == 0
                            else ir.binary("&", q, ir.vc(1 << bit_index))
                        )
                        assert bit is not None
                        entries = [
                            ir.emit("select", args=(bit, entries[j + 1], entries[j]))
                            for j in range(0, len(entries), 2)
                        ]
                    node = entries[0]
                else:
                    addr = ir.binary(
                        "-", ir.vc(3 * (1 << depth) + 5), q, preferred="alu"
                    )
                    node = ir.emit("gather", args=(addr,))
                    v = ir.binary("^", v, ir.vc(_C), preferred="alu")
                v = ir.binary("^", v, node, preferred="alu")
                for h, (op1, c1, op2, op3, c3) in enumerate(HASH_STAGES):
                    if h == 5:
                        shift = ir.binary(op3, v, ir.vc(c3))
                        v = ir.binary(op2, v, shift)
                    elif op1 == "+" and op2 == "+" and op3 == "<<":
                        v = ir.emit("muladd", args=(v, ir.vc(1 + (1 << c3)), ir.vc(c1)))
                    else:
                        a = ir.binary(op1, v, ir.vc(c1))
                        shift = ir.binary(op3, v, ir.vc(c3))
                        v = ir.binary(op2, a, shift)
                values[b] = v
                if r + 1 < _ROUNDS:
                    if depth == _HEIGHT:
                        indices[b], bits[b] = ir.vc(1), None
                    else:
                        bit = ir.binary("&", v, ir.vc(1), preferred="alu")
                        indices[b] = ir.emit("muladd", args=(q, ir.vc(2), bit))
                        bits[b] = bit
    for b in range(blocks):
        v = ir.binary("^", values[b], ir.vc(_C), preferred="alu")
        ir.emit("vstore", args=(pointers[b], v), width=0)

    # Alternative constant construction exchanges load slots for flow slots.
    # Keep a conservative anchor dependency for BOTH forms, so greedy engine
    # choice cannot introduce a new dependency after readiness was calculated.
    anchor = ir.constants[7]
    for op in ir.ops:
        if op.kind == "const" and op.dst != anchor[0]:
            op.code = op.imm  # Absolute immediate used by the load alternative.
            op.imm -= 7
            op.args = (anchor,)
            op.kind = "const_choice"
            op.preferred = "load"
    needed = {i for i, op in enumerate(ir.ops) if op.kind == "vstore"}
    todo = list(needed)
    while todo:
        for value, _ in ir.ops[todo.pop()].args:
            parent = ir.producer[value]
            if parent not in needed:
                needed.add(parent)
                todo.append(parent)
    ir.ops = [op for i, op in enumerate(ir.ops) if i in needed]
    for i, op in enumerate(ir.ops):
        if op.dst is not None:
            ir.producer[op.dst] = i
    return ir


def _engine_cost(op, widths, selected=None):
    if op.kind == "const_choice":
        return selected or "load", 1
    if op.kind == "binary":
        engine = selected or op.preferred
        return engine, widths[op.dst] if engine == "alu" else 1
    return {
        "const": ("load", 1),
        "vload": ("load", 1),
        "gather": ("load", VLEN),
        "broadcast": ("valu", 1),
        "muladd": ("valu", 1),
        "select": ("flow", 1),
        "vstore": ("store", 1),
    }[op.kind]


def _schedule(ir: _IR):
    """Lane-ready issue with greedy engine choices and lifetime-pressure hints.

    Reads see the cycle's old scratch. Results become ready next cycle. An ALU
    expansion can issue some lanes while others await operands or issue slots.
    """
    ops = ir.ops
    successors = [[] for _ in ops]
    remaining = [0] * len(ir.widths)
    for i, op in enumerate(ops):
        for value in {v for v, _ in op.args}:
            successors[ir.producer[value]].append(i)
            remaining[value] += 1
    critical, distance, position = [0] * len(ops), [4] * len(ops), []
    count = 0
    for op in ops:
        position.append(count)
        count += _engine_cost(op, ir.widths)[1]
    for i in range(len(ops) - 1, -1, -1):
        critical[i] = (4 if ops[i].kind == "gather" else 1) + max(
            (critical[j] for j in successors[i]), default=0
        )
        distance[i] = (
            0
            if _engine_cost(ops[i], ir.widths)[0] == "load"
            else min((distance[j] + 1 for j in successors[i]), default=4)
        )
    priority = [
        position[i] - 50 * critical[i] - 600 * max(0, 4 - distance[i])
        for i in range(len(ops))
    ]
    available = [0] * len(ir.widths)
    masks = [(1 << width) - 1 for width in ir.widths]
    progress = [0] * len(ops)
    modes, complete = {}, set()

    def ready_mask(i):
        op = ops[i]
        if op.kind in ("binary", "gather"):
            mask = masks[op.dst]
            for value, offset in op.args:
                mask &= available[value] >> offset
            return mask & ~progress[i]
        sizes = (
            [1, VLEN]
            if op.kind == "vstore"
            else [1]
            if op.kind in ("vload", "broadcast", "const_choice")
            else [VLEN] * len(op.args)
        )
        for (value, offset), width in zip(op.args, sizes):
            need = (1 << width) - 1
            if ((available[value] >> offset) & need) != need:
                return 0
        return 1

    ready = {i for i, op in enumerate(ops) if not op.args}
    starts, ends, program = {}, {}, []
    while len(complete) < len(ops):
        cycle = len(program)
        capacity, bundle, done, updates = dict(SLOT_LIMITS), [], [], []

        def key(i):
            op = ops[i]
            freed = sum(
                ir.widths[v] for v in {v for v, _ in op.args} if remaining[v] == 1
            )
            gained = 0 if op.dst is None or i in modes else ir.widths[op.dst]
            return priority[i] + 100 * (gained - freed), i

        for i in sorted(ready, key=key):
            op, mask = ops[i], ready_mask(i)
            if not mask:
                continue
            if i in modes:
                engine, _ = _engine_cost(op, ir.widths, modes[i])
            else:
                engine, _ = _engine_cost(op, ir.widths)
                if (
                    op.kind == "const_choice"
                    and not capacity["load"]
                    and capacity["flow"]
                ):
                    engine = "flow"
                if op.kind == "binary" and ir.widths[op.dst] == VLEN:
                    if (
                        engine == "valu"
                        and (not capacity["valu"] or mask != masks[op.dst])
                        and min(capacity["alu"], mask.bit_count()) >= 1
                    ):
                        engine = "alu"
                    elif (
                        engine == "alu"
                        and not capacity["alu"]
                        and capacity["valu"]
                        and mask == masks[op.dst]
                    ):
                        engine = "valu"
            if not capacity[engine]:
                continue
            partial = op.kind == "gather" or (op.kind == "binary" and engine == "alu")
            if not partial and op.kind == "binary" and mask != masks[op.dst]:
                continue
            if i not in modes:
                modes[i] = engine
                if op.dst is not None:
                    starts[op.dst], ends[op.dst] = cycle, cycle + 0.5
            if partial:
                lanes = [
                    lane for lane in range(ir.widths[op.dst]) if mask & (1 << lane)
                ][: capacity[engine]]
                issued = sum(1 << lane for lane in lanes)
                bundle.extend((i, engine, lane, 1) for lane in lanes)
                capacity[engine] -= len(lanes)
                progress[i] |= issued
                updates.append((op.dst, issued))
                finished = progress[i] == masks[op.dst]
            else:
                bundle.append((i, engine, 0, 1))
                capacity[engine] -= 1
                if op.dst is not None:
                    updates.append((op.dst, masks[op.dst]))
                finished = True
            if op.dst is not None:
                ends[op.dst] = max(ends[op.dst], cycle + 0.5)
            for value in {v for v, _ in op.args}:
                ends[value] = max(ends[value], cycle)
            if finished:
                done.append(i)
                for value in {v for v, _ in op.args}:
                    remaining[value] -= 1
        if not bundle:
            raise AssertionError(
                ("lane scheduler stalled", cycle, len(complete), len(ready))
            )
        program.append(bundle)
        for value, mask in updates:
            available[value] |= mask
        for i in done:
            complete.add(i)
            ready.remove(i)
        for j in {j for i, _, _, _ in bundle for j in successors[i]}:
            if j not in complete and ready_mask(j):
                ready.add(j)
    assert not any(remaining)
    return program, starts, ends


def _allocate(ir, starts, ends):
    """Color scalar/vector lifetime intervals separately, including partial writes.

    A value lives through its last consuming lane. A last read at cycle t may
    share storage with a write at t, which commits at t + 0.5 in this model.
    """
    addresses, pools = {}, {}
    for width in (1, VLEN):
        active, free, colors = [], [], 0
        values = (v for v in starts if ir.widths[v] == width)
        for value in sorted(values, key=lambda v: (starts[v], v)):
            while active and active[0][0] <= starts[value]:
                _, color = heapq.heappop(active)
                heapq.heappush(free, color)
            if free:
                color = heapq.heappop(free)
            else:
                color = colors
                colors += 1
            addresses[value] = color * width
            heapq.heappush(active, (ends[value], color))
        pools[width] = colors
    for value in addresses:
        if ir.widths[value] == VLEN:
            addresses[value] += pools[1]
    return addresses, pools[1] + pools[VLEN] * VLEN


def _lower(ir, logical, addresses) -> list[Bundle]:
    def address(ref):
        value, offset = ref
        return addresses[value] + offset

    result = []
    for entries in logical:
        bundle = {}
        for i, engine, first, count in entries:
            op = ir.ops[i]
            dest = addresses[op.dst] if op.dst is not None else None
            args = list(map(address, op.args))
            slots = bundle.setdefault(engine, [])
            if op.kind == "binary":
                if engine == "valu":
                    slots.append((op.code, dest, *args))
                else:
                    slots.extend(
                        (op.code, dest + lane, args[0] + lane, args[1] + lane)
                        for lane in range(first, first + count)
                    )
            elif op.kind == "gather":
                slots.extend(
                    ("load", dest + lane, args[0] + lane)
                    for lane in range(first, first + count)
                )
            elif op.kind == "const":
                slots.append(("const", dest, op.imm))
            elif op.kind == "const_choice":
                slots.append(
                    ("add_imm", dest, *args, op.imm)
                    if engine == "flow"
                    else ("const", dest, op.code)
                )
            elif op.kind == "vload":
                slots.append(("vload", dest, *args))
            elif op.kind == "broadcast":
                slots.append(("vbroadcast", dest, *args))
            elif op.kind == "muladd":
                slots.append(("multiply_add", dest, *args))
            elif op.kind == "select":
                slots.append(("vselect", dest, *args))
            elif op.kind == "vstore":
                slots.append(("vstore", *args))
            else:
                raise AssertionError(op)
        result.append(bundle)
    if result[-1].get("flow"):
        result.append({})
    result[-1].setdefault("flow", []).append(("pause",))
    return result


@dataclass(frozen=True)
class CompiledKernel:
    """Immutable cached compilation; callers receive fresh mutable bundles."""

    bundles: tuple
    scratch_size: int
    cache_sites: tuple[Site, ...]
    evaluations: int = 0

    @property
    def cycles(self):
        return len(self.bundles)

    def materialize(self) -> list[Bundle]:
        return [
            {engine: list(slots) for engine, slots in bundle} for bundle in self.bundles
        ]


def _analyze_sites(sites: tuple[Site, ...]):
    ir = _build_ir(sites)
    logical, starts, ends = _schedule(ir)
    addresses, scratch = _allocate(ir, starts, ends)
    return ir, logical, addresses, scratch


def _compile_sites(sites: tuple[Site, ...]) -> CompiledKernel:
    ir, logical, addresses, scratch = _analyze_sites(sites)
    program = _lower(ir, logical, addresses)
    return CompiledKernel(
        tuple(tuple((e, tuple(slots)) for e, slots in b.items()) for b in program),
        scratch,
        sites,
    )


@dataclass(frozen=True)
class _Cost:
    cycles: int
    scratch_size: int
    cache_sites: tuple[Site, ...]


def _rank(candidate):
    return (
        candidate.cycles if candidate.scratch_size <= SCRATCH_SIZE else float("inf"),
        candidate.scratch_size,
        candidate.cache_sites,
    )


@lru_cache(maxsize=1)
def compile_benchmark() -> CompiledKernel:
    """Deterministic public-shape search; no saved configurations or programs.

    Start with no depth-4 caches and admit profitable sites. Stop an admission
    scan early after saving one gather's load-issue budget. This is a search
    heuristic, NOT an upper bound on possible savings. If needed, compare a
    block's first/repeated visits. At most 921 distinct plans are evaluated;
    cache only small scores during search and the immutable final program.
    """
    sites = tuple(
        (b, r)
        for b in range(_BATCH // VLEN)
        for r in range(_ROUNDS)
        if r % (_HEIGHT + 1) == 4
    )
    seen = {}

    def evaluate(selected):
        selected = tuple(sorted(selected))
        if selected not in seen:
            _, logical, _, scratch = _analyze_sites(selected)
            cycles = len(logical) + any(e == "flow" for _, e, _, _ in logical[-1])
            seen[selected] = _Cost(cycles, scratch, selected)
        return seen[selected]

    best = evaluate(())
    gather_budget = (VLEN + SLOT_LIMITS["load"] - 1) // SLOT_LIMITS["load"]
    for _ in range(16):
        candidate = best
        for site in sites:
            if site in best.cache_sites:
                continue
            row = evaluate(best.cache_sites + (site,))
            candidate = min(candidate, row, key=_rank)
            if (
                row.scratch_size <= SCRATCH_SIZE
                and row.cycles <= best.cycles - gather_budget
            ):
                break
        if _rank(candidate) >= _rank(best):
            break
        best = candidate
        if best.cycles <= _TARGET_CYCLES:
            break
    if best.cycles > _TARGET_CYCLES:
        current = best.cache_sites
        rows = []
        for old in current:
            for site in sites:
                if site[0] == old[0] and site not in current:
                    rows.append(
                        evaluate(tuple(s for s in current if s != old) + (site,))
                    )
        best = min([best, *rows], key=_rank)
    assert best.scratch_size <= SCRATCH_SIZE, "No scratch-feasible compilation"
    program = _compile_sites(best.cache_sites)
    assert (program.cycles, program.scratch_size) == (best.cycles, best.scratch_size)
    return CompiledKernel(
        program.bundles, program.scratch_size, program.cache_sites, len(seen)
    )
