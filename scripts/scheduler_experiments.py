#!/usr/bin/env python3
"""
Scheduler experiments for VLIW kernel optimization.

This module implements various scheduling algorithms to find better
instruction orderings than the simple greedy approach.
"""

import sys

sys.path.insert(0, "..")

from collections import defaultdict
from typing import Callable
import heapq
import random

from problem import SLOT_LIMITS, VLEN


def _vec_range(base: int, length: int = VLEN) -> range:
    return range(base, base + length)


def _slot_rw(engine: str, slot: tuple) -> tuple[list[int], list[int]]:
    """Get read and write addresses for a slot."""
    reads: list[int] = []
    writes: list[int] = []

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
            case _:
                raise NotImplementedError(f"Unknown valu op {slot}")
    elif engine == "load":
        match slot:
            case ("load", dest, addr):
                reads = [addr]
                writes = [dest]
            case ("vload", dest, addr):
                reads = [addr]
                writes = list(_vec_range(dest))
            case ("const", dest, _val):
                writes = [dest]
            case ("load_offset", dest, addr, _lane):
                reads = [addr]
                writes = [dest]
            case _:
                raise NotImplementedError(f"Unknown load op {slot}")
    elif engine == "store":
        match slot:
            case ("store", addr, src):
                reads = [addr, src]
            case ("vstore", addr, src):
                reads = [addr] + list(_vec_range(src))
            case _:
                raise NotImplementedError(f"Unknown store op {slot}")
    elif engine == "flow":
        match slot:
            case ("select", dest, cond, a, b):
                reads = [cond, a, b]
                writes = [dest]
            case ("add_imm", dest, a, _imm):
                reads = [a]
                writes = [dest]
            case ("vselect", dest, cond, a, b):
                reads = (
                    list(_vec_range(cond)) + list(_vec_range(a)) + list(_vec_range(b))
                )
                writes = list(_vec_range(dest))
            case (
                ("halt",)
                | ("pause",)
                | ("trace_write", _)
                | ("jump", _)
                | ("jump_indirect", _)
                | ("cond_jump", _, _)
                | ("cond_jump_rel", _, _)
                | ("coreid", _)
            ):
                pass
            case _:
                raise NotImplementedError(f"Unknown flow op {slot}")

    return reads, writes


def build_dependency_graph(slots: list[tuple[str, tuple]]):
    """
    Build a dependency graph for the operations.
    Returns:
        - predecessors: dict mapping op_idx -> set of predecessor op_idx
        - successors: dict mapping op_idx -> set of successor op_idx
        - op_info: list of (engine, slot, reads, writes) for each op
    """
    n = len(slots)
    predecessors = defaultdict(set)
    successors = defaultdict(set)
    op_info = []

    # Track which op last wrote to each address
    last_writer: dict[int, int] = {}
    # Track which ops read from each address (for WAR hazards)
    readers: dict[int, list[int]] = defaultdict(list)

    for i, (engine, slot) in enumerate(slots):
        reads, writes = _slot_rw(engine, slot)
        op_info.append((engine, slot, reads, writes))

        # RAW dependencies: we depend on whoever last wrote what we read
        for addr in reads:
            if addr in last_writer:
                pred = last_writer[addr]
                predecessors[i].add(pred)
                successors[pred].add(i)

        # WAW dependencies: we depend on whoever last wrote what we write
        for addr in writes:
            if addr in last_writer:
                pred = last_writer[addr]
                predecessors[i].add(pred)
                successors[pred].add(i)

        # WAR dependencies: we depend on whoever last read what we write
        for addr in writes:
            for reader in readers[addr]:
                if reader != i:
                    predecessors[i].add(reader)
                    successors[reader].add(i)

        # Update tracking
        for addr in reads:
            readers[addr].append(i)
        for addr in writes:
            last_writer[addr] = i
            readers[addr] = []  # Clear readers since we're writing

    return predecessors, successors, op_info


def compute_critical_path_lengths(
    n: int, predecessors: dict[int, set], successors: dict[int, set]
) -> list[int]:
    """
    Compute the critical path length from each node to any sink.
    Uses reverse topological order.
    """
    # Find nodes with no successors (sinks)
    in_degree = [len(successors[i]) for i in range(n)]
    cp_length = [1] * n  # Each op takes 1 cycle

    # Process in reverse topological order
    queue = [i for i in range(n) if in_degree[i] == 0]

    while queue:
        node = queue.pop()
        for pred in predecessors[node]:
            cp_length[pred] = max(cp_length[pred], cp_length[node] + 1)
            in_degree[pred] -= 1
            if in_degree[pred] == 0:
                queue.append(pred)

    return cp_length


def schedule_greedy(slots: list[tuple[str, tuple]]) -> list[dict[str, list[tuple]]]:
    """Original greedy scheduler (baseline)."""
    cycles: list[dict[str, list[tuple]]] = []
    usage: list[dict[str, int]] = []
    ready_time: dict[int, int] = defaultdict(int)
    last_write: dict[int, int] = defaultdict(lambda: -1)
    last_read: dict[int, int] = defaultdict(lambda: -1)

    def ensure_cycle(cycle: int) -> None:
        while len(cycles) <= cycle:
            cycles.append({})
            usage.append(defaultdict(int))

    def find_cycle(engine: str, earliest: int) -> int:
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


def schedule_critical_path(
    slots: list[tuple[str, tuple]],
) -> list[dict[str, list[tuple]]]:
    """
    Critical path priority scheduler.
    Prioritizes operations on the longest dependency chain.
    """
    n = len(slots)
    predecessors, successors, op_info = build_dependency_graph(slots)
    cp_length = compute_critical_path_lengths(n, predecessors, successors)

    cycles: list[dict[str, list[tuple]]] = []
    usage: list[dict[str, int]] = []
    scheduled = [False] * n
    scheduled_cycle = [-1] * n

    # Track ready time for each address
    ready_time: dict[int, int] = defaultdict(int)

    def ensure_cycle(cycle: int) -> None:
        while len(cycles) <= cycle:
            cycles.append({})
            usage.append(defaultdict(int))

    def get_earliest_cycle(op_idx: int) -> int:
        """Get earliest cycle this op can be scheduled."""
        engine, slot, reads, writes = op_info[op_idx]
        earliest = 0

        # Must wait for all predecessors
        for pred in predecessors[op_idx]:
            if scheduled[pred]:
                earliest = max(earliest, scheduled_cycle[pred] + 1)

        # Must wait for data to be ready
        for addr in reads:
            earliest = max(earliest, ready_time[addr])

        return earliest

    def find_slot(engine: str, earliest: int) -> int:
        """Find first cycle >= earliest with available slot."""
        cycle = earliest
        limit = SLOT_LIMITS[engine]
        while True:
            ensure_cycle(cycle)
            if usage[cycle][engine] < limit:
                return cycle
            cycle += 1

    # Track unscheduled ops with no unscheduled predecessors
    ready_ops = []
    unscheduled_preds = [len(predecessors[i]) for i in range(n)]

    for i in range(n):
        if unscheduled_preds[i] == 0:
            # Priority queue: (-critical_path, original_order, op_idx)
            heapq.heappush(ready_ops, (-cp_length[i], i, i))

    while ready_ops:
        # Get highest priority ready op
        _, _, op_idx = heapq.heappop(ready_ops)

        if scheduled[op_idx]:
            continue

        engine, slot, reads, writes = op_info[op_idx]
        earliest = get_earliest_cycle(op_idx)
        cycle = find_slot(engine, earliest)

        ensure_cycle(cycle)
        cycles[cycle].setdefault(engine, []).append(slot)
        usage[cycle][engine] += 1
        scheduled[op_idx] = True
        scheduled_cycle[op_idx] = cycle

        # Update ready times
        for addr in writes:
            ready_time[addr] = cycle + 1

        # Add newly ready successors
        for succ in successors[op_idx]:
            unscheduled_preds[succ] -= 1
            if unscheduled_preds[succ] == 0:
                heapq.heappush(ready_ops, (-cp_length[succ], succ, succ))

    return [c for c in cycles if c]


def schedule_slack_based(
    slots: list[tuple[str, tuple]],
) -> list[dict[str, list[tuple]]]:
    """
    Slack-based scheduler.
    Prioritizes operations with the least scheduling flexibility (low slack).

    Slack = latest_start - earliest_start
    Lower slack = must be scheduled more precisely
    """
    n = len(slots)
    predecessors, successors, op_info = build_dependency_graph(slots)
    cp_length = compute_critical_path_lengths(n, predecessors, successors)

    # Compute ASAP (As Soon As Possible) times
    asap = [0] * n
    in_degree = [len(predecessors[i]) for i in range(n)]
    queue = [i for i in range(n) if in_degree[i] == 0]

    processed = set()
    while queue:
        node = queue.pop(0)
        processed.add(node)
        for succ in successors[node]:
            asap[succ] = max(asap[succ], asap[node] + 1)
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    # Critical path gives us ALAP implicitly
    # ALAP[i] = max_cp - cp_length[i] (where max_cp is longest path)
    max_cp = max(cp_length)
    alap = [max_cp - cp_length[i] for i in range(n)]

    # Slack = ALAP - ASAP
    slack = [alap[i] - asap[i] for i in range(n)]

    cycles: list[dict[str, list[tuple]]] = []
    usage: list[dict[str, int]] = []
    scheduled = [False] * n
    scheduled_cycle = [-1] * n
    ready_time: dict[int, int] = defaultdict(int)

    def ensure_cycle(cycle: int) -> None:
        while len(cycles) <= cycle:
            cycles.append({})
            usage.append(defaultdict(int))

    def get_earliest_cycle(op_idx: int) -> int:
        engine, slot, reads, writes = op_info[op_idx]
        earliest = 0
        for pred in predecessors[op_idx]:
            if scheduled[pred]:
                earliest = max(earliest, scheduled_cycle[pred] + 1)
        for addr in reads:
            earliest = max(earliest, ready_time[addr])
        return earliest

    def find_slot(engine: str, earliest: int) -> int:
        cycle = earliest
        limit = SLOT_LIMITS[engine]
        while True:
            ensure_cycle(cycle)
            if usage[cycle][engine] < limit:
                return cycle
            cycle += 1

    # Priority queue: (slack, -critical_path, original_order, op_idx)
    ready_ops = []
    unscheduled_preds = [len(predecessors[i]) for i in range(n)]

    for i in range(n):
        if unscheduled_preds[i] == 0:
            heapq.heappush(ready_ops, (slack[i], -cp_length[i], i, i))

    while ready_ops:
        _, _, _, op_idx = heapq.heappop(ready_ops)

        if scheduled[op_idx]:
            continue

        engine, slot, reads, writes = op_info[op_idx]
        earliest = get_earliest_cycle(op_idx)
        cycle = find_slot(engine, earliest)

        ensure_cycle(cycle)
        cycles[cycle].setdefault(engine, []).append(slot)
        usage[cycle][engine] += 1
        scheduled[op_idx] = True
        scheduled_cycle[op_idx] = cycle

        for addr in writes:
            ready_time[addr] = cycle + 1

        for succ in successors[op_idx]:
            unscheduled_preds[succ] -= 1
            if unscheduled_preds[succ] == 0:
                heapq.heappush(ready_ops, (slack[succ], -cp_length[succ], succ, succ))

    return [c for c in cycles if c]


def schedule_engine_balanced(
    slots: list[tuple[str, tuple]],
) -> list[dict[str, list[tuple]]]:
    """
    Engine-balanced scheduler.
    Tries to balance load across engines by prioritizing ops for underutilized engines.
    """
    n = len(slots)
    predecessors, successors, op_info = build_dependency_graph(slots)
    cp_length = compute_critical_path_lengths(n, predecessors, successors)

    cycles: list[dict[str, list[tuple]]] = []
    usage: list[dict[str, int]] = []
    scheduled = [False] * n
    scheduled_cycle = [-1] * n
    ready_time: dict[int, int] = defaultdict(int)

    # Track cumulative engine usage for balancing
    cumulative_usage = defaultdict(int)

    def ensure_cycle(cycle: int) -> None:
        while len(cycles) <= cycle:
            cycles.append({})
            usage.append(defaultdict(int))

    def get_earliest_cycle(op_idx: int) -> int:
        engine, slot, reads, writes = op_info[op_idx]
        earliest = 0
        for pred in predecessors[op_idx]:
            if scheduled[pred]:
                earliest = max(earliest, scheduled_cycle[pred] + 1)
        for addr in reads:
            earliest = max(earliest, ready_time[addr])
        return earliest

    def find_slot(engine: str, earliest: int) -> int:
        cycle = earliest
        limit = SLOT_LIMITS[engine]
        while True:
            ensure_cycle(cycle)
            if usage[cycle][engine] < limit:
                return cycle
            cycle += 1

    def engine_priority(engine: str) -> float:
        """Lower number = higher priority for this engine's ops."""
        # Prioritize bottleneck engine (valu)
        if engine == "valu":
            return 0
        # Then by relative utilization vs limit
        return cumulative_usage[engine] / SLOT_LIMITS[engine]

    ready_ops = []
    unscheduled_preds = [len(predecessors[i]) for i in range(n)]

    for i in range(n):
        if unscheduled_preds[i] == 0:
            engine = op_info[i][0]
            heapq.heappush(ready_ops, (engine_priority(engine), -cp_length[i], i, i))

    while ready_ops:
        _, _, _, op_idx = heapq.heappop(ready_ops)

        if scheduled[op_idx]:
            continue

        engine, slot, reads, writes = op_info[op_idx]
        earliest = get_earliest_cycle(op_idx)
        cycle = find_slot(engine, earliest)

        ensure_cycle(cycle)
        cycles[cycle].setdefault(engine, []).append(slot)
        usage[cycle][engine] += 1
        cumulative_usage[engine] += 1
        scheduled[op_idx] = True
        scheduled_cycle[op_idx] = cycle

        for addr in writes:
            ready_time[addr] = cycle + 1

        for succ in successors[op_idx]:
            unscheduled_preds[succ] -= 1
            if unscheduled_preds[succ] == 0:
                succ_engine = op_info[succ][0]
                heapq.heappush(
                    ready_ops,
                    (engine_priority(succ_engine), -cp_length[succ], succ, succ),
                )

    return [c for c in cycles if c]


def schedule_reverse_topological(
    slots: list[tuple[str, tuple]],
) -> list[dict[str, list[tuple]]]:
    """
    Schedule in reverse dependency order (from sinks to sources),
    then reverse the schedule. Can find different local optima.
    """
    n = len(slots)
    predecessors, successors, op_info = build_dependency_graph(slots)

    # Reverse the graph
    rev_predecessors = successors
    rev_successors = predecessors

    # Schedule in reverse order
    cycles: list[dict[str, list[tuple]]] = []
    usage: list[dict[str, int]] = []
    scheduled = [False] * n
    scheduled_cycle = [-1] * n
    ready_time: dict[int, int] = defaultdict(int)

    def ensure_cycle(cycle: int) -> None:
        while len(cycles) <= cycle:
            cycles.append({})
            usage.append(defaultdict(int))

    def get_earliest_cycle(op_idx: int) -> int:
        engine, slot, reads, writes = op_info[op_idx]
        earliest = 0
        for pred in rev_predecessors[op_idx]:
            if scheduled[pred]:
                earliest = max(earliest, scheduled_cycle[pred] + 1)
        return earliest

    def find_slot(engine: str, earliest: int) -> int:
        cycle = earliest
        limit = SLOT_LIMITS[engine]
        while True:
            ensure_cycle(cycle)
            if usage[cycle][engine] < limit:
                return cycle
            cycle += 1

    ready_ops = []
    unscheduled_preds = [len(rev_predecessors[i]) for i in range(n)]

    for i in range(n):
        if unscheduled_preds[i] == 0:
            heapq.heappush(ready_ops, (i, i))

    while ready_ops:
        _, op_idx = heapq.heappop(ready_ops)

        if scheduled[op_idx]:
            continue

        engine, slot, reads, writes = op_info[op_idx]
        earliest = get_earliest_cycle(op_idx)
        cycle = find_slot(engine, earliest)

        ensure_cycle(cycle)
        cycles[cycle].setdefault(engine, []).append(slot)
        usage[cycle][engine] += 1
        scheduled[op_idx] = True
        scheduled_cycle[op_idx] = cycle

        for succ in rev_successors[op_idx]:
            unscheduled_preds[succ] -= 1
            if unscheduled_preds[succ] == 0:
                heapq.heappush(ready_ops, (succ, succ))

    # Reverse the schedule
    max_cycle = max(scheduled_cycle)
    reversed_cycles: list[dict[str, list[tuple]]] = [{} for _ in range(max_cycle + 1)]

    for op_idx in range(n):
        engine, slot, _, _ = op_info[op_idx]
        new_cycle = max_cycle - scheduled_cycle[op_idx]
        reversed_cycles[new_cycle].setdefault(engine, []).append(slot)

    return [c for c in reversed_cycles if c]


def compare_schedulers(slots: list[tuple[str, tuple]]):
    """Compare different scheduling algorithms."""
    schedulers = [
        ("Greedy (original)", schedule_greedy),
        ("Critical Path", schedule_critical_path),
        ("Slack-based", schedule_slack_based),
        ("Engine-balanced", schedule_engine_balanced),
        ("Reverse topological", schedule_reverse_topological),
    ]

    results = []
    for name, scheduler in schedulers:
        try:
            schedule = scheduler(slots)
            cycles = len(schedule)
            results.append((name, cycles, schedule))
        except Exception as e:
            results.append((name, f"ERROR: {e}", None))

    return results


if __name__ == "__main__":
    # Test with actual kernel
    import sys

    sys.path.insert(0, "..")

    from perf_takehome import KernelBuilder
    import random
    from problem import Tree, Input, build_mem_image

    print("Building kernel operations...")
    forest_height = 10
    rounds = 16
    batch_size = 256

    random.seed(123)
    forest = Tree.generate(forest_height)
    inp = Input.generate(forest, batch_size, rounds)

    # Extract slots from kernel builder
    kb = KernelBuilder()
    # We need to capture the slots before they're scheduled
    # This requires modifying the build_kernel to expose slots

    print("To test: need to extract slots from build_kernel")
    print(
        "Run from parent directory with: python -c 'from scripts.scheduler_experiments import *; ...'"
    )
