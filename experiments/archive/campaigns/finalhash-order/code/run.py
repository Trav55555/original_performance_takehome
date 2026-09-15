"""One frozen eight-case final-hash/justification pilot. Never restart."""
from collections import Counter
import json
import resource
import time
from unittest.mock import patch

if not __debug__:
    raise RuntimeError('assertions required')
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))

import research as R
from research import compiler, retime
import schedules as S
import prior_controls
import final_checks


def rank(row): return row['cycles'],row['scratch'],row['name']


def construct_case(spec):
    cfg=spec['config']
    ir=R.build_ir(cfg)
    logical,_,_=compiler._schedule(ir,lookahead=True,startup=True)
    model=retime.capture(ir,logical)
    times,diagnostic=S.double_justify(model,spec['tie'],1)
    program,words,logical,addresses=retime.lower(ir,model,times)
    return (ir,logical,addresses,words,program,max(times)+1),model,times,diagnostic


def metrics(ir,model,times):
    jobs=model['jobs']
    stores={ir.ops[j['op']].block:i for i,j in enumerate(jobs) if j['op'] is not None and j['engine']=='store'}
    gather=[i for i,j in enumerate(jobs) if j['op'] is not None and ir.ops[j['op']].kind=='gather']
    usage=Counter(times[i] for i in gather)
    _,succ,_=S.structure(model)
    tails={}
    for b in (29,30,31):
        gs=[i for i in gather if (getattr(ir.ops[jobs[i]['op']],'coord',None) or ())[:2]==(b,15)]
        if not gs: continue
        dist=[-1]*len(jobs)
        for i in gs: dist[i]=0
        for i in range(len(jobs)):
            if dist[i]>=0:
                for j,lag in succ[i]: dist[j]=max(dist[j],dist[i]+lag)
        tails[b]={'gather_jobs':gs,'last_gather':max(times[i] for i in gs),
                  'store':times[stores[b]],'dependency_distance':dist[stores[b]],
                  'observed_tail':times[stores[b]]-max(times[i] for i in gs)}
    return {'terminal_store_cycles':{b:times[i] for b,i in stores.items()},'final_tails':tails,
            'gather_stream':{'jobs':len(gather),'first':min(usage),'last':max(usage),
                             'holes':[(t,2-usage[t]) for t in range(min(usage),max(usage)+1) if usage[t]<2]}}


def save_case(name,built,spec,row,model,times):
    R.save(name,built,spec['config'],row)
    p=R.HERE/'artifacts'/name
    (p/'addresses.json').write_text(json.dumps(built[2]))
    (p/'timing.json').write_text(json.dumps(times))
    graphs=R.HERE/'graphs';graphs.mkdir(exist_ok=True)
    graph=graphs/(R.digest(model)+'.json');content=json.dumps(model)
    if graph.exists(): assert graph.read_text()==content
    else: graph.write_text(content)


def main():
    assert not (R.HERE/'attempts.jsonl').exists(),'used manifest cannot restart'
    start=time.monotonic()
    prior_controls.controls()
    specs=json.loads((R.HERE/'selection.json').read_text())
    prior={x['name']:x for x in json.loads((R.HERE/'prior_screen_result.json').read_text())['rows']}
    rows=[];best=None
    for spec in specs:
        R.reserve('candidate',spec['name'])
        built,model,times,diagnostic=construct_case(spec)
        row=R.row_for('candidate',spec['name'],spec['config'],built)
        row.update({'spec':spec,'native_model_digest':R.digest(model),'native_cycles':model['cycles'],
                    'scheduling':diagnostic,**metrics(built[0],model,times)})
        if built[4] is not None:
            assert len(built[4])==row['cycles']
            row['pattern_cases']=R.execute(built[4],patterns=range(5))
            row['status']='screen-passed'
            if not spec['config']['final_blocks']:
                old=prior['B01' if spec['tie']=='native' else 'B03']
                assert all(row[k]==old[k] for k in ('cycles','scratch','digest','counts'))
                row['prior_exact_reproduction']=True
            if best is None or rank(row)<rank(best[0]): best=row,built
        R.write_row(row);save_case(spec['name'],built,spec,row,model,times);rows.append(row)
    verification=None
    if best is not None and best[0]['cycles']<980:
        row,built=best
        assert R.execute(built[4],seeds=range(100),patterns=range(5))==105
        for k in range(2):
            name='reconstruction-'+str(k);R.reserve('validation',name)
            again,model,times,_=final_checks.oracle_blocked_construct(construct_case,row['spec'])
            assert again[3:6]==built[3:6] and R.digest(again[4])==row['digest']
            retime.validate(model,times)
            assert R.execute(again[4],seeds=[100+k])==1
            R.write_row({'arm':'validation','name':name,'status':'passed','cycles':again[5],
                         'scratch':again[3],'digest':R.digest(again[4]),'oracle_blocked':True})
        suite=final_checks.frozen_suite(built[4],row['cycles'])
        verification={'candidate':row['name'],'seeds':100,'patterns':5,'new_reconstructions':2,
                      'oracle_blocked_reconstructions':True,'frozen_suite':suite,
                      'full_incumbent_gates':False,'production_promotion':False}
    R.guard()
    report={'status':'completed','elapsed':time.monotonic()-start,'rows':rows,'best':best[0] if best else None,
            'conditional_verification':verification,'all_budgets_closed':True,'solver_queries':0,'production_changed':False}
    (R.HERE/'screen_result.json').write_text(json.dumps(report,indent=2))
    manifest=json.loads((R.HERE/'manifest.json').read_text());manifest['status']='closed'
    (R.HERE/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'status':'completed','elapsed':report['elapsed'],'verification':verification}),flush=True)


if __name__=='__main__':
    with patch.object(retime,'solve',side_effect=AssertionError('solver forbidden')), \
         patch.object(retime,'repair',side_effect=AssertionError('solver forbidden')), \
         patch.object(retime,'_worker',side_effect=AssertionError('solver forbidden')):
        try: main()
        except BaseException as error:
            (R.HERE/'failure.json').write_text(json.dumps({'type':type(error).__name__,'error':str(error),'budget_closed':True}))
            manifest=json.loads((R.HERE/'manifest.json').read_text());manifest['status']='closed-failed'
            (R.HERE/'manifest.json').write_text(json.dumps(manifest,indent=2))
            raise
