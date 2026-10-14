"""Permutation-only policy seam; all actual issue legality stays in the compiler."""
import math
K=32
KINDS=['const','const_choice','vload','gather','binary','broadcast','muladd','select','vstore']
ENGINES=['alu','valu','load','flow','store']
FEATURES=['priority_gap','critical','load_distance','gained','freed','ready_fraction','started','fanout','cycle','live_words','ready_count','action_candidate','baseline_candidate']+KINDS+ENGINES

def apply(policy,ir,ordered,key,ready_mask,modes,remaining,available,critical,distance,cycle):
    from kernel_compiler import _engine_cost
    positions=[];ms=[]
    for pos,i in enumerate(ordered):
        mask=ready_mask(i)
        if mask:positions.append(pos);ms.append(mask)
        if len(positions)==K:break
    if not positions:return ordered
    live=sum(w for v,w in enumerate(ir.widths) if available[v] and remaining[v])
    base=key(ordered[positions[0]])[0];xs=[]
    for j,(pos,mask) in enumerate(zip(positions,ms)):
        i=ordered[pos];op=ir.ops[i];width=ir.widths[op.dst] if op.dst is not None else 0
        freed=sum(ir.widths[v] for v in {v for v,_ in op.args} if remaining[v]==1)
        gain=0 if op.dst is None or i in modes else width
        engine=_engine_cost(op,ir.widths,modes.get(i))[0]
        x=[min(32,(key(i)[0]-base)/256),critical[i]/256,distance[i]/4,gain/8,freed/32,
           min(1,mask.bit_count()/max(width,1)),float(i in modes),min(32,remaining[op.dst] if op.dst is not None else 0)/32,
           cycle/1024,live/1536,len(positions)/K,float(j<4),float(j==0)]
        x += [float(op.kind==k) for k in KINDS]+[float(engine==e) for e in ENGINES]
        assert len(x)==len(FEATURES) and all(math.isfinite(v) for v in x)
        xs.append(x)
    count=len(xs);xs += [[0.0]*len(FEATURES) for _ in range(K-count)]
    action=policy.choose(xs,count,cycle)
    assert isinstance(action,int) and 0<=action<min(4,count),'illegal policy action'
    if not hasattr(ir,'frontier_actions'):ir.frontier_actions=[]
    target=ordered[positions[action]]
    ir.frontier_actions.append({'cycle':cycle,'action':action,'semantic_key':ir.semantic_keys[target],'scope':ir.ops[target].scope})
    if action:
        chosen=[ordered[p] for p in positions[:action+1]]
        chosen=[chosen[-1]]+chosen[:-1]
        for pos,i in zip(positions,chosen):ordered[pos]=i
    return ordered

class Trace:
    def __init__(self,points):self.points=set(points);self.rows={}
    def wants(self,c):return c in self.points
    def choose(self,x,n,c):self.rows[c]={'features':x,'count':n,'cycle':c};return 0

class Override:
    def __init__(self,cycle,action):self.cycle=cycle;self.action=action;self.calls=0
    def wants(self,c):return c==self.cycle
    def choose(self,x,n,c):
        self.calls+=1;assert self.action<min(4,n)
        return self.action
