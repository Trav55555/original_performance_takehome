"""One-cycle, eight-operation forecasts for the benchmark's engine choices.

Forecasts copy scheduler state. They never allocate scratch or alter the real
schedule; the caller applies the selected engine with its ordinary issue rules.
"""

from kernel_compiler import _engine_cost, SLOT_LIMITS


def make_policy(
    ir,
    succ,
    remaining,
    critical,
    distance,
    priority,
    available,
    progress,
    modes,
    complete,
    ready,
):
    ops = ir.ops
    widths = ir.widths
    masks = [(1 << w) - 1 for w in widths]
    horizon = 1
    width = 8
    per_cycle = 1
    stats = {"forecasts": 0, "decisions": 0, "changed_choices": 0}
    ir.lookahead_stats = stats
    last_cycle = -1
    used = 0

    def forecast(first, engine, position, ordered, capacity, bundle, done, updates):
        avail = available[:]
        prog = progress[:]
        mode = dict(modes)
        left = remaining[:]
        finished = set(complete)
        queue = set(ready)
        cap = dict(capacity)
        new = list(updates)
        done_now = list(done)
        touched = {i for i, _, _, _ in bundle}
        gathers = frontier = 0.0

        def mask(i):
            op = ops[i]
            if op.kind in ("binary", "gather"):
                m = masks[op.dst]
                for v, o in op.args:
                    m &= avail[v] >> o
                return m & ~prog[i]
            sizes = (
                [1, 8]
                if op.kind == "vstore"
                else [1]
                if op.kind in ("vload", "broadcast", "const_choice")
                else [8] * len(op.args)
            )
            for (v, o), n in zip(op.args, sizes):
                if (avail[v] >> o) & ((1 << n) - 1) != (1 << n) - 1:
                    return 0
            return 1

        def key(i):
            op = ops[i]
            freed = sum(widths[v] for v in {v for v, _ in op.args} if left[v] == 1)
            gained = 0 if op.dst is None or i in mode else widths[op.dst]
            return priority[i] + 100 * (gained - freed), i

        order = ordered[position : position + width]
        for step in range(horizon + 1):
            for i in order:
                op = ops[i]
                m = mask(i)
                if not m:
                    continue
                if step == 0 and i == first:
                    e = engine
                elif i in mode:
                    e = mode[i]
                else:
                    e = _engine_cost(op, widths)[0]
                    if op.kind == "const_choice" and not cap["load"] and cap["flow"]:
                        e = "flow"
                    if op.kind == "binary" and widths[op.dst] == 8:
                        if (
                            e == "valu"
                            and (not cap["valu"] or m != 255)
                            and min(cap["alu"], m.bit_count()) >= 1
                        ):
                            e = "alu"
                        elif e == "alu" and not cap["alu"] and cap["valu"] and m == 255:
                            e = "valu"
                if not cap[e]:
                    continue
                partial = op.kind == "gather" or (op.kind == "binary" and e == "alu")
                if not partial and op.kind == "binary" and m != masks[op.dst]:
                    continue
                mode[i] = e
                touched.add(i)
                if partial:
                    lanes = [j for j in range(widths[op.dst]) if m & (1 << j)][: cap[e]]
                    issued = sum(1 << j for j in lanes)
                    cap[e] -= len(lanes)
                    prog[i] |= issued
                    new.append((op.dst, issued))
                    is_done = prog[i] == masks[op.dst]
                    fraction = len(lanes) / widths[op.dst]
                    if op.kind == "gather":
                        gathers += len(lanes) / (step + 1)
                else:
                    cap[e] -= 1
                    is_done = True
                    fraction = 1
                    if op.dst is not None:
                        new.append((op.dst, masks[op.dst]))
                frontier += (
                    (critical[i] + 50 * max(0, 4 - distance[i])) * fraction / (step + 1)
                )
                if is_done:
                    done_now.append(i)
                    for v in {v for v, _ in op.args}:
                        left[v] -= 1
            for v, m in new:
                avail[v] |= m
            for i in done_now:
                finished.add(i)
                queue.discard(i)
            for j in {j for i in touched for j in succ[i]}:
                if j not in finished and mask(j):
                    queue.add(j)
            cap = dict(SLOT_LIMITS)
            new = []
            done_now = []
            touched = set()
            order = sorted(queue, key=key)[:width]
        stats["forecasts"] += 1
        return (-gathers, -frontier)

    def policy(
        current, i, mask, position, ordered, capacity, bundle, done, updates, cycle
    ):
        nonlocal last_cycle, used
        if cycle != last_cycle:
            last_cycle = cycle
            used = 0
        op = ops[i]
        if used >= per_cycle:
            return current
        if op.kind == "const_choice":
            choices = [e for e in ("load", "flow") if capacity[e]]
        elif op.kind == "binary" and widths[op.dst] == 8:
            choices = (["alu"] if capacity["alu"] and mask else []) + (
                ["valu"] if capacity["valu"] and mask == 255 else []
            )
        else:
            return current
        if len(choices) < 2:
            return current
        used += 1
        stats["decisions"] += 1
        ordered_choices = [current] + [e for e in choices if e != current]
        scores = [
            forecast(i, e, position, ordered, capacity, bundle, done, updates)
            for e in ordered_choices
        ]
        selected = min(range(len(scores)), key=lambda j: scores[j])
        result = ordered_choices[selected]
        if result != current:
            stats["changed_choices"] += 1
        return result

    return policy
