import pytest
from bson import ObjectId
from datetime import datetime, timezone

from app.routers import evento_web


class DummyRequest:
    def __init__(self):
        self.cookies = {}


@pytest.mark.asyncio
async def test_participante_form_shows_only_required_fields(monkeypatch):
    # evento config only has Nome, Email, CPF as required (base fields)
    evento = {
        "_id": ObjectId(),
        "nome": "Teste",
        "campos_obrigatorios_planilha": ["Nome", "Email", "CPF"],
    }

    async def fake_get(request):
        return evento, str(evento["_id"])

    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    req = DummyRequest()
    resp = await evento_web.evento_participante_novo_page(req)
    html = resp.body.decode()

    # always have base fields
    assert 'name="nome"' in html
    assert 'name="email"' in html
    assert 'name="cpf"' in html
    # optional fields should NOT appear
    assert 'name="telefone"' not in html
    assert 'name="empresa"' not in html
    assert 'name="nacionalidade"' not in html


@pytest.mark.asyncio
async def test_participante_form_includes_optional_if_configured(monkeypatch):
    evento = {
        "_id": ObjectId(),
        "nome": "Teste",
        "campos_obrigatorios_planilha": ["Nome", "Email", "CPF", "Telefone", "Empresa"],
    }

    async def fake_get(request):
        return evento, str(evento["_id"])

    monkeypatch.setattr(evento_web, "_get_evento_from_cookie", fake_get)

    req = DummyRequest()
    resp = await evento_web.evento_participante_novo_page(req)
    html = resp.body.decode()

    assert 'name="telefone"' in html
    assert 'name="empresa"' in html
    # outros campos ainda não aparecem
    assert 'name="nacionalidade"' not in html
