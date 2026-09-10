#!/usr/bin/env python3
"""Supplementary differential checks; the unchanged submission suite is authoritative.

Run from any directory: python scripts/verify_retry.py
No tests or simulator files are modified. All computation under test executes
on tests/frozen_problem.py's Machine; expected values use its reference kernel.
"""

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from frozen_problem import (  # noqa: E402 - local module path bootstrap above
    CoreState,
    DebugInfo,
    Input,
    Machine,
    N_CORES,
    SCRATCH_SIZE,
    SLOT_LIMITS,
    Tree,
    build_mem_image,
    reference_kernel2,
)
from perf_takehome import KernelBuilder, _schedule_slots  # noqa: E402


def check_output(kernel, tree, inp, *, pause=False):
    memory = build_mem_image(tree, inp)
    output = memory[6]
    machine = Machine(memory, kernel.instrs, kernel.debug_info(), n_cores=N_CORES)
    machine.enable_pause = pause
    machine.enable_debug = False
    machine.run()
    for expected in reference_kernel2(memory.copy()):
        pass
    count = len(inp.values)
    assert machine.mem[output : output + count] == expected[output : output + count], (
        "Incorrect output values"
    )
    assert machine.mem[:output] == memory[:output], "Modified non-output memory"
    return machine.cycle


def check_scheduler():
    # A read must see the old value when its subsequent overwrite shares a cycle.
    slots = [
        ("load", ("const", 0, 9)),
        ("load", ("const", 1, 1)),
        ("alu", ("+", 2, 0, 1)),
        ("load", ("const", 0, 20)),
        ("alu", ("+", 3, 2, 0)),
    ]
    machine = Machine([], _schedule_slots(slots), DebugInfo({}))
    machine.run()
    assert machine.cores[0].scratch[2:4] == [10, 30]

    # load_offset reads/writes base + lane, not base. Check both dependency sides.
    slots = [
        ("load", ("const", 0, 0)),
        ("load", ("const", 1, 1)),
        ("load", ("load_offset", 4, 0, 1)),
        ("load", ("const", 1, 0)),
        ("alu", ("+", 6, 5, 0)),
    ]
    machine = Machine([41, 99], _schedule_slots(slots), DebugInfo({}))
    machine.run()
    assert machine.cores[0].scratch[5:7] == [99, 99]

    # A co-issued store must commit even when flow is visited first and pauses.
    for engines in [("flow", "store"), ("store", "flow")]:
        slots = {"flow": [("pause",)], "store": [("store", 0, 1)]}
        program = [
            {"load": [("const", 0, 0), ("const", 1, 41)]},
            {engine: slots[engine] for engine in engines},
        ]
        machine = Machine([0], program, DebugInfo({}))
        machine.run()
        assert machine.mem == [41] and machine.cycle == 2
        assert machine.cores[0].state == CoreState.PAUSED
        machine.run()
        assert machine.cores[0].state == CoreState.STOPPED and machine.cycle == 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--max-cycles", type=int, default=1113)
    args = parser.parse_args()
    assert args.seeds > 0

    kernel = KernelBuilder()
    kernel.build_kernel(10, 2047, 256, 16)
    assert kernel.scratch_ptr <= SCRATCH_SIZE
    for seed in range(args.seeds):
        random.seed(seed)
        tree = Tree.generate(10)
        inp = Input.generate(tree, 256, 16)
        cycles = check_output(kernel, tree, inp)
        assert cycles <= args.max_cycles, (cycles, args.max_cycles)
        if seed == 0:
            assert check_output(kernel, tree, inp, pause=True) == cycles

    # Full 32-bit and asymmetric patterns exercise more than the 30-bit generator.
    patterns = [
        lambda i: 0,
        lambda i: 0xFFFFFFFF,
        lambda i: 0xAAAAAAAA if i % 2 else 0x55555555,
        lambda i: 1 << (i % 32),
        lambda i: (i * 0x9E3779B9) & 0xFFFFFFFF,
    ]
    for index, pattern in enumerate(patterns):
        tree = Tree(10, [pattern(i) for i in range(2047)])
        values = [patterns[(index + 1) % len(patterns)](i) for i in range(256)]
        check_output(kernel, tree, Input([0] * 256, values, 16))

    # Root starts, shallow/deep wraparound, zero rounds, and smaller vector batches.
    shapes = [
        (3, 0, 8),
        (3, 1, 8),
        (3, 4, 32),
        (3, 9, 64),
        (4, 5, 32),
        (4, 12, 128),
        (10, 11, 256),
        (10, 22, 256),
    ]
    for height, rounds, batch in shapes:
        random.seed(1000 + height + rounds + batch)
        tree = Tree.generate(height)
        inp = Input.generate(tree, batch, rounds)
        other = KernelBuilder()
        other.build_kernel(height, len(tree.values), batch, rounds)
        check_output(other, tree, inp)

    check_scheduler()

    # Negative control: corrupt one emitted constant, not the oracle or simulator.
    mutant = deepcopy(kernel)
    changed = False
    for bundle in mutant.instrs:
        for i, slot in enumerate(bundle.get("load", [])):
            if slot[0] == "const" and slot[2] == 0xB55A4F09:
                bundle["load"][i] = ("const", slot[1], slot[2] ^ 2)
                changed = True
                break
        if changed:
            break
    assert changed, "Negative control did not find the encoding constant"
    random.seed(12345)
    tree = Tree.generate(10)
    inp = Input.generate(tree, 256, 16)
    try:
        check_output(mutant, tree, inp)
    except AssertionError as error:
        assert str(error) == "Incorrect output values", error
    else:
        raise AssertionError("Negative control accepted a corrupted kernel")

    counts = Counter()
    for bundle in kernel.instrs:
        for engine, slots in bundle.items():
            counts[engine] += len(slots)
    bounds = {
        engine: (count + SLOT_LIMITS[engine] - 1) // SLOT_LIMITS[engine]
        for engine, count in counts.items()
    }
    print(
        f"PASS: {args.seeds} random inputs, {len(patterns)} bit patterns, {len(shapes)} other shapes"
    )
    print("PASS: scheduler hazards; co-issued pause/store; corrupted kernel rejected")
    print(f"Cycles: {cycles}; scratch: {kernel.scratch_ptr}/{SCRATCH_SIZE}")
    print(f"Engine operations: {dict(counts)}")
    print(f"Capacity-only lower bounds for this instruction stream: {bounds}")


if __name__ == "__main__":
    main()
