"""Bounded exact coefficient recipes. No input values, scheduling or allocation."""
MASK = (1 << 32) - 1


def combine(a, b, sign=1):
    out = dict(a)
    for key, value in b:
        out[key] = (out.get(key, 0) + sign * value) & MASK
    return tuple(sorted((key, value) for key, value in out.items() if value))


def expr(code, a, b):
    return code, a, b


def is_expr(x):
    return isinstance(x[0], str)


class Bank:
    def __init__(self, ir, scalars):
        self.ir = ir
        self.forms = {ref: ((i, 1),) for i, ref in enumerate(scalars)}
        self.scalar = {form: ref for ref, form in self.forms.items()}
        self.vector = {}
        for op in ir.ops:
            if op.kind == 'binary' and op.code in ('+', '-') and ir.widths[op.dst] == 1:
                a, b = op.args
                if a in self.forms and b in self.forms:
                    form = combine(self.forms[a], self.forms[b], 1 if op.code == '+' else -1)
                    ref = (op.dst, 0)
                    self.forms[ref] = form
                    self.scalar.setdefault(form, ref)
            elif op.kind == 'broadcast' and op.args[0] in self.forms:
                self.vector.setdefault(self.forms[op.args[0]], (op.dst, 0))

    def form(self, x):
        if not is_expr(x):
            return self.forms[x]
        code, a, b = x
        return combine(self.form(a), self.form(b), 1 if code == '+' else -1)

    def missing(self, x):
        form = self.form(x)
        if form in self.scalar:
            return set()
        assert is_expr(x), 'missing leaf'
        return {form} | self.missing(x[1]) | self.missing(x[2])

    def emit(self, x):
        form = self.form(x)
        if form in self.scalar:
            self.ir.shared_coefficients = getattr(self.ir, 'shared_coefficients', 0) + 1
            return self.scalar[form]
        code, a, b = x
        ref = self.ir.binary(code, self.emit(a), self.emit(b), preferred='alu', width=1)
        self.forms[ref] = form
        self.scalar[form] = ref
        return ref

    def choose(self, recipes, label):
        target = self.form(recipes[0])
        assert all(self.form(x) == target for x in recipes), 'inequivalent coefficient recipe'
        choices = []
        if target in self.scalar:
            choices.append(self.scalar[target])
        # Single new operation over any known scalar linear forms.
        for fa, a in sorted(self.scalar.items()):
            fb = combine(fa, target, -1)
            if fb in self.scalar:
                choices.append(expr('-', a, self.scalar[fb]))
            fb = combine(target, fa, -1)
            if fb in self.scalar:
                choices.append(expr('+', a, self.scalar[fb]))
        choices += recipes
        index, selected = min(enumerate(choices), key=lambda pair: (len(self.missing(pair[1])), pair[0]))
        extra = len(self.missing(selected))
        start = len(self.ir.ops)
        ref = self.emit(selected)
        assert len(self.ir.ops) - start == extra
        if not hasattr(self.ir, 'coefficient_recipes'):
            self.ir.coefficient_recipes = []
        self.ir.coefficient_recipes.append({'label': label, 'form': target, 'recipe': selected,
                                           'new_scalar_ops': extra, 'choice': index})
        return ref

    def broadcast(self, ref):
        form = self.forms[ref]
        if form in self.vector:
            self.ir.shared_coefficients = getattr(self.ir, 'shared_coefficients', 0) + 1
            return self.vector[form]
        out = self.ir.emit('broadcast', args=(ref,))
        self.vector[form] = out
        return out


def coefficients(ir, scalars, ids, shape):
    bank = Bank(ir, scalars)
    a, b, c, d = [scalars[i] for i in ids]
    h = bank.choose([expr('-', b, a)], 'horizontal')
    v = bank.choose([expr('-', c, a)], 'vertical')
    if shape == 'slope':
        fourth = bank.choose([expr('-', d, b)], 'second-slope')
    else:
        assert shape == 'tensor'
        fourth = bank.choose([
            expr('-', expr('-', d, c), expr('-', b, a)),
            expr('-', expr('-', d, b), expr('-', c, a)),
            expr('+', expr('-', a, b), expr('-', d, c)),
            expr('+', expr('-', a, c), expr('-', d, b)),
            expr('-', expr('+', a, d), expr('+', b, c)),
        ], 'mixed')
    return [bank.broadcast(x) for x in (a, h, v, fourth)]


def structural_slope(ir, scalars, ids):
    differences, broadcasts = {}, {}
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
        differences[a, b] = ref
        return ref

    def broadcast(x):
        if x in broadcasts:
            ir.shared_coefficients = getattr(ir, 'shared_coefficients', 0) + 1
            return broadcasts[x]
        ref = ir.emit('broadcast', args=(x,))
        broadcasts[x] = ref
        return ref

    a, b, c, d = [scalars[i] for i in ids]
    return [broadcast(x) for x in (a, difference(b, a), difference(c, a), difference(d, b))]
