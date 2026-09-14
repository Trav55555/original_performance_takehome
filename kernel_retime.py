"""Allocation-free native-mode suffix repair with a memory-capped Z3 child.

These SSA/domain/projection checks were exercised by the verified exact pilot.
Models are constructed from the current IR, never from persisted programs.
"""

from collections import Counter, defaultdict
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from problem import SLOT_LIMITS, SCRATCH_SIZE

CAP = {e: SLOT_LIMITS[e] for e in ("alu", "valu", "load", "store", "flow")}


def refs(ir, op, e, f):
    if op.kind in ("binary", "gather"):
        lanes = [f] if e == "alu" or op.kind == "gather" else range(ir.widths[op.dst])
        return [(v, o + l) for v, o in op.args for l in lanes]
    sizes = (
        [1, 8]
        if op.kind == "vstore"
        else [1]
        if op.kind in ("vload", "broadcast", "const_choice")
        else [8] * len(op.args)
    )
    if op.kind == "const_choice" and e == "load":
        return []
    return [(v, o + l) for (v, o), w in zip(op.args, sizes) for l in range(w)]


def assert_graph(m):
    if "ops" not in m:
        return
    producers = {}
    for i, n in enumerate(m["jobs"]):
        for r in n["writes"]:
            r = tuple(r)
            assert r not in producers, "duplicate written lane"
            producers[r] = i
    expected_lanes = {
        (op["dst"], l)
        for op in m["ops"]
        if op["dst"] is not None
        for l in range(m["widths"][op["dst"]])
    }
    assert set(producers) == expected_lanes, "lane coverage"
    expected = {
        (producers[tuple(r)], j, 1) for j, n in enumerate(m["jobs"]) for r in n["reads"]
    }
    assert expected == set(map(tuple, m["edges"])), (
        "missing or spurious data dependency"
    )


def validate(m, times, lo=None, hi=None):
    assert_graph(m)
    assert len(times) == len(m["jobs"]) and all(
        type(t) is int and t >= 0 for t in times
    )
    if lo is not None:
        assert all(a <= t <= b for a, t, b in zip(lo, times, hi))
    assert all(times[b] >= times[a] + d for a, b, d in m["edges"]), "dependency timing"
    use = Counter((t, n["engine"]) for t, n in zip(times, m["jobs"]))
    assert all(n <= CAP[e] for (t, e), n in use.items()), "capacity"
    pauses = [t for t, j in zip(times, m["jobs"]) if j["pause"]]
    if pauses:
        assert len(pauses) == 1 and pauses[0] == max(times), "pause before completion"


def bounds(m, start, target, radius=8):
    assert_graph(m)
    jobs = m["jobs"]
    lo = [
        j["time"] if j["time"] < start else max(start, j["time"] - radius) for j in jobs
    ]
    hi = [
        j["time"] if j["time"] < start else min(target - 1, j["time"] + radius)
        for j in jobs
    ]
    for i, j in enumerate(jobs):
        if j["pause"]:
            lo[i] = hi[i] = target - 1
    for a, b, d in m["edges"]:
        lo[b] = max(lo[b], lo[a] + d)
    for a, b, d in reversed(m["edges"]):
        hi[a] = min(hi[a], hi[b] - d)
    # Edges are sorted by source. Reverse order propagates bounds through all successors.
    conflict = next(
        (
            {"job": i, "lower": l, "upper": h}
            for i, (l, h) in enumerate(zip(lo, hi))
            if l > h
        ),
        None,
    )
    return lo, hi, conflict


def project(m, lo, hi):
    assert all(l <= h for l, h in zip(lo, hi))
    free = [i for i, (l, h) in enumerate(zip(lo, hi)) if l != h]
    fs = set(free)
    fixed = {i: l for i, (l, h) in enumerate(zip(lo, hi)) if l == h}
    occupied = Counter((m["jobs"][i]["engine"], t) for i, t in fixed.items())
    for (e, t), n in occupied.items():
        assert n <= CAP[e], ("fixed capacity", e, t, n)
    edges = []
    boundary = []
    for a, b, d in m["edges"]:
        if a in fs and b in fs:
            edges.append((a, b, d))
        elif a in fs:
            assert hi[a] + d <= fixed[b]
            boundary.append((a, b, d))
        elif b in fs:
            assert fixed[a] + d <= lo[b]
            boundary.append((a, b, d))
        else:
            assert fixed[b] >= fixed[a] + d, ("fixed edge", a, b, d)
    return {
        "free": free,
        "fixed": fixed,
        "edges": edges,
        "boundary": boundary,
        "occupied": occupied,
    }


def cuts(m, lo, hi, start, target):
    N = target - start
    out = []
    for e, cap in CAP.items():
        hist = [[0] * N for _ in range(N)]
        for i, j in enumerate(m["jobs"]):
            if j["engine"] == e and lo[i] >= start and hi[i] < target:
                hist[lo[i] - start][hi[i] - start] += 1
        for a in reversed(range(N)):
            for b in range(N):
                hist[a][b] += (
                    (hist[a + 1][b] if a + 1 < N else 0)
                    + (hist[a][b - 1] if b else 0)
                    - (hist[a + 1][b - 1] if a + 1 < N and b else 0)
                )
        options = [
            (hist[a][b] - cap * (b - a + 1), a, b, hist[a][b])
            for a in range(N)
            for b in range(a, N)
            if hist[a][b]
        ]
        if not options:
            continue
        overload, a, b, work = max(options)
        a += start
        b += start
        ids = [
            i
            for i, j in enumerate(m["jobs"])
            if j["engine"] == e and lo[i] >= a and hi[i] <= b
        ]
        assert len(ids) == work
        out.append(
            {
                "engine": e,
                "from": a,
                "through": b,
                "work": work,
                "capacity": cap,
                "overload": overload,
                "jobs": ids,
            }
        )
    return out


def preflight(m, start, target=980):
    lo, hi, conflict = bounds(m, start, target)
    r = {
        "start": start,
        "target": target,
        "radius": 8,
        "conflict": conflict,
        "jobs": len(m["jobs"]),
        "edges": len(m["edges"]),
        "admitted": False,
    }
    if conflict:
        return r
    cs = cuts(m, lo, hi, start, target)
    r["cuts"] = cs
    r["free_variables"] = sum(l != h for l, h in zip(lo, hi))
    r["membership_terms"] = sum(h - l + 1 for l, h in zip(lo, hi) if l != h)
    if any(c["overload"] > 0 for c in cs):
        r["rejection"] = "mandatory capacity overload"
        return r
    p = project(m, lo, hi)
    r["projected_edges"] = len(p["edges"])
    r["boundary_edges"] = len(p["boundary"])
    r["fixed_jobs"] = len(p["fixed"])
    r["admitted"] = r["free_variables"] <= 2048 and r["membership_terms"] <= 32768
    if not r["admitted"]:
        r["rejection"] = "structural admission caps"
    return r


def solve(m, lo, hi, witness=None, on_ready=None):
    import z3, time

    p = project(m, lo, hi)
    s = z3.Solver()
    s.set(timeout=0)
    ts = {i: z3.Int("t" + str(i)) for i in p["free"]}
    for i, t in ts.items():
        s.add(t >= lo[i], t <= hi[i])
        if witness is not None:
            s.add(t == witness[i])
    for a, b, d in p["edges"]:
        if hi[a] + d > lo[b]:
            s.add(ts[b] >= ts[a] + d)
    bycycle = defaultdict(list)
    for i, t in ts.items():
        for c in range(lo[i], hi[i] + 1):
            bycycle[m["jobs"][i]["engine"], c].append((t == c, 1))
    terms = 0
    for (e, c), xs in bycycle.items():
        cap = CAP[e] - p["occupied"].get((e, c), 0)
        if len(xs) > cap:
            s.add(z3.PbLe(xs, cap))
            terms += len(xs)
    info = {
        "free_variables": len(ts),
        "potential_membership_terms": sum(hi[i] - lo[i] + 1 for i in ts),
        "encoded_capacity_terms": terms,
        "fixed_jobs_removed": len(p["fixed"]),
        "free_edges": len(p["edges"]),
        "boundary_edges_checked": len(p["boundary"]),
        "timeout_ms": 0,
    }
    if witness is not None:
        assert all(witness[i] == t for i, t in p["fixed"].items())
    if on_ready:
        on_ready(info)
    begin = time.monotonic()
    status = s.check()
    r = {**info, "status": str(status), "solver_seconds": time.monotonic() - begin}
    if status == z3.unknown:
        r["reason"] = s.reason_unknown()
    if status == z3.sat:
        sm = s.model()
        times = [
            p["fixed"][i] if i in p["fixed"] else sm.eval(ts[i]).as_long()
            for i in range(len(m["jobs"]))
        ]
        validate(m, times, lo, hi)
        r["times"] = times
    r["statistics"] = {
        k: s.statistics().get_key_value(k) for k in s.statistics().keys()
    }
    return r


def capture(ir, logical):
    """Export current logical instructions, retaining individual scalar lanes."""
    jobs, producer = [], {}
    for cycle, bundle in enumerate(logical):
        for i, engine, first, count in bundle:
            op = ir.ops[i]
            partial = op.kind == "gather" or (op.kind == "binary" and engine == "alu")
            assert count == 1 or partial
            for lane in range(first, first + count):
                writes = (
                    []
                    if op.dst is None
                    else [
                        (op.dst, l)
                        for l in ([lane] if partial else range(ir.widths[op.dst]))
                    ]
                )
                for ref in writes:
                    assert ref not in producer, "duplicate producer lane"
                    producer[ref] = len(jobs)
                jobs.append(
                    {
                        "op": i,
                        "engine": engine,
                        "first": lane,
                        "time": cycle,
                        "pause": False,
                        "reads": refs(ir, op, engine, lane),
                        "writes": writes,
                    }
                )
    pause = len(logical) - 1 + int(any(e == "flow" for _, e, _, _ in logical[-1]))
    jobs.append(
        {
            "op": None,
            "engine": "flow",
            "first": 0,
            "time": pause,
            "pause": True,
            "reads": [],
            "writes": [],
        }
    )
    edges = sorted(
        {
            (producer[tuple(ref)], i, 1)
            for i, job in enumerate(jobs)
            for ref in job["reads"]
        }
    )
    assert all(a < b for a, b, d in edges), "non-topological native jobs"
    result = {
        "jobs": jobs,
        "edges": edges,
        "ops": [asdict(op) for op in ir.ops],
        "widths": ir.widths,
        "cycles": pause + 1,
    }
    validate(result, [j["time"] for j in jobs])
    return result


def lower(ir, model, times):
    """Allocate fresh addresses and reject overflow before instruction lowering."""
    import kernel_compiler as compiler

    validate(model, times)
    logical = [[] for _ in range(max(times) + 1)]
    for job, cycle in zip(model["jobs"], times):
        if job["op"] is not None:
            logical[cycle].append((job["op"], job["engine"], job["first"], 1))
    starts, ends = {}, {}
    for cycle, bundle in enumerate(logical):
        for i, engine, first, count in bundle:
            op = ir.ops[i]
            if op.dst is not None:
                starts[op.dst] = min(starts.get(op.dst, cycle), cycle)
                ends[op.dst] = max(ends.get(op.dst, 0), cycle + 0.5)
            for value, _ in op.args:
                ends[value] = max(ends.get(value, 0), cycle)
    addresses, scratch = compiler._allocate(ir, starts, ends)
    if scratch > SCRATCH_SIZE:
        return None, scratch, logical, addresses
    from kernel_checks import lane_identity

    lane_identity(ir, logical, addresses)
    program = compiler._lower(ir, logical, addresses)
    assert len(program) == max(times) + 1
    return program, scratch, logical, addresses


def repair(model, start, target):
    """No deadline or persisted witness; a fresh capped solver for this model."""
    assert abs(model["cycles"] - target) <= 8
    assert preflight(model, start, target)["admitted"]
    payload = {"model": model, "start": start, "target": target}
    run = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--solve"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(run.stdout)
    if result["status"] == "sat":
        lo, hi, conflict = bounds(model, start, target, 8)
        assert conflict is None
        validate(model, result["times"], lo, hi)
    return result


def _worker():
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    assert resource.getrlimit(resource.RLIMIT_CPU) == (-1, -1)
    import z3

    if z3.get_version_string() != "4.15.4":
        raise RuntimeError("Expected pinned z3-solver==4.15.4.0")
    z3.set_param("smt.random_seed", 0)
    z3.set_param("sat.random_seed", 0)
    data = json.load(sys.stdin)
    model, start, target = data["model"], data["start"], data["target"]
    native = [j["time"] for j in model["jobs"]]
    lo, hi, conflict = bounds(model, start, model["cycles"], 8)
    assert conflict is None
    control = solve(model, lo, hi, witness=native)
    assert control["status"] == "sat" and control["times"] == native
    lo, hi, conflict = bounds(model, start, target, 8)
    assert conflict is None and preflight(model, start, target)["admitted"]
    result = solve(model, lo, hi)
    result["native_control"] = "sat"
    print(json.dumps(result))


if __name__ == "__main__":
    if sys.argv[1:] != ["--solve"]:
        raise SystemExit("This module is a compiler-internal solver worker.")
    _worker()
