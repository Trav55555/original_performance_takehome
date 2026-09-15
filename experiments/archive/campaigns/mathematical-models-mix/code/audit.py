"""Audit saved experiment records without generation or execution."""
import hashlib
import json
from pathlib import Path
from collections import Counter

P=Path(__file__).resolve().parent
ROOT=Path('/home/travers/projects/original_performance_takehome')
for filename,root in [('protected_sources.json',ROOT),('research_sources.json',P)]:
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h
               for n,h in json.loads((P/filename).read_text()).items())
summary=json.loads((P/'screen_result.json').read_text());rows=summary['rows']
log=[json.loads(s) for s in (P/'results.jsonl').read_text().splitlines()]
attempts=[json.loads(s) for s in (P/'attempts.jsonl').read_text().splitlines()]
expected={'control':4,'single':12,'pair':40,'sharing':10,'sharing_cross':6,'event':16,'triple':4}
assert Counter(x['arm'] for x in attempts)==expected
assert len(attempts)==len(log)==92
assert len({x['name'] for x in attempts})==92
assert {x['name'] for x in attempts}=={x['name'] for x in log}
prior={x['name']:x for x in map(json.loads,(P/'prior_results.jsonl').read_text().splitlines())}
candidates=[x for n,x in rows.items() if n!='base']
assert len(candidates)==88
assert all(x['status']=='smoke-passed' and x['scratch']<=1536 and x['smoke_cases']==3 for x in candidates)
for r in candidates:
    if r['arm']=='single':
        old=prior[r['name']]
        assert all(r[k]==old[k] for k in ('cycles','scratch','digest'))
    if 'interaction' in r:
        a,b=r['components']
        assert r['interaction']==r['cycles']-rows[a]['cycles']-rows[b]['cycles']+981
    if 'matched_cycle_delta' in r:
        a=r['components'][0]
        assert r['matched_cycle_delta']==r['cycles']-rows[a]['cycles']
        assert r['matched_scratch_delta']==r['scratch']-rows[a]['scratch']
assert not summary['verification_candidates']
assert all(r['cycles']>=981 for r in candidates)
pairs=[r for r in candidates if r['arm']=='pair']
signs=Counter('favorable' if r['interaction']<0 else 'unfavorable' if r['interaction']>0 else 'neutral' for r in pairs)
assert signs=={'favorable':19,'neutral':14,'unfavorable':7}
assert all(not r['better_than_both'] for r in pairs)
assert all(r['matched_cycle_delta']==0 for r in candidates if r['arm']=='event')
assert len(summary['finalists'])==17
for name in summary['finalists']:
    r=rows[name];artifact=P/'artifacts'/name
    assert r['pattern_cases']==5
    assert json.loads((artifact/'config.json').read_text())==r['config']
    prog=json.loads((artifact/'program.json').read_text())
    assert len(prog)==r['cycles'] and hashlib.sha256(json.dumps(prog).encode()).hexdigest()==r['digest']
result={'status':'passed','counted_attempts':92,'candidate_attempts':88,'controls':4,
        'feasible_candidates':88,'scratch_rejections':0,'candidate_seed_executions':264,
        'finalist_pattern_executions':85,'favorable_pair_interactions':19,
        'neutral_pair_interactions':14,'unfavorable_pair_interactions':7,
        'pairs_beating_both_components':0,'new_incumbents':0,'solver_queries':0,
        'winner_verification_runs':0,'source_hashes_and_finalist_digests_checked':True}
(P/'audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
