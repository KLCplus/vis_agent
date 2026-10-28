from fastapi.testclient import TestClient
from backend.app import main


def test_health_and_unavailable(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA_PATH',tmp_path/'missing.json')
    client=TestClient(main.app)
    assert client.get('/api/health').json()['data_ready'] is False
    assert client.get('/api/dashboard').status_code==503


def test_api_filters_and_detail(tmp_path,monkeypatch):
    import json
    p=tmp_path/'dashboard.json'
    p.write_text(json.dumps({'messages':[{'message_id':'test-a','agent_id':'test','channel':'internal',
                                          'timestamp':'2046-06-05T09:00:00','content':'TEST sample','round_index':0}],
                             'internal_states':[],'events':[],'candidates':[],'communication_edges':[]}))
    monkeypatch.setattr(main,'DATA_PATH',p)
    client=TestClient(main.app)
    assert client.get('/api/messages?q=sample').json()['total']==1
    assert client.get('/api/messages?agent_id=other').json()['total']==0
    assert client.get('/api/messages/test-a').status_code==200
    assert client.get('/api/messages/unknown').status_code==404
    assert client.get('/api/messages?limit=0').status_code==422
