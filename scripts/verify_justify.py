#!/usr/bin/env python3
"""Small executable and failure-sensitive checks; no benchmark discovery."""

from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import kernel_compiler as compiler
import kernel_refinement as refinement
import kernel_retime as retime
from kernel_justify import schedule
from kernel_optimizer import Discovery, MAX_EVALUATIONS, Plan
from frozen_problem import Machine, DebugInfo


def main():
    ir = compiler._IR()
    a, b = ir.const(0), ir.const(7)
    c = ir.emit("broadcast", args=(b,))
    d = ir.binary("+", a, c, preferred="alu", width=1)
    v = ir.emit("broadcast", args=(d,))
    ir.emit("vstore", args=(a, v), width=0)
    logical = [
        [(i, e, 0, 1)]
        for i, e in enumerate(("load", "load", "valu", "alu", "valu", "store"))
    ]
    model = retime.capture(ir, logical)
    original = [j["time"] for j in model["jobs"]]
    for tie in ("native", "tail", "startup"):
        times = schedule(model, tie=tie, caps=dict(retime.CAP, load=1))
        assert max(times) + 1 == 5 and times[0] > original[0]
        program, words, _, _ = retime.lower(ir, model, times)
        assert program is not None and words <= 1536
        machine = Machine([0] * 8, program, DebugInfo({}), n_cores=1)
        machine.run()
        assert machine.mem == [7] * 8 and machine.cycle == 5
    native, _, _, _ = retime.lower(ir, model, original)
    machine = Machine([0] * 8, native, DebugInfo({}), n_cores=1)
    machine.run()
    assert machine.mem == [7] * 8 and machine.cycle == 6
    bad = deepcopy(model)
    bad["edges"].pop()
    try:
        schedule(bad)
    except AssertionError as e:
        assert str(e) == "missing or spurious data dependency"
    else:
        raise AssertionError("Missing edge accepted")
    discovery = Discovery()
    discovery.seed_evaluations = MAX_EVALUATIONS
    with patch.object(
        refinement, "analyze", side_effect=AssertionError("unreserved construction")
    ) as analyze:
        try:
            refinement.justify_finals(discovery, Plan(()))
        except RuntimeError as error:
            assert "budget exhausted" in str(error)
        else:
            raise AssertionError("Budget bypass")
        analyze.assert_not_called()
    discovery = Discovery()
    discovery.reserve_schedule(Plan(()), "native")
    try:
        discovery.reserve_schedule(Plan(()), "native")
    except RuntimeError as error:
        assert str(error) == "Duplicate schedule reservation"
    else:
        raise AssertionError("Duplicate reservation accepted")
    assert discovery.evaluations == 1
    with patch.object(refinement, "candidates", return_value=[]):
        try:
            refinement.finish(discovery, None)
        except RuntimeError as error:
            assert str(error) == "No feasible refinement frontier"
        else:
            raise AssertionError("Empty frontier accepted")
    print(
        json.dumps(
            {
                "toy_before": 6,
                "toy_after": 5,
                "tie_orders": 3,
                "moved_later": True,
                "executions": 4,
                "missing_edge_rejected": True,
                "budget_before_construction": True,
                "duplicate_reservation_rejected": True,
                "empty_frontier_rejected": True,
            }
        )
    )


if __name__ == "__main__":
    main()
