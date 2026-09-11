#!/usr/bin/env python3
"""Verify the promoted compiler through KernelBuilder and the frozen machine.

No tests/simulator edits or temporary prototype imports. Cold subprocesses also
check source-only operation, deterministic selection and bounded host build cost.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "scripts")]

from frozen_problem import Input, SCRATCH_SIZE, SLOT_LIMITS, Tree  # noqa: E402
from kernel_compiler import _analyze_sites, _compile_baseline, _lower  # noqa: E402
from perf_takehome import KernelBuilder  # noqa: E402
from verify_retry import check_output  # noqa: E402

MAX_CYCLES = 1052
MAX_EVALUATIONS = 1049


def performance_gate(kernel, tree, inp, *, pause=False):
    cycles = check_output(kernel, tree, inp, pause=pause)
    assert cycles <= MAX_CYCLES, (cycles, MAX_CYCLES)
    return cycles


def lane_identity(ir, logical, addresses):
    """Independent lane-owner simulation; reads occur before cycle-end writes."""
    owner = {}
    for cycle, bundle in enumerate(logical):
        usage, writes = Counter(), {}
        for i, engine, first, count in bundle:
            op = ir.ops[i]
            usage[engine] += count
            partial = op.kind == "gather" or (op.kind == "binary" and engine == "alu")
            reads = []
            if partial:
                for value, offset in op.args:
                    reads.extend(
                        (value, offset + lane) for lane in range(first, first + count)
                    )
            elif not (op.kind == "const_choice" and engine == "load"):
                sizes = (
                    [1, 8]
                    if op.kind == "vstore"
                    else [1]
                    if op.kind in ("vload", "broadcast", "const_choice")
                    else [8] * len(op.args)
                )
                for (value, offset), width in zip(op.args, sizes):
                    reads.extend((value, offset + lane) for lane in range(width))
            for value, lane in reads:
                address = addresses[value] + lane
                assert 0 <= address < SCRATCH_SIZE
                assert owner.get(address) == (value, lane), (
                    "lane identity",
                    cycle,
                    i,
                    address,
                )
            if op.dst is not None:
                lanes = (
                    range(first, first + count) if partial else range(ir.widths[op.dst])
                )
                for lane in lanes:
                    address = addresses[op.dst] + lane
                    assert 0 <= address < SCRATCH_SIZE
                    assert address not in writes, ("duplicate write", cycle, address)
                    writes[address] = (op.dst, lane)
        assert all(n <= SLOT_LIMITS[engine] for engine, n in usage.items())
        owner.update(writes)


def digest(instructions):
    return hashlib.sha256(json.dumps(instructions).encode()).hexdigest()


def cold_builds(expected):
    code = """
import hashlib,json,resource,time
import perf_takehome,problem
from kernel_compiler import compile_benchmark

def forbidden(*args, **kwargs):
    raise AssertionError('Compiler attempted runtime-data/oracle access')
problem.Machine.__init__ = forbidden
problem.Tree.generate = forbidden
problem.Input.generate = forbidden
for module in (problem, perf_takehome):
    for name in ('reference_kernel', 'reference_kernel2', 'build_mem_image'):
        setattr(module, name, forbidden)
assert compile_benchmark.cache_info().currsize == 0
start=time.monotonic()
k=perf_takehome.KernelBuilder();k.build_kernel(10,2047,256,16)
print(json.dumps({'seconds':time.monotonic()-start,
    'cycles':len(k.instrs),'scratch':k.scratch_ptr,
    'evaluations':k.compile_info['evaluations'],
    'digest':hashlib.sha256(json.dumps(k.instrs).encode()).hexdigest(),
    'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
"""
    rows = []
    # The isolated build has only production source files, no tests, configs,
    # saved programs, project scripts or access through the parent's PYTHONPATH.
    with tempfile.TemporaryDirectory(prefix="kernel-source-only-") as directory:
        for name in (
            "perf_takehome.py",
            "kernel_compiler.py",
            "kernel_lookahead.py",
            "problem.py",
        ):
            shutil.copy2(ROOT / name, Path(directory) / name)
        for seed, cwd in (("0", ROOT), ("17", Path(directory))):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=180,
            )
            row = json.loads(result.stdout)
            assert row["digest"] == expected, row
            assert row["cycles"] <= MAX_CYCLES and row["scratch"] <= SCRATCH_SIZE
            assert row["evaluations"] <= MAX_EVALUATIONS
            row["source_only"] = cwd != ROOT
            rows.append(row)
    return rows


def main():
    started = time.monotonic()
    kernel = KernelBuilder()
    kernel.build_kernel(10, 2047, 256, 16)
    cold_seconds = time.monotonic() - started
    assert kernel.compile_info["path"] == "ssa"
    assert len(kernel.instrs) <= MAX_CYCLES and kernel.scratch_ptr <= SCRATCH_SIZE
    assert kernel.compile_info["evaluations"] <= MAX_EVALUATIONS
    ir, logical, addresses, scratch = _analyze_sites(kernel.compile_info["cache_sites"])
    assert (
        scratch == kernel.scratch_ptr
        and _lower(ir, logical, addresses) == kernel.instrs
    )
    lane_identity(ir, logical, addresses)

    for seed in range(100):
        rng = random.Random(seed)
        tree = Tree(10, [rng.getrandbits(32) for _ in range(2047)])
        inp = Input([0] * 256, [rng.getrandbits(32) for _ in range(256)], 16)
        performance_gate(kernel, tree, inp, pause=seed == 0)
    # Preserve exact fallback behavior for non-default compiler tuning knobs.
    for override in ({"group_size": 16}, {"round_tile": 8}, {"selection_banks": 2}):
        other = KernelBuilder()
        other.build_kernel(10, 2047, 256, 16, **override)
        assert other.compile_info["path"] == "legacy"
        check_output(other, tree, inp)
    legacy = KernelBuilder()
    legacy._build_legacy_kernel(10, 2047, 256, 16)
    assert check_output(legacy, tree, inp) == 1082
    baseline = _compile_baseline()
    prior = KernelBuilder()
    prior.instrs, prior.scratch_ptr = baseline.materialize(), baseline.scratch_size
    assert (baseline.cycles, baseline.scratch_size) == (1076, 1236)
    assert (
        digest(prior.instrs)
        == "a1cedda0acceb4eada28ae1b14aad2898e768370e2028ca5febe9f3ea377ddbe"
    )
    for control, expected_cycles in ((legacy, 1082), (prior, 1076)):
        try:
            performance_gate(control, tree, inp)
        except AssertionError as error:
            assert error.args == ((expected_cycles, MAX_CYCLES),), error
        else:
            raise AssertionError("performance check accepted the incumbent")

    broken = deepcopy(logical)
    cycle, j, entry = next(
        (c, j, entry)
        for c, b in enumerate(broken)
        for j, entry in enumerate(b)
        if ir.ops[entry[0]].kind == "vload"
    )
    broken[cycle].pop(j)
    broken[0].append(entry)
    try:
        lane_identity(ir, broken, addresses)
    except AssertionError as error:
        assert error.args[0][0] == "lane identity", error
    else:
        raise AssertionError("lane checker accepted dependency corruption")

    mutant = deepcopy(kernel)
    slot_cycle = next(
        c
        for c, b in enumerate(logical)
        for i, e, _, _ in b
        if ir.ops[i].kind == "const_choice"
        and e == "flow"
        and ir.ops[i].code == 0xFFFFFFFE
    )
    slot = mutant.instrs[slot_cycle]["flow"][0]
    assert slot[0] == "add_imm"
    # Change the early-address multiplier from -2 to 0. Unlike a random bit
    # flip, this keeps the address in memory and must fail the value oracle.
    mutant.instrs[slot_cycle]["flow"][0] = slot[:-1] + (slot[-1] + 2,)
    try:
        check_output(mutant, tree, inp)
    except AssertionError as error:
        assert str(error) == "Incorrect output values", error
    else:
        raise AssertionError("frozen oracle accepted a corrupted flow constant")

    mutant = deepcopy(kernel)
    slot_cycle, slot_index, slot = next(
        (c, j, slot)
        for c, bundle in enumerate(mutant.instrs)
        for j, slot in enumerate(bundle.get("flow", []))
        if slot[0] == "vselect"
    )
    mutant.instrs[slot_cycle]["flow"][slot_index] = slot[:3] + (slot[4], slot[3])
    try:
        check_output(mutant, tree, inp)
    except AssertionError as error:
        assert str(error) == "Incorrect output values", error
    else:
        raise AssertionError("frozen oracle accepted swapped selector branches")

    expected = digest(kernel.instrs)
    started = time.monotonic()
    other = KernelBuilder()
    other.build_kernel(10, 2047, 256, 16)
    warm_seconds = time.monotonic() - started
    other.instrs[0]["load"][0] = ("const", 0, 0)
    third = KernelBuilder()
    third.build_kernel(10, 2047, 256, 16)
    assert digest(third.instrs) == expected and digest(kernel.instrs) == expected
    assert other.instrs[0] is not third.instrs[0]
    assert other.instrs[0]["load"] is not third.instrs[0]["load"]
    rows = cold_builds(expected)
    print(
        json.dumps(
            {
                "cycles": len(kernel.instrs),
                "scratch": scratch,
                "cache_sites": kernel.compile_info["cache_sites"],
                "search_evaluations": kernel.compile_info["evaluations"],
                "cold_seconds": cold_seconds,
                "warm_seconds": warm_seconds,
                "fresh_processes": rows,
                "full_width_inputs": 100,
                "explicit_override_fallbacks": 3,
                "legacy_cycles": 1082,
                "previous_production_cycles": baseline.cycles,
                "executed_controls_rejected": [1082, 1076],
                "digest": expected,
                "lane_identity": True,
                "dependency_mutation_rejected": True,
                "flow_constant_mutation_rejected": True,
                "selector_mutation_rejected": True,
                "cached_program_isolation": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
