"""Read-only verification of saved artifacts; no generation or execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import kernel_retime as K
from kernel_checks import lane_identity

P=Path(__file__).resolve().parent
ROOT=Path('/home/travers/projects/original_performance_takehome')


def read(name): return json.loads((P/name).read_text())
def digest(x): return hashlib.sha256(json.dumps(x).encode()).hexdigest()


def main():
    for file,base in [('protected_sources.json',ROOT),('research_sources.json',P)]:
        assert all(hashlib.sha256((base/n).read_bytes()).hexdigest()==h for n,h in read(file).items())
    old=Path('/tmp/perf-resource-order.HM8PpA')
    assert all(hashlib.sha256((old/n).read_bytes()).hexdigest()==h for n,h in json.loads((old/'research_sources.json').read_text()).items())
    assert (P/'schedules.py').read_bytes()==(ROOT/'experiments/resource_order_scheduler.py').read_bytes()
    report=read('screen_result.json');manifest=read('manifest.json')
    assert report['all_budgets_closed'] and manifest['status']=='closed'
    attempts=[json.loads(x) for x in (P/'attempts.jsonl').read_text().splitlines()]
    results=[json.loads(x) for x in (P/'results.jsonl').read_text().splitlines()]
    assert len(attempts)==len({x['name'] for x in attempts})==len(results)==14
    assert Counter(x['arm'] for x in attempts)=={'control':4,'candidate':8,'validation':2}
    assert {x['name'] for x in attempts}=={x['name'] for x in results}
    rows={x['name']:x for x in report['rows']}
    assert {x['name']:x for x in results if x['arm']=='candidate'}==rows
    assert all(rows[x['name']]['spec']==x for x in read('selection.json')) and len(rows)==8
    models={}
    for path in (P/'graphs').glob('*.json'):
        m=json.loads(path.read_text());assert digest(m)==path.stem;models[path.stem]=m
    assert len(models)==4
    legal=[]
    for name,row in rows.items():
        m=models[row['native_model_digest']];jobs=m['jobs'];ops=m['ops']
        times=read(f'artifacts/{name}/timing.json');logical=read(f'artifacts/{name}/logical.json')
        program=read(f'artifacts/{name}/program.json')
        addresses={int(k):v for k,v in read(f'artifacts/{name}/addresses.json').items()}
        K.validate(m,times)
        assert max(times)+1==row['cycles']
        projected=[[] for _ in range(max(times)+1)]
        for j,t in zip(jobs,times):
            if j['op'] is not None: projected[t].append([j['op'],j['engine'],j['first'],1])
        assert projected==logical
        stores={str(ops[j['op']]['block']):i for i,j in enumerate(jobs) if j['op'] is not None and j['engine']=='store'}
        assert len(stores)==32 and {b:times[i] for b,i in stores.items()}==row['terminal_store_cycles']
        gathered=[i for i,j in enumerate(jobs) if j['op'] is not None and ops[j['op']]['kind']=='gather']
        usage=Counter(times[i] for i in gathered)
        assert len(gathered)==1816 and min(usage)==61 and max(usage)==968
        assert all(usage[t]==2 for t in range(61,969))
        parents=[[] for _ in jobs];successors=[[] for _ in jobs]
        for a,b,lag in m['edges']:
            assert a<b;parents[b].append(a);successors[a].append((b,lag))
        for block,tail in row['final_tails'].items():
            ancestors=set();stack=[stores[block]]
            while stack:
                i=stack.pop()
                if i not in ancestors: ancestors.add(i);stack.extend(parents[i])
            gs=[i for i in gathered if i in ancestors]
            last_op=max(jobs[i]['op'] for i in gs)
            last=[i for i in gs if jobs[i]['op']==last_op]
            assert last==tail['gather_jobs'] and sorted(jobs[i]['first'] for i in last)==list(range(8))
            distance=[-1]*len(jobs)
            for i in last: distance[i]=0
            for i in range(len(jobs)):
                if distance[i]>=0:
                    for j,lag in successors[i]:distance[j]=max(distance[j],distance[i]+lag)
            expected=10 if int(block) in row['config']['final_blocks'] else 11
            assert distance[stores[block]]==tail['dependency_distance']==expected
            assert max(times[i] for i in last)==tail['last_gather']
            assert times[stores[block]]==tail['store']
            assert tail['store']-tail['last_gather']==tail['observed_tail']==expected
        if row['status']=='scratch-rejected':
            assert name=='F04' and program is None and row['scratch']==1537
            assert 'smoke_cases' not in row and 'pattern_cases' not in row
            continue
        assert row['status']=='screen-passed' and row['scratch']<=1536
        assert digest(program)==row['digest'] and len(program)==row['cycles']
        ir=SimpleNamespace(ops=[SimpleNamespace(**op) for op in ops],widths=m['widths'])
        lane_identity(ir,logical,addresses)
        assert all(addresses[v]+m['widths'][v]<=row['scratch'] for v in addresses)
        counts=Counter()
        for bundle in program:
            for engine,slots in bundle.items():
                assert len(slots)<=K.CAP[engine];counts[engine]+=len(slots)
        assert dict(counts)==row['counts']=={'load':1888,'flow':945,'valu':5800,'alu':11524,'store':32}
        assert program[-1]['flow'][-1]==['pause']
        assert sum(s[0]=='pause' for b in program for slots in b.values() for s in slots)==1
        legal.append(row)
    assert len(legal)==7
    assert sum(r['smoke_cases'] for r in legal)==21 and sum(r['pattern_cases'] for r in legal)==35
    best=min(legal,key=lambda r:(r['cycles'],r['scratch'],r['name']))
    assert best==report['best'] and (best['name'],best['cycles'],best['scratch'])==('F08',979,1463)
    for row in results:
        if row['arm']=='validation':assert row['digest']==best['digest'] and row['oracle_blocked'] and row['scratch']==1463
    verification=report['conditional_verification']
    assert verification['seeds']==100 and verification['patterns']==5 and verification['new_reconstructions']==2
    assert read('submission.json')==verification['frozen_suite'] and read('submission.json')['observed_cycles']==979
    assert read('submission.json')['tests']==9 and read('submission.json')['status']=='passed'
    assert read('pure_checks.json')['final_hash']=={'affine_GF2_basis_cases':33,'wrong_shift_input_rejected':True,'limit':'Both expressions are affine over GF(2); actual emitter wiring checked by frozen execution.'}
    assert report['solver_queries']==0 and not report['production_changed']
    out={'status':'passed','reservations':14,'candidate_timings':8,'allocated_candidate_programs':7,
         'scratch_rejections':{'F04':1537},'best':{k:best[k] for k in ('name','cycles','scratch','digest')},
         'screen_executions':56,'conditional_executions':107,'frozen_suite_tests':9,'frozen_suite_replay_executions':9,
         'full_kernel_control_executions':14,'toy_executions':2,'expected_corrupt_execution_failures':1,
         'four_native_graphs_checked':True,'final_gather_ancestry_and_path_lengths_checked':True,
         'production_unchanged':True,'full_incumbent_gates_run':False,'candidate_generation_by_audit':0,'execution_by_audit':0}
    (P/'audit.json').write_text(json.dumps(out,indent=2))
    print('Audit passed: F08 979/1463; seven allocated programs, one pre-lower rejection, exact 11-to-10 final path.')


if __name__=='__main__':main()
