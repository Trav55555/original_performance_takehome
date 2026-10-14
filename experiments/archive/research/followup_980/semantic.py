"""Semantic DAG identities; priority restoration never adds execution edges."""
import hashlib,json

def annotate(ir):
    keys=[]; descriptions=[]; seen={}; ir.selector_map={}
    for i,op in enumerate(ir.ops):
        args=[(keys[ir.producer[v]],offset) for v,offset in op.args]
        descriptor=(op.scope,op.kind,op.code,op.imm,0 if op.dst is None else ir.widths[op.dst],args)
        text=json.dumps(descriptor,separators=(',',':'))
        key=hashlib.sha256(text.encode()).hexdigest()
        assert key not in seen,('ambiguous semantic operation',op.scope,i,seen.get(key))
        seen[key]=i;keys.append(key);descriptions.append(text)
        if hasattr(op,'site'):
            assert op.site not in ir.selector_map
            ir.selector_map[op.site]=i
    ir.semantic_keys=keys;ir.semantic_descriptions=descriptions

def native_features(ir):
    from kernel_compiler import _engine_cost
    successors=[[] for _ in ir.ops];position=[];critical=[0]*len(ir.ops);cost=0
    for i,op in enumerate(ir.ops):
        position.append(cost);cost+=_engine_cost(op,ir.widths)[1]
        for v in {v for v,o in op.args}:successors[ir.producer[v]].append(i)
    for i in range(len(ir.ops)-1,-1,-1):
        critical[i]=(4 if ir.ops[i].kind=='gather' else 1)+max((critical[j] for j in successors[i]),default=0)
    return critical,position

def restore(ir,critical,position,distance):
    ir.native_critical=critical[:];ir.native_position=position[:];ir.native_distance=distance[:]
    stats={'matched':0,'changed_critical':0,'changed_position':0,'mapping_checked':False}
    rc=getattr(ir,'restore_critical',False);rp=getattr(ir,'restore_position',False)
    if rc or rp:
        ref=ir.priority_reference;crit,pos=native_features(ref)
        lookup={k:i for i,k in enumerate(ref.semantic_keys)}
        for i,k in enumerate(ir.semantic_keys):
            j=lookup.get(k)
            if j is None:continue
            assert ir.semantic_descriptions[i]==ref.semantic_descriptions[j], 'semantic hash collision'
            # Each parent identity and lane offset is included recursively; engine
            # preference is excluded because it does not change operation meaning.
            stats['matched']+=1
            if rc and crit[j]>critical[i]:critical[i]=crit[j];stats['changed_critical']+=1
            if rp and pos[j]!=position[i]:position[i]=pos[j];stats['changed_position']+=1
        stats['mapping_checked']=True
    ir.priority_stats=stats
    ir.effective_critical=critical[:];ir.effective_position=position[:]
    return critical,position
