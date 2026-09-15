"""Max-plus earliest schedule for a native-feasible capacity-chain event graph."""
from collections import defaultdict
from kernel_retime import CAP, validate


def compact(model, ir=None, order='native', start=0):
    jobs = model['jobs']
    parents = [[] for _ in jobs]
    tails = [1] * len(jobs)
    for a, b, lag in model['edges']:
        parents[b].append((a, lag))
    for a, b, lag in reversed(model['edges']):
        tails[a] = max(tails[a], tails[b] + lag)
    def block(i):
        if ir is None or jobs[i]['op'] is None:
            return 0
        coord = getattr(ir.ops[jobs[i]['op']], 'coord', None)
        return coord[0] if coord else -1
    def key(i):
        sub = {'native': i, 'reverse': -i, 'tail': -tails[i],
               'short': tails[i], 'block': block(i), 'reverse-block': -block(i)}[order]
        return jobs[i]['time'], sub, i
    times = [None] * len(jobs)
    channels = {e: [None]*c for e, c in CAP.items()}
    chain_edges = []
    pauses = [i for i, j in enumerate(jobs) if j['pause']]
    assert len(pauses) == 1
    pause = pauses[0]
    processing = sorted((i for i in range(len(jobs)) if i != pause), key=key) + [pause]
    for i in processing:
        job = jobs[i]
        assert all(times[a] is not None for a, _ in parents[i])
        release = max([0] + [times[a] + lag for a, lag in parents[i]])
        if job['time'] < start:
            release = max(release, job['time'])
        else:
            release = max(release, start)
        if i == pause:
            release = max(release, max(t for t in times if t is not None))
        options = []
        for channel, previous in enumerate(channels[job['engine']]):
            if previous is None or jobs[previous]['time'] < job['time']:
                ready = max(release, 0 if previous is None else times[previous]+1)
                options.append((ready, channel, previous))
        assert options, 'native capacity infeasible'
        ready, channel, previous = min(options, key=lambda x: (x[0], x[1]))
        assert ready <= job['time'], 'chain violates native witness'
        if job['time'] < start:
            assert ready == job['time']
        times[i] = ready
        channels[job['engine']][channel] = i
        if previous is not None:
            chain_edges.append((previous, i, 1))
    validate(model, times)
    # Independent event-graph relaxation reaches the same least fixed point.
    incoming = [list(ps) for ps in parents]
    for a, b, lag in chain_edges:
        incoming[b].append((a, lag))
    incoming[pause].extend((i, 0) for i in range(len(jobs)) if i != pause)
    checked = [None] * len(jobs)
    for i in processing:
        lower = jobs[i]['time'] if jobs[i]['time'] < start else start
        checked[i] = max([lower] + [checked[a] + lag for a, lag in incoming[i]])
    assert checked == times
    return times, {'order': order, 'start': start, 'chain_edges': len(chain_edges),
                   'moved_jobs': sum(t != j['time'] for t, j in zip(times, jobs)),
                   'cycles': max(times)+1,
                   'scope': 'least timing for this fixed capacity-chain event graph'}
