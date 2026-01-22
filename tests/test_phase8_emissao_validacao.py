import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routers import bilheteria


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
        query = query or {}
        for doc in self.docs:
            if self._match(doc, query):
                return doc
        return None

    async def insert_one(self, doc):
        new_doc = dict(doc)
        if "_id" not in new_doc:
            new_doc["_id"] = str(len(self.docs) + 1)
        self.docs.append(new_doc)
        return SimpleNamespace(inserted_id=new_doc["_id"])

    async def update_one(self, query, update):
        # minimal implementation to satisfy interface if needed
        for doc in self.docs:
            if self._match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    def _match(self, doc, query):
        for key, value in query.items():
            if key == "$or":
                if not any(self._match(doc, sub) for sub in value):
                    return False
                continue
            doc_value = doc.get(key)
            if isinstance(value, dict) and "$ne" in value:
                if self._equals(doc_value, value["$ne"]):
                    return False
                continue
            if not self._equals(doc_value, value):
                return False
        return True

    def _equals(self, left, right):
        if isinstance(left, ObjectId):
            left = str(left)
        if isinstance(right, ObjectId):
            right = str(right)
        return left == right


class FakeDB:
    def __init__(self, eventos=None, tipos=None, participantes=None, ingressos=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        self.participantes = FakeCollection(participantes or [])
        self.ingressos_emitidos = FakeCollection(ingressos or [])


def _make_event(event_id):
    return {
        "_id": event_id,
        "nome": "Evento Teste",
        "layout_ingresso": {"canvas": {}, "elements": []},
        "data_evento": datetime.now(timezone.utc)
    }


def _make_tipo(tipo_id, event_id):
    return {
        "_id": tipo_id,
        "evento_id": str(event_id),
        "descricao": "VIP",
        "layout_ingresso": {"canvas": {}, "elements": []}
    }


def _make_participante(part_id, cpf):
    return {
        "_id": part_id,
        "nome": "Participante Teste",
        "cpf": cpf,
        "email": "teste@example.com"
    }


def test_emitir_ingresso_bloqueia_cpf_duplicado(monkeypatch):
    event_id = ObjectId()
    tipo_id = ObjectId()
    participante_id = ObjectId()

    fake_db = FakeDB(
        eventos=[_make_event(event_id)],
        tipos=[_make_tipo(tipo_id, event_id)],
        participantes=[_make_participante(participante_id, "52998224725")],
        ingressos=[{
            "_id": "ing1",
            "evento_id": str(event_id),
            "participante_id": str(participante_id),
            "participante_cpf": "52998224725"
        }]
    )

    monkeypatch.setattr(bilheteria, "get_database", lambda: fake_db)

    emissao = bilheteria.EmissaoIngressoRequest(
        tipo_ingresso_id=str(tipo_id),
        participante_id=str(participante_id)
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(bilheteria.emitir_ingresso(emissao, evento_id=str(event_id)))

    assert exc.value.status_code == 409
    assert "CPF" in exc.value.detail


def test_emitir_ingresso_sucesso_salva_cpf(monkeypatch):
    event_id = ObjectId()
    tipo_id = ObjectId()
    participante_id = ObjectId()

    fake_db = FakeDB(
        eventos=[_make_event(event_id)],
        tipos=[_make_tipo(tipo_id, event_id)],
        participantes=[_make_participante(participante_id, "529.982.247-25")],
        ingressos=[]
    )

    monkeypatch.setattr(bilheteria, "get_database", lambda: fake_db)
    monkeypatch.setattr(bilheteria, "generate_qrcode_hash", lambda: "qr-fixed")

    emissao = bilheteria.EmissaoIngressoRequest(
        tipo_ingresso_id=str(tipo_id),
        participante_id=str(participante_id)
    )

    resposta = asyncio.run(bilheteria.emitir_ingresso(emissao, evento_id=str(event_id)))

    assert resposta.ingresso.qrcode_hash == "qr-fixed"
    assert fake_db.ingressos_emitidos.docs[-1]["participante_cpf"] == "52998224725"
