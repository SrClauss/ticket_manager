import asyncio
from io import BytesIO
from types import SimpleNamespace
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.routers import evento_api


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
        for d in self.docs:
            match = True
            for k, v in (query or {}).items():
                if k not in d:
                    match = False
                    break
                if hasattr(v, '__class__') and v.__class__.__name__ == 'ObjectId':
                    if str(d[k]) != str(v):
                        match = False
                        break
                else:
                    if d[k] != v:
                        match = False
                        break
            if match:
                return d
        return None


class FakeDB:
    def __init__(self, eventos=None, tipos=None, participantes=None, ingressos=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        self.participantes = FakeCollection(participantes or [])
        self.ingressos_emitidos = FakeCollection(ingressos or [])


def make_event(ev_id):
    return {'_id': ev_id, 'nome': 'Evt', 'layout_ingresso': {'canvas': {'width': 80, 'height': 120, 'unit': 'mm'}, 'elements': [{'type':'text','value':'{NOME}','x':10,'y':5,'size':12},{'type':'qrcode','value':'{qrcode_hash}','x':10,'y':20,'size':40}]}}


def test_render_ingresso_jpg(monkeypatch):
    ev_id = ObjectId()
    part_id = ObjectId()
    tipo_id = ObjectId()

    evento = make_event(str(ev_id))
    participante = {'_id': part_id, 'nome': 'Joao', 'cpf': '52998224725'}
    ingresso = {'_id': ObjectId(), 'evento_id': str(ev_id), 'participante_id': str(part_id), 'tipo_ingresso_id': str(tipo_id), 'qrcode_hash': 'abc123', 'data_emissao': datetime.now(timezone.utc)}
    tipo = {'_id': tipo_id, 'descricao': 'VIP', 'layout_ingresso': evento['layout_ingresso']}

    fake_db = FakeDB(eventos=[evento], participantes=[participante], ingressos=[ingresso], tipos=[tipo])
    monkeypatch.setattr(evento_api, 'get_database', lambda: fake_db)

    resp = asyncio.run(evento_api.render_ingresso_jpg(str(ev_id), str(ingresso['_id'])))
    # StreamingResponse has media_type attribute
    assert resp.media_type == 'image/jpeg'


def test_meta_endpoint(monkeypatch):
    ev_id = ObjectId()
    part_id = ObjectId()
    tipo_id = ObjectId()

    evento = {'_id': ev_id, 'nome': 'Evt'}
    participante = {'_id': part_id, 'nome': 'Joao', 'cpf': '52998224725'}
    ingresso = {'_id': ObjectId(), 'evento_id': str(ev_id), 'participante_id': str(part_id), 'tipo_ingresso_id': str(tipo_id), 'qrcode_hash': 'abc123', 'data_emissao': datetime.now(timezone.utc)}
    tipo = {'_id': tipo_id, 'descricao': 'VIP'}

    fake_db = FakeDB(eventos=[evento], participantes=[participante], ingressos=[ingresso], tipos=[tipo])
    monkeypatch.setattr(evento_api, 'get_database', lambda: fake_db)

    res = asyncio.run(evento_api.meta_ingresso(str(ev_id), str(ingresso['_id'])))
    assert res['nome'] == 'Joao'
    assert res['tipo'] == 'VIP'
