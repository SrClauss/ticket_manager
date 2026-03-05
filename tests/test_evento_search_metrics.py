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
    participante = {"_id": ObjectId(), "nome": "Fulano", "empresa": "Acme Ltda", "ingressos": []}
    fake_db.eventos.docs.append(evento)
    fake_db.participantes.docs.append(participante)

    async def fake_get(request):
        return evento, str(evento['_id'])
    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    resp = await evento_web.evento_api_busca_smart(DummyRequest(), q="Acme")
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
    metrics = resp if isinstance(resp, list) else json.loads(resp.body)['metrics']
    # find tipo1 entry
    t1 = next(m for m in metrics if m['tipo_nome']=='Publico Geral')
    assert t1['total']==2 and t1['printed']==1
    t2 = next(m for m in metrics if m['tipo_nome']=='VIP')
    assert t2['total']==1 and t2['printed']==0

    # toggle impresso endpoint
    await evento_web.set_ingresso_impresso(str(evento['_id']), str(ing1['_id']), impresso=True)
    # ensure updated in fake_db
    doc = await fake_db.ingressos_emitidos.find_one({"_id": ing1['_id']})
    assert doc.get('impresso') is True
    await evento_web.set_ingresso_impresso(str(evento['_id']), str(ing2['_id']), impresso=False)
    doc2 = await fake_db.ingressos_emitidos.find_one({"_id": ing2['_id']})
    assert doc2.get('impresso') is False

