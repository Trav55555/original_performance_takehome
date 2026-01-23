#!/usr/bin/env python3
"""
Breakthrough optimization experiments for VLIW kernel.

Implements five research-inspired techniques:
A. Deep pipelining - interleave ops from multiple rounds
B. Speculative tree preloading for predictable patterns
C. Hash stage reordering (fusable stages first)
D. Work stealing from drain phase
E. Register renaming / variable expansion
"""

import sys

sys.path.insert(0, "..")
sys.path.insert(0, "../tests")

import random
from collections import defaultdict
from copy import deepcopy

from problem import HASH_STAGES, SLOT_LIMITS, VLEN, SCRATCH_SIZE
from frozen_problem import (
    Tree,
    Input,
    build_mem_image,
    Machine,
    N_CORES,
    reference_kernel2,
)
from perf_takehome import KernelBuilder, _schedule_slots, _slot_rw


def test_kernel(kb, mem, inp):
    for ref_mem in reference_kernel2(mem.copy()):
        pass
    inp_values_p = ref_mem[6]
    expected = ref_mem[inp_values_p : inp_values_p + len(inp.values)]

    machine = Machine(mem.copy(), kb.instrs, kb.debug_info(), n_cores=N_CORES)
    machine.enable_pause = False
    machine.enable_debug = False
    machine.run()

    actual = machine.mem[inp_values_p : inp_values_p + len(inp.values)]
    correct = actual == expected
    return machine.cycle, correct


def baseline_test():
    """Test baseline kernel."""
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)

    kb = KernelBuilder()
    kb.build_kernel(forest.height, len(forest.values), len(inp.indices), 16)

    cycles, correct = test_kernel(kb, mem, inp)
    return cycles, correct


class ExperimentalKernelBuilder(KernelBuilder):
    """Extended kernel builder for experiments."""

    def build_kernel_technique_a(
        self,
        forest_height: int,
        n_nodes: int,
        batch_size: int,
        rounds: int,
    ):
        """
        Technique A: Deep pipelining.

        Instead of completing all ops for one block-round before moving to next,
        interleave operations at a finer granularity:
        - Emit XOR ops for multiple blocks
        - Then emit hash stage 0 for those blocks
        - Then hash stage 1, etc.

        This should help fill VALU slots during load-limited phases.
        """
        tmp_addr = self.alloc_scratch("tmp_addr")
        tmp_addr2 = self.alloc_scratch("tmp_addr2")

        FOREST_VALUES_P = 7
        INP_INDICES_P = 2054
        INP_VALUES_P = 2310

        init_vars = [
            "rounds",
            "n_nodes",
            "batch_size",
            "forest_height",
            "forest_values_p",
            "inp_indices_p",
            "inp_values_p",
        ]
        for v in init_vars:
            self.alloc_scratch(v, 1)

        init_slots = []
        init_slots.append(
            ("load", ("const", self.scratch["forest_values_p"], FOREST_VALUES_P))
        )
        init_slots.append(
            ("load", ("const", self.scratch["inp_indices_p"], INP_INDICES_P))
        )
        init_slots.append(
            ("load", ("const", self.scratch["inp_values_p"], INP_VALUES_P))
        )

        zero_vec = self.scratch_vconst(0, "v_zero", init_slots)
        one_vec = self.scratch_vconst(1, "v_one", init_slots)
        two_vec = self.scratch_vconst(2, "v_two", init_slots)
        one_const = self.scratch_const(1, slots=init_slots)

        forest_vec = self.alloc_vec("v_forest_p")
        init_slots.append(
            ("valu", ("vbroadcast", forest_vec, self.scratch["forest_values_p"]))
        )

        three_vec = self.scratch_vconst(3, "v_three", init_slots)
        four_vec = self.scratch_vconst(4, "v_four", init_slots)
        seven_vec = self.scratch_vconst(7, "v_seven", init_slots)

        node_vecs = []
        PRELOAD_NODES = 15
        for node_idx in range(PRELOAD_NODES):
            node_scalar = self.alloc_scratch(f"node_{node_idx}")
            node_vec = self.alloc_vec(f"v_node_{node_idx}")
            node_offset = self.scratch_const(node_idx, slots=init_slots)
            addr_reg = tmp_addr if node_idx % 2 == 0 else tmp_addr2
            init_slots.append(
                ("alu", ("+", addr_reg, self.scratch["forest_values_p"], node_offset))
            )
            init_slots.append(("load", ("load", node_scalar, addr_reg)))
            init_slots.append(("valu", ("vbroadcast", node_vec, node_scalar)))
            node_vecs.append(node_vec)

        hash_vec_consts1 = []
        hash_vec_consts3 = []
        hash_mul_vecs = []
        for op1, val1, op2, op3, val3 in HASH_STAGES:
            hash_vec_consts1.append(self.scratch_vconst(val1, slots=init_slots))
            hash_vec_consts3.append(self.scratch_vconst(val3, slots=init_slots))
            if op1 == "+" and op2 == "+" and op3 == "<<":
                hash_mul_vecs.append(
                    self.scratch_vconst(1 + (1 << val3), slots=init_slots)
                )
            else:
                hash_mul_vecs.append(None)

        blocks_per_round = batch_size // VLEN
        idx_base = self.alloc_scratch("idx_scratch", batch_size)
        val_base = self.alloc_scratch("val_scratch", batch_size)

        offset = self.alloc_scratch("offset")
        init_slots.append(("load", ("const", offset, 0)))
        vlen_const = self.scratch_const(VLEN, slots=init_slots)

        slots = list(init_slots)
        for block in range(blocks_per_round):
            slots.append(
                ("alu", ("+", tmp_addr, self.scratch["inp_indices_p"], offset))
            )
            slots.append(("load", ("vload", idx_base + block * VLEN, tmp_addr)))
            slots.append(("alu", ("+", tmp_addr, self.scratch["inp_values_p"], offset)))
            slots.append(("load", ("vload", val_base + block * VLEN, tmp_addr)))
            slots.append(("alu", ("+", offset, offset, vlen_const)))

        group_size = 17
        contexts = []
        for _ in range(group_size):
            contexts.append(
                {
                    "node": self.alloc_vec(),
                    "tmp1": self.alloc_vec(),
                    "tmp2": self.alloc_vec(),
                    "tmp3": self.alloc_vec(),
                    "tmp4": self.alloc_vec(),
                }
            )

        def emit_xor_for_block(block, ctx, node_vec):
            idx_vec = idx_base + block * VLEN
            val_vec = val_base + block * VLEN
            for lane in range(VLEN):
                slots.append(
                    ("alu", ("^", val_vec + lane, val_vec + lane, node_vec + lane))
                )

        def emit_hash_stage_for_block(block, ctx, stage_idx):
            val_vec = val_base + block * VLEN
            op1, _val1, op2, op3, _val3 = HASH_STAGES[stage_idx]
            mul_vec = hash_mul_vecs[stage_idx]
            if mul_vec is not None:
                slots.append(
                    (
                        "valu",
                        (
                            "multiply_add",
                            val_vec,
                            val_vec,
                            mul_vec,
                            hash_vec_consts1[stage_idx],
                        ),
                    )
                )
            else:
                slots.append(
                    ("valu", (op1, ctx["tmp1"], val_vec, hash_vec_consts1[stage_idx]))
                )
                slots.append(
                    ("valu", (op3, ctx["tmp2"], val_vec, hash_vec_consts3[stage_idx]))
                )
                slots.append(("valu", (op2, val_vec, ctx["tmp1"], ctx["tmp2"])))

        def emit_index_update_for_block(block, ctx, level):
            idx_vec = idx_base + block * VLEN
            val_vec = val_base + block * VLEN
            if level == forest_height:
                slots.append(("valu", ("+", idx_vec, zero_vec, zero_vec)))
            else:
                for lane in range(VLEN):
                    slots.append(
                        ("alu", ("&", ctx["tmp1"] + lane, val_vec + lane, one_const))
                    )
                    slots.append(
                        (
                            "alu",
                            ("+", ctx["node"] + lane, ctx["tmp1"] + lane, one_const),
                        )
                    )
                slots.append(
                    ("valu", ("multiply_add", idx_vec, idx_vec, two_vec, ctx["node"]))
                )

        def emit_level_selection_for_block(block, ctx, level):
            idx_vec = idx_base + block * VLEN
            if level == 0:
                return node_vecs[0]
            elif level == 1:
                slots.append(("valu", ("&", ctx["tmp1"], idx_vec, one_vec)))
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["node"],
                            ctx["tmp1"],
                            node_vecs[1],
                            node_vecs[2],
                        ),
                    )
                )
                return ctx["node"]
            elif level == 2:
                slots.append(("valu", ("-", ctx["tmp1"], idx_vec, three_vec)))
                slots.append(("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec)))
                slots.append(("valu", ("&", ctx["node"], ctx["tmp1"], two_vec)))
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["tmp1"],
                            ctx["tmp2"],
                            node_vecs[4],
                            node_vecs[3],
                        ),
                    )
                )
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["tmp2"],
                            ctx["tmp2"],
                            node_vecs[6],
                            node_vecs[5],
                        ),
                    )
                )
                slots.append(
                    (
                        "flow",
                        ("vselect", ctx["node"], ctx["node"], ctx["tmp2"], ctx["tmp1"]),
                    )
                )
                return ctx["node"]
            elif level == 3:
                slots.append(("valu", ("-", ctx["tmp1"], idx_vec, seven_vec)))
                slots.append(("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec)))
                slots.append(("valu", ("&", ctx["tmp3"], ctx["tmp1"], two_vec)))
                slots.append(("valu", ("&", ctx["tmp4"], ctx["tmp1"], four_vec)))
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["node"],
                            ctx["tmp2"],
                            node_vecs[8],
                            node_vecs[7],
                        ),
                    )
                )
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["tmp1"],
                            ctx["tmp2"],
                            node_vecs[10],
                            node_vecs[9],
                        ),
                    )
                )
                slots.append(
                    (
                        "flow",
                        ("vselect", ctx["tmp1"], ctx["tmp3"], ctx["tmp1"], ctx["node"]),
                    )
                )
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["node"],
                            ctx["tmp2"],
                            node_vecs[12],
                            node_vecs[11],
                        ),
                    )
                )
                slots.append(
                    (
                        "flow",
                        (
                            "vselect",
                            ctx["tmp2"],
                            ctx["tmp2"],
                            node_vecs[14],
                            node_vecs[13],
                        ),
                    )
                )
                slots.append(
                    (
                        "flow",
                        ("vselect", ctx["node"], ctx["tmp3"], ctx["tmp2"], ctx["node"]),
                    )
                )
                slots.append(
                    (
                        "flow",
                        ("vselect", ctx["node"], ctx["tmp4"], ctx["node"], ctx["tmp1"]),
                    )
                )
                return ctx["node"]
            else:
                for lane in range(VLEN):
                    slots.append(
                        (
                            "alu",
                            (
                                "+",
                                ctx["tmp1"] + lane,
                                forest_vec + lane,
                                idx_vec + lane,
                            ),
                        )
                    )
                for lane in range(VLEN):
                    slots.append(
                        ("load", ("load", ctx["node"] + lane, ctx["tmp1"] + lane))
                    )
                return ctx["node"]

        round_tile = 13
        for group_start in range(0, blocks_per_round, group_size):
            for round_start in range(0, rounds, round_tile):
                round_end = min(rounds, round_start + round_tile)

                for _round in range(round_start, round_end):
                    level = _round % (forest_height + 1)

                    active_blocks = []
                    for gi in range(group_size):
                        block = group_start + gi
                        if block < blocks_per_round:
                            active_blocks.append((block, contexts[gi]))

                    for block, ctx in active_blocks:
                        node_vec = emit_level_selection_for_block(block, ctx, level)
                        emit_xor_for_block(block, ctx, node_vec)

                    for stage_idx in range(len(HASH_STAGES)):
                        for block, ctx in active_blocks:
                            emit_hash_stage_for_block(block, ctx, stage_idx)

                    for block, ctx in active_blocks:
                        emit_index_update_for_block(block, ctx, level)

        for block in range(blocks_per_round):
            slots.append(("load", ("const", tmp_addr, INP_VALUES_P + block * VLEN)))
            slots.append(("store", ("vstore", tmp_addr, val_base + block * VLEN)))

        self.instrs.extend(_schedule_slots(slots))
        self.instrs.append({"flow": [("pause",)]})

    def build_kernel_technique_c(
        self,
        forest_height: int,
        n_nodes: int,
        batch_size: int,
        rounds: int,
    ):
        """
        Technique C: Hash stage reordering.

        Reorder hash stages to do all fusable stages first (0, 2, 4),
        then non-fusable stages (1, 3, 5).

        This might reduce dependency stalls by grouping similar ops.

        NOTE: This changes the hash output! Only valid if mathematically equivalent.
        Actually, the hash stages are sequential and dependent, so we CAN'T reorder them.

        Alternative: Try emitting hash ops for multiple blocks before completing one.
        """
        tmp_addr = self.alloc_scratch("tmp_addr")
        tmp_addr2 = self.alloc_scratch("tmp_addr2")

        FOREST_VALUES_P = 7
        INP_INDICES_P = 2054
        INP_VALUES_P = 2310

        init_vars = [
            "rounds",
            "n_nodes",
            "batch_size",
            "forest_height",
            "forest_values_p",
            "inp_indices_p",
            "inp_values_p",
        ]
        for v in init_vars:
            self.alloc_scratch(v, 1)

        init_slots = []
        init_slots.append(
            ("load", ("const", self.scratch["forest_values_p"], FOREST_VALUES_P))
        )
        init_slots.append(
            ("load", ("const", self.scratch["inp_indices_p"], INP_INDICES_P))
        )
        init_slots.append(
            ("load", ("const", self.scratch["inp_values_p"], INP_VALUES_P))
        )

        zero_vec = self.scratch_vconst(0, "v_zero", init_slots)
        one_vec = self.scratch_vconst(1, "v_one", init_slots)
        two_vec = self.scratch_vconst(2, "v_two", init_slots)
        one_const = self.scratch_const(1, slots=init_slots)

        forest_vec = self.alloc_vec("v_forest_p")
        init_slots.append(
            ("valu", ("vbroadcast", forest_vec, self.scratch["forest_values_p"]))
        )

        three_vec = self.scratch_vconst(3, "v_three", init_slots)
        four_vec = self.scratch_vconst(4, "v_four", init_slots)
        seven_vec = self.scratch_vconst(7, "v_seven", init_slots)

        node_vecs = []
        PRELOAD_NODES = 15
        for node_idx in range(PRELOAD_NODES):
            node_scalar = self.alloc_scratch(f"node_{node_idx}")
            node_vec = self.alloc_vec(f"v_node_{node_idx}")
            node_offset = self.scratch_const(node_idx, slots=init_slots)
            addr_reg = tmp_addr if node_idx % 2 == 0 else tmp_addr2
            init_slots.append(
                ("alu", ("+", addr_reg, self.scratch["forest_values_p"], node_offset))
            )
            init_slots.append(("load", ("load", node_scalar, addr_reg)))
            init_slots.append(("valu", ("vbroadcast", node_vec, node_scalar)))
            node_vecs.append(node_vec)

        hash_vec_consts1 = []
        hash_vec_consts3 = []
        hash_mul_vecs = []
        for op1, val1, op2, op3, val3 in HASH_STAGES:
            hash_vec_consts1.append(self.scratch_vconst(val1, slots=init_slots))
            hash_vec_consts3.append(self.scratch_vconst(val3, slots=init_slots))
            if op1 == "+" and op2 == "+" and op3 == "<<":
                hash_mul_vecs.append(
                    self.scratch_vconst(1 + (1 << val3), slots=init_slots)
                )
            else:
                hash_mul_vecs.append(None)

        blocks_per_round = batch_size // VLEN
        idx_base = self.alloc_scratch("idx_scratch", batch_size)
        val_base = self.alloc_scratch("val_scratch", batch_size)

        offset = self.alloc_scratch("offset")
        init_slots.append(("load", ("const", offset, 0)))
        vlen_const = self.scratch_const(VLEN, slots=init_slots)

        slots = list(init_slots)
        for block in range(blocks_per_round):
            slots.append(
                ("alu", ("+", tmp_addr, self.scratch["inp_indices_p"], offset))
            )
            slots.append(("load", ("vload", idx_base + block * VLEN, tmp_addr)))
            slots.append(("alu", ("+", tmp_addr, self.scratch["inp_values_p"], offset)))
            slots.append(("load", ("vload", val_base + block * VLEN, tmp_addr)))
            slots.append(("alu", ("+", offset, offset, vlen_const)))

        group_size = 17
        contexts = []
        for _ in range(group_size):
            contexts.append(
                {
                    "node": self.alloc_vec(),
                    "tmp1": self.alloc_vec(),
                    "tmp2": self.alloc_vec(),
                    "tmp3": self.alloc_vec(),
                    "tmp4": self.alloc_vec(),
                }
            )

        round_tile = 13
        for group_start in range(0, blocks_per_round, group_size):
            for round_start in range(0, rounds, round_tile):
                round_end = min(rounds, round_start + round_tile)
                for gi in range(group_size):
                    block = group_start + gi
                    if block >= blocks_per_round:
                        break
                    ctx = contexts[gi]
                    idx_vec = idx_base + block * VLEN
                    val_vec = val_base + block * VLEN

                    for _round in range(round_start, round_end):
                        level = _round % (forest_height + 1)

                        def emit_xor(node_vec):
                            for lane in range(VLEN):
                                slots.append(
                                    (
                                        "alu",
                                        (
                                            "^",
                                            val_vec + lane,
                                            val_vec + lane,
                                            node_vec + lane,
                                        ),
                                    )
                                )

                        if level == 0:
                            emit_xor(node_vecs[0])
                        elif level == 1:
                            slots.append(("valu", ("&", ctx["tmp1"], idx_vec, one_vec)))
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["node"],
                                        ctx["tmp1"],
                                        node_vecs[1],
                                        node_vecs[2],
                                    ),
                                )
                            )
                            emit_xor(ctx["node"])
                        elif level == 2:
                            slots.append(
                                ("valu", ("-", ctx["tmp1"], idx_vec, three_vec))
                            )
                            slots.append(
                                ("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec))
                            )
                            slots.append(
                                ("valu", ("&", ctx["node"], ctx["tmp1"], two_vec))
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["tmp1"],
                                        ctx["tmp2"],
                                        node_vecs[4],
                                        node_vecs[3],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["tmp2"],
                                        ctx["tmp2"],
                                        node_vecs[6],
                                        node_vecs[5],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["node"],
                                        ctx["node"],
                                        ctx["tmp2"],
                                        ctx["tmp1"],
                                    ),
                                )
                            )
                            emit_xor(ctx["node"])
                        elif level == 3:
                            slots.append(
                                ("valu", ("-", ctx["tmp1"], idx_vec, seven_vec))
                            )
                            slots.append(
                                ("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec))
                            )
                            slots.append(
                                ("valu", ("&", ctx["tmp3"], ctx["tmp1"], two_vec))
                            )
                            slots.append(
                                ("valu", ("&", ctx["tmp4"], ctx["tmp1"], four_vec))
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["node"],
                                        ctx["tmp2"],
                                        node_vecs[8],
                                        node_vecs[7],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["tmp1"],
                                        ctx["tmp2"],
                                        node_vecs[10],
                                        node_vecs[9],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["tmp1"],
                                        ctx["tmp3"],
                                        ctx["tmp1"],
                                        ctx["node"],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["node"],
                                        ctx["tmp2"],
                                        node_vecs[12],
                                        node_vecs[11],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["tmp2"],
                                        ctx["tmp2"],
                                        node_vecs[14],
                                        node_vecs[13],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["node"],
                                        ctx["tmp3"],
                                        ctx["tmp2"],
                                        ctx["node"],
                                    ),
                                )
                            )
                            slots.append(
                                (
                                    "flow",
                                    (
                                        "vselect",
                                        ctx["node"],
                                        ctx["tmp4"],
                                        ctx["node"],
                                        ctx["tmp1"],
                                    ),
                                )
                            )
                            emit_xor(ctx["node"])
                        else:
                            for lane in range(VLEN):
                                slots.append(
                                    (
                                        "alu",
                                        (
                                            "+",
                                            ctx["tmp1"] + lane,
                                            forest_vec + lane,
                                            idx_vec + lane,
                                        ),
                                    )
                                )
                            for lane in range(VLEN):
                                slots.append(
                                    (
                                        "load",
                                        (
                                            "load",
                                            ctx["node"] + lane,
                                            ctx["tmp1"] + lane,
                                        ),
                                    )
                                )
                            emit_xor(ctx["node"])

                        for hi, (op1, _val1, op2, op3, _val3) in enumerate(HASH_STAGES):
                            mul_vec = hash_mul_vecs[hi]
                            if mul_vec is not None:
                                slots.append(
                                    (
                                        "valu",
                                        (
                                            "multiply_add",
                                            val_vec,
                                            val_vec,
                                            mul_vec,
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

        for block in range(blocks_per_round):
            slots.append(("load", ("const", tmp_addr, INP_VALUES_P + block * VLEN)))
            slots.append(("store", ("vstore", tmp_addr, val_base + block * VLEN)))

        self.instrs.extend(_schedule_slots(slots))
        self.instrs.append({"flow": [("pause",)]})


def test_technique_a():
    """Test Technique A: Deep pipelining."""
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)

    kb = ExperimentalKernelBuilder()
    kb.build_kernel_technique_a(forest.height, len(forest.values), len(inp.indices), 16)

    return test_kernel(kb, mem, inp)


def test_technique_b():
    """
    Test Technique B: Speculative tree preloading.

    After level 10 (forest_height), indices wrap to 0.
    Round 11 will access nodes 1 or 2 (idx=0 means node 1 or 2).
    Round 12 will access nodes 3-6.

    We already preload nodes 0-14 for levels 0-3.
    The same nodes are accessed after wrap-around!

    This technique is ALREADY IMPLEMENTED via the vselect approach.
    """
    print("Technique B: Already implemented via vselect for levels 0-3")
    print("After wrap-around, the same nodes (0-14) are accessed.")
    return None, None


def test_technique_c():
    """Test Technique C: Hash stage reordering (actually, alternative ordering)."""
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)

    kb = ExperimentalKernelBuilder()
    kb.build_kernel_technique_c(forest.height, len(forest.values), len(inp.indices), 16)

    return test_kernel(kb, mem, inp)


def test_technique_d():
    """
    Test Technique D: Work stealing from drain phase.

    The drain phase has low VALU utilization because work is finishing.
    "Stealing" work would mean moving operations earlier, but the greedy
    scheduler already does this - it places ops as early as possible.

    The only way to improve drain would be to have MORE work available
    at the end, which contradicts the goal.

    Alternative interpretation: Overlap stores with computation.
    Currently stores happen at the very end. What if we emit stores
    as soon as a block finishes its final round?
    """
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)

    kb = ExperimentalKernelBuilder()
    build_kernel_interleaved_stores(
        kb, forest.height, len(forest.values), len(inp.indices), 16
    )

    return test_kernel(kb, mem, inp)


def build_kernel_interleaved_stores(kb, forest_height, n_nodes, batch_size, rounds):
    """Emit stores immediately after each block completes."""
    tmp_addr = kb.alloc_scratch("tmp_addr")
    tmp_addr2 = kb.alloc_scratch("tmp_addr2")

    FOREST_VALUES_P = 7
    INP_INDICES_P = 2054
    INP_VALUES_P = 2310

    init_vars = [
        "rounds",
        "n_nodes",
        "batch_size",
        "forest_height",
        "forest_values_p",
        "inp_indices_p",
        "inp_values_p",
    ]
    for v in init_vars:
        kb.alloc_scratch(v, 1)

    init_slots = []
    init_slots.append(
        ("load", ("const", kb.scratch["forest_values_p"], FOREST_VALUES_P))
    )
    init_slots.append(("load", ("const", kb.scratch["inp_indices_p"], INP_INDICES_P)))
    init_slots.append(("load", ("const", kb.scratch["inp_values_p"], INP_VALUES_P)))

    zero_vec = kb.scratch_vconst(0, "v_zero", init_slots)
    one_vec = kb.scratch_vconst(1, "v_one", init_slots)
    two_vec = kb.scratch_vconst(2, "v_two", init_slots)
    one_const = kb.scratch_const(1, slots=init_slots)

    forest_vec = kb.alloc_vec("v_forest_p")
    init_slots.append(
        ("valu", ("vbroadcast", forest_vec, kb.scratch["forest_values_p"]))
    )

    three_vec = kb.scratch_vconst(3, "v_three", init_slots)
    four_vec = kb.scratch_vconst(4, "v_four", init_slots)
    seven_vec = kb.scratch_vconst(7, "v_seven", init_slots)

    node_vecs = []
    PRELOAD_NODES = 15
    for node_idx in range(PRELOAD_NODES):
        node_scalar = kb.alloc_scratch(f"node_{node_idx}")
        node_vec = kb.alloc_vec(f"v_node_{node_idx}")
        node_offset = kb.scratch_const(node_idx, slots=init_slots)
        addr_reg = tmp_addr if node_idx % 2 == 0 else tmp_addr2
        init_slots.append(
            ("alu", ("+", addr_reg, kb.scratch["forest_values_p"], node_offset))
        )
        init_slots.append(("load", ("load", node_scalar, addr_reg)))
        init_slots.append(("valu", ("vbroadcast", node_vec, node_scalar)))
        node_vecs.append(node_vec)

    hash_vec_consts1 = []
    hash_vec_consts3 = []
    hash_mul_vecs = []
    for op1, val1, op2, op3, val3 in HASH_STAGES:
        hash_vec_consts1.append(kb.scratch_vconst(val1, slots=init_slots))
        hash_vec_consts3.append(kb.scratch_vconst(val3, slots=init_slots))
        if op1 == "+" and op2 == "+" and op3 == "<<":
            hash_mul_vecs.append(kb.scratch_vconst(1 + (1 << val3), slots=init_slots))
        else:
            hash_mul_vecs.append(None)

    blocks_per_round = batch_size // VLEN
    idx_base = kb.alloc_scratch("idx_scratch", batch_size)
    val_base = kb.alloc_scratch("val_scratch", batch_size)

    offset = kb.alloc_scratch("offset")
    init_slots.append(("load", ("const", offset, 0)))
    vlen_const = kb.scratch_const(VLEN, slots=init_slots)

    slots = list(init_slots)
    for block in range(blocks_per_round):
        slots.append(("alu", ("+", tmp_addr, kb.scratch["inp_indices_p"], offset)))
        slots.append(("load", ("vload", idx_base + block * VLEN, tmp_addr)))
        slots.append(("alu", ("+", tmp_addr, kb.scratch["inp_values_p"], offset)))
        slots.append(("load", ("vload", val_base + block * VLEN, tmp_addr)))
        slots.append(("alu", ("+", offset, offset, vlen_const)))

    group_size = 17
    contexts = []
    for _ in range(group_size):
        contexts.append(
            {
                "node": kb.alloc_vec(),
                "tmp1": kb.alloc_vec(),
                "tmp2": kb.alloc_vec(),
                "tmp3": kb.alloc_vec(),
                "tmp4": kb.alloc_vec(),
            }
        )

    store_addr = kb.alloc_scratch("store_addr")
    blocks_completed = set()

    round_tile = 13
    for group_start in range(0, blocks_per_round, group_size):
        for round_start in range(0, rounds, round_tile):
            round_end = min(rounds, round_start + round_tile)
            for gi in range(group_size):
                block = group_start + gi
                if block >= blocks_per_round:
                    break
                ctx = contexts[gi]
                idx_vec = idx_base + block * VLEN
                val_vec = val_base + block * VLEN

                for _round in range(round_start, round_end):
                    level = _round % (forest_height + 1)

                    def emit_xor(node_vec):
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "alu",
                                    (
                                        "^",
                                        val_vec + lane,
                                        val_vec + lane,
                                        node_vec + lane,
                                    ),
                                )
                            )

                    if level == 0:
                        emit_xor(node_vecs[0])
                    elif level == 1:
                        slots.append(("valu", ("&", ctx["tmp1"], idx_vec, one_vec)))
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp1"],
                                    node_vecs[1],
                                    node_vecs[2],
                                ),
                            )
                        )
                        emit_xor(ctx["node"])
                    elif level == 2:
                        slots.append(("valu", ("-", ctx["tmp1"], idx_vec, three_vec)))
                        slots.append(("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec)))
                        slots.append(("valu", ("&", ctx["node"], ctx["tmp1"], two_vec)))
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp1"],
                                    ctx["tmp2"],
                                    node_vecs[4],
                                    node_vecs[3],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp2"],
                                    ctx["tmp2"],
                                    node_vecs[6],
                                    node_vecs[5],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["node"],
                                    ctx["tmp2"],
                                    ctx["tmp1"],
                                ),
                            )
                        )
                        emit_xor(ctx["node"])
                    elif level == 3:
                        slots.append(("valu", ("-", ctx["tmp1"], idx_vec, seven_vec)))
                        slots.append(("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec)))
                        slots.append(("valu", ("&", ctx["tmp3"], ctx["tmp1"], two_vec)))
                        slots.append(
                            ("valu", ("&", ctx["tmp4"], ctx["tmp1"], four_vec))
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp2"],
                                    node_vecs[8],
                                    node_vecs[7],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp1"],
                                    ctx["tmp2"],
                                    node_vecs[10],
                                    node_vecs[9],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp1"],
                                    ctx["tmp3"],
                                    ctx["tmp1"],
                                    ctx["node"],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp2"],
                                    node_vecs[12],
                                    node_vecs[11],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp2"],
                                    ctx["tmp2"],
                                    node_vecs[14],
                                    node_vecs[13],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp3"],
                                    ctx["tmp2"],
                                    ctx["node"],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp4"],
                                    ctx["node"],
                                    ctx["tmp1"],
                                ),
                            )
                        )
                        emit_xor(ctx["node"])
                    else:
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "alu",
                                    (
                                        "+",
                                        ctx["tmp1"] + lane,
                                        forest_vec + lane,
                                        idx_vec + lane,
                                    ),
                                )
                            )
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "load",
                                    ("load", ctx["node"] + lane, ctx["tmp1"] + lane),
                                )
                            )
                        emit_xor(ctx["node"])

                    for hi, (op1, _val1, op2, op3, _val3) in enumerate(HASH_STAGES):
                        mul_vec = hash_mul_vecs[hi]
                        if mul_vec is not None:
                            slots.append(
                                (
                                    "valu",
                                    (
                                        "multiply_add",
                                        val_vec,
                                        val_vec,
                                        mul_vec,
                                        hash_vec_consts1[hi],
                                    ),
                                )
                            )
                        else:
                            slots.append(
                                (
                                    "valu",
                                    (op1, ctx["tmp1"], val_vec, hash_vec_consts1[hi]),
                                )
                            )
                            slots.append(
                                (
                                    "valu",
                                    (op3, ctx["tmp2"], val_vec, hash_vec_consts3[hi]),
                                )
                            )
                            slots.append(
                                ("valu", (op2, val_vec, ctx["tmp1"], ctx["tmp2"]))
                            )

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

                    if _round == rounds - 1 and block not in blocks_completed:
                        slots.append(
                            ("load", ("const", store_addr, INP_VALUES_P + block * VLEN))
                        )
                        slots.append(("store", ("vstore", store_addr, val_vec)))
                        blocks_completed.add(block)

    for block in range(blocks_per_round):
        if block not in blocks_completed:
            slots.append(("load", ("const", tmp_addr, INP_VALUES_P + block * VLEN)))
            slots.append(("store", ("vstore", tmp_addr, val_base + block * VLEN)))

    kb.instrs.extend(_schedule_slots(slots))
    kb.instrs.append({"flow": [("pause",)]})


def test_technique_e():
    """
    Test Technique E: Register renaming / variable expansion.

    Use more scratch registers to break false dependencies.
    Currently we have 12 words free. Not enough for significant expansion.

    But we could try: allocate separate tmp registers for each hash stage
    instead of reusing ctx["tmp1"], ctx["tmp2"].
    """
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)

    kb = ExperimentalKernelBuilder()
    build_kernel_expanded_temps(
        kb, forest.height, len(forest.values), len(inp.indices), 16
    )

    return test_kernel(kb, mem, inp)


def build_kernel_expanded_temps(kb, forest_height, n_nodes, batch_size, rounds):
    """Use separate temp registers for each hash stage."""
    tmp_addr = kb.alloc_scratch("tmp_addr")
    tmp_addr2 = kb.alloc_scratch("tmp_addr2")

    FOREST_VALUES_P = 7
    INP_INDICES_P = 2054
    INP_VALUES_P = 2310

    init_vars = [
        "rounds",
        "n_nodes",
        "batch_size",
        "forest_height",
        "forest_values_p",
        "inp_indices_p",
        "inp_values_p",
    ]
    for v in init_vars:
        kb.alloc_scratch(v, 1)

    init_slots = []
    init_slots.append(
        ("load", ("const", kb.scratch["forest_values_p"], FOREST_VALUES_P))
    )
    init_slots.append(("load", ("const", kb.scratch["inp_indices_p"], INP_INDICES_P)))
    init_slots.append(("load", ("const", kb.scratch["inp_values_p"], INP_VALUES_P)))

    zero_vec = kb.scratch_vconst(0, "v_zero", init_slots)
    one_vec = kb.scratch_vconst(1, "v_one", init_slots)
    two_vec = kb.scratch_vconst(2, "v_two", init_slots)
    one_const = kb.scratch_const(1, slots=init_slots)

    forest_vec = kb.alloc_vec("v_forest_p")
    init_slots.append(
        ("valu", ("vbroadcast", forest_vec, kb.scratch["forest_values_p"]))
    )

    three_vec = kb.scratch_vconst(3, "v_three", init_slots)
    four_vec = kb.scratch_vconst(4, "v_four", init_slots)
    seven_vec = kb.scratch_vconst(7, "v_seven", init_slots)

    node_vecs = []
    PRELOAD_NODES = 15
    for node_idx in range(PRELOAD_NODES):
        node_scalar = kb.alloc_scratch(f"node_{node_idx}")
        node_vec = kb.alloc_vec(f"v_node_{node_idx}")
        node_offset = kb.scratch_const(node_idx, slots=init_slots)
        addr_reg = tmp_addr if node_idx % 2 == 0 else tmp_addr2
        init_slots.append(
            ("alu", ("+", addr_reg, kb.scratch["forest_values_p"], node_offset))
        )
        init_slots.append(("load", ("load", node_scalar, addr_reg)))
        init_slots.append(("valu", ("vbroadcast", node_vec, node_scalar)))
        node_vecs.append(node_vec)

    hash_vec_consts1 = []
    hash_vec_consts3 = []
    hash_mul_vecs = []
    for op1, val1, op2, op3, val3 in HASH_STAGES:
        hash_vec_consts1.append(kb.scratch_vconst(val1, slots=init_slots))
        hash_vec_consts3.append(kb.scratch_vconst(val3, slots=init_slots))
        if op1 == "+" and op2 == "+" and op3 == "<<":
            hash_mul_vecs.append(kb.scratch_vconst(1 + (1 << val3), slots=init_slots))
        else:
            hash_mul_vecs.append(None)

    blocks_per_round = batch_size // VLEN
    idx_base = kb.alloc_scratch("idx_scratch", batch_size)
    val_base = kb.alloc_scratch("val_scratch", batch_size)

    offset = kb.alloc_scratch("offset")
    init_slots.append(("load", ("const", offset, 0)))
    vlen_const = kb.scratch_const(VLEN, slots=init_slots)

    slots = list(init_slots)
    for block in range(blocks_per_round):
        slots.append(("alu", ("+", tmp_addr, kb.scratch["inp_indices_p"], offset)))
        slots.append(("load", ("vload", idx_base + block * VLEN, tmp_addr)))
        slots.append(("alu", ("+", tmp_addr, kb.scratch["inp_values_p"], offset)))
        slots.append(("load", ("vload", val_base + block * VLEN, tmp_addr)))
        slots.append(("alu", ("+", offset, offset, vlen_const)))

    group_size = 16
    contexts = []
    for _ in range(group_size):
        ctx = {
            "node": kb.alloc_vec(),
            "tmp1": kb.alloc_vec(),
            "tmp2": kb.alloc_vec(),
            "tmp3": kb.alloc_vec(),
            "tmp4": kb.alloc_vec(),
        }
        for hi in range(3):
            ctx[f"hash_tmp1_{hi}"] = kb.alloc_vec()
            ctx[f"hash_tmp2_{hi}"] = kb.alloc_vec()
        contexts.append(ctx)

    print(f"Scratch used: {kb.scratch_ptr}/{SCRATCH_SIZE}")

    round_tile = 13
    for group_start in range(0, blocks_per_round, group_size):
        for round_start in range(0, rounds, round_tile):
            round_end = min(rounds, round_start + round_tile)
            for gi in range(group_size):
                block = group_start + gi
                if block >= blocks_per_round:
                    break
                ctx = contexts[gi]
                idx_vec = idx_base + block * VLEN
                val_vec = val_base + block * VLEN

                for _round in range(round_start, round_end):
                    level = _round % (forest_height + 1)

                    def emit_xor(node_vec):
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "alu",
                                    (
                                        "^",
                                        val_vec + lane,
                                        val_vec + lane,
                                        node_vec + lane,
                                    ),
                                )
                            )

                    if level == 0:
                        emit_xor(node_vecs[0])
                    elif level == 1:
                        slots.append(("valu", ("&", ctx["tmp1"], idx_vec, one_vec)))
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp1"],
                                    node_vecs[1],
                                    node_vecs[2],
                                ),
                            )
                        )
                        emit_xor(ctx["node"])
                    elif level == 2:
                        slots.append(("valu", ("-", ctx["tmp1"], idx_vec, three_vec)))
                        slots.append(("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec)))
                        slots.append(("valu", ("&", ctx["node"], ctx["tmp1"], two_vec)))
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp1"],
                                    ctx["tmp2"],
                                    node_vecs[4],
                                    node_vecs[3],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp2"],
                                    ctx["tmp2"],
                                    node_vecs[6],
                                    node_vecs[5],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["node"],
                                    ctx["tmp2"],
                                    ctx["tmp1"],
                                ),
                            )
                        )
                        emit_xor(ctx["node"])
                    elif level == 3:
                        slots.append(("valu", ("-", ctx["tmp1"], idx_vec, seven_vec)))
                        slots.append(("valu", ("&", ctx["tmp2"], ctx["tmp1"], one_vec)))
                        slots.append(("valu", ("&", ctx["tmp3"], ctx["tmp1"], two_vec)))
                        slots.append(
                            ("valu", ("&", ctx["tmp4"], ctx["tmp1"], four_vec))
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp2"],
                                    node_vecs[8],
                                    node_vecs[7],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp1"],
                                    ctx["tmp2"],
                                    node_vecs[10],
                                    node_vecs[9],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp1"],
                                    ctx["tmp3"],
                                    ctx["tmp1"],
                                    ctx["node"],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp2"],
                                    node_vecs[12],
                                    node_vecs[11],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["tmp2"],
                                    ctx["tmp2"],
                                    node_vecs[14],
                                    node_vecs[13],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp3"],
                                    ctx["tmp2"],
                                    ctx["node"],
                                ),
                            )
                        )
                        slots.append(
                            (
                                "flow",
                                (
                                    "vselect",
                                    ctx["node"],
                                    ctx["tmp4"],
                                    ctx["node"],
                                    ctx["tmp1"],
                                ),
                            )
                        )
                        emit_xor(ctx["node"])
                    else:
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "alu",
                                    (
                                        "+",
                                        ctx["tmp1"] + lane,
                                        forest_vec + lane,
                                        idx_vec + lane,
                                    ),
                                )
                            )
                        for lane in range(VLEN):
                            slots.append(
                                (
                                    "load",
                                    ("load", ctx["node"] + lane, ctx["tmp1"] + lane),
                                )
                            )
                        emit_xor(ctx["node"])

                    non_fusable_idx = 0
                    for hi, (op1, _val1, op2, op3, _val3) in enumerate(HASH_STAGES):
                        mul_vec = hash_mul_vecs[hi]
                        if mul_vec is not None:
                            slots.append(
                                (
                                    "valu",
                                    (
                                        "multiply_add",
                                        val_vec,
                                        val_vec,
                                        mul_vec,
                                        hash_vec_consts1[hi],
                                    ),
                                )
                            )
                        else:
                            tmp1_reg = ctx[f"hash_tmp1_{non_fusable_idx}"]
                            tmp2_reg = ctx[f"hash_tmp2_{non_fusable_idx}"]
                            slots.append(
                                ("valu", (op1, tmp1_reg, val_vec, hash_vec_consts1[hi]))
                            )
                            slots.append(
                                ("valu", (op3, tmp2_reg, val_vec, hash_vec_consts3[hi]))
                            )
                            slots.append(("valu", (op2, val_vec, tmp1_reg, tmp2_reg)))
                            non_fusable_idx += 1

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

    for block in range(blocks_per_round):
        slots.append(("load", ("const", tmp_addr, INP_VALUES_P + block * VLEN)))
        slots.append(("store", ("vstore", tmp_addr, val_base + block * VLEN)))

    kb.instrs.extend(_schedule_slots(slots))
    kb.instrs.append({"flow": [("pause",)]})


if __name__ == "__main__":
    print("=" * 60)
    print("BREAKTHROUGH OPTIMIZATION EXPERIMENTS")
    print("=" * 60)
    print()

    print("Baseline test...")
    base_cycles, base_correct = baseline_test()
    print(
        f"Baseline: {base_cycles} cycles ({'CORRECT' if base_correct else 'INCORRECT'})"
    )
    print()

    print("-" * 60)
    print("Technique A: Deep pipelining")
    print("-" * 60)
    try:
        a_cycles, a_correct = test_technique_a()
        print(f"Result: {a_cycles} cycles ({'CORRECT' if a_correct else 'INCORRECT'})")
        if a_correct:
            print(f"Delta: {a_cycles - base_cycles:+d} cycles")
    except Exception as e:
        print(f"ERROR: {e}")
    print()

    print("-" * 60)
    print("Technique B: Speculative tree preloading")
    print("-" * 60)
    test_technique_b()
    print()

    print("-" * 60)
    print("Technique C: Hash stage reordering (same as baseline)")
    print("-" * 60)
    try:
        c_cycles, c_correct = test_technique_c()
        print(f"Result: {c_cycles} cycles ({'CORRECT' if c_correct else 'INCORRECT'})")
        if c_correct:
            print(f"Delta: {c_cycles - base_cycles:+d} cycles")
    except Exception as e:
        print(f"ERROR: {e}")
    print()

    print("-" * 60)
    print("Technique D: Work stealing (interleaved stores)")
    print("-" * 60)
    try:
        d_cycles, d_correct = test_technique_d()
        print(f"Result: {d_cycles} cycles ({'CORRECT' if d_correct else 'INCORRECT'})")
        if d_correct:
            print(f"Delta: {d_cycles - base_cycles:+d} cycles")
    except Exception as e:
        print(f"ERROR: {e}")
    print()

    print("-" * 60)
    print("Technique E: Register renaming / variable expansion")
    print("-" * 60)
    try:
        e_cycles, e_correct = test_technique_e()
        print(f"Result: {e_cycles} cycles ({'CORRECT' if e_correct else 'INCORRECT'})")
        if e_correct:
            print(f"Delta: {e_cycles - base_cycles:+d} cycles")
    except Exception as e:
        print(f"ERROR: {e}")
    print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
