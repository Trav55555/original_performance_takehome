"""Native-engine SSA instruction jobs, independently joined to physical reads."""
from collections import Counter,defaultdict
import hashlib,json
CAP={'alu':12,'valu':6,'load':2,'store':2,'flow':1}
def rw(e,s):
 vec=lambda a:set(range(a,a+8));op=s[0]
 if e=='alu':return {s[2],s[3]},{s[1]}
 if e=='valu':return ({s[2]} if op=='vbroadcast' else set().union(*(vec(a) for a in s[2:]))),vec(s[1])
 if e=='load':
  if op=='const':return set(),{s[1]}
  if op=='vload':return {s[2]},vec(s[1])
  if op=='load':return {s[2]},{s[1]}
 if e=='store':return ({s[1]}|vec(s[2]) if op=='vstore' else {s[1],s[2]}),set()
 if e=='flow':
  if op=='pause':return set(),set()
  if op=='add_imm':return {s[2]},{s[1]}
  if op=='vselect':return set().union(*(vec(a) for a in s[2:])),vec(s[1])
 raise AssertionError((e,s))
def refs(ir,op,e,f):
 if op.kind in ('binary','gather'):
  lanes=[f] if e=='alu' or op.kind=='gather' else range(ir.widths[op.dst])
  return [(v,o+l) for v,o in op.args for l in lanes]
 sizes=[1,8] if op.kind=='vstore' else [1] if op.kind in ('vload','broadcast','const_choice') else [8]*len(op.args)
 if op.kind=='const_choice' and e=='load':return []
 return [(v,o+l) for (v,o),w in zip(op.args,sizes) for l in range(w)]
def capture(ir,logical,addresses,k,cfg):
 jobs=[];producer={}
 for t,bundle in enumerate(k.instrs):
  queues={e:iter(ss) for e,ss in bundle.items()}
  for i,e,f,n in logical[t] if t<len(logical) else []:
   assert n==1
   op=ir.ops[i];s=next(queues[e]);rs=refs(ir,op,e,f)
   ws=[] if op.dst is None else [(op.dst,l) for l in ([f] if op.kind=='gather' or (op.kind=='binary' and e=='alu') else range(ir.widths[op.dst]))]
   pr,pw=rw(e,s)
   assert pr=={addresses[v]+l for v,l in rs} and pw=={addresses[v]+l for v,l in ws},('physical/SSA operands',i)
   j=len(jobs)
   for r in ws:assert r not in producer;producer[r]=j
   jobs.append({'time':t,'engine':e,'pause':False,'op':i,'first':f,'slot':s,'reads':rs,'writes':ws,'scope':op.scope,'semantic':ir.semantic_keys[i]})
  for e,q in queues.items():
   for s in q:
    assert e=='flow' and tuple(s)==('pause',)
    jobs.append({'time':t,'engine':e,'pause':True,'op':None,'first':0,'slot':s,'reads':[],'writes':[],'scope':['pause'],'semantic':'pause'})
 edges=sorted({(producer[tuple(r)],j,1) for j,n in enumerate(jobs) for r in n['reads']})
 physical=set();owners={};cycles=defaultdict(list)
 for j,n in enumerate(jobs):cycles[n['time']].append(j)
 for t,ids in sorted(cycles.items()):
  pending={}
  for j in ids:
   rs,ws=rw(jobs[j]['engine'],jobs[j]['slot'])
   for a in rs:assert a in owners;physical.add((owners[a],j,1))
   for a in ws:assert a not in pending;pending[a]=j
  owners.update(pending)
 assert set(edges)==physical,'SSA/physical RAW edges differ'
 assert all(a<b and jobs[a]['time']<jobs[b]['time'] for a,b,d in edges)
 assert len([n for n in jobs if n['pause']])==1
 m={'config':cfg,'jobs':jobs,'edges':edges,'native_digest':hashlib.sha256(json.dumps(k.instrs).encode()).hexdigest(),'scratch':k.scratch_ptr,'cycles':len(k.instrs),'ops':[op.__dict__ for op in ir.ops],'widths':ir.widths,'SSA_physical_RAW_equality':True}
 validate(m,[n['time'] for n in jobs]);return m

def assert_graph(m):
 if 'ops' not in m:return
 producers={}
 for i,n in enumerate(m['jobs']):
  for r in n['writes']:
   r=tuple(r);assert r not in producers,'duplicate written lane';producers[r]=i
 expected_lanes={(op['dst'],l) for op in m['ops'] if op['dst'] is not None for l in range(m['widths'][op['dst']])}
 assert set(producers)==expected_lanes,'lane coverage'
 expected={(producers[tuple(r)],j,1) for j,n in enumerate(m['jobs']) for r in n['reads']}
 assert expected==set(map(tuple,m['edges'])),'missing or spurious data dependency'

def validate(m,times,lo=None,hi=None):
 assert_graph(m)
 assert len(times)==len(m['jobs']) and all(type(t) is int and t>=0 for t in times)
 if lo is not None:assert all(a<=t<=b for a,t,b in zip(lo,times,hi))
 assert all(times[b]>=times[a]+d for a,b,d in m['edges']),'dependency timing'
 use=Counter((t,n['engine']) for t,n in zip(times,m['jobs']))
 assert all(n<=CAP[e] for (t,e),n in use.items()),'capacity'
 pauses=[t for t,j in zip(times,m['jobs']) if j['pause']]
 if pauses:assert len(pauses)==1 and pauses[0]==max(times),'pause before completion'

def bounds(m,start,target,radius=8):
 assert_graph(m)
 jobs=m['jobs'];lo=[j['time'] if j['time']<start else max(start,j['time']-radius) for j in jobs];hi=[j['time'] if j['time']<start else min(target-1,j['time']+radius) for j in jobs]
 for i,j in enumerate(jobs):
  if j['pause']:lo[i]=hi[i]=target-1
 for a,b,d in m['edges']:lo[b]=max(lo[b],lo[a]+d)
 for a,b,d in reversed(m['edges']):hi[a]=min(hi[a],hi[b]-d)
 # Edges are sorted by source. Reverse order propagates bounds through all successors.
 conflict=next(({'job':i,'lower':l,'upper':h} for i,(l,h) in enumerate(zip(lo,hi)) if l>h),None)
 return lo,hi,conflict

def project(m,lo,hi):
 assert all(l<=h for l,h in zip(lo,hi))
 free=[i for i,(l,h) in enumerate(zip(lo,hi)) if l!=h];fs=set(free)
 fixed={i:l for i,(l,h) in enumerate(zip(lo,hi)) if l==h}
 occupied=Counter((m['jobs'][i]['engine'],t) for i,t in fixed.items())
 for (e,t),n in occupied.items():assert n<=CAP[e],('fixed capacity',e,t,n)
 edges=[];boundary=[]
 for a,b,d in m['edges']:
  if a in fs and b in fs:edges.append((a,b,d))
  elif a in fs:assert hi[a]+d<=fixed[b];boundary.append((a,b,d))
  elif b in fs:assert fixed[a]+d<=lo[b];boundary.append((a,b,d))
  else:assert fixed[b]>=fixed[a]+d,('fixed edge',a,b,d)
 return {'free':free,'fixed':fixed,'edges':edges,'boundary':boundary,'occupied':occupied}

def cuts(m,lo,hi,start,target):
 N=target-start;out=[]
 for e,cap in CAP.items():
  hist=[[0]*N for _ in range(N)]
  for i,j in enumerate(m['jobs']):
   if j['engine']==e and lo[i]>=start and hi[i]<target:hist[lo[i]-start][hi[i]-start]+=1
  for a in reversed(range(N)):
   for b in range(N):hist[a][b]+=(hist[a+1][b] if a+1<N else 0)+(hist[a][b-1] if b else 0)-(hist[a+1][b-1] if a+1<N and b else 0)
  options=[(hist[a][b]-cap*(b-a+1),a,b,hist[a][b]) for a in range(N) for b in range(a,N) if hist[a][b]]
  if not options:continue
  overload,a,b,work=max(options);a+=start;b+=start
  ids=[i for i,j in enumerate(m['jobs']) if j['engine']==e and lo[i]>=a and hi[i]<=b]
  assert len(ids)==work
  out.append({'engine':e,'from':a,'through':b,'work':work,'capacity':cap,'overload':overload,'jobs':ids})
 return out

def preflight(m,start,target=980):
 lo,hi,conflict=bounds(m,start,target);r={'start':start,'target':target,'radius':8,'conflict':conflict,'jobs':len(m['jobs']),'edges':len(m['edges']),'admitted':False}
 if conflict:return r
 cs=cuts(m,lo,hi,start,target);r['cuts']=cs
 r['free_variables']=sum(l!=h for l,h in zip(lo,hi));r['membership_terms']=sum(h-l+1 for l,h in zip(lo,hi) if l!=h)
 if any(c['overload']>0 for c in cs):r['rejection']='mandatory capacity overload';return r
 p=project(m,lo,hi);r['projected_edges']=len(p['edges']);r['boundary_edges']=len(p['boundary']);r['fixed_jobs']=len(p['fixed'])
 r['admitted']=r['free_variables']<=2048 and r['membership_terms']<=32768
 if not r['admitted']:r['rejection']='structural admission caps'
 return r

def reconstruct(m,times,ir=None,force_scratch=None):
 from generator import build_ir,kernel,compiler
 from checker import lane_identity
 validate(m,times)
 if ir is None:ir=build_ir(m['config'])
 assert len(ir.ops)==len(m['ops'])
 assert [ir.semantic_keys[n['op']] for n in m['jobs'] if n['op'] is not None]==[n['semantic'] for n in m['jobs'] if n['op'] is not None]
 logical=[[] for _ in range(max(times)+1)]
 for n,t in zip(m['jobs'],times):
  if n['op'] is not None:logical[t].append((n['op'],n['engine'],n['first'],1))
 # Never compact empty cycles: fixed-prefix and witness times remain intact.
 starts={};ends={}
 for t,b in enumerate(logical):
  for i,e,f,n in b:
   op=ir.ops[i]
   if op.dst is not None:starts[op.dst]=min(starts.get(op.dst,t),t);ends[op.dst]=max(ends.get(op.dst,0),t+.5)
   for v,o in op.args:ends[v]=max(ends.get(v,0),t)
 addresses,scratch=compiler._allocate(ir,starts,ends)
 if force_scratch is not None:scratch=force_scratch
 if scratch>1536:return {'status':'scratch-rejected','scratch':scratch,'lower_calls':0},None
 lane_identity(ir,logical,addresses)
 program=compiler._lower(ir,logical,addresses);k=kernel(program,scratch)
 assert len(program)==max(times)+1
 return {'status':'allocated','cycles':len(program),'scratch':scratch,'digest':hashlib.sha256(json.dumps(program).encode()).hexdigest(),'lane_identity':True},k

def solve(m,lo,hi,witness=None,on_ready=None):
 import z3,time
 p=project(m,lo,hi);s=z3.Solver();s.set(timeout=0)
 ts={i:z3.Int('t'+str(i)) for i in p['free']}
 for i,t in ts.items():
  s.add(t>=lo[i],t<=hi[i])
  if witness is not None:s.add(t==witness[i])
 for a,b,d in p['edges']:
  if hi[a]+d>lo[b]:s.add(ts[b]>=ts[a]+d)
 bycycle=defaultdict(list)
 for i,t in ts.items():
  for c in range(lo[i],hi[i]+1):bycycle[m['jobs'][i]['engine'],c].append((t==c,1))
 terms=0
 for (e,c),xs in bycycle.items():
  cap=CAP[e]-p['occupied'].get((e,c),0)
  if len(xs)>cap:s.add(z3.PbLe(xs,cap));terms+=len(xs)
 info={'free_variables':len(ts),'potential_membership_terms':sum(hi[i]-lo[i]+1 for i in ts),'encoded_capacity_terms':terms,'fixed_jobs_removed':len(p['fixed']),'free_edges':len(p['edges']),'boundary_edges_checked':len(p['boundary']),'timeout_ms':0}
 if witness is not None:
  assert all(witness[i]==t for i,t in p['fixed'].items())
 if on_ready:on_ready(info)
 begin=time.monotonic();status=s.check();r={**info,'status':str(status),'solver_seconds':time.monotonic()-begin}
 if status==z3.unknown:r['reason']=s.reason_unknown()
 if status==z3.sat:
  sm=s.model();times=[p['fixed'][i] if i in p['fixed'] else sm.eval(ts[i]).as_long() for i in range(len(m['jobs']))]
  validate(m,times,lo,hi);r['times']=times
 r['statistics']={k:s.statistics().get_key_value(k) for k in s.statistics().keys()}
 return r
