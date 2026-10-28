"""Explicitly synthetic fixture matching the inspected official schema."""
import copy
import json
from pathlib import Path
import pytest
from pipeline import normalize, parse_time, analyze


def fixture():
    def m(mid,aid,t,**kw):
        return {'message_id':mid,'agent_id':aid,'agent_role':aid,'agent_label':aid+'-Agent',
                'timestamp':t,'channel':'one_on_one_chat','recipients':[],'message_type':'chat',
                'responding_to':None,'content':'test fixture','internal_state':None,**kw}
    return {'rounds':[{'hour':'2046-05-17T09:00:00','environment_context':{},'participants':[],
                       'communications':[m('a','legal','2046-05-17T09:00:00',recipients=['ALL']),
                                         m('b','pr','2046-05-17T09:01:00',recipients=['legal'],responding_to='a',internal_state={'reacting':None,'deliberating':'test'})]},
                      {'hour':'2046-05-20T09:00:00','environment_context':{},'participants':[],
                       'communications':[m('c','pr','2046-05-20T09:30:00',responding_to='@legal')]}]}


def test_parse_and_normalize():
    d=normalize(fixture(),'TEST_ONLY.json')
    assert len(d['messages'])==3 and d['messages'][1]['recipients']==['legal']
    assert d['messages'][1]['json_pointer']=='/rounds/0/communications/1'
    assert len(d['internal_states'])==1
    assert d['messages'][0]['broadcast'] and not d['messages'][0]['recipients']


def test_nonuniform_time():
    d=normalize(fixture(),'TEST_ONLY.json')
    assert d['rounds'][0]['window_hours']==72 and d['rounds'][1]['window_hours']==.5
    assert parse_time('2046-06-05T18:00')=='2046-06-05T18:00:00'
    with pytest.raises(ValueError):parse_time('not-time')
    with pytest.raises(ValueError):parse_time('2046-06-05T18:00Z')


def test_edges_separate_recipient_and_reply():
    d=normalize(fixture(),'TEST_ONLY.json');edges=d['communication_edges']
    assert {e['relation'] for e in edges}=={'recipient','reply'}
    assert all(e['target']=='legal' and not e['propagation_confirmed'] for e in edges)
    assert d['quality']['issue_counts']=={'invalid_reply_reference':1}


def test_future_reference_flagged_not_propagation():
    f=fixture();f['rounds'][0]['communications'][0]['responding_to']='c'
    d=analyze(normalize(f,'TEST_ONLY.json'))
    assert any(not e['temporal_valid'] for e in d['communication_edges'])
    assert d['quality']['issue_counts']['future_reply_reference']==1
    assert not d['evidence_summary']['topic_reply_relations']


def test_duplicates_and_invalid_time():
    f=fixture();f['rounds'][0]['communications'].append(copy.deepcopy(f['rounds'][0]['communications'][0]))
    d=normalize(f,'TEST_ONLY.json');assert len(d['messages'])==3
    assert d['quality']['exact_id_duplicates_removed']==1
    f['rounds'][0]['communications'][-1]['content']='conflict'
    with pytest.raises(ValueError,match='Conflicting'):normalize(f,'TEST_ONLY.json')
    f=fixture();f['rounds'][0]['communications'][0]['timestamp']='invalid'
    assert normalize(f,'TEST_ONLY.json')['quality']['excluded_count']==1


def test_keywords_alone_not_public_disclosure():
    f=fixture();f['rounds'][0]['communications'][0]['content']='CivicLoom merger'
    d=analyze(normalize(f,'TEST_ONLY.json'))
    assert not any(c['type'].startswith('named_public') for c in d['candidates'])
    assert d['evidence_summary']['formal_lift'] is None


def test_release_marker_ignores_proposed_lift():
    f=fixture();m=f['rounds'][0]['communications'][0]
    m['content']='Request an accelerated embargo lift at 3 PM.'
    f['rounds'][1]['communications'][0]['content']='Embargo formally lifted 6:00 PM.'
    d=analyze(normalize(f,'TEST_ONLY.json'))
    assert d['evidence_summary']['formal_lift']['message_id']=='c'


def test_real_integrity_when_downloaded():
    p=Path('data/processed/dashboard.json')
    if not p.exists():pytest.skip('Run preprocess for official integration check')
    d=json.loads(p.read_text());ms=d['messages'];ids={m['message_id'] for m in ms}
    assert len(ids)==len(ms)==sum(a['message_count'] for a in d['agents'])
    assert sum(c['message_count'] for c in d['channels'])==len(ms)
    assert all(e['message_id'] in ids for e in d['communication_edges'])
    assert all(not e['propagation_confirmed'] for e in d['communication_edges'])
    assert sum(t['message_count'] for t in d['temporal'])==len(ms)


def test_acquisition_topic_is_not_dropped():
    f=fixture();f["rounds"][0]["communications"][0]["content"]="An acquisition is under discussion."
    d=analyze(normalize(f,"TEST_ONLY.json"))
    assert d["messages"][0]["topic_match"]
    assert any(e["message_id"]=="a" for e in d["evidence"])


def test_agent_rates_share_full_corpus_denominator():
    d=analyze(normalize(fixture(),'TEST_ONLY.json'))
    assert len({a['observed_window_hours'] for a in d['agents']})==1
    hours=sum(r['window_hours'] for r in d['rounds'])
    assert all(a['messages_per_window_hour']==a['message_count']/hours for a in d['agents'])

def test_real_round_candidate_support_covers_whole_agent_round():
    p=Path('data/processed/dashboard.json')
    if not p.exists():pytest.skip('Run preprocess')
    d=json.loads(p.read_text())
    for c in d['candidates']:
        if c['candidate_unit']=='round':
            assert set(c['supporting_message_ids'])=={m['message_id'] for m in d['messages'] if m['agent_id']==c['agent_id'] and m['round_index']==c['round_index']}
