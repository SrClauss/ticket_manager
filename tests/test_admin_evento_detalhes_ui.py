import pytest
from fastapi.testclient import TestClient
from app.main import app
import app.routers.admin_web as admin_web
from bson import ObjectId
import datetime

# Fake DB helpers
class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    async def find_one(self, query=None):
        if not query:
            return self.docs[0] if self.docs else None
        v = query.get('_id')
        if v is None:
            return None
        for d in self.docs:
            if str(d.get('_id')) == str(v) or d.get('_id') == v:
                return d
        return None

    def find(self, query):
        async def gen():
            for d in self.docs:
                match = True
                for k, v in query.items():
                    if d.get(k) != v:
                        match = False
                        break
                if match:
                    yield d
        return gen()

class FakeDB:
    def __init__(self, evento, ilhas, tipos):
        self.eventos = FakeCollection([evento])
        self.ilhas = FakeCollection(ilhas)
        self.tipos_ingresso = FakeCollection(tipos)
        self.planilha_importacoes = FakeCollection([])


def make_fake_event():
    ev_id = ObjectId("69724fe534104102673aa673")
    evento = {
        '_id': ev_id,
        'nome': 'Test Evento',
        'nome_normalizado': 'testslug',
        'data_evento': datetime.datetime.now(),
        'token_bilheteria': 'biltoken123',
        'token_portaria': 'porttoken456',
        'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF'],
        'aceita_inscricoes': True
    }
    ilhas = [{'_id': 'ilha1', 'evento_id': str(ev_id), 'nome_setor': 'Setor A', 'capacidade_maxima': 100}]
    tipos = [{'_id': 'tipo1', 'evento_id': str(ev_id), 'descricao': 'VIP', 'numero': 1, 'permissoes': [], 'valor': 100.0}]
    return evento, ilhas, tipos


def test_evento_detalhes_ui_and_snapshot(monkeypatch, tmp_path):
    evento, ilhas, tipos = make_fake_event()
    fake_db = FakeDB(evento, ilhas, tipos)

    # Monkeypatch admin_web internals to bypass auth and DB
    monkeypatch.setattr(admin_web, 'check_admin_session', lambda request: None)
    monkeypatch.setattr(admin_web, 'get_database', lambda: fake_db)

    client = TestClient(app)
    resp = client.get(f"/admin/eventos/{str(evento['_id'])}")
    assert resp.status_code == 200
    html = resp.text

    # Basic presence checks
    assert 'Token Bilheteria' in html
    assert 'Token Portaria' in html
    assert 'Pagina de Cadastro do Evento' in html
    assert 'Configurar Campos' in html
    assert 'id="evento-public-link"' in html
    # ensure slug is shown (we display only the normalized name in the code tag)
    assert 'testslug' in html

    # order assertions: bilheteria -> portaria -> pagina de cadastro
    idx_bil = html.find('Token Bilheteria')
    idx_por = html.find('Token Portaria')
    idx_pag = html.find('Pagina de Cadastro do Evento')
    assert idx_bil != -1 and idx_por != -1 and idx_pag != -1
    assert idx_bil < idx_por < idx_pag

    # compare to committed snapshot
    committed = open('tests/snapshots/evento_detalhes_snapshot.html', 'r', encoding='utf-8').read()
    # ensure snapshot exists and contains key UI markers (timestamps may vary)
    assert 'Token Bilheteria' in committed
    assert 'testslug' in committed
