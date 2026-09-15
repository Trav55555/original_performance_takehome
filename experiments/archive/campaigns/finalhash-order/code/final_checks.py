"""Final hash proof and explicitly scoped experimental verification helpers."""
import copy
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import importlib.util
import json
import random
import sys
import unittest
from unittest.mock import patch
import research as R


def algebra():
    c = 0xb55a4f09
    assert R.compiler._C == c
    words = [0] + [1 << k for k in range(32)]
    for u in words:
        assert (u ^ (u >> 16)) ^ c == (u ^ c) ^ (u >> 16)
    assert ((0 ^ c) ^ ((0 ^ c) >> 16)) != ((0 ^ (0 >> 16)) ^ c)
    return {'affine_GF2_basis_cases':33, 'wrong_shift_input_rejected':True,
            'limit':'Both expressions are affine over GF(2); actual emitter wiring checked by frozen execution.'}


def oracle_blocked_construct(construct, spec):
    names = ('Machine','Tree','Input','build_mem_image','reference_kernel','reference_kernel2','execute')
    def forbidden(*args, **kwargs):
        raise AssertionError('oracle forbidden during generation')
    modules = [R, R.compiler] + [sys.modules[n] for n in ('problem','frozen_problem') if n in sys.modules]
    with ExitStack() as stack:
        for module in modules:
            for name in names:
                if hasattr(module,name): stack.enter_context(patch.object(module,name,side_effect=forbidden))
        try: R.execute(None)
        except AssertionError as e: assert str(e)=='oracle forbidden during generation'
        else: raise AssertionError('oracle guard inactive')
        return construct(spec)


def frozen_suite(program, cycles):
    """Replay through unchanged frozen tests, not through the production builder."""
    class ReplayBuilder:
        def build_kernel(self, height, nodes, batch, rounds):
            assert (height,nodes,batch,rounds)==(10,2047,256,16)
            self.instrs=copy.deepcopy(program)
        def debug_info(self): return R.DebugInfo({})
    source = R.ROOT/'tests/submission_tests.py'
    spec = importlib.util.spec_from_file_location('finalhash_frozen_submission',source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.KernelBuilder=ReplayBuilder
    random.seed(8087)
    with (R.HERE/'submission.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
        suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        actual=module.cycles()
    assert result.wasSuccessful() and result.testsRun==9 and actual==cycles
    receipt={'tests':9,'status':'passed','observed_cycles':actual,
             'adapter':'saved experimental program replay; production builder not exercised',
             'full_incumbent_gates':False}
    (R.HERE/'submission.json').write_text(json.dumps(receipt,indent=2))
    return receipt
