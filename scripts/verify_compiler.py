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

from frozen_problem import HASH_STAGES, Input, SCRATCH_SIZE, SLOT_LIMITS, Tree  # noqa: E402
from kernel_compiler import (  # noqa: E402
    _analyze_compiled,
    _compile_seed,
    _compile_baseline,
    _compile_sites,
    _lower,
    compile_benchmark,
)
from perf_takehome import KernelBuilder  # noqa: E402
from verify_retry import check_output  # noqa: E402

MAX_CYCLES = 975
MAX_EVALUATIONS = 4096


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
import perf_takehome,problem,kernel_retime
from kernel_compiler import compile_benchmark

def forbidden(*args, **kwargs):
    raise AssertionError('Compiler attempted runtime-data/oracle access')
problem.Machine.__init__ = forbidden
problem.Tree.generate = forbidden
problem.Input.generate = forbidden
for module in (problem, perf_takehome):
    for name in ('reference_kernel', 'reference_kernel2', 'build_mem_image'):
        setattr(module, name, forbidden)
for name in ('solve', 'repair', '_worker'):
    setattr(kernel_retime, name, forbidden)
assert compile_benchmark.cache_info().currsize == 0
start=time.monotonic()
k=perf_takehome.KernelBuilder();k.build_kernel(10,2047,256,16)
print(json.dumps({'seconds':time.monotonic()-start,
    'cycles':len(k.instrs),'scratch':k.scratch_ptr,
    'evaluations':k.compile_info['evaluations'],
    'solver_queries':compile_benchmark().solver_queries,
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
            "kernel_optimizer.py",
            "kernel_refinement.py",
            "kernel_justify.py",
            "kernel_retime.py",
            "kernel_checks.py",
            "problem.py",
        ):
            shutil.copy2(ROOT / name, Path(directory) / name)
        for seed, cwd in (("0", Path(directory)), ("17", Path(directory))):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            row = json.loads(result.stdout)
            assert row["digest"] == expected, row
            assert row["cycles"] <= MAX_CYCLES and row["scratch"] <= SCRATCH_SIZE
            assert row["evaluations"] <= MAX_EVALUATIONS and row["solver_queries"] == 0
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
    ir, logical, addresses, scratch = _analyze_compiled(compile_benchmark())
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
    previous = compile_benchmark(startup=False)
    previous_kernel = KernelBuilder()
    previous_kernel.instrs = previous.materialize()
    previous_kernel.scratch_ptr = previous.scratch_size
    assert (previous.cycles, previous.scratch_size) == (1052, 1457)
    assert (
        digest(previous_kernel.instrs)
        == "ca588b18f9790385cc509caf5bc5c57b85bff1ab01029766195a48cdd07b4a76"
    )
    prototype = _compile_sites(previous.cache_sites)
    prototype_kernel = KernelBuilder()
    prototype_kernel.instrs = prototype.materialize()
    prototype_kernel.scratch_ptr = prototype.scratch_size
    assert (prototype.cycles, prototype.scratch_size) == (1042, 1459)
    assert (
        digest(prototype_kernel.instrs)
        == "af7f9144e670c98df1f23356683481145199dddaf2bc2f3ee2db8353eca88993"
    )
    startup_control = _compile_seed()
    startup_kernel = KernelBuilder()
    startup_kernel.instrs = startup_control.materialize()
    startup_kernel.scratch_ptr = startup_control.scratch_size
    assert startup_control.cycles == 1041
    for control, expected_cycles in (
        (startup_kernel, 1041),
        (legacy, 1082),
        (prior, 1076),
        (previous_kernel, 1052),
        (prototype_kernel, 1042),
    ):
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
        and ir.ops[i].code in {stage[1] for stage in HASH_STAGES}
    )
    slot = mutant.instrs[slot_cycle]["flow"][0]
    assert slot[0] == "add_imm"
    # Select a hash constant actually assigned to flow, not an address constant
    # whose engine can change when caches or startup priorities change.
    mutant.instrs[slot_cycle]["flow"][0] = slot[:-1] + (slot[-1] ^ 2,)
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
                "previous_production_cycles": previous.cycles,
                "startup_prototype_cycles": prototype.cycles,
                "executed_controls_rejected": [1082, 1076, 1052, 1042, 1041],
                "solver_queries": compile_benchmark().solver_queries,
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
