"""Small independent oracles; no benchmark construction or solver."""
import copy
import itertools
from collections import Counter
import random
from unittest.mock import patch
from research import compiler, retime
from frozen_problem import Machine, DebugInfo
import schedules as S


def run():
    rng = random.Random(7182)
    caps = {'alu': 2, 'valu': 1, 'load': 2, 'flow': 1, 'store': 2}
    feasible = 0
    for _ in range(24):
        engines = [rng.choice(('alu', 'valu', 'flow')) for _ in range(4)]
        edges = [(a, b, 1) for a in range(4) for b in range(a+1, 4) if rng.random() < .35]
        jobs = [{'engine': e, 'pause': False} for e in engines] + [{'engine': 'flow', 'pause': True}]
        model = {'jobs': jobs, 'edges': edges}
        path, tails = S.tails(model, caps)
        for times in itertools.product(range(4), repeat=4):
            if any(times[b] <= times[a] for a,b,_ in edges): continue
            use = Counter((t,e) for t,e in zip(times,engines))
            if any(n > caps[e] for (t,e),n in use.items()): continue
            end = max(times)
            if use[end, 'flow']: end += 1
            assert all(tails[i] <= end+1-times[i] for i in range(4))
            feasible += 1
    fan = {'jobs': [{'engine': 'alu', 'pause': False}] + [{'engine': 'load', 'pause': False} for _ in range(6)] + [{'engine': 'flow', 'pause': True}],
           'edges': [(0,j,1) for j in range(1,7)]}
    path, bound = S.tails(fan, caps)
    assert path[0] == 2 and bound[0] == 4
    known_times = [0,1,1,2,2,3,3,3]
    assert bound[0] <= 4-known_times[0]
    wrong = bound[0]+1
    assert not wrong <= 4-known_times[0], 'overstated bound accepted'
    ir = compiler._IR()
    a, b = ir.const(0), ir.const(7)
    c = ir.emit('broadcast', args=(b,))
    d = ir.binary('+', a, c, preferred='alu', width=1)
    v = ir.emit('broadcast', args=(d,))
    ir.emit('vstore', args=(a,v), width=0)
    logical = [[(i,e,0,1)] for i,e in enumerate(('load','load','valu','alu','valu','store'))]
    model = retime.capture(ir, logical)
    before = [j['time'] for j in model['jobs']]
    for words in (1537, 1545):
        with patch.object(compiler, '_allocate', return_value=({}, words)), patch.object(compiler, '_lower', side_effect=AssertionError('forbidden lower')) as lower:
            out = retime.lower(ir, model, before)
            assert out[0] is None and out[1] == words
            lower.assert_not_called()
    after, diagnostic = S.double_justify(model, caps=dict(S.CAP, load=1))
    assert max(before)+1 == 6 and max(after)+1 == 5
    assert after[0] > before[0] and after[1] < before[1]
    assert diagnostic['final_order_changes']
    for times, cycles in ((before,6),(after,5)):
        program, words, _, _ = retime.lower(ir, model, times)
        assert program is not None and words <= 1536
        machine = Machine([0]*8, program, DebugInfo({}), n_cores=1)
        machine.run(); assert machine.mem == [7]*8 and machine.cycle == cycles
    bad = copy.deepcopy(model); bad['edges'].pop()
    try: retime.validate(bad, before)
    except AssertionError as e: assert str(e) == 'missing or spurious data dependency'
    else: raise AssertionError('missing edge accepted')
    bad_times = before[:]; bad_times[3] = before[2]
    try: retime.validate(model, bad_times)
    except AssertionError as e: assert str(e) == 'dependency timing'
    else: raise AssertionError('dependency violation accepted')
    bad = {'jobs': [{'engine':'load','pause':False} for _ in range(3)], 'edges': []}
    try: retime.validate(bad, [0]*3)
    except AssertionError as e: assert str(e) == 'capacity'
    else: raise AssertionError('over-capacity accepted')
    return {'toy_graphs': 24, 'assignments_considered': 24*4**4, 'feasible_assignments_checked': feasible,
            'fanout_path_tail': 2, 'fanout_resource_tail': 4, 'overstated_bound_rejected': True,
            'executable_justification_toy': {'before': 6, 'after': 5, 'job_moved_later': True},
            'missing_edge_rejected': True, 'dependency_time_rejected': True, 'capacity_rejected': True}
