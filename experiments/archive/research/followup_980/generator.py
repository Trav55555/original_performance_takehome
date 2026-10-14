"""Source-only experimental generation: input values and runtime APIs unavailable."""
from types import SimpleNamespace
import kernel_compiler as compiler
from problem import DebugInfo,SCRATCH_SIZE
from checker import lane_identity

def build_ir(cfg,reference=False):
    ir=compiler._build_ir(tuple(sorted(map(tuple,cfg['sites']))),advanced=True,
        pairs=tuple(cfg.get('pairs',(2,3))),early_sites=tuple(map(tuple,cfg.get('early_sites',((0,3),)))),
        final_blocks=() if reference else cfg.get('final_blocks',()),
        final_engines=tuple(cfg.get('final_engines',('valu','alu','valu'))),
        selector_sites=cfg.get('selector_sites',()),difference_policy=cfg.get('difference_policy','shared'))
    return ir

def kernel(program,scratch):
    return SimpleNamespace(instrs=program,scratch_ptr=scratch,debug_info=lambda:DebugInfo({}))

def compile_config(cfg,policy=None,observer=None):
    ir=build_ir(cfg)
    ir.decision_observer=observer
    ir.restore_critical=bool(cfg.get('restore_critical',False))
    ir.restore_position=bool(cfg.get('restore_position',False))
    if ir.restore_critical or ir.restore_position:ir.priority_reference=build_ir(cfg,reference=True)
    ir.forecast_config=cfg.get('forecast',{})
    if policy is None and cfg.get('edits'):
        from plans import Planned
        policy=Planned(cfg['edits'])
    ir.frontier_policy=policy
    logical,starts,ends=compiler._schedule(ir,lookahead=True,startup=True)
    addresses,scratch=compiler._allocate(ir,starts,ends)
    ir.lifetimes=(starts,ends)
    if scratch>SCRATCH_SIZE:
        return ir,logical,addresses,kernel([],scratch)
    assert all(0<=a and a+ir.widths[v]<=SCRATCH_SIZE for v,a in addresses.items())
    lane_identity(ir,logical,addresses)
    program=compiler._lower(ir,logical,addresses)
    return ir,logical,addresses,kernel(program,scratch)
