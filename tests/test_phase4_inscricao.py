import asyncio
import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.participante import ParticipanteCreate
from app.routers import inscricao


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
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

    async def insert_one(self, doc):
        new = dict(doc)
        new_id = str(len(self.docs) + 1)
        new['_id'] = new_id
        self.docs.append(new)
        return type('R', (), {'inserted_id': new_id})


class FakeDB:
    def __init__(self, eventos=None, tipos=None, participantes=None, ingressos=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        self.participantes = FakeCollection(participantes or [])
        self.ingressos_emitidos = FakeCollection(ingressos or [])


def make_event():
    ev_id = ObjectId()
    return {
        '_id': ev_id,
        'nome': 'Show Do Gustavo Lima Limeira 2025',
        'nome_normalizado': 'showgustavolimalimeira2025',
        'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF'],
        'aceita_inscricoes': True
    }


def test_get_inscricao_form(monkeypatch):
    event = make_event()
    fake_db = FakeDB(eventos=[event])
    monkeypatch.setattr(inscricao, 'get_database', lambda: fake_db)

    res = asyncio.run(inscricao.get_inscricao_form(event['nome_normalizado']))
    assert res['nome'] == event['nome']
    assert 'CPF' in res['campos_obrigatorios_planilha']


def test_post_inscricao_creates_participant_and_ingresso(monkeypatch):
    event = make_event()
    tipo = {'_id': 't1', 'evento_id': str(event['_id']), 'padrao': True, 'numero': 1}
    fake_db = FakeDB(eventos=[event], tipos=[tipo])
    monkeypatch.setattr(inscricao, 'get_database', lambda: fake_db)
    monkeypatch.setattr(inscricao, 'generate_qrcode_hash', lambda: 'fixedqrcode')

    participante = ParticipanteCreate(nome='Carlos', email='carlos@example.com', cpf='529.982.247-25')
    res = asyncio.run(inscricao.post_inscricao(event['nome_normalizado'], participante))

    assert res['message'] == 'Inscrição realizada com sucesso'
    ingresso = res['ingresso']
    assert ingresso.qrcode_hash == 'fixedqrcode'
    # participant and ingresso inserted
    assert len(fake_db.participantes.docs) == 1
    assert len(fake_db.ingressos_emitidos.docs) == 1


def test_post_inscricao_duplicate_cpf_conflict(monkeypatch):
    event = make_event()
    # existing participant with normalized cpf
    existing_part = {'_id': 'p1', 'cpf': '52998224725'}
    # existing ingresso linking them to the event
    existing_ing = {'_id': 'i1', 'evento_id': str(event['_id']), 'participante_id': 'p1'}

    fake_db = FakeDB(eventos=[event], participantes=[existing_part], ingressos=[existing_ing])
    monkeypatch.setattr(inscricao, 'get_database', lambda: fake_db)

    participante = ParticipanteCreate(nome='Carlos', email='carlos@example.com', cpf='529.982.247-25')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(inscricao.post_inscricao(event['nome_normalizado'], participante))
    assert exc.value.status_code == 409
