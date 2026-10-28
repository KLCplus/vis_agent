"""Read-only local data service; generate data before starting."""
import json
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DATA_PATH=Path(__file__).resolve().parents[2]/'data/processed/dashboard.json'
app=FastAPI(title='HarborCrest Evidence Lab',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET'])


@lru_cache(maxsize=2)
def read_snapshot(path, modified):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def snapshot():
    if not DATA_PATH.exists():raise HTTPException(503,'Run python scripts/preprocess.py before starting the API')
    return read_snapshot(str(DATA_PATH),DATA_PATH.stat().st_mtime_ns)


@app.get('/api/health')
def health():
    return {'status':'ok','data_ready':DATA_PATH.exists()}


@app.get('/api/dashboard')
def dashboard():return snapshot()


@app.get('/api/messages')
def messages(agent_id: str|None=None,channel: str|None=None,start: str|None=None,end: str|None=None,
             q: str='',offset: int=Query(0,ge=0),limit: int=Query(100,ge=1,le=1000)):
    rows=[m for m in snapshot()['messages'] if (not agent_id or m['agent_id']==agent_id)
          and (not channel or m['channel']==channel) and (not start or m['timestamp']>=start)
          and (not end or m['timestamp']<=end) and q.lower() in m['content'].lower()]
    return {'total':len(rows),'items':rows[offset:offset+limit]}


@app.get('/api/messages/{message_id}')
def message(message_id:str):
    d=snapshot();m=next((m for m in d['messages'] if m['message_id']==message_id),None)
    if m is None:raise HTTPException(404,'Unknown message_id')
    return {'message':m,'internal_states':[s for s in d['internal_states'] if s['message_id']==message_id],
            'candidates':[c for c in d['candidates'] if message_id in c.get('supporting_message_ids',[c['message_id']])],
            'events':[e for e in d['events'] if e['round_index']==m['round_index']],
            'relations':[e for e in d['communication_edges'] if message_id in (e['message_id'],e['related_message_id'])]}
