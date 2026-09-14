#!/usr/bin/env python3
"""Failure-sensitive checks for the discovered compiler's repair boundary."""

from copy import deepcopy
import json
from pathlib import Path
import random
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "tests")]
import kernel_compiler as compiler
import kernel_retime as retime
from kernel_optimizer import Discovery, MAX_EVALUATIONS, Plan, analyze
from frozen_problem import Tree, Input
from perf_takehome import KernelBuilder
from verify_retry import check_output


def rejected(call, text):
    try:
        call()
    except AssertionError as error:
        assert text in str(error), error
    else:
        raise AssertionError("Mutation accepted: " + text)


def main():
    compiled = compiler.compile_benchmark()
    ir, logical, addresses, scratch = compiler._analyze_compiled(compiled)
    model = retime.capture(ir, logical)
    times = [j["time"] for j in model["jobs"]]
    program, words, _, _ = retime.lower(ir, model, times)
    assert program == compiled.materialize() and words == scratch
    for _ in range(2):
        again = retime.lower(ir, model, times)
        assert again[:2] == (program, words)
    bad = deepcopy(model)
    bad["jobs"].append(deepcopy(bad["jobs"][0]))
    rejected(lambda: retime.validate(bad, times + [times[0]]), "duplicate written lane")
    bad = deepcopy(model)
    bad["edges"].pop()
    rejected(lambda: retime.validate(bad, times), "missing or spurious data dependency")
    a, b, lag = next(e for e in model["edges"] if e[2] == 1)
    bad_times = times[:]
    bad_times[b] = bad_times[a]
    rejected(lambda: retime.validate(model, bad_times), "dependency timing")
    for oversized in (1537, 1545):
        with (
            patch.object(compiler, "_allocate", return_value=(addresses, oversized)),
            patch.object(
                compiler, "_lower", side_effect=AssertionError("forbidden lowering")
            ) as lower,
        ):
            output, size, _, _ = retime.lower(ir, model, times)
            assert output is None and size == oversized
            lower.assert_not_called()
    # A real, unmodified over-scratch graph must be rejected before lowering too.
    all_sites = tuple((b, r) for b in range(32) for r in (4, 15))
    _, _, _, rejected_words = compiler._analyze_sites(all_sites)
    assert rejected_words > 1536
    with patch.object(
        compiler, "_lower", side_effect=AssertionError("forbidden lowering")
    ) as lower:
        try:
            compiler._compile_sites(all_sites)
        except ValueError as error:
            assert error.args[0][0] == "Scratch limit exceeded"
        else:
            raise AssertionError("Oversized graph accepted")
        lower.assert_not_called()
    discovery = Discovery()
    discovery.seed_evaluations = MAX_EVALUATIONS
    with patch(
        "kernel_optimizer.analyze", side_effect=AssertionError("unreserved evaluation")
    ):
        try:
            discovery.evaluate(Plan(()))
        except RuntimeError as error:
            assert "budget exhausted" in str(error)
        else:
            raise AssertionError("Evaluation budget bypassed")
    pairs, final_blocks, selector_sites = compiled.parameters
    cost, (native_ir, native_logical, native_addresses) = analyze(
        Plan(compiled.cache_sites, pairs, final_blocks, selector_sites)
    )
    assert cost.feasible and cost.cycles == 981
    kernel = KernelBuilder()
    kernel.instrs = compiler._lower(native_ir, native_logical, native_addresses)
    kernel.scratch_ptr = cost.scratch
    rng = random.Random(612)
    tree = Tree(10, [rng.getrandbits(32) for _ in range(2047)])
    inp = Input([0] * 256, [rng.getrandbits(32) for _ in range(256)], 16)
    assert check_output(kernel, tree, inp) == 981 > 980
    print(
        json.dumps(
            {
                "fresh_allocations": 3,
                "duplicate_lane_rejected": True,
                "missing_dependency_rejected": True,
                "dependency_timing_rejected": True,
                "injected_scratch_rejected": [1537, 1545],
                "natural_scratch_rejected": rejected_words,
                "overscratch_lower_calls": 0,
                "budget_rejected_before_evaluation": True,
                "executed_native_control": 981,
                "cycles": compiled.cycles,
                "scratch": scratch,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
