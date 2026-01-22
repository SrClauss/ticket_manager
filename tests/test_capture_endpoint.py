import asyncio
import os
from bson import ObjectId
from datetime import datetime, timezone

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

    async def update_one(self, query, update):
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                if '$set' in update:
                    for kk, vv in update['$set'].items():
                        d[kk] = vv
                return type('R', (), {'modified_count': 1})
        return type('R', (), {'modified_count': 0})


class FakeDB:
    def __init__(self, eventos=None, tipos=None, participantes=None, ingressos=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        self.participantes = FakeCollection(participantes or [])
        self.ingressos_emitidos = FakeCollection(ingressos or [])


class FakeUploadFile:
    def __init__(self, data: bytes, filename: str = 'cap.jpg'):
        self._data = data
        self.filename = filename

    async def read(self):
        return self._data


def test_capture_endpoint_creates_file_and_updates_db(monkeypatch, tmp_path):
    ev_id = ObjectId()
    ingresso_id = ObjectId()

    ingresso = {'_id': ingresso_id, 'evento_id': str(ev_id), 'participante_id': 'p1'}
    fake_db = FakeDB(eventos=[{'_id': ev_id}], ingressos=[ingresso], participantes=[{'_id': 'p1', 'nome': 'X'}])

    monkeypatch.setattr(evento_api, 'get_database', lambda: fake_db)

    data = b'JPEGDATA'
    upload = FakeUploadFile(data)

    # call capture
    res = asyncio.run(evento_api.capture_ingresso(str(ev_id), str(ingresso_id), file=upload))
    assert res['message'] == 'captured'
    path = res['path']
    assert os.path.exists(path)

    # check db updated
    updated = fake_db.ingressos_emitidos.docs[0]
    assert 'captured_image_path' in updated
    assert updated['captured_image_path'] == path
    assert 'captured_at' in updated

    # cleanup
    try:
        os.remove(path)
    except Exception:
        pass
