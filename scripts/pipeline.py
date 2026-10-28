"""MC1 normalization and explainable analysis. All record IDs keep source pointers."""
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from inspect_data import ROOT, RAW, REPORTS, dump, inspect

OUT = ROOT / 'data/processed'
PUBLIC = {'official_post', 'personal_post', 'anonymous_post'}
INTERNAL = {'comms_huddle', 'one_on_one_chat', 'side_huddle'}
TOPIC = re.compile(r'harborcrest|civicloom|residentedge|\bmerger\b|\bacquir\w*|\bembargo\b', re.I)
NAMED = re.compile(r'harborcrest|civicloom|residentedge', re.I)
DECISION = re.compile(r'\b(publish|post it|execute|approved|authorize|release|consent|confirm)\w*', re.I)


def parse_time(value):
    """Keep scenario wall time. Do not invent UTC for timezone-free official timestamps."""
    if not isinstance(value, str): raise ValueError('timestamp must be string')
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None: raise ValueError('Unexpected timezone: review scenario time semantics')
    return parsed.isoformat(timespec='seconds')


def token(value):
    return re.sub(r'[^a-z0-9]', '', str(value).lower())


def aliases(records):
    groups = defaultdict(set)
    for a in records:
        for name in [a['agent_id'], a.get('agent_role',''), a.get('agent_label','')]:
            if name:
                groups[token(name)].add(a['agent_id'])
                groups[token(name.removesuffix('-Agent'))].add(a['agent_id'])
    # Actual recipients use social_manager; actual messages label the same sender Social-Manager-Agent.
    for a in records:
        if a.get('agent_label') == 'Social-Manager-Agent': groups[token('social_manager')].add(a['agent_id'])
    return {k:next(iter(v)) for k,v in groups.items() if len(v)==1}


def write_csv(name, rows, fields=None, directory=OUT):
    directory.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ['id'])
    with (directory / (name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in fields})


def normalize(doc, source):
    rounds=doc.get('rounds')
    if not isinstance(rounds,list): raise ValueError('Expected rounds array')
    roster=[a for r in rounds for a in r.get('participants',[])]+[m for r in rounds for m in r.get('communications',[])]
    amap=aliases(roster)
    messages=[];states=[];events=[];participation=[];round_rows=[];seen={};issues=[];nulls=Counter();missing=Counter()
    raw_count=0;duplicates=0
    def issue(kind, **kw): issues.append({'type':kind,**kw})
    for ri,r in enumerate(rounds):
        start=parse_time(r['hour']);env=r.get('environment_context',{});pointer=f'/rounds/{ri}'
        unavailable=[]
        for name in env.get('agents_unavailable',[]):
            resolved=amap.get(token(name))
            if resolved: unavailable.append(resolved)
            else: issue('unresolved_unavailable',round_index=ri,value=name)
        round_rows.append({'round_index':ri,'timestamp':start,'headline':env.get('event_headline',''),
                           'market_snapshot':env.get('market_snapshot',{}),'unavailable':unavailable,
                           'environment_context':env,'source_file':source,'json_pointer':pointer})
        for ei,(kind,val) in enumerate(env.items()):
            if kind in {'market_snapshot','agents_unavailable','event_headline'}: continue
            for j,entry in enumerate(val if isinstance(val,list) else [val]):
                if entry is None or entry=='': continue
                events.append({'event_id':f'env-{ri}-{ei}-{j}','round_index':ri,'timestamp':start,
                               'time_precision':'round','type':kind,'content':entry if isinstance(entry,str) else json.dumps(entry,ensure_ascii=False),
                               'source_file':source,'json_pointer':pointer+f'/environment_context/{kind}'+(f'/{j}' if isinstance(val,list) else '')})
        for pi,a in enumerate(r.get('participants',[])):
            participation.append({**a,'round_index':ri,'timestamp':start,'source_file':source,'json_pointer':pointer+f'/participants/{pi}'})
        for mi,m in enumerate(r.get('communications',[])):
            raw_count+=1;mid=m.get('message_id');mp=pointer+f'/communications/{mi}'
            for k in ['message_id','agent_id','timestamp','recipients','responding_to','internal_state','content','channel']:
                if k not in m: missing[k]+=1
                elif m[k] is None: nulls[k]+=1
            if not mid or not m.get('agent_id'):
                issue('missing_identity',json_pointer=mp);continue
            try: ts=parse_time(m['timestamp'])
            except (ValueError,KeyError,TypeError):
                issue('invalid_time',message_id=mid,json_pointer=mp);continue
            if mid in seen:
                if seen[mid]!=m: raise ValueError(f'Conflicting duplicate message_id {mid}')
                duplicates+=1;continue
            seen[mid]=m
            rec=m.get('recipients') or []
            if not isinstance(rec,list): issue('invalid_recipients',message_id=mid);rec=[]
            targets=[]
            for name in rec:
                if name=='ALL':continue
                aid=amap.get(token(name))
                if aid: targets.append(aid)
                else: issue('unresolved_recipient',message_id=mid,value=name)
            channel=(m.get('channel') or 'unknown').strip().lower()
            scope='external' if channel in PUBLIC else 'internal' if channel in INTERNAL else 'unknown'
            text=m.get('content') or ''
            row={'message_id':mid,'round_index':ri,'timestamp':ts,'agent_id':m['agent_id'],
                 'role':m.get('agent_role'),'label':m.get('agent_label'),'channel':channel,'scope':scope,
                 'message_type':m.get('message_type'),'recipients_raw':rec,'recipients':sorted(set(targets)),
                 'broadcast':'ALL' in rec,'responding_to':m.get('responding_to'),'content':text,
                 'topic_match':bool(TOPIC.search(text)),'named_topic':bool(NAMED.search(text)),
                 'source_file':source,'json_pointer':mp}
            if scope=='unknown':issue('unknown_channel',message_id=mid,value=channel)
            if ts<start:issue('message_before_round',message_id=mid)
            if ri+1<len(rounds) and ts>=parse_time(rounds[ri+1]['hour']):issue('message_outside_round',message_id=mid)
            messages.append(row)
            state=m.get('internal_state')
            if isinstance(state,dict):
                for kind,val in state.items():
                    if val is None:continue
                    states.append({'state_id':f'{mid}:{kind}','message_id':mid,'agent_id':m['agent_id'],'round_index':ri,
                                   'timestamp':ts,'state_type':kind,'content':str(val),'topic_match':bool(TOPIC.search(str(val))),
                                   'source_file':source,'json_pointer':mp+'/internal_state/'+kind})
            elif state is not None: issue('unexpected_state',message_id=mid)
    edges,ref_issues=build_edges(messages)
    issues.extend(ref_issues)
    roster_ids=sorted(set(a['agent_id'] for a in roster))
    agent_rows=[]
    for aid in roster_ids:
        ar=[a for a in roster if a['agent_id']==aid]; mm=[m for m in messages if m['agent_id']==aid]
        agent_rows.append({'agent_id':aid,'role':ar[0].get('agent_role'),'label':ar[0].get('agent_label'),
                           'roles':sorted(set(a.get('agent_role','') for a in ar)),
                           'labels':sorted(set(a.get('agent_label','') for a in ar)),
                           'participating_rounds':sorted(set(a['round_index'] for a in participation if a['agent_id']==aid)),
                           'message_count':len(mm)})
    for i,r in enumerate(round_rows):
        end=round_rows[i+1]['timestamp'] if i+1<len(round_rows) else max([m['timestamp'] for m in messages if m['round_index']==i] or [r['timestamp']])
        r['window_hours']=max((datetime.fromisoformat(end)-datetime.fromisoformat(r['timestamp'])).total_seconds()/3600,1/60)
    quality={'raw_message_count':raw_count,'clean_message_count':len(messages),'exact_id_duplicates_removed':duplicates,
             'excluded_count':raw_count-len(messages)-duplicates,'missing_fields':dict(missing),'null_fields':dict(nulls),
             'same_text_repetitions':sum(v-1 for v in Counter(m['content'] for m in messages).values() if v>1),
             'empty_recipients':sum(not m['recipients_raw'] for m in messages),
             'broadcast_messages':sum(m['broadcast'] for m in messages),
             'issues':issues,'issue_counts':dict(Counter(i['type'] for i in issues)),
             'notes':['Empty recipients do not prove absence of audience. ALL does not prove reading.',
                      'Null internal state and responding_to are preserved, not imputed.',
                      'Repeated content with distinct IDs retained. No reattribution based on prose.',
                      'Documentation IDs social_manager_agent/judge_eval_agent differ from actual data IDs.',
                      'Environment timestamps have round precision; agent quoted times are not parsed as event time.']}
    return {'messages':messages,'agents':agent_rows,'events':events,'internal_states':states,'communication_edges':edges,
            'participants':participation,'rounds':round_rows,'quality':quality}


def build_edges(messages):
    by_id={m['message_id']:m for m in messages};edges=[];issues=[]
    for m in messages:
        for target in m['recipients']:
            edges.append({'source':m['agent_id'],'target':target,'relation':'recipient','message_id':m['message_id'],
                          'related_message_id':None,'round_index':m['round_index'],'timestamp':m['timestamp'],'channel':m['channel'],
                          'evidence_level':'recorded_recipient','temporal_valid':True,'propagation_confirmed':False})
        parent=by_id.get(m['responding_to'])
        if m['responding_to'] and not parent:
            issues.append({'type':'invalid_reply_reference','message_id':m['message_id'],'reference':m['responding_to']})
        if parent:
            if parent['timestamp']>m['timestamp']:issues.append({'type':'future_reply_reference','message_id':m['message_id'],'reference':parent['message_id']})
            edges.append({'source':m['agent_id'],'target':parent['agent_id'],'relation':'reply','message_id':m['message_id'],
                          'related_message_id':parent['message_id'],'round_index':m['round_index'],'timestamp':m['timestamp'],
                          'channel':m['channel'],'evidence_level':'recorded_reply','temporal_valid':parent['timestamp']<=m['timestamp'],'propagation_confirmed':False})
    return edges,issues


def detect(data):
    ms=data['messages'];rs=data['rounds'];by_round={r['round_index']:r for r in rs}
    # Only an explicit completed lift statement establishes a formal marker, never a proposed earlier lift.
    lifted=[m for m in ms if re.search(r'embargo\s+(?:is\s+)?formally lifted',m['content'],re.I)]
    release=min(lifted,key=lambda m:m['timestamp']) if lifted else None
    out=[]
    def add(m,kind,score,rule):
        out.append({'candidate_id':f"{m['message_id']}:{kind}",'type':kind,'timestamp':m['timestamp'],
                    'round_index':m['round_index'],'agent_id':m['agent_id'],'message_id':m['message_id'],
                    'risk_score':score,'risk_level':'high' if score>=70 else 'medium' if score>=40 else 'low',
                    'rule':rule,'evidence':m['content'],'source_file':m['source_file'],'json_pointer':m['json_pointer'],
                    'interpretation':'Heuristic review candidate; does not establish unauthorized disclosure.'})
    history=defaultdict(list);channel_seen=defaultdict(Counter)
    for r in rs:
        for aid in [a['agent_id'] for a in data['agents']]:
            batch=[m for m in ms if m['round_index']==r['round_index'] and m['agent_id']==aid]
            rate=len(batch)/r['window_hours'];past=history[aid]
            if len(past)>=3 and len(batch)>=5:
                baseline=statistics.median(past)
                if rate>max(baseline*3,2):
                    add(batch[0],'rate_surge',45,f'round rate {rate:.2f}/h > max(3 × historical median {baseline:.2f}/h, 2/h); observation windows are sampled rounds')
            history[aid].append(rate)
            for m in batch:
                c=m['channel'];seen=channel_seen[aid]
                if sum(seen.values())>=10 and seen[c]==0 and m['scope']=='external':
                    add(m,'new_public_channel',40,'First recorded use of this public channel after ≥10 earlier messages; dataset history only')
                seen[c]+=1
                if m['scope']=='external' and m['named_topic']:
                    before=release is not None and m['timestamp']<release['timestamp']
                    add(m,'named_public_before_formal_lift' if before else 'named_public_topic',85 if before else 30,
                        'Public channel + named merger entity' + (f" + before explicit formal marker {release['message_id']}; consent and context still require review" if before else '; keyword is a screening signal only'))
                unavailable=by_round[m['round_index']]['unavailable']
                if unavailable and (m['topic_match'] and (m['scope']=='external' or DECISION.search(m['content']))):
                    add(m,'decision_during_unavailability',70,'Topic + public action/decision verb while environment reports unavailable: '+', '.join(unavailable)+'; round precision, not proof all oversight failed')
    return out,release


def analyze(data):
    ms=data['messages'];rs=data['rounds'];cs,release=detect(data);data['candidates']=cs
    agent_stats=[];temporal=[];channel=[]
    for a in data['agents']:
        aid=a['agent_id'];batch=[m for m in ms if m['agent_id']==aid];ext=sum(m['scope']=='external' for m in batch)
        hours=sum(r['window_hours'] for r in rs if any(m['round_index']==r['round_index'] for m in batch))
        contacts=set(e['target'] if e['source']==aid else e['source'] for e in data['communication_edges'] if e['temporal_valid'] and aid in (e['source'],e['target']))-{aid}
        s={**a,'external_count':ext,'internal_count':sum(m['scope']=='internal' for m in batch),'external_ratio':ext/len(batch) if batch else 0,
           'messages_per_window_hour':len(batch)/hours if hours else 0,'observed_window_hours':hours,
           'contact_count':len(contacts),'candidate_count':sum(c['agent_id']==aid for c in cs),
           'channel_counts':dict(Counter(m['channel'] for m in batch)),
           'before_formal_lift':sum(m['scope']=='external' and release is not None and m['timestamp']<release['timestamp'] for m in batch),
           'after_formal_lift':sum(m['scope']=='external' and release is not None and m['timestamp']>=release['timestamp'] for m in batch)}
        agent_stats.append(s)
    data['agents']=agent_stats
    for r in rs:
        for a in data['agents']:
            batch=[m for m in ms if m['round_index']==r['round_index'] and m['agent_id']==a['agent_id']]
            temporal.append({'round_index':r['round_index'],'timestamp':r['timestamp'],'agent_id':a['agent_id'],
                             'message_count':len(batch),'external_count':sum(m['scope']=='external' for m in batch),
                             'candidate_count':sum(c['round_index']==r['round_index'] and c['agent_id']==a['agent_id'] for c in cs),
                             'window_hours':r['window_hours'],'messages_per_hour':len(batch)/r['window_hours']})
    for name,n in Counter(m['channel'] for m in ms).most_common():
        channel.append({'channel':name,'message_count':n,'ratio':n/len(ms),'scope':next(m['scope'] for m in ms if m['channel']==name)})
    data['temporal']=temporal;data['channels']=channel
    evidence=[]
    for m in ms:
        if m['topic_match']:
            evidence.append({'evidence_id':m['message_id'],'kind':'public_message' if m['scope']=='external' else 'internal_message',
                             'evidence_level':'fact_record','timestamp':m['timestamp'],'round_index':m['round_index'],
                             'agent_id':m['agent_id'],'message_id':m['message_id'],'channel':m['channel'],'content':m['content'],
                             'decision_signal':bool(DECISION.search(m['content'])),'source_file':m['source_file'],'json_pointer':m['json_pointer']})
    for s in data['internal_states']:
        if s['topic_match']:evidence.append({'evidence_id':s['state_id'],'kind':'internal_state','evidence_level':'fact_record',**s})
    for e in data['events']:
        if TOPIC.search(e['content']):evidence.append({'evidence_id':e['event_id'],'kind':'environment','evidence_level':'fact_record',**e})
    evidence.sort(key=lambda e:(e['timestamp'],e['evidence_id']))
    ids={m['message_id'] for m in ms if m['topic_match']}
    relations=[{'from_message_id':e['related_message_id'],'to_message_id':e['message_id'],'evidence_level':'inference_reply',
                'claim':'Topic messages linked by reply; information transfer or causality remains unconfirmed.'}
               for e in data['communication_edges'] if e['relation']=='reply' and e['temporal_valid'] and e['message_id'] in ids and e['related_message_id'] in ids]
    public=[m for m in ms if m['scope']=='external' and m['named_topic']]
    data['evidence']=evidence
    data['evidence_summary']={'formal_lift':release,'first_topic_record':evidence[0] if evidence else None,
                              'first_named_public':min(public,key=lambda m:m['timestamp']) if public else None,
                              'topic_reply_relations':relations,
                              'unknowns':['Reply does not establish causal transmission.',
                                          'Public posts before formal lift may follow bilateral consent; review permission context.',
                                          'Embedded hearsay and proposed times are not independent events.',
                                          'Sampled daily vs hourly rounds do not represent continuous observation.']}
    return data


def run():
    profile=inspect();paths=sorted(p for p in RAW.rglob('*.json') if '__MACOSX' not in p.parts)
    if len(paths)!=1:raise ValueError('Expected one MC1 JSON; select source explicitly if upstream changes')
    p=paths[0];data=analyze(normalize(json.loads(p.read_text(encoding='utf-8')),str(p.relative_to(RAW))))
    for table in ['messages','agents','events','internal_states','communication_edges','participants','rounds','candidates']:
        write_csv(table,data[table])
    for name,rows in [('agent_statistics',data['agents']),('channel_statistics',data['channels']),('temporal_statistics',data['temporal'])]:
        write_csv(name,rows,directory=REPORTS)
    times=[m['timestamp'] for m in data['messages']]
    profile.update({'source':'official VAST Challenge 2026 MC1','agent_count':len(data['agents']),
                    'message_count':len(data['messages']),'round_count':len(data['rounds']),
                    'start':min(times),'end':max(times),'channel_counts':{c['channel']:c['message_count'] for c in data['channels']},
                    'internal_state_rows':len(data['internal_states']),'event_count':len(data['events']),
                    'edge_count':len(data['communication_edges']),'candidate_count':len(data['candidates']),
                    'round_window_hours':sorted(set(r['window_hours'] for r in data['rounds'])),
                    'time_semantics':'Official scenario wall time, timezone unspecified. Round windows are not equal.'})
    data['profile']=profile
    dump(REPORTS/'data_profile.json',profile);dump(REPORTS/'data_quality_report.json',data['quality'])
    dump(REPORTS/'evidence_chain.json',data['evidence_summary']);dump(OUT/'dashboard.json',data)
    print(json.dumps({k:profile[k] for k in ['agent_count','message_count','round_count','candidate_count','edge_count']}))
    return data

if __name__=='__main__':run()
