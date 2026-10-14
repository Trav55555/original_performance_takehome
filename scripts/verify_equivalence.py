#!/usr/bin/env python3
"""Prove an emitted VLIW program equals reference_kernel2 for every input.

The instruction bundles are interpreted symbolically with the simulator's
semantics (start-of-cycle reads, end-of-cycle writes, 32-bit wraparound) over
a z3 array for memory; nothing from the compiler is used.  Straight-line
programs only: jumps, halt and debug slots are rejected, and the single pause
must be the last bundle's flow slot.  The frozen simulator first runs a few
random memories as a cheap gate, then steps alongside only to PROPOSE cut
points: a scratch word that equals a reference intermediate (optionally XOR a
constant) of one batch element in every sample.  Each proposal is proved with
z3 against the spec's own stage and index formulas and the word is replaced by
a fresh symbol, so the proof composes by induction over the data flow; an
unprovable proposal is just dropped.  At the end every inp_values word is
proved equal to the reference's final value and every other memory word proved
unchanged, and every memory access was proved in bounds.  An element whose
rounds never complete makes the run fail.  The alpha-renaming lemma cache only
reuses a proof for a goal identical up to symbol names.

Trust base: z3; the opcode table below (mirrors problem.Machine); the stage and
index formulas transcribed from problem.py (HASH_STAGES is imported); the
build_mem_image layout (forest at 7, values at 7 + n_nodes + batch); and the
contract that initial indices are zero and final indices are not written.
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import z3
from problem import (
    HASH_STAGES,
    SCRATCH_SIZE,
    SLOT_LIMITS,
    VLEN,
    DebugInfo,
    Input,
    Machine,
    Tree,
    build_mem_image,
    myhash,
    reference_kernel2,
)

W = 32
MASK = (1 << W) - 1
HEADER = 7
BV = z3.BitVecSort(W)
NONE = frozenset()


def bv(k):
    return z3.BitVecVal(k & MASK, W)


def stage(k, a):
    # On a zero-extended 64-bit copy the spec's Python +, ^, <<, >>, % 2**32
    # are exactly the unsigned bit-vector operations.
    op1, c1, op2, op3, c3 = HASH_STAGES[k]
    fns = {
        "+": lambda x, y: x + y,
        "^": lambda x, y: x ^ y,
        "<<": lambda x, y: x << y,
        ">>": lambda x, y: z3.LShR(x, y),
    }
    a = z3.ZeroExt(32, a)
    r = lambda x: z3.URem(x, 1 << 32)
    return z3.Extract(31, 0, r(fns[op2](r(fns[op1](a, c1)), r(fns[op3](a, c3)))))


def fold(e):
    """Constant-fold so concrete addresses stay recognizable without simplifying big terms."""
    return z3.simplify(e) if all(z3.is_bv_value(c) for c in e.children()) else e


def next_index(idx, val, n_nodes):
    nxt = bv(2) * idx + z3.If(z3.URem(val, bv(2)) == bv(0), bv(1), bv(2))
    return z3.If(z3.UGE(nxt, bv(n_nodes)), bv(0), nxt)


def alu(op, a, b):
    """Scalar ALU result and the side conditions the simulator needs to not crash."""
    wide = lambda x: z3.ZeroExt(W, x)
    table = {
        "+": lambda: a + b,
        "-": lambda: a - b,
        "*": lambda: a * b,
        "^": lambda: a ^ b,
        "&": lambda: a & b,
        "|": lambda: a | b,
        "<<": lambda: a << b,
        ">>": lambda: z3.LShR(a, b),
        "//": lambda: z3.UDiv(a, b),
        "%": lambda: z3.URem(a, b),
        "cdiv": lambda: z3.Extract(W - 1, 0, z3.UDiv(wide(a) + wide(b) - 1, wide(b))),
        "<": lambda: z3.If(z3.ULT(a, b), bv(1), bv(0)),
        "==": lambda: z3.If(a == b, bv(1), bv(0)),
    }
    assert op in table, f"unknown alu op {op}"
    return table[op](), [b != bv(0)] if op in ("//", "%", "cdiv") else []


class Element:
    def __init__(self, i, val_p, mem):
        self.true = z3.Select(mem, bv(val_p + i))
        self.idx = bv(0)
        self.node = None
        self.round = 0
        self.stage = None
        self.cuts = 0


class Verifier:
    def __init__(self, program, shape, timeout_ms, samples, seed):
        self.program = program
        self.height, self.n_nodes, self.batch, self.rounds = shape
        self.val_p = HEADER + self.n_nodes + self.batch
        self.timeout_ms = timeout_ms
        self.mem0 = self.mem = z3.Array("mem", BV, BV)
        self.scr = [bv(0)] * SCRATCH_SIZE
        self.taint = [NONE] * SCRATCH_SIZE
        self.states = [Element(i, self.val_p, self.mem0) for i in range(self.batch)]
        self.cache = set()
        self.hits = 0
        self.fresh = 0
        self.queries = {}
        self.rejected = {}
        self.seconds = {}
        self.failures = []
        self.machines = []
        self.want = {}
        rng = random.Random(seed)
        for _ in range(samples):
            random.seed(rng.getrandbits(32))
            tree = Tree.generate(self.height)
            assert len(tree.values) == self.n_nodes, "shape is not a perfect tree"
            mem = build_mem_image(tree, Input.generate(tree, self.batch, self.rounds))
            trace = {}
            gen = reference_kernel2(list(mem), trace)
            next(gen)
            final = next(gen)
            probe = Machine(mem, program, DebugInfo({}))
            try:
                for pc, bundle in enumerate(program):
                    probe.step(bundle, probe.cores[0])
            except Exception as e:
                raise AssertionError(f"simulator rejects bundle {pc}: {e!r}") from e
            lo, hi = self.val_p, self.val_p + self.batch
            assert probe.mem[lo:hi] == final[lo:hi], (
                "simulator disagrees with the reference"
            )
            for i in range(self.batch):
                for r in range(self.rounds):
                    node = trace[r, i, "node_val"]
                    row = [node, trace[r, i, "val"] ^ node]
                    row += [trace[r, i, "hash_stage", k] for k in range(6)]
                    for k, v in enumerate(row):
                        self.want.setdefault((i, r, k), []).append(v)
            self.machines.append(Machine(mem, program, DebugInfo({})))
        self.mem_len = len(mem)

    def canon(self, goal):
        syms, seen, todo = [], set(), [goal]
        while todo:
            t = todo.pop()
            if t.get_id() in seen:
                continue
            seen.add(t.get_id())
            if (
                z3.is_const(t)
                and t.decl().kind() == z3.Z3_OP_UNINTERPRETED
                and t.sort() == BV
            ):
                syms.append(t)
            todo.extend(reversed(t.children()))
        renamed = [(s, z3.BitVec(f"x{n}", W)) for n, s in enumerate(syms)]
        return z3.substitute(goal, *renamed).sexpr() if renamed else goal.sexpr()

    def prove(self, goal, kind, fatal=True):
        """Prove `goal` for all symbol values; a cut proposal (fatal=False) may just be a coincidence."""
        key = self.canon(goal)
        if key in self.cache:
            self.hits += 1
            return True
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)
        solver.add(z3.Not(goal))
        t = time.time()
        res = solver.check()
        dt = time.time() - t
        self.queries[kind] = self.queries.get(kind, 0) + 1
        self.seconds[kind] = self.seconds.get(kind, 0.0) + dt
        if dt > 1:
            print(f"  {kind}: {res} in {dt:.1f}s", file=sys.stderr, flush=True)
        if res == z3.unsat:
            self.cache.add(key)
            return True
        if fatal:
            self.failures.append((kind, str(res)))
        else:
            self.rejected[kind] = self.rejected.get(kind, 0) + 1
        return False

    def propose(self, expr, i, conc):
        """Cut `expr` (a word of element i) at the next reference intermediate it equals."""
        st = self.states[i]
        if st.round >= self.rounds:
            return expr
        node_ref = st.node
        if node_ref is None:
            node_ref = z3.Select(self.mem0, bv(HEADER) + st.idx)
        first = 0 if st.stage is None else st.stage + 1
        kinds = list(range(2 + first, 8))
        if st.stage is None:
            kinds = ([0] if st.node is None else []) + [1] + kinds
        for kind in kinds:
            diff = {c ^ w for c, w in zip(conc, self.want[i, st.round, kind])}
            if len(diff) != 1:
                continue
            mask = diff.pop()
            if kind == 0:
                expected = node_ref
            else:
                expected = st.true if st.stage is not None else st.true ^ node_ref
                for k in range(first, kind - 1):
                    expected = stage(k, expected)
            name = ("node", "xin", *(f"stage{first}..{k}" for k in range(6)))[kind]
            name += " masked" if mask else ""
            if not self.prove(expr == expected ^ bv(mask), name, fatal=False):
                continue
            fresh = z3.BitVec(f"k{self.fresh}", W)
            self.fresh += 1
            value = fresh ^ bv(mask) if mask else fresh
            st.cuts += 1
            if kind == 0:
                st.node = value
            else:
                st.true, st.stage = value, kind - 2
                if kind == 7:
                    st.idx = next_index(st.idx, st.true, self.n_nodes)
                    st.round, st.stage, st.node = st.round + 1, None, None
            return fresh
        return expr

    def rd(self, a, n=1):
        assert type(a) is int and 0 <= a and a + n <= SCRATCH_SIZE, f"scratch {a}"
        return self.scr[a], self.taint[a]

    def address(self, addr, n):
        """Memory address of an n-word access, proved to fit below mem_len."""
        if z3.is_bv_value(addr):
            assert addr.as_long() + n <= self.mem_len, f"memory address {addr}"
        else:
            assert self.prove(z3.ULE(addr, bv(self.mem_len - n)), "bounds"), "bounds"
        return addr

    def load(self, addr, taint, n=1):
        """Memory words addr..addr+n-1 read at the start of the cycle."""
        addr = self.address(addr, n)
        words = []
        for v in range(n):
            word = fold(addr + bv(v))
            k = word.as_long() - self.val_p if z3.is_bv_value(word) else -1
            own = frozenset([k]) if 0 <= k < self.batch else taint
            words.append((z3.Select(self.mem, word), own))
        return words

    def slot(self, engine, slot, writes, stores):
        op, args = slot[0], slot[1:]
        assert all(type(x) is int for x in args), f"bad operands {slot}"
        put = lambda d, n, vals: writes.update(zip(range(d, d + n), vals))
        if engine == "alu" or (engine == "valu" and len(slot) == 4):
            n = 1 if engine == "alu" else VLEN
            dest, a1, a2 = args
            self.rd(dest, n)
            for v in range(n):
                (x, tx), (y, ty) = self.rd(a1 + v), self.rd(a2 + v)
                res, conds = alu(op, x, y)
                for c in conds:
                    assert self.prove(c, "division"), "division by zero"
                writes[dest + v] = (fold(res), tx | ty)
        elif engine == "valu" and op == "vbroadcast":
            dest, src = args
            self.rd(dest, VLEN)
            put(dest, VLEN, [self.rd(src)] * VLEN)
        elif engine == "valu" and op == "multiply_add":
            dest, a, b, c = args
            self.rd(dest, VLEN)
            for v in range(VLEN):
                (x, tx), (y, ty), (z, tz) = map(self.rd, (a + v, b + v, c + v))
                writes[dest + v] = (fold(x * y + z), tx | ty | tz)
        elif engine == "load" and op == "const":
            dest, val = args
            self.rd(dest)
            writes[dest] = (bv(val), NONE)
        elif engine == "load" and op in ("load", "vload", "load_offset"):
            assert len(args) == (3 if op == "load_offset" else 2), slot
            dest, addr, *offset = args
            off = offset[0] if op == "load_offset" else 0
            n = VLEN if op == "vload" else 1
            self.rd(dest + off, n)
            put(dest + off, n, self.load(*self.rd(addr + off), n))
        elif engine == "store" and op in ("store", "vstore"):
            addr, src = args
            n = VLEN if op == "vstore" else 1
            a = self.address(self.rd(addr)[0], n)
            stores.extend((fold(a + bv(v)), self.rd(src + v)[0]) for v in range(n))
        elif engine == "flow" and op in ("select", "vselect"):
            dest, cond, a, b = args
            n = VLEN if op == "vselect" else 1
            self.rd(dest, n)
            for v in range(n):
                (c, tc), (x, tx), (y, ty) = map(self.rd, (cond + v, a + v, b + v))
                writes[dest + v] = (z3.If(c != bv(0), x, y), tc | tx | ty)
        elif engine == "flow" and op == "add_imm":
            dest, a, imm = args
            self.rd(dest)
            x, tx = self.rd(a)
            writes[dest] = (fold(x + bv(imm)), tx)
        else:
            assert engine == "flow" and op == "pause", (
                f"unsupported slot {engine} {slot}"
            )

    def run(self):
        last = len(self.program) - 1
        for pc, bundle in enumerate(self.program):
            writes, stores = {}, []
            for engine, slots in bundle.items():
                assert engine in SLOT_LIMITS and engine != "debug", f"engine {engine}"
                assert len(slots) <= SLOT_LIMITS[engine], f"slot limit at {pc}"
                for s in slots:
                    assert (s[0] == "pause") == (engine == "flow" and pc == last), (
                        f"pause must be exactly the last bundle's flow slot, pc={pc}"
                    )
                    self.slot(engine, tuple(s), writes, stores)
            for m in self.machines:
                m.step(bundle, m.cores[0])
            for addr, (expr, taint) in writes.items():
                if len(taint) == 1:
                    conc = tuple(m.cores[0].scratch[addr] for m in self.machines)
                    expr = self.propose(expr, next(iter(taint)), conc)
                self.scr[addr], self.taint[addr] = expr, taint
            for addr, val in stores:
                self.mem = z3.Store(self.mem, addr, val)
        assert any(s[0] == "pause" for s in self.program[last].get("flow", ())), (
            "no pause"
        )

    def finish(self):
        proved = []
        for i, st in enumerate(self.states):
            if st.round < self.rounds:
                self.failures.append(
                    (f"element {i} stuck at round {st.round} stage {st.stage}", "")
                )
                continue
            goal = z3.Select(self.mem, bv(self.val_p + i)) == st.true
            if self.prove(goal, "final value"):
                proved.append(i)
        a = z3.BitVec("addr", W)
        outside = z3.Not(
            z3.And(z3.ULE(bv(self.val_p), a), z3.ULT(a, bv(self.val_p + self.batch)))
        )
        untouched = self.prove(
            z3.Implies(outside, z3.Select(self.mem, a) == z3.Select(self.mem0, a)),
            "other memory unchanged",
        )
        return proved, untouched


def check_transcription():
    for x in (0, 1, MASK, *(random.Random(1).getrandbits(W) for _ in range(5))):
        v = bv(x)
        for k in range(6):
            v = stage(k, v)
        assert z3.simplify(v).as_long() == myhash(x), "stage transcription"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--program", help="JSON with key 'instrs'; default builds via KernelBuilder"
    )
    ap.add_argument(
        "--shape",
        nargs=4,
        type=int,
        default=(10, 2047, 256, 16),
        metavar=("HEIGHT", "N_NODES", "BATCH", "ROUNDS"),
    )
    ap.add_argument(
        "--legacy", action="store_true", help="build with the legacy generator"
    )
    ap.add_argument("--timeout", type=float, default=300.0, help="seconds per z3 query")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    check_transcription()
    shape = tuple(args.shape)
    t0 = time.time()
    if args.program:
        instrs = json.loads(Path(args.program).read_text())["instrs"]
    else:
        from perf_takehome import KernelBuilder

        builder = KernelBuilder()
        if args.legacy:
            builder._build_legacy_kernel(*shape, 32, 12, 4)
        else:
            builder.build_kernel(*shape)
        instrs = builder.instrs
    program = [{e: [tuple(s) for s in slots] for e, slots in b.items()} for b in instrs]
    digest = hashlib.sha256(json.dumps(program).encode()).hexdigest()
    built = time.time() - t0
    v = Verifier(program, shape, int(args.timeout * 1000), args.samples, args.seed)
    t1 = time.time()
    v.run()
    proved, untouched = v.finish()
    complete = untouched and len(proved) == shape[2]
    print(
        json.dumps(
            {
                "digest": digest,
                "cycles": len(program),
                "shape": shape,
                "elements_proved": len(proved),
                "cuts": sum(s.cuts for s in v.states),
                "other_memory_unchanged": untouched,
                "queries": v.queries,
                "rejected_proposals": v.rejected,
                "query_seconds": {k: round(s, 2) for k, s in v.seconds.items()},
                "cache_hits": v.hits,
                "failures": v.failures[:20],
                "build_seconds": round(built, 1),
                "proof_seconds": round(time.time() - t1, 1),
                "proved": complete,
            }
        )
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
