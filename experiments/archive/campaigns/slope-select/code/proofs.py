"""Independent symbolic interpreter for the emitted micro-IR, not a simulator."""
import itertools
from research import compiler, variants
from linear_coefficients import coefficients as algebraic

MOD = 1 << 32


def normalized(d):
    return {key: value % MOD for key, value in d.items() if value % MOD}


def plus(a, b, sign=1):
    d = a.copy()
    for key, value in b.items():
        d[key] = d.get(key, 0) + sign * value
    return normalized(d)


def constant(x):
    assert set(x) <= {-1}, 'nonconstant condition/address'
    return x.get(-1, 0)


def multiply(a, b):
    if set(a) <= {-1}:
        return normalized({key: constant(a) * value for key, value in b.items()})
    assert set(b) <= {-1}, 'nonlinear node-data product'
    return normalized({key: constant(b) * value for key, value in a.items()})


def interpret(ir):
    vals = {}
    def get(ref, lane=0):
        return vals[ref[0]][ref[1] + lane]
    for op in ir.ops:
        width = ir.widths[op.dst]
        if op.kind == 'const':
            result = [normalized({-1: op.imm})]
        elif op.kind == 'load':
            result = [{constant(get(op.args[0])): 1}]
        elif op.kind == 'broadcast':
            result = [get(op.args[0]).copy() for _ in range(width)]
        else:
            result = []
            for lane in range(width):
                args = [get(ref, lane) for ref in op.args]
                if op.kind == 'binary':
                    assert op.code in ('+', '-')
                    value = plus(args[0], args[1], 1 if op.code == '+' else -1)
                elif op.kind == 'muladd':
                    value = plus(multiply(args[0], args[1]), args[2])
                else:
                    assert op.kind == 'select'
                    bit = constant(args[0]); assert bit in (0, 1)
                    value = args[1 if bit else 2]
                result.append(value)
        vals[op.dst] = result
    return vals


def fixture(ids, preloaded, shape, sharing, order, address):
    ir = compiler._IR()
    scalars = [ir.emit('load', args=(ir.const(i),), width=1) for i in range(8)]
    for ref in scalars:
        ir.emit('broadcast', args=(ref,))
    pairs = {}
    if preloaded:
        for high, low in ((ids[1], ids[0]), (ids[3], ids[2])):
            ref = ir.binary('-', scalars[high], scalars[low], preferred='alu', width=1)
            pairs[high, low] = ir.emit('broadcast', args=(ref,))
    bits = [ir.vc(address & 1), ir.vc(address >> 1)]
    start = len(ir.ops)
    variants.CFG = {'shape': shape, 'sharing': sharing, 'share': True}
    base, slope = variants.tile_first(ir, scalars, ids, bits, order)
    result = ir.emit('muladd', args=(bits[0 if order else 1], slope, base))
    return ir, scalars, result, pairs, start


def run():
    count = 0
    for ids, preloaded, shape, sharing, order, address in itertools.product(
            ([0, 1, 2, 3], [4, 6, 5, 7]), (False, True), ('tensor', 'slope'),
            ('structural', 'algebraic'), (0, 1), range(4)):
        ir, _, result, _, _ = fixture(ids, preloaded, shape, sharing, order, address)
        got = interpret(ir)[result[0]]
        assert got == [{ids[address]: 1}] * 8, (ids, preloaded, shape, sharing, order, address, got)
        count += 1
    assert count == 128
    ir, _, result, pairs, _ = fixture([0, 1, 2, 3], True, 'slope', 'structural', 0, 3)
    trace = ir.tile_traces[0]
    op = ir.ops[ir.producer[trace['slope'][0]]]
    op.args = (op.args[0], pairs[3, 2], op.args[2])
    assert interpret(ir)[result[0]] != [{3: 1}] * 8, 'wrong slope accepted'
    ir, scalars, _, _, _ = fixture([0, 1, 2, 3], True, 'tensor', 'algebraic', 0, 3)
    first = algebraic(ir, scalars, [0, 1, 2, 3], 'tensor')
    second = algebraic(ir, scalars, [0, 2, 1, 3], 'tensor')
    assert first[3] == second[3], 'mixed difference was not shared across axes'
    assert first[1] == second[2] and first[2] == second[1]
    new_ops = {}
    for sharing in ('structural', 'algebraic'):
        ir, _, result, _, start = fixture([0, 1, 2, 3], True, 'tensor', sharing, 1, 3)
        new_ops[sharing] = sum(op.kind == 'binary' and ir.widths[op.dst] == 1 for op in ir.ops[start:])
        assert interpret(ir)[result[0]] == [{3: 1}] * 8
    assert new_ops == {'structural': 3, 'algebraic': 2}
    variants.CFG = {}
    return {'symbolic_corner_checks': count, 'all_eight_lanes_checked': True,
            'wrong_slope_rejected': True, 'cross_axis_coefficient_identity': True,
            'reversed_tensor_new_scalar_ops': new_ops}
