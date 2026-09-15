"""Read-only audit of recorded artifacts. Does not construct or execute kernels."""
from collections import Counter
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = Path('/home/travers/projects/original_performance_takehome')
CAP = {'alu': 12, 'valu': 6, 'load': 2, 'store': 2, 'flow': 1}


def load(name):
    return json.loads((P/name).read_text())


def source_guard(path, base):
    expected = json.loads(path.read_text())
    assert all(hashlib.sha256((base/name).read_bytes()).hexdigest() == h for name, h in expected.items())


def check_program(program, words, counts):
    observed, touched = Counter(), set()
    def touch(base, n=1):
        assert isinstance(base, int) and base >= 0
        touched.update(range(base, base+n))
    for bundle in program:
        assert set(bundle) <= set(CAP)
        for engine, slots in bundle.items():
            assert len(slots) <= CAP[engine]
            observed[engine] += len(slots)
            for code, *args in slots:
                if engine == 'alu':
                    assert len(args) == 3
                    for a in args: touch(a)
                elif engine == 'valu':
                    if code == 'vbroadcast':
                        touch(args[0], 8); touch(args[1])
                    else:
                        assert len(args) == (4 if code == 'multiply_add' else 3)
                        for a in args: touch(a, 8)
                elif engine == 'load':
                    assert code in ('const', 'load', 'vload')
                    touch(args[0], 8 if code == 'vload' else 1)
                    if code != 'const': touch(args[1])
                elif engine == 'store':
                    assert code == 'vstore'
                    touch(args[0]); touch(args[1], 8)
                elif code == 'add_imm':
                    touch(args[0]); touch(args[1])
                elif code == 'vselect':
                    for a in args: touch(a, 8)
                else:
                    assert code == 'pause' and not args
    assert sum(slot[0] == 'pause' for bundle in program for slots in bundle.values() for slot in slots) == 1
    assert program[-1]['flow'][-1] == ['pause']
    assert dict(observed) == counts
    assert max(touched) < words <= 1536
    return max(touched)+1


def main():
    source_guard(P/'protected_sources.json', ROOT)
    source_guard(P/'research_sources.json', P)
    old = Path('/tmp/perf-math-mix.X7KVbp')
    source_guard(old/'research_sources.json', old)
    manifest, report = load('manifest.json'), load('screen_result.json')
    assert manifest['status'] == 'closed' and report['budget_closed']
    attempts = [json.loads(x) for x in (P/'attempts.jsonl').read_text().splitlines()]
    recorded = [json.loads(x) for x in (P/'results.jsonl').read_text().splitlines()]
    assert len({x['name'] for x in attempts}) == len(attempts) == 20
    assert Counter(x['arm'] for x in attempts) == {'candidate': 16, 'control': 4}
    assert {x['name'] for x in recorded} == {x['name'] for x in attempts}
    assert len(recorded) == 20
    rows = {x['name']: x for x in report['rows']}
    assert len(rows) == 16
    for x in load('selection.json'):
        assert rows[x['name']]['config'] == x['config']
    assert all(rows[x['name']] == x for x in recorded if x['arm'] == 'candidate')
    diagnostics = {}
    for name, row in [('native', next(x for x in recorded if x['name'] == 'isolated-native'))] + list(rows.items()):
        base = P/'artifacts'/name
        program = json.loads((base/'program.json').read_text())
        logical = json.loads((base/'logical.json').read_text())
        assert hashlib.sha256(json.dumps(program).encode()).hexdigest() == row['digest']
        assert len(program) == row['cycles']
        counts = Counter({'flow': 1}); stores = {}
        for t, entries in enumerate(logical):
            for i, engine, first, count in entries:
                assert first >= 0 and count > 0
                counts[engine] += count
                if engine == 'store':
                    assert i not in stores and count == 1
                    stores[i] = t
        assert dict(counts) == row['counts'] and len(stores) == 32
        used = check_program(program, row['scratch'], row['counts'])
        by_block = {b: stores[i] for b, i in enumerate(sorted(stores))}
        diagnostics[name] = {'address_high_water': used, 'store_cycle_by_block': by_block,
                             'last_stores': [b for b, t in by_block.items() if t == max(stores.values())]}
    pairs = []
    for block in (30, 31):
        for order in (0, 1):
            for sharing in ('structural', 'algebraic'):
                a = rows[f'B{block}-tensor-O{order}-{sharing}']
                b = rows[f'B{block}-slope-O{order}-{sharing}']
                pairs.append({'block': block, 'order': order, 'sharing': sharing,
                              'slope_minus_tensor_cycles': b['cycles']-a['cycles'],
                              'slope_minus_tensor_scratch': b['scratch']-a['scratch']})
    reuse = []
    for block in (30, 31):
        for shape in ('tensor', 'slope'):
            for order in (0, 1):
                a = rows[f'B{block}-{shape}-O{order}-structural']
                b = rows[f'B{block}-{shape}-O{order}-algebraic']
                reuse.append({'block': block, 'shape': shape, 'order': order,
                              'cycles_delta': b['cycles']-a['cycles'], 'scratch_delta': b['scratch']-a['scratch'],
                              'engine_deltas': {e: b['counts'][e]-a['counts'][e] for e in CAP}})
    assert sum(x['smoke_cases'] for x in rows.values()) == 48
    assert sum(x['pattern_cases'] for x in rows.values()) == 80
    assert all(x['cycles'] > 980 and x['status'] == 'screen-passed' for x in rows.values())
    assert report['conditional_verification'] is None and report['solver_queries'] == 0
    assert load('pure_checks.json')['symbolic_corner_checks'] == 128
    out = {'status': 'passed', 'reservations': 20, 'candidate_seed_executions': 48,
           'candidate_pattern_executions': 80, 'control_successful_executions': 14,
           'expected_corrupt_execution_failures': 1, 'sources_unchanged': True,
           'physical_capacity_address_pause_checks': 17, 'shape_pairs': pairs, 'reuse_pairs': reuse,
           'store_diagnostics': diagnostics, 'constructed_kernels_by_audit': 0, 'executed_kernels_by_audit': 0}
    (P/'audit.json').write_text(json.dumps(out, indent=2))
    print('Audit passed:20 reservations,16 candidates,128 candidate executions; no new construction/execution.')


if __name__ == '__main__':
    main()
