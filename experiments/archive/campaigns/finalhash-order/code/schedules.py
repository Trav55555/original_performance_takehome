"""Fixed-engine job scheduling; no solver and no physical scratch assumptions."""
import heapq
from collections import Counter
from kernel_retime import CAP, validate


def structure(model):
    jobs = model['jobs']; n = len(jobs)
    parents, successors = [[] for _ in jobs], [[] for _ in jobs]
    pause, = [i for i, job in enumerate(jobs) if job['pause']]
    for a, b, lag in model['edges']:
        assert a < b and lag >= 1 and pause not in (a, b)
        parents[b].append((a, lag)); successors[a].append((b, lag))
    return parents, successors, pause


def tails(model, caps=CAP, resource=True):
    parents, successors, pause = structure(model)
    jobs = model['jobs']; n = len(jobs)
    path, tail = [0]*n, [0]*n
    descendants = [0]*n if resource else None
    masks = {e: 0 for e in caps}
    for i, job in enumerate(jobs):
        if i != pause: masks[job['engine']] |= 1 << i
    for i in reversed(range(n)):
        if i == pause: continue
        path[i] = max([2 if jobs[i]['engine'] == 'flow' else 1] + [lag+path[j] for j, lag in successors[i]])
        bound = path[i]
        if resource:
            bits = 0
            for j, lag in successors[i]:
                bits |= (1 << j) | descendants[j]
                bound = max(bound, lag+tail[j])
            descendants[i] = bits
            for e, mask in masks.items():
                q = (bits & mask).bit_count()
                if q:
                    bound = max(bound, 1+(q+caps[e]-1)//caps[e]+int(e == 'flow'))
        tail[i] = bound
    return path, tail


def make_calendar(jobs, times, caps, horizon):
    used = {e: [0]*horizon for e in caps}
    for i, job in enumerate(jobs):
        used[job['engine']][times[i]] += 1
    assert all(max(v, default=0) <= caps[e] for e, v in used.items())
    return used


def order_changes(jobs, before, after, pause):
    witnesses = []
    for engine in CAP:
        groups = {}
        for i, job in enumerate(jobs):
            if i != pause and job['engine'] == engine:
                groups.setdefault(after[i], []).append(i)
        largest = None
        for time, ids in sorted(groups.items()):
            for i in ids:
                if largest is not None and before[i] < before[largest] and len(witnesses) < 12:
                    witnesses.append({'engine': engine, 'old_earlier_job': i, 'old_later_job': largest,
                                      'before': [before[i], before[largest]], 'after': [after[i], after[largest]]})
            for i in ids:
                if largest is None or before[i] > before[largest]: largest = i
    return witnesses


def right_justify(model, times, tie='native', caps=CAP):
    parents, successors, pause = structure(model)
    path, _ = tails(model, caps, resource=False)
    jobs = model['jobs']; new = list(times); end = times[pause]
    used = make_calendar(jobs, times, caps, end+1)
    order = sorted((i for i in range(len(jobs)) if i != pause),
                   key=lambda i: (-times[i], i if tie == 'native' else path[i], i))
    for i in order:
        e = jobs[i]['engine']; old = new[i]
        latest = min([end-int(e == 'flow')] + [new[j]-lag for j, lag in successors[i]])
        assert latest >= old
        used[e][old] -= 1
        placed = next(t for t in range(latest, old-1, -1) if used[e][t] < caps[e])
        used[e][placed] += 1; new[i] = placed
    validate(model, new)
    return new


def serial_place(model, priority, caps=CAP):
    parents, successors, pause = structure(model)
    jobs = model['jobs']; n = len(jobs)
    indegree = [len(ps) for ps in parents]
    queue = [(priority[i], i) for i in range(n) if i != pause and not indegree[i]]
    heapq.heapify(queue)
    assigned = [None]*n
    used = {e: {} for e in caps}
    count = 0
    while queue:
        _, i = heapq.heappop(queue)
        release = max([0] + [assigned[p]+lag for p, lag in parents[i]])
        e = jobs[i]['engine']; calendar = used[e]
        while calendar.get(release, 0) == caps[e]: release += 1
        calendar[release] = calendar.get(release, 0)+1
        assigned[i] = release; count += 1
        for j, lag in successors[i]:
            indegree[j] -= 1
            if indegree[j] == 0: heapq.heappush(queue, (priority[j], j))
    assert count == n-1
    end = max(t for t in assigned if t is not None)
    while used['flow'].get(end, 0) == caps['flow']: end += 1
    assigned[pause] = end
    validate(model, assigned)
    return assigned


def double_justify(model, tie='native', passes=1, caps=CAP):
    _, _, pause = structure(model)
    original = [j['time'] for j in model['jobs']]
    current = original[:]; details = []
    path, _ = tails(model, caps, resource=False)
    for k in range(passes):
        right = right_justify(model, current, tie, caps)
        priority = [(right[i], i if tie == 'native' else -path[i], i) for i in range(len(right))]
        forward = serial_place(model, priority, caps)
        assert max(forward) <= max(current)
        details.append({'pass': k+1, 'right_moved_jobs': sum(a != b for a,b in zip(current,right)),
                        'right_order_changes': order_changes(model['jobs'], current, right, pause),
                        'cycles': max(forward)+1})
        current = forward
    return current, {'method': 'double-justification', 'tie': tie, 'passes': details,
                     'moved_earlier': sum(a < b for a,b in zip(current,original)),
                     'moved_later': sum(a > b for a,b in zip(current,original)),
                     'final_order_changes': order_changes(model['jobs'], original, current, pause)}


def deadline_schedule(model, rule, caps=CAP):
    original = [j['time'] for j in model['jobs']]; horizon = max(original)+1
    path, resource = tails(model, caps)
    pause = next(i for i,j in enumerate(model['jobs']) if j['pause'])
    assert all(resource[i] <= horizon-original[i] for i in range(len(original)) if i != pause), 'invalid resource tail'
    if rule == 'path':
        priority = [(horizon-path[i], i) for i in range(len(original))]
    else:
        num, den = {'resource-eighth': (1,8), 'resource-half': (1,2), 'resource': (1,1)}[rule]
        priority = [((den-num)*original[i]+num*(horizon-resource[i]), i) for i in range(len(original))]
    times = serial_place(model, priority, caps)
    differences = [i for i in range(len(path)) if resource[i] > path[i]]
    return times, {'method': 'resource-tail-deadline', 'rule': rule,
                   'stronger_tail_jobs': len(differences),
                   'max_tail_gain': max([0]+[resource[i]-path[i] for i in differences]),
                   'stronger_tail_late_native_jobs': sum(original[i] >= 900 for i in differences),
                   'tail_examples': [{'job': i, 'path': path[i], 'resource': resource[i], 'native_time': original[i]}
                                     for i in sorted(differences, key=lambda i: (path[i]-resource[i], i))[:8]],
                   'moved_earlier': sum(a < b for a,b in zip(times,original)),
                   'moved_later': sum(a > b for a,b in zip(times,original))}
