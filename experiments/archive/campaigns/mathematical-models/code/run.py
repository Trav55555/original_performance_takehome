"""Execute the declared finite five-arm program. No solver or production search."""
import copy
import importlib.util
import json
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch

import research as R
import event
from research import compiler, retime, variants


def pure_checks():
    class Evaluator:
        def __init__(self): self.values = []
        def const(self, value):
            self.values.append(value & 0xffffffff)
            return (len(self.values)-1, 0)
        vc = const
        def binary(self, code, a, b, **kwargs):
            x, y = self.values[a[0]], self.values[b[0]]
            value = {'-': lambda:x-y, '^':lambda:x^y, '&':lambda:x&y, '>>':lambda:x>>y}[code]()
            return self.const(value)
        def emit(self, kind, args, **kwargs):
            xs = [self.values[a[0]] for a in args]
            return self.const(xs[0] if kind == 'broadcast' else xs[0]*xs[1]+xs[2])
    rng = random.Random(1701)
    counts = {'recursive':0, 'tile':0, 'branch':0}
    for _ in range(64):
        for depth in (3,4):
            values = [rng.getrandbits(32) for _ in range(1<<depth)]
            for reverse in (False,True):
                variants.CFG = {'full':{'reverse':reverse}}
                for address in range(1<<depth):
                    e = Evaluator(); scalars = [e.const(x) for x in values]
                    bits = [e.const((address>>k)&1) for k in range(depth)]
                    ref = variants.full_lookup(e, scalars, list(range(1<<depth)), bits)
                    assert e.values[ref[0]] == values[address]
                    counts['recursive'] += 1
        values = [rng.getrandbits(32) for _ in range(4)]
        for order in (0,1):
            for address in range(4):
                e=Evaluator(); scalars=[e.const(x) for x in values]
                bits=[e.const(address&1),e.const(address>>1)]
                u,v=variants.tile_first(e,scalars,list(range(4)),bits,order)
                ref=e.emit('muladd',args=(bits[0 if order else 1],v,u))
                assert e.values[ref[0]] == values[address]
                counts['tile'] += 1
    for x in [0,5268,5269,65535,65536,0x7fffffff,0x80000000,0xffffffff]+[rng.getrandbits(32) for _ in range(1024)]:
        u=(9*x+0xfd7046c5)&0xffffffff
        for kind in ('project','radix'):
            variants.CFG={'branch_kind':kind}
            e=Evaluator(); ref=variants.branch(e,e.const(x),e.const(u>>16))
            assert e.values[ref[0]] == ((u^(u>>16))&1)
            counts['branch'] += 1
    variants.CFG={}
    return counts


def controls():
    R.reserve('control','original-native')
    spec=importlib.util.spec_from_file_location('original_compiler', R.HERE/'original/kernel_compiler.py')
    original=importlib.util.module_from_spec(spec);sys.modules[spec.name]=original;spec.loader.exec_module(original)
    baseline=R.construct({},original)
    assert baseline[3] == 1465 and baseline[5] == 981
    assert R.execute(baseline[4],seeds=range(3))==3
    R.write_row({'arm':'control','name':'original-native','cycles':981,'scratch':1465,'status':'passed','digest':R.digest(baseline[4])})
    R.reserve('control','isolated-native')
    native=R.construct({})
    assert native[4]==baseline[4] and native[3]==baseline[3]
    R.write_row(R.row_for('control','isolated-native',{},native))
    R.save('native',native,{}, {'cycles':981,'scratch':1465,'digest':R.digest(native[4])})
    R.reserve('control','published980-replay')
    ir=native[0]
    logical=json.loads(Path('/tmp/perf-promote980-run.qim8Di/refined_logical.json').read_text())
    model=retime.capture(ir,logical)
    times=[j['time'] for j in model['jobs']]
    program,words,_,_=retime.lower(ir,model,times)
    assert words==1465 and len(program)==980
    assert R.digest(program)=='c17788082bd3757c95f02bd743582ff1acd3f55c56e3326d9fc72e65da7ba5bc'
    assert R.execute(program,seeds=range(3),patterns=range(5))==8
    R.write_row({'arm':'control','name':'published980-replay','cycles':980,'scratch':words,'status':'passed','digest':R.digest(program)})
    for words in (1537,1545):
        with patch.object(compiler,'_allocate',return_value=({},words)), patch.object(compiler,'_lower',side_effect=AssertionError('forbidden')) as lower:
            assert R.allocate_lower(ir,[],{}, {})[:2]==(None,words)
            lower.assert_not_called()
    attempts=(R.HERE/'attempts.jsonl').read_text()
    with patch.object(R,'CAPS',dict(R.CAPS,A=0)):
        try:R.reserve('A','zero-budget-control')
        except AssertionError as error:assert str(error)=='arm budget exhausted'
        else:raise AssertionError('budget bypass')
    assert (R.HERE/'attempts.jsonl').read_text()==attempts
    corrupt=copy.deepcopy(program);changed=False
    for bundle in corrupt:
        for engine in ('load','flow'):
            for i,slot in enumerate(bundle.get(engine,[])):
                if (slot[0]=='const' and slot[-1]==0xb55a4f09) or (slot[0]=='add_imm' and slot[-1]==0xb55a4f09-7):
                    bundle[engine][i]=tuple(slot[:-1])+(slot[-1]^2,);changed=True;break
            if changed:break
        if changed:break
    assert changed
    try:R.execute(corrupt,seeds=[0])
    except AssertionError as error:assert str(error)=='output mismatch'
    else:raise AssertionError('corruption accepted')
    R.reserve('control','event-toy')
    variants.CFG={}; toy=compiler._IR(); ptr=toy.const(0); scalar=toy.const(41)
    vector=toy.emit('broadcast',args=(scalar,));toy.emit('vstore',args=(ptr,vector),width=0)
    logical=[[(0,'load',0,1),(1,'load',0,1)],[],[],[],[(2,'valu',0,1)],[],[],[],[(3,'store',0,1)]]
    model=retime.capture(toy,logical)
    times,info=event.compact(model,toy)
    out,words,_,_=retime.lower(toy,model,times)
    assert len(out)==3
    from frozen_problem import Machine,DebugInfo
    machine=Machine([0]*8,out,DebugInfo({}),n_cores=1);machine.run()
    assert machine.mem==[41]*8 and machine.cycle==3
    R.write_row({'arm':'control','name':'event-toy','cycles':3,'scratch':words,'status':'passed','native_cycles':9})
    return native


def candidates(native):
    ir,logical,*_=native
    tiles={}; penultimate={}
    for time, entries in enumerate(logical):
        for i,e,f,n in entries:
            op=ir.ops[i]
            if op.site:
                b,r,layer,leaf=op.site
                if layer==0:tiles[b,r,leaf//2]=max(time,tiles.get((b,r,leaf//2),-1))
            coord=getattr(op,'coord',None)
            if coord and coord[1]==14 and coord[2]==6 and op.kind=='binary' and op.code=='&':
                penultimate[coord[0]]=max(time,penultimate.get(coord[0],-1))
    chosen=sorted(tiles,key=lambda k:(-tiles[k],k))[:12]
    branches=sorted(penultimate,key=lambda b:(-penultimate[b],b))[:4]
    rows=[]
    for tile in chosen:
        for order in (0,1):rows.append(('A',{'tiles':[[*tile,order]]}))
    for depths in ([3],[4],[3,4]):
        for repeated in (False,True):
            for reverse in (False,True):rows.append(('B',{'full':{'depths':depths,'repeated':repeated,'reverse':reverse}}))
    for b in branches:
        for kind in ('radix','project'):rows.append(('C',{'branch_sites':[[b,14]],'branch_kind':kind}))
    for kind in ('wave4','wave8','wave16','morton','gray','bitreverse'):
        for num,den in ((1,8),(1,2),(1,1)):rows.append(('D',{'geometry':[kind,num,den]}))
    for order in ('native','reverse','tail','short','block','reverse-block'):
        for start in (0,981-128):rows.append(('E',{'event':{'order':order,'start':start}}))
    counts={a:0 for a in 'ABCDE'};out=[]
    for arm,cfg in rows:
        counts[arm]+=1;out.append({'arm':arm,'name':f'{arm}{counts[arm]:02}','config':cfg})
    assert counts=={a:R.CAPS[a] for a in counts}
    (R.HERE/'selection.json').write_text(json.dumps({'tiles':chosen,'branches':branches,'candidates':out},indent=2))
    return out


def evaluate(case,native,base_model):
    arm,name,cfg=case['arm'],case['name'],case['config']
    R.reserve(arm,name)
    try:
        if 'event' in cfg:
            base = R.construct({k:v for k,v in cfg.items() if k!='event'}) if arm=='X' else native
            ir=base[0]
            model=retime.capture(ir,base[1]) if arm=='X' else base_model
            times,info=event.compact(model,ir,**cfg['event'])
            program,words,logical,addresses=retime.lower(ir,model,times)
            built=(ir,logical,addresses,words,program,max(times)+1)
        else:
            built=R.construct(cfg);info=None
        row=R.row_for(arm,name,cfg,built)
        if info:row['event']=info
        R.write_row(row)
        return row,built
    except Exception as error:
        R.write_row({'arm':arm,'name':name,'config':cfg,'status':'error','error':repr(error)})
        raise


def main():
    assert not (R.HERE/'attempts.jsonl').exists(), 'completed/started manifest cannot restart'
    began=time.monotonic(); R.guard()
    (R.HERE/'pure_checks.json').write_text(json.dumps(pure_checks(),indent=2))
    native=controls(); cases=candidates(native)
    model=retime.capture(native[0],native[1]);best={};blocked=set()
    for case in cases:
        arm=case['arm']
        if arm in blocked:continue
        try:row,built=evaluate(case,native,model)
        except Exception:
            blocked.add(arm);continue
        if row['status']=='smoke-passed':
            old=best.get(arm)
            if old is None or (row['cycles'],row['scratch'])<(old[0]['cycles'],old[0]['scratch']):
                best[arm]=(row,built)
    combinations=[]
    graph=[best[a] for a in 'ABC' if a in best and best[a][0]['cycles']<981]
    schedules=[best[a] for a in 'DE' if a in best and best[a][0]['cycles']<981]
    for g in graph:
        for s in schedules:
            cfg={**g[0]['config'],**s[0]['config']}
            combinations.append({'arm':'X','name':f'X{len(combinations)+1:02}','config':cfg})
    # At most one pair of disjoint winning local graph transformations.
    if 'A' in best and 'C' in best and best['A'][0]['cycles']<981 and best['C'][0]['cycles']<981:
        combinations.append({'arm':'X','name':f'X{len(combinations)+1:02}',
                             'config':{**best['A'][0]['config'],**best['C'][0]['config']}})
    (R.HERE/'combinations.json').write_text(json.dumps(combinations[:8],indent=2))
    for case in combinations[:8]:
        try:row,built=evaluate(case,native,model)
        except Exception:blocked.add('X');break
        if row['status']=='smoke-passed' and ('X' not in best or (row['cycles'],row['scratch'])<(best['X'][0]['cycles'],best['X'][0]['scratch'])):
            best['X']=(row,built)
    for arm,(row,built) in best.items():
        row['pattern_cases']=R.execute(built[4],patterns=range(5))
        R.save(row['name'],built,row['config'],row)
    final={'best_by_arm':{a:x[0] for a,x in best.items()},'blocked_arms':sorted(blocked),
           'elapsed_seconds':time.monotonic()-began,'solver_queries':0,
           'full_verification_required':[x[0]['name'] for x in sorted(best.values(),key=lambda x:(x[0]['cycles'],x[0]['scratch'])) if x[0]['cycles']<980][:2]}
    R.guard();(R.HERE/'screen_result.json').write_text(json.dumps(final,indent=2))
    print(json.dumps(final,indent=2))


if __name__=='__main__':main()
