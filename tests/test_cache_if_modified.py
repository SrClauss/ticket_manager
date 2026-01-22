import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from email.utils import format_datetime

from app.routers import evento_api


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
        query = query or {}
        for d in self.docs:
            match = True
            for k, v in query.items():
                if k not in d:
                    match = False
                    break
                # simple equality (ObjectId compared as str in tests)
                if isinstance(v, ObjectId):
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


class FakeRequest:
    def __init__(self, headers):
        self.headers = headers


def make_event(ev_id):
    return {'_id': ev_id, 'nome': 'Evt', 'layout_ingresso': {'canvas': {'width': 80, 'height': 120, 'unit': 'mm'}, 'elements': [{'type':'text','value':'{NOME}','x':10,'y':5,'size':12},{'type':'qrcode','value':'{qrcode_hash}','x':10,'y':20,'size':30}]}}


async def _call_render(fake_db, ev_id, ingresso):
    # monkeypatch via assignment
    evento_api.get_database = lambda: fake_db
    return await evento_api.render_ingresso_jpg(str(ev_id), str(ingresso['_id']))


def test_if_none_match_returns_304(monkeypatch):
    ev_id = ObjectId()
    part_id = ObjectId()
    tipo_id = ObjectId()

    data_em = datetime.now(timezone.utc)
    ingresso_id = ObjectId()
    ingresso = {'_id': ingresso_id, 'evento_id': str(ev_id), 'participante_id': str(part_id), 'tipo_ingresso_id': str(tipo_id), 'qrcode_hash': 'abc123', 'data_emissao': data_em}
    evento = make_event(str(ev_id))
    fake_db = FakeDB(eventos=[evento], participantes=[{'_id': part_id, 'nome': 'Joao'}], ingressos=[ingresso], tipos=[{'_id': tipo_id, 'descricao': 'VIP'}])

    # compute expected etag
    etag_src = ingresso['qrcode_hash'] + str(ingresso['data_emissao'])
    etag = hashlib.sha1(etag_src.encode()).hexdigest()

    # call with If-None-Match header
    evento_api.get_database = lambda: fake_db
    resp = asyncio.run(evento_api.render_ingresso_jpg(str(ev_id), str(ingresso['_id']), request=FakeRequest({'if-none-match': etag})))
    assert getattr(resp, 'status_code', None) == 304


def test_if_modified_since_returns_304(monkeypatch):
    ev_id = ObjectId()
    part_id = ObjectId()
    tipo_id = ObjectId()

    data_em = datetime.now(timezone.utc)
    ingresso_id = ObjectId()
    ingresso = {'_id': ingresso_id, 'evento_id': str(ev_id), 'participante_id': str(part_id), 'tipo_ingresso_id': str(tipo_id), 'qrcode_hash': 'abc123', 'data_emissao': data_em}
    evento = make_event(str(ev_id))
    fake_db = FakeDB(eventos=[evento], participantes=[{'_id': part_id, 'nome': 'Joao'}], ingressos=[ingresso], tipos=[{'_id': tipo_id, 'descricao': 'VIP'}])

    # set If-Modified-Since to a time AFTER data_emissao
    ims = format_datetime(data_em + timedelta(seconds=5))

    evento_api.get_database = lambda: fake_db
    resp = asyncio.run(evento_api.render_ingresso_jpg(str(ev_id), str(ingresso['_id']), request=FakeRequest({'if-modified-since': ims})))
    assert getattr(resp, 'status_code', None) == 304


def test_if_modified_since_before_emission_renders(monkeypatch):
    ev_id = ObjectId()
    part_id = ObjectId()
    tipo_id = ObjectId()

    data_em = datetime.now(timezone.utc)
    ingresso_id = ObjectId()
    ingresso = {'_id': ingresso_id, 'evento_id': str(ev_id), 'participante_id': str(part_id), 'tipo_ingresso_id': str(tipo_id), 'qrcode_hash': 'abc123', 'data_emissao': data_em}
    evento = make_event(str(ev_id))
    fake_db = FakeDB(eventos=[evento], participantes=[{'_id': part_id, 'nome': 'Joao'}], ingressos=[ingresso], tipos=[{'_id': tipo_id, 'descricao': 'VIP'}])

    ims = format_datetime(data_em - timedelta(days=1))

    evento_api.get_database = lambda: fake_db
    resp = asyncio.run(evento_api.render_ingresso_jpg(str(ev_id), str(ingresso['_id']), request=FakeRequest({'if-modified-since': ims})))
    # should be image/jpeg StreamingResponse
    assert getattr(resp, 'media_type', '') == 'image/jpeg'
