"""Tests for evento_web search and metric endpoints."""
import pytest
from bson import ObjectId

from app.routers import evento_web
from tests.conftest import FakeCollection


class DummyRequest:
    def __init__(self):
        self.cookies = {}


@pytest.mark.asyncio
async def test_busca_smart_by_empresa(monkeypatch, fake_db, mock_get_database):
    # prepare fake event and participant
    evento = {"_id": ObjectId(), "nome": "Ev", "ilhas": []}
    # participant must have an ingresso for this event to be considered
    ingresso = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": "", "qrcode_hash": "", "impresso": False}
    participante = {"_id": ObjectId(), "nome": "Fulano", "empresa": "Acme Ltda", "cpf": "12345678901", "ingressos": [ingresso]}
    fake_db.eventos.docs.append(evento)
    fake_db.participantes.docs.append(participante)
    fake_db.ingressos_emitidos.docs.append({**ingresso, "participante_id": str(participante['_id'])})

    async def fake_get(request):
        return evento, str(evento['_id'])
    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    resp = await evento_web.evento_api_busca_smart(DummyRequest(), q="Acme")

    # substring of cpf should also match
    resp_cpf = await evento_web.evento_api_busca_smart(DummyRequest(), q="123")
    if not isinstance(resp_cpf, list):
        import json
        tmp = json.loads(resp_cpf.body)
        resp_cpf = tmp
    assert len(resp_cpf) == 1
    assert resp_cpf[0]['empresa'] == 'Acme Ltda'
    assert isinstance(resp, list) or hasattr(resp, 'body')
    # Response may be JSONResponse; extract list
    results = resp if isinstance(resp, list) else resp.body
    # body might be bytes
    if not isinstance(results, list):
        import json
        results = json.loads(results)
    assert len(results) == 1
    assert results[0]['empresa'] == 'Acme Ltda'


@pytest.mark.asyncio
async def test_busca_smart_by_tipo(monkeypatch, fake_db, mock_get_database):
    evento = {"_id": ObjectId(), "nome": "Ev", "ilhas": []}
    # create a ticket type
    tipo = {"_id": ObjectId(), "nome": "Palestrante"}
    fake_db.tipos_ingresso.docs.append(tipo)
    # participant with an ingresso of that tipo
    ingresso = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": str(tipo['_id']), "qrcode_hash": "abc"}
    participante = {"_id": ObjectId(), "nome": "Zé", "empresa": "X", "ingressos": [ingresso]}
    fake_db.eventos.docs.append(evento)
    fake_db.participantes.docs.append(participante)
    fake_db.ingressos_emitidos.docs.append({**ingresso, "participante_id": str(participante['_id'])})

    async def fake_get(request):
        return evento, str(evento['_id'])
    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    resp = await evento_web.evento_api_busca_smart(DummyRequest(), q="Palestrante")
    import json
    if not isinstance(resp, list):
        results = json.loads(resp.body)
    else:
        results = resp
    assert len(results) == 1
    assert results[0]['nome'] == 'Zé'


@pytest.mark.asyncio
async def test_busca_smart_excludes_other_event(monkeypatch, fake_db, mock_get_database):
    # create two events and a participant with ingresso in the other one
    evento = {"_id": ObjectId(), "nome": "Ev", "ilhas": []}
    other_event = {"_id": ObjectId(), "nome": "Outro", "ilhas": []}
    fake_db.eventos.docs.extend([evento, other_event])
    # ticket type (not really used)
    tipo = {"_id": ObjectId(), "nome": "Tipo"}
    fake_db.tipos_ingresso.docs.append(tipo)
    ingresso = {"_id": ObjectId(),
               "evento_id": str(other_event['_id']),
               "tipo_ingresso_id": str(tipo['_id']),
               "qrcode_hash": "tok",
               "impresso": False}
    participante = {"_id": ObjectId(), "nome": "Xpto", "empresa": "Nada", "cpf": "12345678901", "ingressos": [ingresso]}
    fake_db.participantes.docs.append(participante)
    fake_db.ingressos_emitidos.docs.append({**ingresso, "participante_id": str(participante['_id'])})

    async def fake_get(request):
        return evento, str(evento['_id'])
    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    # search by name should yield no results
    resp = await evento_web.evento_api_busca_smart(DummyRequest(), q="Xpto")
    import json
    results = resp if isinstance(resp, list) else json.loads(resp.body)
    assert len(results) == 0

    # search by cpf snippet should also yield none (since participant belongs to other event)
    resp2 = await evento_web.evento_api_busca_smart(DummyRequest(), q="123")
    results2 = resp2 if isinstance(resp2, list) else json.loads(resp2.body)
    assert len(results2) == 0

    # search full 11 digits should also return none
    resp3 = await evento_web.evento_api_busca_smart(DummyRequest(), q="12345678901")
    results3 = resp3 if isinstance(resp3, list) else json.loads(resp3.body)
    assert len(results3) == 0

@pytest.mark.asyncio
async def test_ilha_capacity_metrics(monkeypatch, fake_db, mock_get_database):
    evento = {"_id": ObjectId(), "nome": "Ev", "ilhas": []}
    fake_db.eventos.docs.append(evento)
    # ilhas
    ilha1 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "nome_setor": "A", "capacidade_maxima": 100}
    ilha2 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "nome_setor": "B", "capacidade_maxima": 50}
    fake_db.ilhas.docs.extend([ilha1, ilha2])
    # tipos with permissions
    tipo1 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "nome": "T1", "permissoes": [str(ilha1['_id'])]}
    tipo2 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "nome": "T2", "permissoes": [str(ilha1['_id']), str(ilha2['_id'])]}
    fake_db.tipos_ingresso.docs.extend([tipo1, tipo2])
    # ingressos
    ing1 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": str(tipo1['_id']), "impresso": False}
    ing2 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": str(tipo2['_id']), "impresso": True}
    fake_db.ingressos_emitidos.docs.extend([ing1, ing2])
    async def fake_get(request):
        return evento, str(evento['_id'])
    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)
    resp = await evento_web.evento_api_ingresso_metrics(DummyRequest())
    import json
    body = resp if isinstance(resp, list) else json.loads(resp.body)
    ilha_metrics = body.get('ilha_metrics', [])
    # find entries
    m1 = next(i for i in ilha_metrics if i['ilha_id']==str(ilha1['_id']))
    assert m1['capacidade']==100 and m1['vendidos']==2
    m2 = next(i for i in ilha_metrics if i['ilha_id']==str(ilha2['_id']))
    assert m2['capacidade']==50 and m2['vendidos']==1

@pytest.mark.asyncio
async def test_ingresso_metrics_and_impresso_toggle(monkeypatch, fake_db, mock_get_database):
    evento = {"_id": ObjectId(), "nome": "Ev", "ilhas": []}
    fake_db.eventos.docs.append(evento)
    # two types
    tipo1 = {"_id": ObjectId(), "nome": "Publico Geral"}
    tipo2 = {"_id": ObjectId(), "nome": "VIP"}
    fake_db.tipos_ingresso.docs.extend([tipo1, tipo2])
    # create ingressos
    ing1 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": str(tipo1['_id']), "impresso": False}
    ing2 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": str(tipo1['_id']), "impresso": True}
    ing3 = {"_id": ObjectId(), "evento_id": str(evento['_id']), "tipo_ingresso_id": str(tipo2['_id']), "impresso": False}
    fake_db.ingressos_emitidos.docs.extend([ing1, ing2, ing3])

    async def fake_get(request):
        return evento, str(evento['_id'])
    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    # metrics
    resp = await evento_web.evento_api_ingresso_metrics(DummyRequest())
    assert isinstance(resp, list) or hasattr(resp,'body')
    import json
    body = resp if isinstance(resp, list) else json.loads(resp.body)
    # old metrics under tipo_metrics
    metrics = body.get('tipo_metrics', [])
    # find tipo1 entry
    t1 = next(m for m in metrics if m['tipo_nome']=='Publico Geral')
    assert t1['total']==2 and t1['printed']==1
    t2 = next(m for m in metrics if m['tipo_nome']=='VIP')
    assert t2['total']==1 and t2['printed']==0
    # ilha_metrics should exist (no ilhas defined => empty)
    assert body.get('ilha_metrics') == []

    # toggle impresso endpoint using evento_api
    from app.routers import evento_api
    from app.routers.evento_api import ImpressoUpdate
    resp1 = await evento_api.set_ingresso_impresso(str(evento['_id']), str(ing1['_id']), ImpressoUpdate(impresso=True))
    assert resp1.get('success') is True
    resp2 = await evento_api.set_ingresso_impresso(str(evento['_id']), str(ing2['_id']), ImpressoUpdate(impresso=False))
    assert resp2.get('success') is True

