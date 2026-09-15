"""Local research boundary: finite reservations, source guards, safe lowering."""
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import random
import sys
import time
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/travers/projects/original_performance_takehome')
sys.path.extend([str(ROOT / 'tests')])
import kernel_compiler as compiler
import kernel_retime as retime
import math_variants as variants
from kernel_checks import lane_identity
from frozen_problem import Machine, DebugInfo, Tree, Input, build_mem_image, reference_kernel2

CAPS = {'A': 24, 'B': 12, 'C': 8, 'D': 18, 'E': 12, 'X': 8, 'control': 4, 'validation': 8}
PLAN = json.loads((HERE / 'baseline_plan.json').read_text())


def digest(program):
    return hashlib.sha256(json.dumps(program).encode()).hexdigest()


def hashes(paths, root):
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}


def guard():
    expected = json.loads((HERE / 'protected_sources.json').read_text())
    assert hashes(expected, ROOT) == expected, 'production source changed'
    expected = json.loads((HERE / 'research_sources.json').read_text())
    assert hashes(expected, HERE) == expected, 'research source changed'


def reserve(arm, name):
    guard()
    with (HERE / 'attempts.jsonl').open('a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        rows = [json.loads(x) for x in f if x.strip()]
        assert arm in CAPS
        assert not any(x['name'] == name for x in rows), 'duplicate reservation'
        assert sum(x['arm'] == arm for x in rows) < CAPS[arm], 'arm budget exhausted'
        f.seek(0, 2)
        f.write(json.dumps({'arm': arm, 'name': name, 'at': time.time()})+'\n')
        f.flush()


def build_ir(cfg, module=compiler):
    variants.CFG = cfg
    return module._build_ir(tuple(map(tuple, PLAN['sites'])), advanced=True,
        pairs=tuple(PLAN['pairs']), final_blocks=tuple(PLAN['final_blocks']),
        selector_sites=tuple(map(tuple, PLAN['selector_sites'])))


def allocate_lower(ir, logical, starts, ends, module=compiler):
    addresses, words = module._allocate(ir, starts, ends)
    if words > 1536:
        return None, words, addresses
    lane_identity(ir, logical, addresses)
    program = module._lower(ir, logical, addresses)
    return program, words, addresses


def construct(cfg, module=compiler):
    ir = build_ir(cfg, module)
    logical, starts, ends = module._schedule(ir, lookahead=True, startup=True)
    program, words, addresses = allocate_lower(ir, logical, starts, ends, module)
    cycles = len(logical) + bool(any(e == 'flow' for _, e, _, _ in logical[-1]))
    return ir, logical, addresses, words, program, cycles


def execute(program, seeds=(), patterns=()):
    assert program is not None
    pattern_functions = [lambda i: 0, lambda i: 0xffffffff,
        lambda i: 0xaaaaaaaa if i % 2 else 0x55555555,
        lambda i: 1 << (i % 32), lambda i: (i*0x9e3779b9) & 0xffffffff]
    cases = [(s, None) for s in seeds] + [(30000+p, p) for p in patterns]
    for seed, pattern in cases:
        rng = random.Random(seed)
        ns = [rng.getrandbits(32) if pattern is None else pattern_functions[pattern](i)
              for i in range(2047)]
        vs = [rng.getrandbits(32) if pattern is None else pattern_functions[(pattern+1)%5](i)
              for i in range(256)]
        memory = build_mem_image(Tree(10, ns), Input([0]*256, vs, 16))
        out = memory[6]
        machine = Machine(memory[:], program, DebugInfo({}), n_cores=1)
        machine.enable_debug = False
        machine.enable_pause = True
        machine.run()
        for expected in reference_kernel2(memory[:]):
            pass
        assert machine.mem[out:out+256] == expected[out:out+256], 'output mismatch'
        assert machine.mem[:out] == memory[:out] and machine.mem[out+256:] == memory[out+256:]
        assert len(machine.mem) == len(memory)
        assert machine.cycle == len(program), 'uncharged timing'
    return len(cases)


def diagnostic(ir, logical, program):
    counts = Counter()
    for entries in logical:
        for _, engine, _, count in entries:
            counts[engine] += count
    counts['flow'] += 1
    issue = {}
    for t, entries in enumerate(logical):
        for i, e, f, n in entries:
            issue[i] = max(issue.get(i, -1), t)
    gathers = [(issue[i], getattr(op, 'coord', None)) for i, op in enumerate(ir.ops)
               if op.kind == 'gather']
    last_round = [(t, coord[0]) for t, coord in gathers if coord and coord[1] == 15]
    return {'counts': dict(counts),
            'capacity_lower_bound': max((n+retime.CAP[e]-1)//retime.CAP[e] for e, n in counts.items()),
            'last_gather': max((t for t, _ in gathers), default=None),
            'final_gather_by_block': dict((b,t) for t,b in last_round)}


def row_for(arm, name, cfg, built):
    ir, logical, addresses, words, program, cycles = built
    row = {'arm': arm, 'name': name, 'config': cfg, 'cycles': cycles,
           'scratch': words, 'status': 'scratch-rejected' if program is None else 'legal'}
    if program is not None:
        model = retime.capture(ir, logical)
        retime.validate(model, [j['time'] for j in model['jobs']])
        row.update(diagnostic(ir, logical, program))
        row['digest'] = digest(program)
        row['smoke_cases'] = execute(program, seeds=range(3))
        row['status'] = 'smoke-passed'
    return row


def write_row(row):
    with (HERE / 'results.jsonl').open('a') as f:
        f.write(json.dumps(row)+'\n')
    print(json.dumps({k:row[k] for k in ('arm','name','cycles','scratch','status') if k in row}), flush=True)


def save(name, built, cfg, row):
    ir, logical, addresses, words, program, cycles = built
    directory = HERE / 'artifacts' / name
    directory.mkdir(parents=True, exist_ok=True)
    for filename, value in [('config.json',cfg), ('result.json',row),
                            ('logical.json',logical), ('program.json',program)]:
        (directory/filename).write_text(json.dumps(value))
