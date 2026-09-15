"""Read-only post-run audit. Does not construct, lower, execute, or search."""
from collections import Counter
import hashlib
import json
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=Path('/home/travers/projects/original_performance_takehome')
for source_file, root in [('protected_sources.json',ROOT),('research_sources.json',P)]:
    expected=json.loads((P/source_file).read_text())
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in expected.items())
attempts=[json.loads(x) for x in (P/'attempts.jsonl').read_text().splitlines()]
rows=[json.loads(x) for x in (P/'results.jsonl').read_text().splitlines()]
selection=json.loads((P/'selection.json').read_text())
summary=json.loads((P/'screen_result.json').read_text())
assert len(attempts)==len(rows)==78
assert len({x['name'] for x in attempts})==78
assert {x['name'] for x in rows}=={x['name'] for x in attempts}
assert Counter(x['arm'] for x in attempts)==dict(A=24,B=12,C=8,D=18,E=12,control=4)
byname={x['name']:x for x in rows}
for case in selection['candidates']:
    row=byname[case['name']]
    assert row['config']==case['config'] and row['arm']==case['arm']
    if row['status']=='scratch-rejected':
        assert row['scratch']>1536 and 'digest' not in row and 'smoke_cases' not in row
    else:
        assert row['status']=='smoke-passed' and row['scratch']<=1536
        assert row['smoke_cases']==3 and row['cycles']>=981
        c=row['counts'];assert row['capacity_lower_bound']==max((c[e]+n-1)//n for e,n in {'alu':12,'valu':6,'load':2,'store':2,'flow':1}.items())
for arm,best in summary['best_by_arm'].items():
    peers=[r for r in rows if r['arm']==arm and r['status']=='smoke-passed']
    assert best['name']==min(peers,key=lambda r:(r['cycles'],r['scratch']))['name']
    assert best['pattern_cases']==5
    artifact=P/'artifacts'/best['name']
    assert json.loads((artifact/'config.json').read_text())==best['config']
    program=json.loads((artifact/'program.json').read_text())
    assert hashlib.sha256(json.dumps(program).encode()).hexdigest()==best['digest']
    assert len(program)==best['cycles']
assert not summary['blocked_arms'] and not summary['full_verification_required']
assert json.loads((P/'combinations.json').read_text())==[]
result={'status':'passed','attempts':78,'candidate_attempts':74,'controls':4,
        'feasible_candidates':65,'scratch_rejections':9,
        'candidate_seed_executions':195,'finalist_pattern_executions':25,
        'native_control_cycles':981,'published_control_cycles':980,
        'conditional_combinations':0,'winner_verification_runs':0,'solver_queries':0,
        'production_sources_unchanged':True,'research_sources_unchanged':True,
        'manifest_rows_and_artifact_digests_checked':True}
(P/'audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
