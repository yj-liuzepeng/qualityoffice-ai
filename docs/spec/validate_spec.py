#!/usr/bin/env python3
# Copyright (C) 2026 Lenovo
# All Rights Reserved.
# Lenovo Confidential Restricted.
"""Validate specification consistency with Python stdlib. Not application acceptance."""
from pathlib import Path
import collections, datetime, json, re, sqlite3, sys, uuid
R=Path(__file__).resolve().parent
errors=[]; checks=[]
def check(condition,message):
    checks.append(message)
    if not condition:errors.append(message)
def read(name):return json.loads((R/name).read_text(encoding='utf-8'))
files={p.relative_to(R).as_posix():json.loads(p.read_text(encoding='utf-8')) for p in R.rglob('*.json') if p.name!='validation_report.json'}
reqs=read('requirements.json')['requirements']; tasks=read('tasks.json')['tasks']; cycles=read('tasks.json')['cycles']; tests=read('test_cases.json')['tests']
def indexed(rows,name):
    out={x['id']:x for x in rows}
    check(len(out)==len(rows),name+' IDs unique')
    return out
rq=indexed(reqs,'requirements'); ts=indexed(tasks,'tasks'); te=indexed(tests,'tests'); cy=indexed(cycles,'cycles')
check(len(cycles)==15 and sum(x['planned_development_hours']+x['buffer_hours'] for x in cycles)==990,'15 cycles, 990 development hours')
check(sum(t['estimate_hours'] for t in tasks)==792,'792 planned work-package hours')
check(all(t['status']=='planned' for t in tasks) and all(t['status']=='not_run' for t in tests),'no fabricated completed tasks/tests')
check(cycles[0]['weeks'][0]==1 and cycles[-1]['weeks'][-1]==33,'33-week schedule')
check(sum(c['review_hours'] for c in cycles)==66,'66 review hours')
for i,c in enumerate(cycles):
    check(c['weeks'][1]>=c['weeks'][0] and (i==0 or c['weeks'][0]==cycles[i-1]['weeks'][1]+1),c['id']+' continuous week range')
    members=[t for t in tasks if t['cycle']==c['id']]
    check(set(c['task_ids'])=={t['id'] for t in members},c['id']+' membership')
    check(sum(t['estimate_hours'] for t in members)==c['planned_development_hours'],c['id']+' capacity')
for t in tasks:
    check(t['cycle'] in cy and len(t['steps'])>=3 and bool(t['deliverables']),t['id']+' actionable fields')
    check(set(t['requirement_ids'])<=rq.keys(),t['id']+' requirements resolve')
    check(set(t['depends_on'])<=ts.keys(),t['id']+' dependencies resolve')
    check(set(t['test_ids'])=={x['id'] for x in tests if x['task_id']==t['id']},t['id']+' bidirectional tests')
    for dep in t['depends_on']:
        if dep in ts:check(ts[dep]['cycle']<=t['cycle'],t['id']+' dependency not in later cycle: '+dep)
visiting=set(); done=set()
def visit(tid):
    if tid in visiting:errors.append('dependency cycle at '+tid);return
    if tid in done:return
    visiting.add(tid)
    for dep in ts[tid]['depends_on']:
        if dep in ts:visit(dep)
    visiting.remove(tid);done.add(tid)
for tid in ts:visit(tid)
check(len(done)==len(tasks),'all task nodes checked for cycles')
for t in tests:
    check(t['task_id'] in ts and t['cycle']==ts[t['task_id']]['cycle'],t['id']+' owner and cycle')
    check(bool(t['preconditions']) and bool(t['steps']) and bool(t['expected']),t['id']+' preconditions/actions/oracle')
    check(set(t['requirement_ids'])<=rq.keys(),t['id']+' requirement references')
    check(set(t['requirement_ids'])<=set(ts[t['task_id']]['requirement_ids']),t['id']+' task requirement coverage')
trace=read('traceability.json')
for rid in rq:
    et={t['id'] for t in tasks if rid in t['requirement_ids']}
    ec={t['id'] for t in tests if rid in t['requirement_ids']}
    check(bool(et) and bool(ec),rid+' has tasks and tests')
    check(set(trace['requirements'][rid]['tasks'])==et and set(trace['requirements'][rid]['tests'])==ec,rid+' traceability matches')
check(set(trace['prd_scenarios'])=={f'T{i:02}' for i in range(1,20)},'PRD original T01-T15 and revision T16-T19 mapped')
for k,v in trace['prd_scenarios'].items():check(bool(v) and set(v)<=te.keys(),k+' detailed tests resolve')
for g in read('acceptance/fixture_manifest.json')['groups']:
    check(g['owner_task'] in ts,g['id']+' fixture owner resolves')
    check(bool(g['required_content']) and bool(g['oracle']),g['id']+' has content and oracle definition')
for g in read('baseline/decisions.json')['gates']:check(g['due_cycle'] in cy,g['id']+' gate cycle resolves')

schemas={k:v for k,v in files.items() if k.startswith('contracts/') and k.endswith('.json')}
ids={v['$id']:(k,v) for k,v in schemas.items() if '$id' in v}
def pointer(root,frag):
    cur=root
    if frag:
        if not frag.startswith('/'):raise ValueError('unsupported anchor '+frag)
        for p in frag[1:].split('/'):cur=cur[p.replace('~1','/').replace('~0','~')]
    return cur
def resolve(reference,doc_name,root):
    if reference.startswith('#'):return doc_name,root,pointer(root,reference[1:])
    base,_,frag=reference.partition('#')
    if base in ids:name,doc=ids[base]
    else:
        name=(Path(doc_name).parent/base).as_posix()
        doc=schemas[name]
    return name,doc,pointer(doc,frag)
def walk(node,doc_name,root):
    if isinstance(node,dict):
        if '$ref' in node:
            try:resolve(node['$ref'],doc_name,root)
            except Exception as e:errors.append(f'{doc_name} unresolved $ref {node["$ref"]}: {e}')
        if 'properties' in node and 'required' in node:
            check(set(node['required'])<=node['properties'].keys(),doc_name+' schema required fields exist')
        for v in node.values():walk(v,doc_name,root)
    elif isinstance(node,list):
        for v in node:walk(v,doc_name,root)
for name,s in schemas.items():walk(s,name,s)
api=schemas['contracts/openapi.json']; op_ids=[]
matrix=read('contracts/office-operation-matrix.json')['operations']
plan_schema=schemas['contracts/office-plan.schema.json']
check(set(matrix)==set(plan_schema['properties']['operation']['enum']),'Office matrix covers operation enum')
declared_steps={s['properties']['type']['const'] for s in plan_schema['properties']['steps']['items']['oneOf']}
for op,entry in matrix.items():
    check(set(entry['steps'])<=declared_steps,op+' matrix step types resolve')
for path,methods in api['paths'].items():
    for method,op in methods.items():
        op_ids.append(op['operationId'])
        pars={p['name'] for p in op.get('parameters',[]) if p.get('in')=='path' and p.get('required')}
        check(set(re.findall(r'\{([^}]+)\}',path))==pars,method+' '+path+' path params')
        check(bool(op['responses']),op['operationId']+' responses exist')
        if op.get('x-role')=='admin':check(bool(op.get('security')),op['operationId']+' authenticated')
check(len(op_ids)==len(set(op_ids)),'OpenAPI operation IDs unique')

# Deliberately limited JSON Schema smoke interpreter: validates these examples,
# not a standards conformance claim. Full validation belongs in implementation CI.
def conforms(x,s,name,root):
    if '$ref' in s:
        n,r,ss=resolve(s['$ref'],name,root);return conforms(x,ss,n,r)
    if 'oneOf' in s and sum(conforms(x,z,name,root) for z in s['oneOf'])!=1:return False
    if 'anyOf' in s and not any(conforms(x,z,name,root) for z in s['anyOf']):return False
    if 'const' in s and x!=s['const']:return False
    if 'enum' in s and x not in s['enum']:return False
    if 'type' in s:
        types=s['type'] if isinstance(s['type'],list) else [s['type']]
        match={'object':isinstance(x,dict),'array':isinstance(x,list),'string':isinstance(x,str),'integer':isinstance(x,int) and not isinstance(x,bool),
               'number':isinstance(x,(int,float)) and not isinstance(x,bool),'boolean':isinstance(x,bool),'null':x is None}
        if not any(match.get(t,False) for t in types):return False
    if isinstance(x,dict):
        if not set(s.get('required',[]))<=x.keys():return False
        props=s.get('properties',{})
        if s.get('additionalProperties') is False and not x.keys()<=props.keys():return False
        if any(not conforms(v,props[k],name,root) for k,v in x.items() if k in props):return False
    if isinstance(x,list):
        if len(x)<s.get('minItems',0) or len(x)>s.get('maxItems',10**15):return False
        if 'items' in s and any(not conforms(v,s['items'],name,root) for v in x):return False
    if isinstance(x,str):
        if len(x)<s.get('minLength',0) or len(x)>s.get('maxLength',10**15):return False
        if 'pattern' in s and not re.search(s['pattern'],x):return False
        if s.get('format')=='uuid':
            try:uuid.UUID(x)
            except ValueError:return False
        if s.get('format')=='date-time':
            try:
                if datetime.datetime.fromisoformat(x.replace('Z','+00:00')).tzinfo is None:return False
            except ValueError:return False
    if isinstance(x,(int,float)) and not isinstance(x,bool):
        if x<s.get('minimum',float('-inf')) or x>s.get('maximum',float('inf')):return False
    return True
example=read('contracts/examples.json')
for e in example['schema_smoke_examples']:
    name='contracts/'+e['schema']; schema=schemas[name]
    check(conforms(e['value'],schema,name,schema)==e['expected_valid'],'schema smoke: '+e['name'])
try:
    db=sqlite3.connect(':memory:');db.executescript((R/'data/local.sql').read_text(encoding='utf-8'))
    check(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite DDL executes and integrity_check ok')
    check(not db.execute('PRAGMA foreign_key_check').fetchall(),'SQLite foreign key structure check')
    sqlite_tables=db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    db.close()
except Exception as e:
    sqlite_tables=None;errors.append('SQLite DDL error: '+str(e))
server_sql=(R/'data/server.sql').read_text(encoding='utf-8')
server_tables=re.findall(r'CREATE TABLE\s+(\w+)',server_sql,re.I)
check(bool(server_tables) and len(server_tables)==len(set(server_tables)),'PostgreSQL table names unique (static only)')
server_refs=re.findall(r'REFERENCES\s+(\w+)',server_sql,re.I)
check(set(server_refs)<=set(server_tables),'PostgreSQL referenced tables declared (static only)')
check('document_body' not in server_sql and 'prompt_body' not in server_sql,'server baseline has no document/prompt body columns')
report={'check_type':'specification_structure_only','result':'passed' if not errors else 'failed',
 'counts':{'requirements':len(reqs),'cycles':len(cycles),'tasks':len(tasks),'planned_tests':len(tests),'checks':len(checks),
           'api_operations':len(op_ids),'local_sqlite_tables_including_fts':sqlite_tables,'server_tables_static':len(server_tables)},
 'errors':errors,'product_tests_run':0,
 'not_validated':['application implementation','real Windows install/runtime','real PostgreSQL execution','full JSON Schema/OpenAPI standards validation',
 'real model/search/OCR/Office behavior','licenses of an actual selected distribution','performance/accuracy/cost targets','stage gates and binary fixture completion']}
(R/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
