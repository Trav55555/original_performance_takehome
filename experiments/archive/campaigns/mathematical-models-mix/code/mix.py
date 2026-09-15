"""Bounded matched-factor experiment; never resumes an old manifest."""
from collections import Counter
from itertools import combinations, product
import copy
import json
import time

import research as R
from research import compiler,retime,variants
import event
import prior_controls

IDS={'A':['A18','A09','A16','A21'],'C':['C02','C06','C01'],
     'D':['D01','D10','D16'],'E':['E01','E05']}
PRIOR={r['name']:r for r in map(json.loads,(R.HERE/'prior_results.jsonl').read_text().splitlines())}
ROWS={}; BUILT={}; FAMILY={}


def merge(*configs):
    result={}
    for cfg in configs:
        for key,value in cfg.items():
            if key in ('tiles','branch_sites'):
                result[key]=sorted([list(x) for x in set(map(tuple,result.get(key,[])+value))])
            elif key not in result or result[key]==value:
                result[key]=copy.deepcopy(value)
            else:
                raise ValueError('incompatible factor '+key)
    tiles=result.get('tiles',[])
    assert len({tuple(t[:3]) for t in tiles})==len(tiles), 'conflicting tile order'
    assert not ('full' in result and tiles), 'full lookup overrides tiles'
    return result


def rank(name):
    r=ROWS[name]
    return r['cycles'],r['scratch'],name


def pick(names,n):
    return sorted((x for x in names if ROWS[x]['status']=='smoke-passed'),key=rank)[:n]


def run_case(arm,name,cfg,components=(),family=None,base=None):
    R.reserve(arm,name)
    try:
        if 'event' in cfg:
            assert base is not None
            ir=base[0];model=retime.capture(ir,base[1])
            times,info=event.compact(model,ir,**cfg['event'])
            program,words,logical,addresses=retime.lower(ir,model,times)
            built=(ir,logical,addresses,words,program,max(times)+1)
        else:
            built=R.construct(cfg);info=None
        row=R.row_for(arm,name,cfg,built)
        row['components']=list(components)
        if family:row['family']=family
        if info:row['event']=info
        valid=row['status']=='smoke-passed'
        if valid:
            row['beats_native']=row['cycles']<981
            row['beats_published']=row['cycles']<980
            if len(components)==2 and all(x in ROWS and ROWS[x]['status']=='smoke-passed' for x in components):
                a,b=[ROWS[x]['cycles'] for x in components]
                row.update(interaction=row['cycles']-a-b+981,
                           better_than_both=row['cycles']<min(a,b))
            if arm in ('sharing','event') and components:
                parent=ROWS[components[0]]
                if parent['status']=='smoke-passed':
                    row['matched_cycle_delta']=row['cycles']-parent['cycles']
                    row['matched_scratch_delta']=row['scratch']-parent['scratch']
        R.write_row(row);ROWS[name]=row;BUILT[name]=built
        if family:FAMILY.setdefault(family,[]).append(name)
        return row
    except Exception as error:
        R.write_row({'arm':arm,'name':name,'config':cfg,'status':'error','error':repr(error)})
        raise


def pattern_finalists():
    chosen=set()
    for family,names in FAMILY.items():
        chosen.update(pick(names,1))
    for name in chosen:
        row=ROWS[name];built=BUILT[name]
        row['pattern_cases']=R.execute(built[4],patterns=range(5))
        R.save(name,built,row['config'],row)
    return sorted(chosen)


def main():
    assert not (R.HERE/'attempts.jsonl').exists(), 'used manifest cannot restart'
    R.guard();started=time.monotonic()
    # Schema negative controls do not construct or execute programs.
    for configs in [({'tiles':[[30,14,0,0]]},{'tiles':[[30,14,0,1]]}),
                    ({'branch_kind':'radix'},{'branch_kind':'project'}),
                    ({'full':{'depths':[3]}},{'tiles':[[30,14,0,1]]})]:
        try:merge(*configs)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('conflict accepted')
    (R.HERE/'pure_checks.json').write_text(json.dumps(prior_controls.pure_checks()))
    native=prior_controls.controls()
    ROWS['base']={'cycles':981,'scratch':1465,'status':'smoke-passed','config':{}}
    BUILT['base']=native
    manifest={'components':{i:PRIOR[i]['config'] for xs in IDS.values() for i in xs},
              'caps':R.CAPS,'selection_rule':'program.md; deterministic ranks on measured feasible cells'}
    (R.HERE/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for arm,ids in IDS.items():
        for name in ids:
            cfg=PRIOR[name]['config']
            row=run_case('single',name,cfg,family='single-'+arm,
                         base=native if arm=='E' else None)
            assert (row['cycles'],row['scratch'],row['digest'])==(PRIOR[name]['cycles'],PRIOR[name]['scratch'],PRIOR[name]['digest']), 'component failed reproduction'
    pair_cells={}
    for family,pairs in [('AC',product(IDS['A'],IDS['C'])),('AD',product(IDS['A'],IDS['D'])),
                         ('CD',product(IDS['C'],IDS['D'])),('AA',combinations(IDS['A'],2)),
                         ('CC',[('C02','C06')])]:
        for a,b in pairs:
            name=a+'+'+b
            run_case('pair',name,merge(ROWS[a]['config'],ROWS[b]['config']),(a,b),family)
            pair_cells[frozenset((a,b))]=name
    shared=[]
    for name in IDS['A']+list(FAMILY['AA']):
        new='S+'+name
        run_case('sharing',new,merge(ROWS[name]['config'],{'share':True}),(name,),
                 'S-A' if name in IDS['A'] else 'S-AA')
        if name in IDS['A']:shared.append(new)
    selection={'sharing_cross_parents':pick(shared,2)}
    for a in selection['sharing_cross_parents']:
        for c in IDS['C']:
            name=a+'+'+c
            run_case('sharing_cross',name,merge(ROWS[a]['config'],ROWS[c]['config']),(a,c),'S-AC')
    selection['event_parents']={}
    for family in ('AC','AD','CD','AA'):
        names=FAMILY[family]+(FAMILY['S-AA'] if family=='AA' else [])
        selection['event_parents'][family]=pick(names,2)
        for parent in selection['event_parents'][family]:
            for e in IDS['E']:
                run_case('event',parent+'+'+e,merge(ROWS[parent]['config'],ROWS[e]['config']),
                         (parent,e),'event-'+family,base=BUILT[parent])
    selection['triple_parents']=pick(FAMILY['AC'],2)
    for ac in selection['triple_parents']:
        a,c=ROWS[ac]['components']
        for d in ('D01','D16'):
            name=ac+'+'+d
            row=run_case('triple',name,merge(ROWS[ac]['config'],ROWS[d]['config']),(ac,d),'triple')
            cells=[a,c,d,ac,pair_cells[frozenset((a,d))],pair_cells[frozenset((c,d))]]
            if row['status']=='smoke-passed' and all(ROWS[x]['status']=='smoke-passed' for x in cells):
                ta,tc,td,tac,tad,tcd=[ROWS[x]['cycles'] for x in cells]
                row['third_order_interaction']=row['cycles']-tac-tad-tcd+ta+tc+td-981
    (R.HERE/'selection.json').write_text(json.dumps(selection,indent=2))
    finalists=pattern_finalists()
    ordered=pick([n for n in ROWS if n!='base'],len(ROWS))
    candidates=[];seen=set()
    for name in ordered:
        row=ROWS[name]
        if row['cycles']<=980 and row['digest'] not in seen:
            candidates.append(name);seen.add(row['digest'])
        if len(candidates)==2:break
    result={'rows':ROWS,'families':FAMILY,'finalists':finalists,
            'verification_candidates':candidates,'best':ordered[:10],
            'elapsed_seconds':time.monotonic()-started,'solver_queries':0}
    R.guard();(R.HERE/'screen_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'best':[(n,ROWS[n]['cycles'],ROWS[n]['scratch']) for n in ordered[:10]],
                      'verification_candidates':candidates,'elapsed_seconds':result['elapsed_seconds']},indent=2))


if __name__=='__main__':main()
