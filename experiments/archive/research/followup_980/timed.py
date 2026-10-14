"""Experimental selected-timing replay. No saved physical instructions or addresses.

Rebuild semantic SSA from the selected configuration; consume a timing assignment
(key, engine, lane, cycle), check full coverage, allocate, then lower. This is NOT
automatic production schedule discovery.
"""
from collections import defaultdict
from generator import build_ir,kernel,compiler
from checker import lane_identity
from model import refs,validate

def build(cfg,assignment,force_scratch=None):
 ir=build_ir(cfg);lookup={k:i for i,k in enumerate(ir.semantic_keys)}
 jobs=[];producer={};seen=defaultdict(list)
 for key,e,f,t in assignment:
  assert type(t) is int and t>=0 and type(f) is int
  if key=='pause':
   assert e=='flow' and f==0
   jobs.append({'op':None,'engine':'flow','first':0,'time':t,'pause':True,'reads':[],'writes':[]});continue
  assert key in lookup,'unknown semantic timing key'
  i=lookup[key];op=ir.ops[i]
  allowed=('alu','valu') if op.kind=='binary' and ir.widths[op.dst]==8 else ('alu',) if op.kind=='binary' else ('load','flow') if op.kind=='const_choice' else (compiler._engine_cost(op,ir.widths)[0],)
  assert e in allowed,('illegal fixed mode',i,e)
  partial=op.kind=='gather' or (op.kind=='binary' and e=='alu')
  assert 0<=f<(ir.widths[op.dst] if partial else 1)
  seen[i].append((e,f))
  ws=[] if op.dst is None else [(op.dst,l) for l in ([f] if partial else range(ir.widths[op.dst]))]
  n={'op':i,'engine':e,'first':f,'time':t,'pause':False,'reads':refs(ir,op,e,f),'writes':ws}
  for r in ws:assert r not in producer,'duplicate timed lane';producer[r]=len(jobs)
  jobs.append(n)
 assert set(seen)==set(range(len(ir.ops))),'operation coverage'
 for i,rows in seen.items():
  engines={e for e,f in rows};assert len(engines)==1,'mixed engine modes'
  e=next(iter(engines));op=ir.ops[i];partial=op.kind=='gather' or (op.kind=='binary' and e=='alu')
  assert sorted(f for e,f in rows)==list(range(ir.widths[op.dst] if partial else 1)),'lane coverage'
 edges=sorted({(producer[tuple(r)],i,1) for i,j in enumerate(jobs) for r in j['reads']})
 m={'jobs':jobs,'edges':edges,'ops':[op.__dict__ for op in ir.ops],'widths':ir.widths}
 times=[j['time'] for j in jobs];validate(m,times)
 assert sum(j['pause'] for j in jobs)==1
 logical=[[] for _ in range(max(times)+1)]
 for n in jobs:
  if n['op'] is not None:logical[n['time']].append((n['op'],n['engine'],n['first'],1))
 starts={};ends={}
 for c,b in enumerate(logical):
  for i,e,f,count in b:
   op=ir.ops[i]
   if op.dst is not None:starts[op.dst]=min(starts.get(op.dst,c),c);ends[op.dst]=max(ends.get(op.dst,0),c+.5)
   for v,o in op.args:ends[v]=max(ends.get(v,0),c)
 addresses,scratch=compiler._allocate(ir,starts,ends)
 if force_scratch is not None:scratch=force_scratch
 if scratch>1536:return ir,logical,addresses,kernel([],scratch)
 lane_identity(ir,logical,addresses)
 program=compiler._lower(ir,logical,addresses);assert len(program)==len(logical)
 return ir,logical,addresses,kernel(program,scratch)
