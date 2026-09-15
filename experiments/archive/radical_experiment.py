#!/usr/bin/env python3
"""
RADICAL EXPERIMENT: Finding a fundamentally different algorithm.

Key insight from analysis:
- Node 0 is accessed 512 times (every element, rounds 0 and 11)
- Nodes 1-14 (levels 1-3) are accessed 100+ times combined
- We already preload these 15 nodes

NEW INSIGHT: What if we preload MORE levels and use SCALAR indexing?

The tree has 2047 nodes but we only have 1536 scratch words.
BUT - we're using VECTOR scratch (8 words per "register").

What if we stored tree nodes as SCALARS and used vbroadcast on demand?
2047 scalars fit in scratch!

Let's try it.
"""

import sys
import random
from collections import defaultdict

sys.path.insert(0, ".")

from problem import (
    SLOT_LIMITS,
    VLEN,
    SCRATCH_SIZE,
    HASH_STAGES,
    Tree,
    Input,
    build_mem_image,
    reference_kernel2,
    Machine,
    N_CORES,
)


def _vec_range(base, length=VLEN):
    return range(base, base + length)


def _slot_rw(engine, slot):
    reads, writes = [], []
    if engine == "alu":
        _op, dest, a1, a2 = slot
        reads = [a1, a2]
        writes = [dest]
    elif engine == "valu":
        match slot:
            case ("vbroadcast", dest, src):
                reads = [src]
                writes = list(_vec_range(dest))
            case ("multiply_add", dest, a, b, c):
                reads = list(_vec_range(a)) + list(_vec_range(b)) + list(_vec_range(c))
                writes = list(_vec_range(dest))
            case (_op, dest, a1, a2):
                reads = list(_vec_range(a1)) + list(_vec_range(a2))
                writes = list(_vec_range(dest))
    elif engine == "load":
        match slot:
            case ("load", dest, addr):
                reads, writes = [addr], [dest]
            case ("vload", dest, addr):
                reads, writes = [addr], list(_vec_range(dest))
            case ("const", dest, _val):
                writes = [dest]
            case ("load_offset", dest, addr, _lane):
                reads, writes = [addr], [dest]
    elif engine == "store":
        match slot:
            case ("store", addr, src):
                reads = [addr, src]
            case ("vstore", addr, src):
                reads = [addr] + list(_vec_range(src))
    elif engine == "flow":
        match slot:
            case ("select", dest, cond, a, b):
                reads, writes = [cond, a, b], [dest]
            case ("add_imm", dest, a, _imm):
                reads, writes = [a], [dest]
            case ("vselect", dest, cond, a, b):
                reads = (
                    list(_vec_range(cond)) + list(_vec_range(a)) + list(_vec_range(b))
                )
                writes = list(_vec_range(dest))
            case _:
                pass
    return reads, writes


def _schedule_slots(slots):
    cycles, usage = [], []
    ready_time = defaultdict(int)
    last_write = defaultdict(lambda: -1)
    last_read = defaultdict(lambda: -1)

    def ensure_cycle(cycle):
        while len(cycles) <= cycle:
            cycles.append({})
            usage.append(defaultdict(int))

    def find_cycle(engine, earliest):
        cycle = earliest
        limit = SLOT_LIMITS[engine]
        while True:
            ensure_cycle(cycle)
            if usage[cycle][engine] < limit:
                return cycle
            cycle += 1

    for engine, slot in slots:
        reads, writes = _slot_rw(engine, slot)
        earliest = 0
        for addr in reads:
            earliest = max(earliest, ready_time[addr])
        for addr in writes:
            earliest = max(earliest, last_write[addr] + 1, last_read[addr])

        cycle = find_cycle(engine, earliest)
        ensure_cycle(cycle)
        cycles[cycle].setdefault(engine, []).append(slot)
        usage[cycle][engine] += 1

        for addr in reads:
            if last_read[addr] < cycle:
                last_read[addr] = cycle
        for addr in writes:
            last_write[addr] = cycle
            ready_time[addr] = cycle + 1

    return [c for c in cycles if c]


class RadicalKernel:
    """
    Radical approach: Preload ENTIRE tree as scalars.
    Use scalar indexing + vbroadcast for node access.
    """

    def __init__(self):
        self.scratch = {}
        self.scratch_ptr = 0
        self.const_map = {}
        self.vconst_map = {}
        self.debug_info = {}

    def alloc_scratch(self, name=None, length=1):
        addr = self.scratch_ptr
        if name:
            self.scratch[name] = addr
            self.debug_info[addr] = (name, length)
        self.scratch_ptr += length
        if self.scratch_ptr > SCRATCH_SIZE:
            raise RuntimeError(
                f"Out of scratch! Used {self.scratch_ptr}, limit {SCRATCH_SIZE}"
            )
        return addr

    def alloc_vec(self, name=None):
        return self.alloc_scratch(name, VLEN)

    def scratch_const(self, val, slots):
        if val not in self.const_map:
            addr = self.alloc_scratch(f"const_{val}")
            slots.append(("load", ("const", addr, val)))
            self.const_map[val] = addr
        return self.const_map[val]

    def scratch_vconst(self, val, slots):
        if val not in self.vconst_map:
            scalar = self.scratch_const(val, slots)
            addr = self.alloc_vec(f"vconst_{val}")
            slots.append(("valu", ("vbroadcast", addr, scalar)))
            self.vconst_map[val] = addr
        return self.vconst_map[val]

    def build_kernel(
        self, forest_height, n_nodes, batch_size, rounds, group_size=17, round_tile=13
    ):
        FOREST_VALUES_P = 7
        INP_INDICES_P = FOREST_VALUES_P + n_nodes
        INP_VALUES_P = INP_INDICES_P + batch_size

        slots = []

        tmp_addr = self.alloc_scratch("tmp_addr")
        tmp_addr2 = self.alloc_scratch("tmp_addr2")

        zero_vec = self.scratch_vconst(0, slots)
        one_vec = self.scratch_vconst(1, slots)
        two_vec = self.scratch_vconst(2, slots)
        one_const = self.scratch_const(1, slots)

        forest_p_const = self.scratch_const(FOREST_VALUES_P, slots)
        n_nodes_vec = self.scratch_vconst(n_nodes, slots)

        # Hash constants
        hash_vec_consts1, hash_vec_consts3, hash_mul_vecs = [], [], []
        for op1, val1, op2, op3, val3 in HASH_STAGES:
            hash_vec_consts1.append(self.scratch_vconst(val1, slots))
            hash_vec_consts3.append(self.scratch_vconst(val3, slots))
            if op1 == "+" and op2 == "+" and op3 == "<<":
                hash_mul_vecs.append(self.scratch_vconst(1 + (1 << val3), slots))
            else:
                hash_mul_vecs.append(None)

        blocks = batch_size // VLEN

        # Allocate persistent idx/val storage
        idx_base = self.alloc_scratch("idx_scratch", batch_size)
        val_base = self.alloc_scratch("val_scratch", batch_size)

        # Load initial data
        vlen_const = self.scratch_const(VLEN, slots)
        offset = self.alloc_scratch("offset")
        slots.append(("load", ("const", offset, 0)))

        for block in range(blocks):
            slots.append(
                (
                    "alu",
                    ("+", tmp_addr, self.scratch_const(INP_INDICES_P, slots), offset),
                )
            )
            slots.append(("load", ("vload", idx_base + block * VLEN, tmp_addr)))
            slots.append(
                (
                    "alu",
                    ("+", tmp_addr, self.scratch_const(INP_VALUES_P, slots), offset),
                )
            )
            slots.append(("load", ("vload", val_base + block * VLEN, tmp_addr)))
            slots.append(("alu", ("+", offset, offset, vlen_const)))

        # Allocate working vectors for groups
        contexts = []
        for g in range(group_size):
            contexts.append(
                {
                    "node": self.alloc_vec(f"node_{g}"),
                    "tmp1": self.alloc_vec(f"tmp1_{g}"),
                    "tmp2": self.alloc_vec(f"tmp2_{g}"),
                    "addr": self.alloc_vec(f"addr_{g}"),
                }
            )

        # Main kernel - tiled processing
        for group_start in range(0, blocks, group_size):
            for round_start in range(0, rounds, round_tile):
                round_end = min(rounds, round_start + round_tile)

                for gi in range(group_size):
                    block = group_start + gi
                    if block >= blocks:
                        break

                    ctx = contexts[gi]
                    idx_vec = idx_base + block * VLEN
                    val_vec = val_base + block * VLEN

                    for rnd in range(round_start, round_end):
                        level = rnd % (forest_height + 1)

                        # Compute address: forest_p + idx
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "alu",
                                    (
                                        "+",
                                        ctx["addr"] + lane,
                                        forest_p_const,
                                        idx_vec + lane,
                                    ),
                                )
                            )

                        # Gather node values
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "load",
                                    ("load", ctx["node"] + lane, ctx["addr"] + lane),
                                )
                            )

                        # XOR val with node
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "alu",
                                    (
                                        "^",
                                        val_vec + lane,
                                        val_vec + lane,
                                        ctx["node"] + lane,
                                    ),
                                )
                            )

                        # Hash computation
                        for hi, (op1, _v1, op2, op3, _v3) in enumerate(HASH_STAGES):
                            if hash_mul_vecs[hi] is not None:
                                slots.append(
                                    (
                                        "valu",
                                        (
                                            "multiply_add",
                                            val_vec,
                                            val_vec,
                                            hash_mul_vecs[hi],
                                            hash_vec_consts1[hi],
                                        ),
                                    )
                                )
                            else:
                                slots.append(
                                    (
                                        "valu",
                                        (
                                            op1,
                                            ctx["tmp1"],
                                            val_vec,
                                            hash_vec_consts1[hi],
                                        ),
                                    )
                                )
                                slots.append(
                                    (
                                        "valu",
                                        (
                                            op3,
                                            ctx["tmp2"],
                                            val_vec,
                                            hash_vec_consts3[hi],
                                        ),
                                    )
                                )
                                slots.append(
                                    ("valu", (op2, val_vec, ctx["tmp1"], ctx["tmp2"]))
                                )

                        # Index update
                        if level == forest_height:
                            slots.append(("valu", ("+", idx_vec, zero_vec, zero_vec)))
                        else:
                            for lane in range(VLEN):
                                slots.append(
                                    (
                                        "alu",
                                        (
                                            "&",
                                            ctx["tmp1"] + lane,
                                            val_vec + lane,
                                            one_const,
                                        ),
                                    )
                                )
                                slots.append(
                                    (
                                        "alu",
                                        (
                                            "+",
                                            ctx["node"] + lane,
                                            ctx["tmp1"] + lane,
                                            one_const,
                                        ),
                                    )
                                )
                            slots.append(
                                (
                                    "valu",
                                    (
                                        "multiply_add",
                                        idx_vec,
                                        idx_vec,
                                        two_vec,
                                        ctx["node"],
                                    ),
                                )
                            )

        # Store results
        for block in range(blocks):
            slots.append(("load", ("const", tmp_addr, INP_VALUES_P + block * VLEN)))
            slots.append(("store", ("vstore", tmp_addr, val_base + block * VLEN)))

        return _schedule_slots(slots)


def test_kernel():
    print("=" * 70)
    print("RADICAL EXPERIMENT: Simplified gather-only approach")
    print("=" * 70)

    random.seed(123)
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)

    kernel = RadicalKernel()

    try:
        instrs = kernel.build_kernel(
            forest.height,
            len(forest.values),
            len(inp.indices),
            16,
            group_size=17,
            round_tile=13,
        )

        print(f"Scratch used: {kernel.scratch_ptr} / {SCRATCH_SIZE}")
        print(f"Cycles: {len(instrs)}")

        # Verify correctness
        from problem import DebugInfo

        debug = DebugInfo(scratch_map=kernel.debug_info)
        machine = Machine(mem, instrs, debug, n_cores=N_CORES)

        for ref_mem in reference_kernel2(mem, {}):
            machine.run()

        inp_values_p = mem[6]
        expected = ref_mem[inp_values_p : inp_values_p + len(inp.values)]
        actual = machine.mem[inp_values_p : inp_values_p + len(inp.values)]

        if actual == expected:
            print("✓ Correctness: PASSED")
        else:
            print("✗ Correctness: FAILED")
            return None

        return len(instrs)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def compare_with_baseline():
    from perf_takehome import KernelBuilder

    random.seed(123)

    kb = KernelBuilder()
    kb.build_kernel(10, 2047, 256, 16)
    baseline = len(kb.instrs)

    radical = test_kernel()

    if radical:
        print(f"\nComparison:")
        print(f"  Baseline: {baseline} cycles")
        print(f"  Radical:  {radical} cycles")
        print(f"  Delta:    {radical - baseline:+d} cycles")


if __name__ == "__main__":
    compare_with_baseline()
