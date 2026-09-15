"""Experimental transformations. Inputs are graph structure/configuration only."""
CFG = {}


def tile_order(b, r, tile):
    for bb, rr, tt, order in CFG.get('tiles', []):
        if (b, r, tile) == (bb, rr, tt):
            return order
    return None


def coefficients(ir, scalars, ids):
    key = tuple(ids)
    cache = getattr(ir, 'basis_cache', None)
    if cache is None:
        ir.basis_cache = cache = {}
    if key not in cache:
        differences, broadcasts = {}, {}
        if CFG.get('share'):
            for op in ir.ops:
                if op.kind == 'binary' and op.code == '-' and ir.widths[op.dst] == 1:
                    differences[op.args] = (op.dst, 0)
                elif op.kind == 'broadcast':
                    broadcasts[op.args[0]] = (op.dst, 0)
        def difference(a, b):
            if (a, b) in differences:
                ir.shared_coefficients = getattr(ir, 'shared_coefficients', 0) + 1
                return differences[a, b]
            ref = ir.binary('-', a, b, preferred='alu', width=1)
            if CFG.get('share'):
                differences[a, b] = ref
            return ref
        def broadcast(x):
            if x in broadcasts:
                ir.shared_coefficients = getattr(ir, 'shared_coefficients', 0) + 1
                return broadcasts[x]
            ref = ir.emit('broadcast', args=(x,))
            if CFG.get('share'):
                broadcasts[x] = ref
            return ref
        refs = [scalars[i] for i in ids]
        for axis in range((len(ids) - 1).bit_length()):
            for index in range(len(refs)):
                if index & (1 << axis):
                    refs[index] = difference(refs[index], refs[index ^ (1 << axis)])
        cache[key] = [broadcast(x) for x in refs]
    return cache[key]


def tile_first(ir, scalars, ids, bits, order):
    if order:
        ids = [ids[0], ids[2], ids[1], ids[3]]
        bits = list(reversed(bits))
    a, h, v, cross = coefficients(ir, scalars, ids)
    return [ir.emit('muladd', args=(bits[0], h, a)),
            ir.emit('muladd', args=(bits[0], cross, v))]


def full_enabled(b, r, depth):
    full = CFG.get('full')
    return bool(full and depth in full['depths'] and (not full['repeated'] or r >= 11))


def full_lookup(ir, scalars, ids, bits):
    if CFG['full']['reverse']:
        d = len(bits)
        ids = [ids[int(f'{j:0{d}b}'[::-1], 2)] for j in range(len(ids))]
        bits = list(reversed(bits))
    entries = coefficients(ir, scalars, ids)
    for bit in bits:
        entries = [ir.emit('muladd', args=(bit, entries[j+1], entries[j]))
                   for j in range(0, len(entries), 2)]
    assert len(entries) == 1
    return entries[0]


def radix_enabled(b, r):
    return [b, r] in CFG.get('branch_sites', [])


def branch(ir, x, shifted):
    # Last affine stage is 9*x + 0xfd7046c5. Its low-bit constant is one.
    def binary(code, a, b):
        return ir.binary(code, a, b, preferred='alu')
    if CFG['branch_kind'] == 'project':
        pre = binary('^', x, ir.vc(1))
        return binary('&', binary('^', pre, shifted), ir.vc(1))
    assert CFG['branch_kind'] == 'radix'
    lo = binary('&', x, ir.vc(65535))
    low_sum = ir.emit('muladd', args=(lo, ir.vc(9), ir.vc(0x46c5)))
    carry = binary('>>', low_sum, ir.vc(16))
    high = binary('>>', x, ir.vc(16))
    pre = binary('^', binary('^', x, high), ir.vc(1))
    return binary('&', binary('^', pre, carry), ir.vc(1))


def geometric_priority(ir, position, priority):
    spec = CFG.get('geometry')
    if not spec:
        return priority
    kind, num, den = spec
    def interleave(a, b):
        return sum(((a >> k) & 1) << (2*k) | ((b >> k) & 1) << (2*k+1)
                   for k in range(5))
    def key(i):
        op = ir.ops[i]
        coord = getattr(op, 'coord', None)
        if coord is None or op.kind in ('const', 'const_choice', 'broadcast', 'vload'):
            return (0, 0, 0, 0, 0, i)
        b, r, h = coord
        if kind.startswith('wave'):
            width = int(kind[4:])
            return (1, r//12, r%12 + b//width, b%width, h, i)
        if kind == 'morton':
            return (1, r//12, interleave(b, r%12), 0, h, i)
        bb = b ^ (b >> 1) if kind == 'gray' else int(f'{b:05b}'[::-1], 2)
        return (1, r//12, bb, r%12, h, i)
    # Alternative structural positions, with the same native operation weights.
    import kernel_compiler as compiler
    alternative = [0] * len(ir.ops)
    total = 0
    for i in sorted(range(len(ir.ops)), key=key):
        alternative[i] = total
        total += compiler._engine_cost(ir.ops[i], ir.widths)[1]
    return [p + num*(q-r)//den for p, q, r in zip(priority, alternative, position)]
