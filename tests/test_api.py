import pytest
from fastapi.testclient import TestClient
from aquarium.api import app
from aquarium import api

client=TestClient(app)

def test_empty_tank_and_validation():
    assert client.post('/compatibility',json={'ids':[]}).json()['status']=='compatible'
    assert client.post('/compatibility',json={'ids':['invalid']} ).status_code==422
    assert client.post('/compatibility',json={'ids':['a'*16]*61}).status_code==422
    assert client.get('/species').status_code==200

def test_missing_index_fails_closed(monkeypatch,tmp_path):
    from aquarium.rag import SpeciesIndex
    monkeypatch.setattr(api,'index',SpeciesIndex(tmp_path))
    assert client.post('/compatibility',json={'ids':['a'*16]}).status_code==503

@pytest.mark.skipif(not (api.index.path/'metadata.json').exists(),reason='Build semantic index first')
def test_real_vector_index():
    from aquarium.catalog import load_catalog
    ids=[load_catalog()[n]['id'] for n in [0,35,260]]
    response=client.post('/compatibility',json={'ids':ids})
    assert response.status_code==200
    result=response.json();assert len(result['evidence'])==3;assert {r['id'] for r in result['retrieved']}==set(ids)
    assert result['status']=='uncertain'
    assert len(client.get('/search',params={'q':'camarão pacífico água doce'}).json())==5
    assert client.post('/compatibility',json={'ids':['0'*16]}).status_code==422
