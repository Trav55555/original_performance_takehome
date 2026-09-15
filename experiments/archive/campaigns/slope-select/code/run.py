"""Finite slope-select pilot. No solver, materialization sweep, or production edits."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import research as R
from research import compiler, retime
import proofs


def schedule_times(built):
    ir, logical = built[:2]
    issue = {}
    for t, entries in enumerate(logical):
        for i, _, _, _ in entries:
            issue[i] = max(t, issue.get(i, -1))
    def ready(ref):
        return issue[ir.producer[ref[0]]] + 1
    return issue, ready


def native_tile(built, block):
    ir = built[0]
    issue, ready = schedule_times(built)
    first = [i for i, op in enumerate(ir.ops) if op.site == (block, 14, 0, 0)]
    second = [i for i, op in enumerate(ir.ops) if op.site == (block, 14, 0, 1)]
    assert len(first) == len(second) == 1
    left, right = (ir.ops[first[0]].dst, 0), (ir.ops[second[0]].dst, 0)
    parent = [i for i, op in enumerate(ir.ops) if op.kind == 'select' and op.args[1:] == (right, left)]
    assert len(parent) == 1
    op = ir.ops[parent[0]]
    return {'final_cycle': issue[parent[0]], 'final_engine': 'flow',
            'first_bit_ready': ready(ir.ops[first[0]].args[0]), 'last_bit_ready': ready(op.args[0]),
            'final_operands_ready': max(ready(ref) for ref in op.args)}


def tile_diagnostic(built):
    ir = built[0]
    assert len(ir.tile_traces) == 1
    trace = ir.tile_traces[0]
    issue, ready = schedule_times(built)
    parent = [i for i, op in enumerate(ir.ops) if op.kind == 'muladd'
              and op.args[1:] == (trace['slope'], trace['base'])]
    assert len(parent) == 1
    op = ir.ops[parent[0]]
    return {'final_cycle': issue[parent[0]], 'final_engine': 'valu',
            'base_cycle': ready(trace['base']) - 1, 'slope_cycle': ready(trace['slope']) - 1,
            'slope_engine': 'flow' if trace['shape'] == 'slope' else 'valu',
            'bits_ready': [ready(ref) for ref in trace['bits']],
            'coefficients_ready': [ready(ref) for ref in trace['coefficients']],
            'final_operands_ready': max(ready(ref) for ref in op.args),
            'coefficient_recipes': getattr(ir, 'coefficient_recipes', [])}


def controls():
    R.reserve('control', 'symbolic-and-guards')
    pure = proofs.run()
    (R.HERE/'pure_checks.json').write_text(json.dumps(pure, indent=2))
    for words in (1537, 1545):
        with patch.object(compiler, '_allocate', return_value=({}, words)), patch.object(compiler, '_lower', side_effect=AssertionError('forbidden lower')) as lower:
            assert R.allocate_lower(compiler._IR(), [], {}, {})[:2] == (None, words)
            lower.assert_not_called()
    attempts = (R.HERE/'attempts.jsonl').read_text()
    with patch.object(R, 'CAPS', dict(R.CAPS, candidate=0)), patch.object(R, 'construct', side_effect=AssertionError('forbidden construction')) as build:
        try:
            R.reserve('candidate', 'zero-budget-control')
            R.construct({})
        except AssertionError as e:
            assert str(e) == 'arm budget exhausted'
        else:
            raise AssertionError('budget bypass')
        build.assert_not_called()
    assert attempts == (R.HERE/'attempts.jsonl').read_text()
    R.write_row({'arm': 'control', 'name': 'symbolic-and-guards', 'status': 'passed', **pure,
                 'overscratch_pre_lower': [1537, 1545], 'zero_budget_pre_construct': True})
    R.reserve('control', 'original-native')
    spec = importlib.util.spec_from_file_location('original_compiler', R.HERE/'original/kernel_compiler.py')
    original = importlib.util.module_from_spec(spec); sys.modules[spec.name] = original; spec.loader.exec_module(original)
    baseline = R.construct({}, original)
    assert (baseline[5], baseline[3]) == (981, 1465)
    assert R.execute(baseline[4], seeds=range(3)) == 3
    R.write_row({'arm': 'control', 'name': 'original-native', 'status': 'passed', 'cycles': 981,
                 'scratch': 1465, 'digest': R.digest(baseline[4]), 'smoke_cases': 3})
    R.reserve('control', 'isolated-native')
    native = R.construct({})
    assert native[3:6] == baseline[3:6]
    row = R.row_for('control', 'isolated-native', {}, native)
    row['native_tiles'] = {b: native_tile(native, b) for b in (30, 31)}
    R.write_row(row); R.save('native', native, {}, row)
    R.reserve('control', 'published980-replay')
    logical = json.loads(Path('/tmp/perf-promote980-run.qim8Di/refined_logical.json').read_text())
    model = retime.capture(native[0], logical)
    program, words, _, _ = retime.lower(native[0], model, [j['time'] for j in model['jobs']])
    assert len(program) == 980 and words == 1465
    assert R.digest(program) == 'c17788082bd3757c95f02bd743582ff1acd3f55c56e3326d9fc72e65da7ba5bc'
    assert R.execute(program, seeds=range(3), patterns=range(5)) == 8
    corrupt = copy.deepcopy(program); changed = False
    for bundle in corrupt:
        for engine in ('load', 'flow'):
            for i, slot in enumerate(bundle.get(engine, [])):
                if (slot[0] == 'const' and slot[-1] == 0xb55a4f09) or (slot[0] == 'add_imm' and slot[-1] == 0xb55a4f09-7):
                    bundle[engine][i] = tuple(slot[:-1]) + (slot[-1] ^ 2,); changed = True; break
            if changed: break
        if changed: break
    assert changed
    try:
        R.execute(corrupt, seeds=[0])
    except AssertionError as e:
        assert str(e) == 'output mismatch'
    else:
        raise AssertionError('corruption accepted')
    R.write_row({'arm': 'control', 'name': 'published980-replay', 'status': 'passed', 'cycles': 980,
                 'scratch': words, 'digest': R.digest(program), 'execution_cases': 8, 'corruption_rejected': True})
    return native


def main():
    assert not (R.HERE/'attempts.jsonl').exists(), 'used manifest cannot restart'
    started = time.monotonic()
    native = controls()
    selection = json.loads((R.HERE/'selection.json').read_text())
    previous = json.loads((R.HERE/'prior_screen_result.json').read_text())['rows']
    rows, builds = [], {}
    for case in selection:
        name, cfg = case['name'], case['config']
        R.reserve('candidate', name)
        built = R.construct(cfg)
        row = R.row_for('candidate', name, cfg, built)
        if built[4] is not None:
            assert row['cycles'] == len(built[4])
            row['pattern_cases'] = R.execute(built[4], patterns=range(5))
            row['tile'] = tile_diagnostic(built)
            row['native_tile'] = native_tile(native, cfg['tiles'][0][0])
            row['tile_cycle_delta'] = row['tile']['final_cycle'] - row['native_tile']['final_cycle']
            if cfg['shape'] == 'tensor' and cfg['sharing'] == 'structural' and cfg['tiles'][0][3] == 1:
                old = previous['S+A18' if cfg['tiles'][0][0] == 30 else 'S+A16']
                assert all(row[key] == old[key] for key in ('cycles', 'scratch', 'digest', 'counts'))
                row['prior_exact_reproduction'] = True
            row['status'] = 'screen-passed'
            builds[name] = built
            R.save(name, built, cfg, row)
        rows.append(row); R.write_row(row)
    legal = [row for row in rows if row['status'] == 'screen-passed']
    winner = min(legal, key=lambda r: (r['cycles'], r['scratch'], r['name'])) if legal else None
    verification = None
    if winner and winner['cycles'] <= 980:
        built = builds[winner['name']]
        checked = R.execute(built[4], seeds=range(100), patterns=range(5))
        for k in range(2):
            R.reserve('validation', 'reconstruction-'+str(k))
            again = R.construct(winner['config'])
            assert again[3:6] == built[3:6]
            assert R.digest(again[4]) == winner['digest']
            model = retime.capture(again[0], again[1]); retime.validate(model, [j['time'] for j in model['jobs']])
            assert R.execute(again[4], seeds=[100+k]) == 1
            R.write_row({'arm': 'validation', 'name': 'reconstruction-'+str(k), 'status': 'passed',
                         'cycles': again[5], 'scratch': again[3], 'digest': R.digest(again[4])})
        verification = {'candidate': winner['name'], 'full_width_seeds': 100, 'patterns': 5,
                        'new_reconstructions': 2, 'cases': checked, 'production_promotion': False}
    R.guard()
    report = {'status': 'completed', 'budget_closed': True, 'elapsed': time.monotonic()-started,
              'rows': rows, 'best': winner, 'conditional_verification': verification,
              'solver_queries': 0, 'production_changed': False, 'full_incumbent_gates_run': False}
    (R.HERE/'screen_result.json').write_text(json.dumps(report, indent=2))
    manifest = json.loads((R.HERE/'manifest.json').read_text()); manifest['status'] = 'closed'
    (R.HERE/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: report[k] for k in ('status', 'elapsed', 'conditional_verification')}), flush=True)


if __name__ == '__main__':
    with patch.object(retime, 'solve', side_effect=AssertionError('solver forbidden')), \
         patch.object(retime, 'repair', side_effect=AssertionError('solver forbidden')), \
         patch.object(retime, '_worker', side_effect=AssertionError('solver forbidden')):
        try:
            main()
        except BaseException as error:
            (R.HERE/'failure.json').write_text(json.dumps({'type': type(error).__name__, 'error': str(error), 'budget_closed': True}))
            raise
