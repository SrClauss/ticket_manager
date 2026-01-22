import asyncio
from bson import ObjectId
from app.routers import admin
from app.routers import admin as admin_router


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
        # simple matching for _id which can be ObjectId
        for d in self.docs:
            match = True
            for k, v in (query or {}).items():
                val = d.get(k)
                if hasattr(v, '__class__') and v.__class__.__name__ == 'ObjectId':
                    if str(val) != str(v):
                        match = False
                        break
                else:
                    if val != v:
                        match = False
                        break
            if match:
                return d
        return None

    async def find(self, query=None):
        for d in self.docs:
            match = True
            for k, v in (query or {}).items():
                if d.get(k) != v:
                    match = False
                    break
            if match:
                yield d


class FakeDB:
    def __init__(self, eventos=None, tipos=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])


def test_gerar_planilha_modelo_returns_excel(monkeypatch):
    ev_id = ObjectId()
    evento = {'_id': ev_id, 'nome': 'Test Event', 'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF']}
    tipo = {'_id': 't1', 'evento_id': str(ev_id), 'numero': 1, 'descricao': 'VIP'}
    fake_db = FakeDB(eventos=[evento], tipos=[tipo])

    monkeypatch.setattr(admin, 'get_database', lambda: fake_db)

    resp = asyncio.run(admin.gerar_planilha_modelo(str(ev_id)))
    assert resp.media_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    async def read_all(response):
        data = b''
        async for chunk in response.body_iterator:
            data += chunk
        return data

    content = asyncio.run(read_all(resp))
    assert len(content) > 0
    # content should start with PK.. because xlsx is a zip
    assert content[:2] == b'PK'
