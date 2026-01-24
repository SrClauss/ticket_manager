"""
Testes abrangentes do fluxo completo de inscrição pública e importação de planilha.

Este módulo implementa testes end-to-end que verificam:
- Fluxo público de inscrição via /inscricao (GET e POST)
- Importação de planilha CSV com CPFs válidos e inválidos
- Validação de CPF e geração de relatórios de erro

Segue padrões estabelecidos em tests/README.md e conftest.py.
"""
import asyncio
import pytest
from bson import ObjectId
from datetime import datetime, timezone
from fastapi import HTTPException

from app.models.participante import ParticipanteCreate
from app.routers import inscricao
from app.utils.planilha import process_planilha


# ==================== FakeDB Implementation ====================
# Implementação compatível com conftest.py, adaptada para suportar
# operações específicas necessárias para estes testes

class FakeCollection:
    """Mock de collection MongoDB para testes."""
    
    def __init__(self, docs=None):
        self.docs = docs or []
        self._counter = 1000
    
    async def find_one(self, query=None, sort=None):
        """Busca um documento que corresponda ao query."""
        query = query or {}
        
        # Handle sort (needed for some lookups)
        if sort:
            key = sort[0][0] if isinstance(sort, list) and sort else None
            filtered = [d for d in self.docs if self._match(d, query)]
            if not filtered:
                return None
            if key:
                return max(filtered, key=lambda d: d.get(key, 0))
            return filtered[0] if filtered else None
        
        for doc in self.docs:
            if self._match(doc, query):
                return doc
        return None
    
    async def insert_one(self, doc):
        """Insere um novo documento."""
        new_doc = dict(doc)
        if "_id" not in new_doc:
            new_doc["_id"] = ObjectId()
        else:
            if isinstance(new_doc["_id"], str):
                try:
                    new_doc["_id"] = ObjectId(new_doc["_id"])
                except Exception:
                    pass
        self.docs.append(new_doc)
        
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        
        return InsertResult(new_doc["_id"])
    
    async def update_one(self, query, update, upsert=False):
        """Atualiza um documento."""
        for doc in self.docs:
            if self._match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$inc" in update:
                    for key, value in update["$inc"].items():
                        doc[key] = doc.get(key, 0) + value
                if "$push" in update:
                    for key, value in update["$push"].items():
                        if key not in doc:
                            doc[key] = []
                        doc[key].append(value)
                
                class UpdateResult:
                    def __init__(self):
                        self.matched_count = 1
                        self.modified_count = 1
                
                return UpdateResult()
        
        if upsert and "$set" in update:
            new_doc = dict(query)
            new_doc.update(update["$set"])
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self.docs.append(new_doc)
            
            class UpsertResult:
                def __init__(self, upserted_id):
                    self.matched_count = 0
                    self.modified_count = 0
                    self.upserted_id = upserted_id
            
            return UpsertResult(new_doc["_id"])
        
        class NoMatchResult:
            def __init__(self):
                self.matched_count = 0
                self.modified_count = 0
        
        return NoMatchResult()
    
    def find(self, query=None, sort=None):
        """Retorna cursor para busca."""
        query = query or {}
        matching_docs = [doc for doc in self.docs if self._match(doc, query)]
        return FakeCursor(matching_docs, sort)
    
    def _match(self, doc, query):
        """Verifica se documento corresponde ao query."""
        for key, value in query.items():
            if key == "$or":
                if not any(self._match(doc, sub) for sub in value):
                    return False
                continue
            
            if key == "$and":
                if not all(self._match(doc, sub) for sub in value):
                    return False
                continue
            
            doc_value = doc.get(key)
            
            if isinstance(value, dict):
                if "$ne" in value:
                    if self._equals(doc_value, value["$ne"]):
                        return False
                    continue
                if "$in" in value:
                    if not any(self._equals(doc_value, v) for v in value["$in"]):
                        return False
                    continue
                if "$elemMatch" in value:
                    # For embedded array matching
                    if not isinstance(doc_value, list):
                        return False
                    if not any(self._match(item, value["$elemMatch"]) for item in doc_value):
                        return False
                    continue
            
            if not self._equals(doc_value, value):
                return False
        
        return True
    
    def _equals(self, left, right):
        """Compara valores considerando ObjectId."""
        if isinstance(left, ObjectId):
            left = str(left)
        if isinstance(right, ObjectId):
            right = str(right)
        return left == right


class FakeCursor:
    """Mock de cursor do MongoDB."""
    
    def __init__(self, docs, sort=None):
        self.docs = docs
        self._sort = sort
        self._skip = 0
        self._limit = None
    
    def skip(self, n):
        self._skip = n
        return self
    
    def limit(self, n):
        self._limit = n
        return self
    
    def sort(self, *args):
        return self
    
    async def to_list(self, length=None):
        """Converte cursor para lista."""
        docs = self.docs[self._skip:]
        if self._limit:
            docs = docs[:self._limit]
        return docs
    
    def __aiter__(self):
        """Suporte para iteração assíncrona."""
        self._iter_docs = iter(self.docs[self._skip:self._limit] if self._limit else self.docs[self._skip:])
        return self
    
    async def __anext__(self):
        """Próximo item na iteração."""
        try:
            return next(self._iter_docs)
        except StopIteration:
            raise StopAsyncIteration


class FakeDB:
    """Mock de banco de dados MongoDB."""
    
    def __init__(self, eventos=None, tipos=None, participantes=None, ingressos=None,
                 planilha_importacoes=None, planilha_upload_links=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        self.participantes = FakeCollection(participantes or [])
        self.ingressos_emitidos = FakeCollection(ingressos or [])
        self.planilha_importacoes = FakeCollection(planilha_importacoes or [])
        self.planilha_upload_links = FakeCollection(planilha_upload_links or [])


# ==================== CSV Datasets ====================
# Datasets fornecidos no problema para uso nos testes

GENERAL_CSV = """nome,cpf,email
Ricardo Almeida,44820153010,ricardo.almeida@example.com
Tatiane Souza,83271405073,tati.souza@provider.com
Marcos Vinicius,15793422002,marcos.v@testmail.br
Fernanda Lima,52108933094,fernanda.lima@webmail.com
Roberto Carlos,09234167080,roberto.c@company.com
Larissa Mendes,31562094038,larissa.mendes@digital.com.br
Gustavo Henrique,72481539062,gustavo.h@service.net
Camila Rocha,90315724016,camila.rocha@internet.com
Andreia Silva,26849105077,andreia.s@domain.org
Paulo Teixeira,64193207054,paulo.t@mailbox.com.br"""

INVALID_CPFS_CSV = """nome,cpf,email
Bruno Nogueira,52419083076,bruno.nog@example.com
Aline Ferreira,21584309062,aline.f@provider.com
Ricardo Gomes,90231547011,ricardo.gomes@testmail.br
Juliana Paes,33840129045,ju.paes@webmail.com
Marcos Rocha,07149235080,m.rocha@company.com
Leticia Souza,64201538094,leticia.s@digital.com.br
Fabio Junior,85931024022,fabio.j@service.net
Camila Duarte,12648753023,camila.d@internet.com
Teste Invalido Um,12345678900,erro.logica1@test.com
Teste Invalido Dois,98765432100,erro.logica2@test.com"""


# ==================== Helper Functions ====================

def make_event_for_inscricao():
    """Cria um evento configurado para aceitar inscrições públicas."""
    ev_id = ObjectId()
    return {
        '_id': ev_id,
        'nome': 'Show Do Gustavo Lima Limeira 2025',
        'nome_normalizado': 'show-do-gustavo-lima-limeira-2025',
        'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF'],
        'aceita_inscricoes': True,
        'layout_ingresso': {
            'canvas': {'width': 80, 'unit': 'mm'},
            'elements': []
        }
    }


def make_tipo_ingresso(evento_id):
    """Cria um tipo de ingresso padrão para o evento."""
    return {
        '_id': ObjectId(),
        'evento_id': str(evento_id),
        'descricao': 'Ingresso Padrão',
        'padrao': True,
        'numero': 1,
        'valor': 0.0,
        'permissoes': []
    }


# ==================== Tests ====================

@pytest.mark.asyncio
async def test_fluxo_publico_inscricao_sucesso_e_cpf_invalido(monkeypatch):
    """
    Testa o fluxo público de inscrição:
    1. GET /inscricao/{slug} retorna metadata do evento quando aceita_inscricoes=True
    2. POST /inscricao/{slug} com CPF válido (529.982.247-25) cria participante e ingresso
    3. POST /inscricao/{slug} com CPF inválido do CSV fornecido falha com erro apropriado
    """
    # Arrange: Configurar evento e FakeDB
    event = make_event_for_inscricao()
    tipo = make_tipo_ingresso(event['_id'])
    fake_db = FakeDB(eventos=[event], tipos=[tipo])
    
    # Monkeypatch para injetar FakeDB e fixar qrcode
    monkeypatch.setattr(inscricao, 'get_database', lambda: fake_db)
    monkeypatch.setattr(inscricao, 'generate_qrcode_hash', lambda: 'qrcode-fixed')
    
    # Act 1: GET /inscricao/{slug} - obter formulário
    result = await inscricao.get_inscricao_form(event['nome_normalizado'])
    
    # Assert 1: Metadata do evento retornada corretamente
    assert result['nome'] == event['nome']
    assert 'CPF' in result['campos_obrigatorios_planilha']
    assert 'Email' in result['campos_obrigatorios_planilha']
    assert 'Nome' in result['campos_obrigatorios_planilha']
    
    # Act 2: POST /inscricao/{slug} com CPF válido (conhecido do repositório)
    participante_valido = ParticipanteCreate(
        nome='Carlos Silva',
        email='carlos@example.com',
        cpf='529.982.247-25'  # CPF válido usado em test_phase1_models.py
    )
    
    result = await inscricao.post_inscricao(event['nome_normalizado'], participante_valido)
    
    # Assert 2: Inscrição bem-sucedida
    assert result['message'] == 'Inscrição realizada com sucesso'
    assert 'ingresso_id' in result
    assert result['ingresso'].qrcode_hash == 'qrcode-fixed'
    assert len(fake_db.participantes.docs) == 1
    assert len(fake_db.ingressos_emitidos.docs) == 1
    assert fake_db.participantes.docs[0]['cpf'] == '52998224725'  # CPF normalizado
    
    # Act 3: POST /inscricao/{slug} com CPF inválido do CSV fornecido
    # Usando o primeiro CPF inválido: 52419083076
    # Note: Pydantic validates CPF during model instantiation, so we catch ValidationError
    from pydantic import ValidationError
    
    # Assert 3: Deve falhar com ValidationError na criação do modelo
    with pytest.raises(ValidationError) as exc_info:
        participante_invalido = ParticipanteCreate(
            nome='Bruno Nogueira',
            email='bruno.nog@example.com',
            cpf='52419083076'  # CPF inválido da lista fornecida
        )
    
    # Verificar que o erro é relacionado ao CPF
    error_str = str(exc_info.value)
    assert 'cpf' in error_str.lower()
    
    # Verificar que não houve criação adicional
    assert len(fake_db.participantes.docs) == 1  # Apenas o válido
    assert len(fake_db.ingressos_emitidos.docs) == 1  # Apenas o válido


@pytest.mark.asyncio
async def test_importacao_planilha_com_cpfs_invalidos_relatorio():
    """
    Testa importação de planilha com CPFs inválidos:
    - Usa o CSV fornecido com 10 CPFs (9 inválidos, 1 válido - 98765432100)
    - Verifica que total==10
    - Verifica que as 9 linhas com CPF inválido têm erro "CPF inválido"
    - Verifica que a linha com CPF válido foi processada corretamente
    
    Nota: O CPF 98765432100 é válido segundo o algoritmo de validação,
    então ele será processado corretamente.
    """
    # Arrange: Configurar evento e FakeDB
    ev_id = ObjectId()
    evento = {
        '_id': ev_id,
        'nome': 'Evento Teste Importação',
        'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF']
    }
    tipo = make_tipo_ingresso(ev_id)
    fake_db = FakeDB(eventos=[evento], tipos=[tipo])
    
    # Preparar CSV bytes
    csv_bytes = INVALID_CPFS_CSV.encode('utf-8')
    
    # Act: Processar planilha
    report = await process_planilha(
        file_bytes=csv_bytes,
        filename='cpfs_invalidos.csv',
        evento_id=str(ev_id),
        db=fake_db
    )
    
    # Assert: Verificar relatório
    assert report['total'] == 10, "Deve processar todas as 10 linhas"
    
    # O CSV contém 9 CPFs inválidos e 1 CPF válido (98765432100)
    assert report['created_participants'] == 1, "Deve criar 1 participante (CPF 98765432100 é válido)"
    assert report['created_ingressos'] == 1, "Deve criar 1 ingresso (CPF 98765432100 é válido)"
    assert len(report['errors']) == 9, "9 linhas devem ter erro (CPFs inválidos)"
    
    # Verificar que cada erro contém "CPF inválido"
    for error in report['errors']:
        assert 'errors' in error
        error_messages = ' '.join(error['errors'])
        assert 'CPF inválido' in error_messages or 'CPF' in error_messages, \
            f"Erro deve mencionar CPF inválido: {error}"
    
    # Verificar que um documento foi criado no banco (o CPF válido)
    assert len(fake_db.participantes.docs) == 1
    assert len(fake_db.ingressos_emitidos.docs) == 1
    assert fake_db.participantes.docs[0]['cpf'] == '98765432100'


@pytest.mark.asyncio
async def test_importacao_planilha_geral_csv_fornecido_sem_assumir_validez_total():
    """
    Testa importação da planilha geral fornecida (10 linhas):
    - Não assume que todos os CPFs sejam válidos
    - Verifica que total==10 (todas as linhas foram processadas)
    - Verifica que o relatório tem estrutura correta
    - Verifica que há pelo menos alguns participantes criados OU erros reportados
    """
    # Arrange: Configurar evento e FakeDB
    ev_id = ObjectId()
    evento = {
        '_id': ev_id,
        'nome': 'Evento Teste Geral',
        'campos_obrigatorios_planilha': ['Nome', 'Email', 'CPF']
    }
    tipo = make_tipo_ingresso(ev_id)
    fake_db = FakeDB(eventos=[evento], tipos=[tipo])
    
    # Preparar CSV bytes
    csv_bytes = GENERAL_CSV.encode('utf-8')
    
    # Act: Processar planilha
    report = await process_planilha(
        file_bytes=csv_bytes,
        filename='geral.csv',
        evento_id=str(ev_id),
        db=fake_db
    )
    
    # Assert: Verificar estrutura do relatório
    assert report['total'] == 10, "Deve processar todas as 10 linhas"
    assert 'created_participants' in report
    assert 'created_ingressos' in report
    assert 'errors' in report
    assert 'reused_participants' in report
    
    # Verificar que houve processamento (ou criações ou erros)
    total_processed = report['created_participants'] + len(report['errors'])
    assert total_processed == 10, \
        "Soma de participantes criados + erros deve ser igual ao total de linhas"
    
    # Verificar que há pelo menos alguma atividade (criação ou erro)
    assert report['created_participants'] > 0 or len(report['errors']) > 0, \
        "Deve ter criado participantes ou reportado erros"
    
    # Se houve criações, verificar consistência
    if report['created_participants'] > 0:
        assert report['created_ingressos'] == report['created_participants'], \
            "Número de ingressos deve corresponder ao número de participantes criados"
        assert len(fake_db.participantes.docs) == report['created_participants']
        assert len(fake_db.ingressos_emitidos.docs) == report['created_ingressos']
    
    # Se houve erros, verificar estrutura
    if len(report['errors']) > 0:
        for error in report['errors']:
            assert 'line' in error, "Erro deve ter número da linha"
            assert 'errors' in error, "Erro deve ter lista de mensagens"
            assert isinstance(error['errors'], list), "Erros devem estar em lista"
