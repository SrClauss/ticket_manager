import asyncio
from types import SimpleNamespace
from bson import ObjectId

from app.models.tipo_ingresso import TipoIngressoCreate
from app.routers import admin as admin_router


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
        # Support sort to return max(numero)
        if sort:
            key = sort[0][0]
            filtered = [d for d in self.docs if (not query) or all(
                (k not in query) or self._match_field(d.get(k), v) for k, v in query.items()
            )]
            if not filtered:
                return None
            return max(filtered, key=lambda d: d.get(key) or 0)

        if not query:
            return self.docs[0] if self.docs else None

        for d in self.docs:
            match = True
            for k, v in query.items():
                if k not in d:
                    match = False
                    break
                if hasattr(v, 'binary') or v.__class__.__name__ == 'ObjectId':
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

    async def update_many(self, filter_query, update):
        matched = 0
        for d in self.docs:
            ok = True
            for k, v in filter_query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                if '$set' in update:
                    for kk, vv in update['$set'].items():
                        d[kk] = vv
                matched += 1
        return SimpleNamespace(matched_count=matched)

    async def insert_one(self, doc):
        new = dict(doc)
        new_id = str(len(self.docs) + 1)
        new['_id'] = new_id
        self.docs.append(new)
        return SimpleNamespace(inserted_id=new_id)

    def _match_field(self, a, b):
        if hasattr(b, 'binary') or b.__class__.__name__ == 'ObjectId':
            return str(a) == str(b)
        return a == b


class FakeDB:
    def __init__(self, eventos=None, tipos=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        # unused but present
        self.participantes = FakeCollection([])
        self.ingressos_emitidos = FakeCollection([])
        self.ilhas = FakeCollection([])
        self.lead_interacoes = FakeCollection([])
        self.administradores = FakeCollection([])


def test_first_tipo_becomes_padrao(monkeypatch):
    event_id = ObjectId()
    fake_db = FakeDB(eventos=[{'_id': event_id}], tipos=[])
    monkeypatch.setattr(admin_router, 'get_database', lambda: fake_db)

    tipo = TipoIngressoCreate(descricao='Primeiro', evento_id=str(event_id))
    created = asyncio.run(admin_router.create_tipo_ingresso(tipo))

    assert created.numero == 1
    assert created.padrao is True


def test_sequential_numero_and_unset_previous_padrao(monkeypatch):
    event_id = ObjectId()
    # existing tipo with numero 1 and padrao True
    existing = {'_id': '1', 'evento_id': str(event_id), 'numero': 1, 'padrao': True}
    fake_db = FakeDB(eventos=[{'_id': event_id}], tipos=[existing])
    monkeypatch.setattr(admin_router, 'get_database', lambda: fake_db)

    tipo = TipoIngressoCreate(descricao='Segundo', evento_id=str(event_id), padrao=True)
    created = asyncio.run(admin_router.create_tipo_ingresso(tipo))

    assert created.numero == 2
    assert created.padrao is True
    # previous should have been unset
    assert fake_db.tipos_ingresso.docs[0]['padrao'] is False
