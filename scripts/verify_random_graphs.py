#!/usr/bin/env python3
"""Random IR graphs through every schedule, allocation and retiming path.

An independent interpreter of the logical IR predicts final memory. The frozen
simulator must agree for native and lookahead schedules and for all three
justification orders. Runs in seconds; no benchmark discovery.
"""

import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import kernel_compiler as compiler
import kernel_retime as retime
from kernel_checks import lane_identity
from kernel_justify import schedule
from frozen_problem import DebugInfo, Machine, SCRATCH_SIZE, VLEN

MASK = 0xFFFFFFFF
MEMORY_WORDS = 512
INPUT_BASE, OUTPUT_BASE = 64, 256


def random_ir(rng, n_ops):
    ir = compiler._IR()
    scalars, vectors = [], []
    for k in range(rng.randint(1, 4)):
        vectors.append(ir.emit("vload", args=(ir.const(INPUT_BASE + 8 * k),)))
    for _ in range(rng.randint(1, 4)):
        scalars.append(
            ir.const(
                rng.choice([1, 2, 3, 7, 15, 33, 4097, 0xB55A4F09, rng.getrandbits(32)])
            )
        )
    while len(ir.ops) < n_ops:
        kind = rng.choice(
            [
                "binary",
                "binary",
                "muladd",
                "select",
                "broadcast",
                "sbinary",
                "gather",
                "lane",
            ]
        )
        if kind == "broadcast":
            vectors.append(ir.emit("broadcast", args=(rng.choice(scalars),)))
        elif kind == "sbinary" and len(scalars) >= 2:
            a, b = rng.choice(scalars), rng.choice(scalars)
            scalars.append(ir.binary(rng.choice("^&-"), a, b, preferred="alu", width=1))
        elif kind == "lane":
            lane = (rng.choice(vectors)[0], rng.randrange(VLEN))
            scalars.append(
                ir.binary("^", lane, rng.choice(scalars), preferred="alu", width=1)
            )
        elif kind == "binary":
            code = rng.choice(["^", "&", "-", ">>"])
            a, b = rng.choice(vectors), rng.choice(vectors)
            if code == ">>":
                b = ir.vc(rng.choice([1, 3, 5, 9, 12, 16, 19]))
            vectors.append(ir.binary(code, a, b, preferred=rng.choice(["alu", "valu"])))
        elif kind == "muladd":
            args = tuple(rng.choice(vectors) for _ in range(3))
            vectors.append(ir.emit("muladd", args=args))
        elif kind == "select":
            cond = ir.binary("&", rng.choice(vectors), ir.vc(1), preferred="alu")
            vectors.append(cond)
            args = (cond, rng.choice(vectors), rng.choice(vectors))
            vectors.append(ir.emit("select", args=args))
        elif kind == "gather":
            low = ir.binary("&", rng.choice(vectors), ir.vc(31), preferred="alu")
            address = ir.emit("muladd", args=(low, ir.vc(1), ir.vc(INPUT_BASE)))
            vectors.extend([low, address, ir.emit("gather", args=(address,))])
    for k, v in enumerate(rng.sample(vectors, rng.randint(1, min(4, len(vectors))))):
        ir.emit("vstore", args=(ir.const(OUTPUT_BASE + 8 * k), v), width=0)
        ir.ops[-1].block = k
    return ir


def reference(ir, memory):
    values, stores = {}, []
    memory = list(memory)

    def lanes(ref, width):
        value, offset = ref
        return values[value][offset : offset + width]

    binary = {
        "^": lambda a, b: a ^ b,
        "&": lambda a, b: a & b,
        "-": lambda a, b: a - b,
        ">>": lambda a, b: a >> b,
    }
    for op in ir.ops:
        if op.kind == "const":
            values[op.dst] = [op.imm & MASK]
        elif op.kind == "vload":
            (pointer,) = lanes(op.args[0], 1)
            values[op.dst] = memory[pointer : pointer + VLEN]
        elif op.kind == "gather":
            values[op.dst] = [memory[a] for a in lanes(op.args[0], VLEN)]
        elif op.kind == "broadcast":
            values[op.dst] = lanes(op.args[0], 1) * VLEN
        elif op.kind == "binary":
            width = ir.widths[op.dst]
            pairs = zip(lanes(op.args[0], width), lanes(op.args[1], width))
            values[op.dst] = [binary[op.code](a, b) & MASK for a, b in pairs]
        elif op.kind == "muladd":
            a, b, c = (lanes(ref, VLEN) for ref in op.args)
            values[op.dst] = [(x * y + z) & MASK for x, y, z in zip(a, b, c)]
        elif op.kind == "select":
            c, a, b = (lanes(ref, VLEN) for ref in op.args)
            values[op.dst] = [x if k else y for k, x, y in zip(c, a, b)]
        elif op.kind == "vstore":
            (pointer,) = lanes(op.args[0], 1)
            stores.append((pointer, lanes(op.args[1], VLEN)))
        else:
            raise AssertionError(op)
    for pointer, vector in stores:
        memory[pointer : pointer + VLEN] = vector
    return memory


def run(program, memory):
    machine = Machine(list(memory), program, DebugInfo({}), n_cores=1)
    machine.run()
    assert machine.cycle == len(program)
    return machine.mem


def main(graphs=300):
    counts = {
        "graphs": graphs,
        "programs": 0,
        "retimed_shorter": 0,
        "startup_longer": 0,
    }
    for seed in range(graphs):
        rng = random.Random(seed)
        ir = random_ir(rng, rng.randint(12, 60))
        memory = [rng.getrandbits(32) for _ in range(MEMORY_WORDS)]
        expected = reference(ir, memory)
        for lookahead in (False, True):
            logical, starts, ends = compiler._schedule(ir, lookahead=lookahead)
            addresses, scratch = compiler._allocate(ir, starts, ends)
            assert scratch <= SCRATCH_SIZE, seed
            lane_identity(ir, logical, addresses)
            program = compiler._lower(ir, logical, addresses)
            assert run(program, memory) == expected, (seed, lookahead)
            model = retime.capture(ir, logical)
            for tie in ("native", "tail", "startup"):
                times = schedule(model, tie=tie)
                retimed, _, _, _ = retime.lower(ir, model, times)
                assert retimed is not None, (seed, lookahead, tie)
                assert run(retimed, memory) == expected, (seed, lookahead, tie)
                if tie == "startup":
                    counts["startup_longer"] += len(retimed) > len(program)
                else:
                    assert len(retimed) <= len(program), (seed, lookahead, tie)
                    counts["retimed_shorter"] += len(retimed) < len(program)
            counts["programs"] += 4
    assert counts["startup_longer"], "No graph exercised a lengthening startup order"
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
