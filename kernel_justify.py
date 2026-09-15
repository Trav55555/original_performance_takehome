"""One fixed-engine backward/forward pass, before physical allocation."""

import heapq
from kernel_retime import CAP, validate


def schedule(model, *, tie="native", caps=CAP):
    """Right-justify, then insert in the derived order at earliest legal times.

    Jobs may move later than their native times and cross original cycle
    boundaries. Engine choices and exact lane dependencies stay fixed.
    Scratch feasibility is deliberately left to fresh allocation by the caller.
    """
    if tie not in ("native", "tail"):
        raise ValueError("Unknown justification tie order")
    jobs = model["jobs"]
    native = [j["time"] for j in jobs]
    validate(model, native)
    (pause,) = [i for i, j in enumerate(jobs) if j["pause"]]
    parents, successors = [[] for _ in jobs], [[] for _ in jobs]
    for a, b, lag in model["edges"]:
        assert a < b and lag >= 1 and pause not in (a, b)
        parents[b].append((a, lag))
        successors[a].append((b, lag))
    path = [0] * len(jobs)
    for i in reversed(range(len(jobs))):
        if i != pause:
            path[i] = max(
                [2 if jobs[i]["engine"] == "flow" else 1]
                + [lag + path[j] for j, lag in successors[i]]
            )
    end = native[pause]
    used = {e: [0] * (end + 1) for e in caps}
    for i, job in enumerate(jobs):
        used[job["engine"]][native[i]] += 1
    assert all(max(v, default=0) <= caps[e] for e, v in used.items())
    right = native[:]
    order = sorted(
        (i for i in range(len(jobs)) if i != pause),
        key=lambda i: (-native[i], i if tie == "native" else path[i], i),
    )
    for i in order:
        e = jobs[i]["engine"]
        latest = min(
            [end - int(e == "flow")] + [right[j] - lag for j, lag in successors[i]]
        )
        assert latest >= right[i]
        used[e][right[i]] -= 1
        t = next(t for t in range(latest, right[i] - 1, -1) if used[e][t] < caps[e])
        used[e][t] += 1
        right[i] = t
    validate(model, right)
    priority = [
        (right[i], i if tie == "native" else -path[i], i) for i in range(len(jobs))
    ]
    indegree = [len(p) for p in parents]
    ready = [
        (priority[i], i) for i in range(len(jobs)) if i != pause and not indegree[i]
    ]
    heapq.heapify(ready)
    forward = [None] * len(jobs)
    used = {e: {} for e in caps}
    count = 0
    while ready:
        _, i = heapq.heappop(ready)
        t = max([0] + [forward[p] + lag for p, lag in parents[i]])
        calendar = used[jobs[i]["engine"]]
        while calendar.get(t, 0) == caps[jobs[i]["engine"]]:
            t += 1
        calendar[t] = calendar.get(t, 0) + 1
        forward[i] = t
        count += 1
        for j, _ in successors[i]:
            indegree[j] -= 1
            if indegree[j] == 0:
                heapq.heappush(ready, (priority[j], j))
    assert count == len(jobs) - 1
    end = max(t for t in forward if t is not None)
    while used["flow"].get(end, 0) == caps["flow"]:
        end += 1
    forward[pause] = end
    validate(model, forward)
    assert max(forward) <= max(native)
    return forward
