import asyncio
from app.utils.planilha import process_planilha
from app.utils.validations import normalize_event_name
from bson import ObjectId


def make_csv():
    header = 'Nome,Email,CPF,Tipo Ingresso\n'
    # valid row and invalid cpf row
    rows = (
        'Joao Silva,joao@example.com,529.982.247-25,1\n'
        'Maria Invalid,maria@ex,111.111.111-11,1\n'
    )
    return (header + rows).encode('utf-8')


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
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
        self.planilha_importacoes = FakeCollection([])


def test_process_planilha_csv():
    ev_object_id = ObjectId()
    ev_id = str(ev_object_id)
    evento = {'_id': ev_object_id, 'nome': 'Evt', 'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF']}
    tipo = {'_id': 't1', 'evento_id': ev_id, 'padrao': True, 'numero': 1}
    fake_db = FakeDB(eventos=[evento], tipos=[tipo])

    csv_bytes = make_csv()
    report = asyncio.run(process_planilha(csv_bytes, 'test.csv', ev_id, fake_db))

    print('REPORT:', report)
    assert report['total'] == 2
    assert report['created_participants'] == 1
    assert report['created_ingressos'] == 1
    assert len(report['errors']) == 1
    assert 'Email inválido' in report['errors'][0]['errors'] or 'CPF inválido' in report['errors'][0]['errors']
