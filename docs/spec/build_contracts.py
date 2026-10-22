#!/usr/bin/env python3
"""Product-owned contracts. These are NOT upstream dsh APIs."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent/'contracts'
R.mkdir(exist_ok=True)
def obj(props,required=None):
    return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False}
def arr(item,minimum=0,maximum=100):return {'type':'array','items':item,'minItems':minimum,'maxItems':maximum}
def st(maximum=1000):return {'type':'string','maxLength':maximum}
def enum(*values):return {'type':'string','enum':list(values)}
def ref(name):return {'$ref':'#/components/schemas/'+name}
def locref(name):return {'$ref':'#/$defs/'+name}
UUID={'type':'string','format':'uuid'}
DT={'type':'string','format':'date-time'}
INT={'type':'integer','minimum':0,'maximum':9007199254740991}
POS={'type':'integer','minimum':1,'maximum':9007199254740991}
HASH={'type':'string','pattern':'^[a-f0-9]{64}$'}
NULLSTR={'type':['string','null'],'maxLength':1000}
SCALAR={'type':['string','number','boolean','null']}
def nullable(schema):return {'anyOf':[schema,{'type':'null'}]}
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

bbox={'type':'array','items':{'type':'number','minimum':0},'minItems':4,'maxItems':4,
      'description':'[x0,y0,x1,y1]; application validates x1>=x0,y1>=y0 and page/image bounds'}
locator_variants=[]
for kind,fields,required in [
 ('docx',{'part':st(256),'paragraph_index':INT,'table_index':INT,'row':INT,'column':INT,'preview_page':POS},['part']),
 ('pdf',{'page':POS,'bbox':bbox},['page']),
 ('xlsx',{'sheet':st(128),'range':{'type':'string','pattern':'^[A-Z]+[1-9][0-9]*(:[A-Z]+[1-9][0-9]*)?$'}},['sheet','range']),
 ('csv',{'record_start':POS,'record_end':POS,'physical_line_start':POS,'physical_line_end':POS},['record_start','record_end']),
 ('pptx',{'slide_id':st(128),'slide_number':POS,'shape_id':st(128),'notes':{'type':'boolean'}},['slide_id','slide_number']),
 ('image',{'frame':POS,'width':POS,'height':POS,'bbox':bbox},['frame','width','height'])]:
    variant=obj({'kind':{'const':kind},**fields},['kind',*required])
    if kind=='docx':variant['anyOf']=[{'required':['paragraph_index']},{'required':['table_index','row','column']}]
    locator_variants.append(variant)
locator={'oneOf':locator_variants,'description':'Human page/frame/row/column references are 1-based; DOCX paragraph/table indices and rows/columns are 0-based. PDF bbox points (72dpi); image bbox pixels.'}
warning=obj({'code':st(80),'message':st(2000),'locator':nullable(locref('Locator'))},['code','message'])
segment=obj({'segment_id':st(128),'order':INT,'kind':enum('paragraph','heading','table','cell','slide_text','image_text','other'),
 'text':st(200000),'locator':locref('Locator'),'confidence':{'type':['number','null'],'minimum':0,'maximum':1},
 'extraction':enum('native','ocr'),
 'cell':nullable(obj({'value':SCALAR,'formula':NULLSTR,'cached_value':SCALAR,'cached_value_present':{'type':'boolean'},
  'data_type':enum('string','number','boolean','date','error','blank'),'number_format':NULLSTR})),
 'object_metadata':nullable(obj({'shape_type':st(128),'is_supported':{'type':'boolean'},'media_ref':nullable(UUID),'slide_hidden':{'type':'boolean'}}))},
 ['segment_id','order','kind','text','locator','extraction'])
coverage=obj({'unit':enum('pages','slides','records','cells','paragraphs','frames'),
 'total_units':nullable(INT),'processed_units':INT,'selected_ranges':arr(st(200),0,500),
 'omitted':arr(obj({'range':st(200),'reason':st(500)}),0,500),
 'complete':{'type':'boolean'}},['unit','total_units','processed_units','selected_ranges','omitted','complete'])
parse=obj({'schema_version':{'const':'1.0'},'document_id':UUID,'document_version_id':UUID,'sha256':HASH,
 'parser_version':st(128),'status':enum('ok','partial','error','cancelled'),
 'segments':arr(locref('Segment'),0,100000),'coverage':locref('Coverage'),
 'warnings':arr(locref('Warning'),0,1000),'error':nullable(obj({'code':st(80),'message':st(2000)}))})
parse['properties']['document_metadata']=obj({
 'sheets':arr(obj({'name':st(128),'visibility':enum('visible','hidden','veryHidden'),'used_range':st(100),'merged_ranges':arr(st(100),0,10000)}),0,100),
 'unsupported_objects':arr(obj({'type':st(128),'locator':locref('Locator'),'reason':st(500)}),0,10000)},[])
parse.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:qdesk:parse-result:1.0',
 '$defs':{'Locator':locator,'Segment':segment,'Warning':warning,'Coverage':coverage}})
write(R/'parse-result.schema.json',parse)

# Product-owned local configuration contracts, versioned independently from HTTP API.
config_id='urn:qdesk:personalization-subscriptions:1.0'
def cfgref(name):return {'$ref':config_id+'#/$defs/'+name}
VREF=obj({'id':st(128),'version':POS})
template_ref=obj({'template_id':UUID,'version':POS})
fields=obj({
 'audience':st(300),'language':st(80),'tone':enum('formal','concise','explanatory','training'),
 'length':enum('brief','standard','detailed'),
 'terminology':arr(obj({'term':st(200),'preferred':st(200)}),0,100),
 'must_include':arr(st(500),0,50),'must_avoid':arr(st(500),0,50),'extra_instructions':st(4000),
 'word':obj({'heading_levels':{'type':'integer','minimum':1,'maximum':3},'font':st(128),
    'body_pt':{'type':'number','minimum':9,'maximum':24},'page_size':enum('A4','Letter'),
    'margin_mm':{'type':'number','minimum':10,'maximum':40}},[]),
 'excel':obj({'decimal_places':{'type':'integer','minimum':0,'maximum':10},'unit':st(100),
    'date_format':enum('yyyy-mm-dd','yyyy/mm/dd','yyyy年mm月dd日'),'header_style':enum('plain','light','accent')},[]),
 'ppt':obj({'style':enum('minimal','professional','training'),'accent_hex':{'type':'string','pattern':'^#[0-9A-Fa-f]{6}$'},
    'font':st(128),'slide_count':{'type':'integer','minimum':5,'maximum':30},
    'body_pt':{'type':'number','minimum':18,'maximum':36},'title_pt':{'type':'number','minimum':24,'maximum':60}},[])
},[])
profile=obj({'kind':{'const':'office_profile'},'schema_version':{'const':'1.0'},'profile_id':UUID,'revision':POS,
 'name':{'type':'string','minLength':1,'maxLength':60},'description':st(500),'is_default':{'type':'boolean'},
 'fields':fields,'template':nullable(template_ref),'knowledge_base_ids':arr(UUID,0,20),
 'domain':nullable(VREF),'created_at':DT},None)
scope=obj({'knowledge_base_id':UUID,'generation_id':UUID,'document_version_ids':arr(UUID,1,1000)})
effective=obj({'kind':{'const':'effective_preferences'},'schema_version':{'const':'1.0'},
 'profile':nullable(obj({'profile_id':UUID,'revision':POS})),'domain':nullable(VREF),
 'template':nullable(template_ref),'fields':fields,
 'provenance':arr(obj({'field_path':st(200),'origin':enum('policy','task','profile','template','domain','app'),
    'origin_ref':NULLSTR}),0,300),
 'conflicts':arr(obj({'field_path':st(200),'message':st(1000),'resolution':enum('applied','needs_input','rejected')}),0,100),
 'knowledge_scope':arr(scope,0,20),'snapshot_sha256':HASH})
choice=obj({'id':st(128),'label':st(200)})
package=obj({'kind':{'const':'domain_package'},'schema_version':{'const':'1.0'},'domain_id':st(128),
 'version':POS,'name':st(100),'description':st(1000),'state':enum('draft','published','withdrawn'),
 'topics':arr(choice,1,100),'content_types':arr(choice,1,30),
 'sources':arr(obj({'source_id':st(128),'adapter_id':st(128),'adapter_version':st(128),
    'topic_ids':arr(st(128),1,100),'content_type_ids':arr(st(128),1,30)}),1,100),
 'default_topic_ids':arr(st(128),1,100),'default_content_type_ids':arr(st(128),1,30),
 'summary_fields':arr(st(100),1,20),'office_defaults':fields,'sha256':HASH})
selection=obj({'domain_id':st(128),'package_version':POS,'topic_ids':arr(st(128),1,100),
 'content_type_ids':arr(st(128),1,30),'keywords':arr(st(100),0,20)})
subplan=obj({'kind':{'const':'subscription_plan'},'schema_version':{'const':'1.0'},'plan_id':UUID,'revision':POS,
 'enabled':{'type':'boolean'},'selections':arr(selection,1,10),
 'timezone':st(128),'local_time':{'type':'string','pattern':'^([01][0-9]|2[0-3]):[0-5][0-9]$'},
 'resolved_source_ids':arr(st(128),1,10),'windows_notifications':{'type':'boolean'},'effective_from':DT})
config_defs={'OfficeProfile':profile,'EffectivePreferences':effective,'DomainPackage':package,'SubscriptionPlan':subplan}
write(R/'personalization-and-subscriptions.schema.json',{
 '$schema':'https://json-schema.org/draft/2020-12/schema','$id':config_id,
 'oneOf':[{'$ref':'#/$defs/'+k} for k in config_defs],'$defs':config_defs,
 'description':'Local product configuration. App validates catalog membership, references, field compatibility, precedence, hashes and permissions; no arbitrary code/config paths.'})

target={'oneOf':[
 obj({'kind':{'const':'docx_range'},'target_id':st(128),'part':st(256),'start_index':INT,'end_index':INT}),
 obj({'kind':{'const':'xlsx_range'},'target_id':st(128),'sheet':st(128),'range':st(100)}),
 obj({'kind':{'const':'ppt_shape'},'target_id':st(128),'slide_id':st(128),'shape_id':st(128)})]}
steps=[]
def step(kind,props,required=None):
    steps.append(obj({'type':{'const':kind},**props},['type',*(list(props) if required is None else required)]))
step('fill_placeholder',{'key':st(128),'value':st(20000),'source_ids':arr(st(128),0,50)})
step('replace_text',{'target_id':st(128),'value':st(20000),'source_ids':arr(st(128),0,50)})
step('write_table',{'target_id':st(128),'columns':arr(st(200),1,100),'rows':arr(arr(SCALAR,1,100),0,10000),'source_ids':arr(st(128),0,50)})
step('write_cells',{'sheet':st(128),'start_cell':st(30),'values':arr(arr(SCALAR,1,1000),1,10000)})
step('set_formula',{'sheet':st(128),'cell':st(30),'formula':st(1000),'source_ids':arr(st(128),0,50)})
step('clean_range',{'sheet':st(128),'range':st(100),'action':enum('deduplicate','normalize_date','normalize_text','missing_values'),
 'columns':arr(st(128),1,100),'missing_policy':enum('keep','drop','fill'),'fill_value':SCALAR})
step('create_chart',{'sheet':st(128),'chart_type':enum('bar','line'),'data_range':st(100),'title':st(300)})
step('append_doc_section',{'heading':st(300),'paragraphs':arr(st(20000),0,100),'source_ids':arr(st(128),0,50)})
step('append_table',{'columns':arr(st(200),1,100),'rows':arr(arr(SCALAR,1,100),0,10000),'source_ids':arr(st(128),0,50)})
step('append_image',{'image_document_version_id':UUID,'caption':st(1000),'source_ids':arr(st(128),0,50)})
step('aggregate_range',{'sheet':st(128),'range':st(100),'group_by':arr(st(128),0,100),
 'aggregations':arr(obj({'column':st(128),'function':enum('count','sum','average','min','max')}),1,100),
 'output_sheet':st(128),'source_ids':arr(st(128),0,50)})
step('create_slide',{'slide_id':st(128),'layout':enum('cover','agenda','body','two_column','table','chart','summary'),
 'title':st(300),'bullets':arr(st(2000),0,20),'source_ids':arr(st(128),0,50),
 'table_data':obj({'columns':arr(st(200),1,20),'rows':arr(arr(SCALAR,1,20),1,100)}),
 'chart_data':obj({'chart_type':enum('bar','line'),'categories':arr(st(200),1,100),
  'series':arr(obj({'name':st(200),'values':arr({'type':['number','null']},1,100)}),1,20)}),
 'image_document_version_id':UUID,'notes':st(20000)},['slide_id','layout','title','bullets','source_ids'])
step('replace_image',{'target_id':st(128),'image_document_version_id':UUID,'source_ids':arr(st(128),0,50)})
plan=obj({'schema_version':{'const':'1.0'},'operation':enum('base_docx','base_xlsx','base_pptx','word_generate','word_edit','excel_process','ppt_generate','ppt_patch'),
 'input_version_ids':arr(UUID,0,10),'template':nullable(obj({'template_id':UUID,'version':POS})),
 'targets':arr(target,0,500),'steps':arr({'oneOf':steps},1,500),
 'output_format':enum('docx','xlsx','pptx'),'missing_fields':arr(st(300),0,100),
 'allowed_changes':arr(st(200),1,100)},None)
plan.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:qdesk:office-plan:1.0',
 'description':'Schema validation is necessary, not sufficient. Broker also validates operation/step compatibility, target ownership, source IDs, template and formula allowlists, size and business authorization.'})
plan['properties']['effective_preferences']=cfgref('EffectivePreferences')
write(R/'office-plan.schema.json',plan)
tool_variants=[]
def tool(name,args):tool_variants.append(obj({'tool':{'const':name},'operation_id':UUID,'arguments':args}))
tool('qdesk.file.parse',obj({'document_version_id':UUID,'selected_ranges':arr(st(200),0,500)}))
tool('qdesk.file.read_segments',obj({'document_version_id':UUID,'segment_ids':arr(st(128),1,100)}))
tool('qdesk.web.search',obj({'query':st(500),'limit':{'type':'integer','minimum':1,'maximum':5}}))
tool('qdesk.web.read',obj({'source_id':UUID}))
tool('qdesk.office.plan',obj({'plan':{'$ref':'urn:qdesk:office-plan:1.0'}}))
tool('qdesk.office.execute',obj({'plan_id':UUID}))
tool('qdesk.kb.search',obj({'knowledge_base_ids':arr(UUID,1,20),'query':st(2000),'include_historical':{'type':'boolean'}}))
write(R/'local-tools.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema',
 '$id':'urn:qdesk:tool-request:1.0','oneOf':tool_variants,
 'description':'Product-owned model-visible tool allowlist. Resource IDs are resolved by host, never by model-supplied OS paths.'})
write(R/'tool-result.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema',
 **obj({'operation_id':UUID,'status':enum('ok','partial','error','cancelled'),
 'data':{'type':['object','null']},'warnings':arr(obj({'code':st(80),'message':st(2000)}),0,1000),
 'error':nullable(obj({'code':st(80),'message':st(2000),'retryable':{'type':'boolean'}})),
 'source_refs':arr(obj({'source_id':st(128),'document_version_id':nullable(UUID),'locator':nullable(locator),'url':NULLSTR}),0,1000)})})

S={}
S['Error']=obj({'code':st(80),'message':st(2000),'request_id':UUID,'retryable':{'type':'boolean'},'details':{'type':'object'}},['code','message','request_id','retryable'])
S['Device']=obj({'device_id':UUID,'label':st(128),'last_seen_at':DT,'revoked_at':nullable(DT),'version':POS})
S['Session']=obj({'access_token':st(8192),'refresh_token':st(1024),'token_type':{'const':'Bearer'},'expires_in':{'const':900},'user_id':UUID})
S['Usage']=obj({'uncached_input_tokens':INT,'cached_input_tokens':INT,'output_tokens':INT,'reasoning_tokens':nullable(INT),'source':enum('provider','reconciled','unknown')})
S['Run']=obj({'run_id':UUID,'request_id':UUID,'task_id':UUID,'attempt_id':UUID,
 'state':enum('reserved','dispatched','streaming','completed','failed','cancelled','unknown'),
 'billing_state':enum('held','settled','pending_usage','released','waived_unknown'),
 'reserved_units':INT,'charged_units':nullable(INT),'platform_absorbed_units':INT,
 'usage':nullable(ref('Usage')),'created_at':DT,'updated_at':DT,'cancel_requested':{'type':'boolean'},'version':POS,
 'error':nullable(ref('Error'))})
S['AdminRun']=obj({**S['Run']['properties'],'provider_config_ref':st(128),'provider_request_id':NULLSTR,
 'model_id':st(256),'route_id':UUID,'price_card_id':UUID,'provider_currency':NULLSTR,
 'provider_cost_amount':nullable({'type':'string','pattern':'^[0-9]+(\\.[0-9]{1,8})?$'})})
S['Entitlements']=obj({'user_id':UUID,'username':st(128),'account_state':enum('active','disabled'),
 'membership_starts_at':nullable(DT),'membership_expires_at':nullable(DT),
 'features':arr(st(80),0,100),'available_units':INT,'reserved_units':INT,'used_units':INT,
 'server_time':DT,'device_limit':{'type':'integer','minimum':1,'maximum':10},
 'pricing_policy_version':st(80),'can_start_paid_call':{'type':'boolean'},'blocking_reason':NULLSTR})
S['Source']=obj({'source_id':UUID,'url':{'type':'string','format':'uri','maxLength':4000},
 'final_url':NULLSTR,'canonical_url':NULLSTR,'title':st(1000),'publisher':NULLSTR,
 'published_at':nullable(DT),'fetched_at':DT,'body_hash':nullable(HASH),
 'status':enum('search_snippet','full_text','partial','failed'),'snippet':st(5000),
 'text':nullable(st(100000)),'truncated':{'type':'boolean'}})
S['UserAdmin']=obj({'user_id':UUID,'username':st(128),'email':NULLSTR,'state':enum('active','disabled'),
 'version':POS,'created_at':DT,'membership_starts_at':nullable(DT),'membership_expires_at':nullable(DT),
 'available_units':INT,'reserved_units':INT})
S['Grant']=obj({'grant_id':UUID,'user_id':UUID,'amount_units':POS,'spent_units':INT,'reserved_units':INT,
 'starts_at':DT,'expires_at':DT,'revoked_units':INT,'version':POS})
S['Audit']=obj({'audit_id':UUID,'actor_user_id':UUID,'action':st(80),'object_type':st(80),
 'object_id':UUID,'before':{'type':['object','null']},'after':{'type':['object','null']},
 'reason':st(1000),'created_at':DT,'request_id':UUID})
S['MessagePart']={'oneOf':[
 obj({'type':{'const':'text'},'text':st(500000)}),
 obj({'type':{'const':'tool_use'},'tool_call_id':st(128),'name':st(128),'arguments':{'type':'object'}}),
 obj({'type':{'const':'tool_result'},'tool_call_id':st(128),'text':st(200000),'is_error':{'type':'boolean'}})]}
S['Message']=obj({'role':enum('system','user','assistant','tool'),'parts':arr(ref('MessagePart'),1,100)})
S['ModelRequest']=obj({'request_id':UUID,'task_id':UUID,'attempt_id':UUID,
 'model_role':{'const':'quality-assistant'},'purpose':enum('chat','task','news'),
 'messages':arr(ref('Message'),1,200),'tools':arr(obj({'name':st(128),'description':st(4000),'input_schema':{'type':'object'}}),0,30),
 'max_output_tokens':{'type':'integer','minimum':1,'maximum':8192}})
S['SseEvent']=obj({'event_id':UUID,'run_id':UUID,'seq':POS,
 'type':enum('run.created','text.delta','tool.delta','usage','final','error'),'data':{'type':'object'}})
S['SseEvent']['description']='Wire framing: event=<type>, id=<event_id>, data=<JSON>. seq strictly increases per run. See sse-events.md for type-specific data. Heartbeats are SSE comments every 15s.'
S['ActivateRequest']=obj({'username':st(128),'activation_code':{'type':'string','minLength':20,'maxLength':256},
 'password':{'type':'string','minLength':12,'maxLength':128},'device_id':UUID,'device_label':st(128)})
S['LoginRequest']=obj({'username':st(128),'password':{'type':'string','maxLength':128},'device_id':UUID,'device_label':st(128)})
S['RefreshRequest']=obj({'refresh_token':st(1024),'device_id':UUID})
S['AdminMutation']=obj({'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}})
S['UserStateRequest']=obj({'state':enum('active','disabled'),'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}})
S['MembershipRequest']=obj({'starts_at':DT,'expires_at':DT,'features':arr(st(80),0,100),'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}})
S['GrantRequest']=obj({'amount_units':POS,'starts_at':DT,'expires_at':DT,'origin_ref':NULLSTR,'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}})
S['RevokeGrantRequest']=obj({'amount_units':POS,'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}})

paths={}
def response(schema=None,desc='成功',mime='application/json'):
    x={'description':desc}
    if schema is not None:x['content']={mime:{'schema':schema}}
    return x
def endpoint(path,method,operation,summary,body=None,result=None,status='200',auth=True,admin=False,idem=False,params=None,sse=False):
    rs={status:response(result,'流式事件，非持久输出缓存' if sse else '成功','text/event-stream' if sse else 'application/json')}
    for code in ['400','401','403','404','409','422','429','502','503']:
        rs[code]=response(ref('Error'),'业务或验证错误')
    o={'operationId':operation,'summary':summary,'responses':rs,'security':[{'BearerAuth':[]} ] if auth else [],
       'tags':['admin' if admin else 'client'],'x-role':'admin' if admin else 'user' if auth else 'public'}
    pars=params or []
    if idem:pars=pars+[{'name':'Idempotency-Key','in':'header','required':True,'schema':UUID,'description':'same user/key/body => same result; different body => 409; retained >=7 days'}]
    if pars:o['parameters']=pars
    if body is not None:o['requestBody']={'required':True,'content':{'application/json':{'schema':body}}}
    paths.setdefault(path,{})[method]=o
def path_id(name):return {'name':name,'in':'path','required':True,'schema':UUID}
page_params=[{'name':'cursor','in':'query','schema':st(1000)},{'name':'limit','in':'query','schema':{'type':'integer','minimum':1,'maximum':100,'default':20}}]
def page(schema):return obj({'items':arr(schema,0,100),'next_cursor':NULLSTR})
endpoint('/api/v1/auth/activate','post','activate','激活邀请并创建会话',ref('ActivateRequest'),ref('Session'),auth=False)
endpoint('/api/v1/auth/login','post','login','账号登录',ref('LoginRequest'),ref('Session'),auth=False)
endpoint('/api/v1/auth/refresh','post','refresh','轮换刷新令牌',ref('RefreshRequest'),ref('Session'),auth=False)
endpoint('/api/v1/auth/logout','post','logout','撤销当前刷新会话',ref('RefreshRequest'),status='204')
endpoint('/api/v1/me','get','me','当前用户权益与服务端时间',result=ref('Entitlements'))
endpoint('/api/v1/me/usage','get','myUsage','当前用户调用与结算记录',result=page(ref('Run')),params=page_params)
endpoint('/api/v1/model-runs','post','createModelRun','预留并派发一次模型调用',ref('ModelRequest'),{'type':'string'},idem=True,sse=True)
endpoint('/api/v1/model-runs/{run_id}','get','getModelRun','查询原调用，不重新派发',result=ref('Run'),params=[path_id('run_id')])
endpoint('/api/v1/model-runs/{run_id}/cancel','post','cancelModelRun','请求停止并保留结算状态',obj({}),ref('Run'),status='202',idem=True,params=[path_id('run_id')])
endpoint('/api/v1/search','post','search','公开网页搜索',obj({'request_id':UUID,'task_id':UUID,'attempt_id':UUID,'query':st(500),'limit':{'type':'integer','minimum':1,'maximum':5}}),obj({'request_id':UUID,'sources':arr(ref('Source'),0,5)}),idem=True)
endpoint('/api/v1/search/read','post','readSource','受控读取公开来源',obj({'request_id':UUID,'task_id':UUID,'attempt_id':UUID,'source_id':UUID,'url':{'type':'string','format':'uri','maxLength':4000}}),ref('Source'),idem=True)
endpoint('/api/v1/admin/users','get','adminUsers','管理用户列表',result=page(ref('UserAdmin')),admin=True,params=page_params)
invite_response=obj({'user':ref('UserAdmin'),'activation_code':nullable(st(256)),'activation_expires_at':DT,'secret_unavailable':{'type':'boolean'}})
endpoint('/api/v1/admin/users','post','adminInvite','创建用户与一次性激活码',obj({'username':{'type':'string','minLength':3,'maxLength':128},'email':NULLSTR,'reason':{'type':'string','minLength':1,'maxLength':1000}}),invite_response,status='201',admin=True,idem=True)
endpoint('/api/v1/admin/users/{user_id}','patch','adminUserState','启用或停用用户',ref('UserStateRequest'),ref('UserAdmin'),admin=True,idem=True,params=[path_id('user_id')])
endpoint('/api/v1/admin/users/{user_id}/membership','put','adminMembership','设置会员时间及功能',ref('MembershipRequest'),ref('UserAdmin'),admin=True,idem=True,params=[path_id('user_id')])
endpoint('/api/v1/admin/users/{user_id}/rotate-activation','post','adminRotateActivation','轮换激活或密码恢复码',obj({'kind':enum('activate','password_reset'),'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}}),invite_response,admin=True,idem=True,params=[path_id('user_id')])
endpoint('/api/v1/admin/users/{user_id}/devices','get','adminDevices','查看设备用于人工解绑',result=page(ref('Device')),admin=True,params=[path_id('user_id'),*page_params])
endpoint('/api/v1/admin/users/{user_id}/devices/{device_id}/revoke','post','adminRevokeDevice','解绑旧设备并撤销会话',ref('AdminMutation'),ref('Device'),admin=True,idem=True,params=[path_id('user_id'),path_id('device_id')])
endpoint('/api/v1/admin/users/{user_id}/grants','post','adminGrant','人工发放独立额度批次',ref('GrantRequest'),ref('Grant'),status='201',admin=True,idem=True,params=[path_id('user_id')])
endpoint('/api/v1/admin/grants/{grant_id}/revoke','post','adminRevokeGrant','仅撤销未使用未预留额度',ref('RevokeGrantRequest'),ref('Grant'),admin=True,idem=True,params=[path_id('grant_id')])
endpoint('/api/v1/admin/model-runs','get','adminModelRuns','按用户状态时间查询用量与成本',result=page(ref('AdminRun')),admin=True,params=page_params+[{'name':'user_id','in':'query','schema':UUID},{'name':'billing_state','in':'query','schema':st(80)},{'name':'created_from','in':'query','schema':DT},{'name':'created_until','in':'query','schema':DT}])
endpoint('/api/v1/admin/model-runs/{run_id}/reconcile','post','adminReconcile','查询服务商用量或人工发起未知豁免',obj({'action':enum('query_provider','waive_unknown'),'expected_version':POS,'reason':{'type':'string','minLength':1,'maxLength':1000}}),ref('Run'),admin=True,idem=True,params=[path_id('run_id')])
endpoint('/api/v1/admin/audits','get','adminAudits','管理审计查询',result=page(ref('Audit')),admin=True,params=page_params)
endpoint('/healthz','get','health','健康状态，不暴露环境密钥',result=obj({'status':{'const':'ok'}}),auth=False)
api={'openapi':'3.1.0','info':{'title':'QualityOffice AI产品API','version':'1.0.0','description':'Product-owned baseline. HTTPS origin is deployment configuration; no real credentials included. See API-semantics.md for transactions, streams and role rules.'},
 'servers':[{'url':'https://api.example.invalid','description':'Placeholder only; G03 MUST replace in deployment config'}],
 'tags':[{'name':'client'},{'name':'admin'}],'paths':paths,
 'components':{'securitySchemes':{'BearerAuth':{'type':'http','scheme':'bearer'}},'schemas':S}}
write(R/'openapi.json',api)
event_variants=[]
event_defs={
 'run.created':obj({'request_id':UUID,'reserved_units':INT,'route_version':st(128)}),
 'text.delta':obj({'text':st(100000)}),
 'tool.delta':obj({'index':INT,'arguments_delta':st(100000),'tool_call_id':st(128),'name_delta':st(128)},['index','arguments_delta']),
 'usage':S['Usage'],
 'error':obj({'code':st(80),'message':st(2000),'retryable':{'type':'boolean'}}),
 'final':obj({'state':enum('completed','failed','cancelled','unknown'),
  'billing_state':enum('held','settled','pending_usage','released','waived_unknown'),
  'charged_units':nullable(INT),'finish_reason':enum('stop','tool_calls','cancelled','error','length')})}
for name,fields in event_defs.items():
 event_variants.append(obj({'event_id':UUID,'run_id':UUID,'seq':POS,'type':{'const':name},'data':fields}))
write(R/'sse-event.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:qdesk:sse-event:1.0','oneOf':event_variants})
print(json.dumps({'schemas':len(S),'operations':sum(len(v) for v in paths.values()),'files':7}))
