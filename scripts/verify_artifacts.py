"""Cross-check generated figures, reports and tables against the normalized source."""
import csv
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def verify():
    d=json.loads((ROOT/'data/processed/dashboard.json').read_text());p=d['profile'];ms=d['messages'];ids={m['message_id'] for m in ms}
    assert len(ids)==len(ms)==p['message_count']
    assert len(d['agents'])==p['agent_count']
    assert sum(a['message_count'] for a in d['agents'])==len(ms)
    assert sum(t['message_count'] for t in d['temporal'])==len(ms)
    assert sum(c['message_count'] for c in d['channels'])==len(ms)
    for e in d['communication_edges']:
        assert e['source'] in {a['agent_id'] for a in d['agents']} and e['target'] in {a['agent_id'] for a in d['agents']}
        assert e['message_id'] in ids and (not e['related_message_id'] or e['related_message_id'] in ids)
    for c in d['candidates']:assert c['message_id'] in ids and 0<=c['risk_score']<=100
    source=next((ROOT/'data/raw').rglob('MC1*.json'));raw=json.loads(source.read_text())
    for m in ms:
        obj=raw
        for key in m['json_pointer'].strip('/').split('/'):obj=obj[int(key)] if isinstance(obj,list) else obj[key]
        assert obj['message_id']==m['message_id'] and obj['content']==m['content']
    mf=json.loads((ROOT/'reports/figures/figure_manifest.json').read_text());figs=mf['figures'];assert len(figs)==7
    assert figs[1]['totals']=={a['agent_id']:a['message_count'] for a in d['agents']}
    assert figs[2]['totals']=={c['channel']:c['message_count'] for c in d['channels']}
    assert figs[3]['totals']['sum']==figs[4]['totals']['sum']==len(ms)
    assert figs[5]['totals']['nodes']==len(d['agents'])
    assert figs[6]['totals']['标准化后 保留']==len(ms)
    for f in figs:assert (ROOT/'reports/figures'/f['file']).stat().st_size>1000
    for name in ['data_profile.json','data_dictionary.csv','data_quality_report.json','agent_statistics.csv','channel_statistics.csv','temporal_statistics.csv']:
        assert (ROOT/'data/reports'/name).exists()
    for name in ['messages','agents','events','internal_states','communication_edges','participants','rounds','candidates']:
        with (ROOT/'data/processed'/(name+'.csv')).open(encoding='utf-8-sig') as f:
            assert len(list(csv.DictReader(f)))==len(d[name])
    for n in range(1,7):assert list((ROOT/'docs').glob(f'{n:02d}_*.md'))
    assert (ROOT/'frontend/dist/index.html').exists()
    print(f'Verified {len(ms)} raw source pointers, 8 tables, 6 reports, 7 figures and frontend artifact.')
    return {'raw_source_pointers':len(ms),'tables':8,'required_reports':6,'figures':7,'status':'passed'}

if __name__=='__main__':
    result=verify();(ROOT/'reports/artifact_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
