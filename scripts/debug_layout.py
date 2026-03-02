from fastapi.testclient import TestClient
from app.main import app
import app.routers.admin_web as admin_web
from bson import ObjectId
import datetime

def make_fake_event():
    ev_id = ObjectId('69724fe534104102673aa673')
    evento = {
        '_id': ev_id,
        'nome': 'Test Evento',
        'nome_normalizado': 'testslug',
        'data_evento': datetime.datetime.now(),
        'token_bilheteria': 'biltoken123',
        'token_portaria': 'porttoken456',
        'campos_obrigatorios_planilha': ['Nome','Email','CPF'],
        'aceita_inscricoes': True
    }
    ilhas = [{'_id': 'ilha1', 'evento_id': str(ev_id), 'nome_setor': 'Setor A', 'capacidade_maxima': 100}]
    tipos = [{'_id':'tipo1','evento_id':str(ev_id),'descricao':'VIP','numero':1,'permissoes':[],'valor':100.0}]
    return evento, ilhas, tipos

evento, ilhas, tipos = make_fake_event()

class FakeCol:
    def __init__(self, docs): self.docs = docs
    async def find_one(self, q=None): return self.docs[0]
    def count_documents(self, q): return len(self.docs)

fake_db = type('DB', (object,), {
    'eventos': FakeCol([evento]),
    'ilhas': FakeCol(ilhas),
    'tipos_ingresso': FakeCol(tipos),
    'planilha_importacoes': FakeCol([])
})

admin_web.check_admin_session = lambda req: None
admin_web.get_database = lambda: fake_db

client = TestClient(app)
resp = client.get(f"/admin/eventos/{str(evento['_id'])}")
print('status', resp.status_code)
print(resp.text)
