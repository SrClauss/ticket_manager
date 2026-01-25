"""
Configuração compartilhada para testes.
Define fixtures reutilizáveis em todos os testes.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace


@pytest.fixture(scope="session")
def event_loop():
    """Cria um event loop para testes assíncronos."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class FakeCollection:
    """Mock de collection do MongoDB para testes."""
    
    def __init__(self, docs=None):
        self.docs = docs or []
        self._counter = 1000
    
    async def find_one(self, query=None, sort=None):
        """Busca um documento que corresponda ao query."""
        query = query or {}
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
                new_doc["_id"] = ObjectId(new_doc["_id"])
        self.docs.append(new_doc)
        return SimpleNamespace(inserted_id=new_doc["_id"])
    
    async def update_one(self, query, update, upsert=False):
        """Atualiza um documento."""
        for doc in self.docs:
            if self._match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$inc" in update:
                    for key, value in update["$inc"].items():
                        doc[key] = doc.get(key, 0) + value
                return SimpleNamespace(matched_count=1, modified_count=1)
        
        if upsert and "$set" in update:
            new_doc = dict(query)
            new_doc.update(update["$set"])
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self.docs.append(new_doc)
            return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=new_doc["_id"])
        
        return SimpleNamespace(matched_count=0, modified_count=0)
    
    async def delete_one(self, query):
        """Remove um documento."""
        for i, doc in enumerate(self.docs):
            if self._match(doc, query):
                self.docs.pop(i)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)
    
    async def count_documents(self, query=None):
        """Conta documentos que correspondem ao query."""
        query = query or {}
        count = 0
        for doc in self.docs:
            if self._match(doc, query):
                count += 1
        return count
    
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
                if "$regex" in value:
                    import re
                    pattern = value["$regex"]
                    flags = value.get("$options", "")
                    regex_flags = 0
                    if "i" in flags:
                        regex_flags |= re.IGNORECASE
                    if not re.search(pattern, str(doc_value), regex_flags):
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
        # Implementação simplificada de sort
        return self
    
    async def to_list(self, length=None):
        """Converte cursor para lista."""
        docs = self.docs[self._skip:]
        if self._limit:
            docs = docs[:self._limit]
        return docs
    
    def __aiter__(self):
        """Suporte para iteração assíncrona."""
        if self._limit:
            self._iter_docs = iter(self.docs[self._skip:self._skip + self._limit])
        else:
            self._iter_docs = iter(self.docs[self._skip:])
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
                 ilhas=None, admins=None, leads=None, planilhas=None):
        self.eventos = FakeCollection(eventos or [])
        self.tipos_ingresso = FakeCollection(tipos or [])
        self.participantes = FakeCollection(participantes or [])
        self.ingressos_emitidos = FakeCollection(ingressos or [])
        self.ilhas = FakeCollection(ilhas or [])
        self.admins = FakeCollection(admins or [])
        self.lead_interacoes = FakeCollection(leads or [])
        self.planilhas_upload = FakeCollection(planilhas or [])


@pytest.fixture
def fake_db():
    """Fixture que fornece um banco de dados fake para testes."""
    return FakeDB()


@pytest.fixture
def sample_evento():
    """Fixture que fornece um evento de exemplo."""
    evento_id = ObjectId()
    return {
        "_id": evento_id,
        "nome": "Tech Conference 2024",
        "descricao": "Conferência anual de tecnologia",
        "data_evento": datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc),
        "data_criacao": datetime.now(timezone.utc),
        "token_bilheteria": "bilheteria_token_123",
        "token_portaria": "portaria_token_456",
        "logo_url": None,
        "layout_ingresso": {
            "canvas": {"width": 80, "unit": "mm"},
            "elements": []
        },
        "nome_normalizado": "tech-conference-2024"
    }


@pytest.fixture
def sample_ilha(sample_evento):
    """Fixture que fornece uma ilha de exemplo."""
    ilha_id = ObjectId()
    return {
        "_id": ilha_id,
        "evento_id": str(sample_evento["_id"]),
        "nome_setor": "VIP",
        "capacidade_maxima": 100
    }


@pytest.fixture
def sample_tipo_ingresso(sample_evento, sample_ilha):
    """Fixture que fornece um tipo de ingresso de exemplo."""
    tipo_id = ObjectId()
    return {
        "_id": tipo_id,
        "evento_id": str(sample_evento["_id"]),
        "descricao": "VIP All Access",
        "valor": 150.0,
        "permissoes": [str(sample_ilha["_id"])],
        "padrao": False
    }


@pytest.fixture
def sample_participante(sample_evento):
    """Fixture que fornece um participante de exemplo."""
    participante_id = ObjectId()
    return {
        "_id": participante_id,
        "nome": "João Silva",
        "email": "joao@example.com",
        "cpf": "52998224725",
        "telefone": "11999999999",
        "empresa": "Tech Corp",
        "cargo": "Desenvolvedor"
    }


@pytest.fixture
def sample_ingresso(sample_evento, sample_tipo_ingresso, sample_participante):
    """Fixture que fornece um ingresso de exemplo."""
    ingresso_id = ObjectId()
    return {
        "_id": ingresso_id,
        "evento_id": str(sample_evento["_id"]),
        "tipo_ingresso_id": str(sample_tipo_ingresso["_id"]),
        "participante_id": str(sample_participante["_id"]),
        "qrcode_hash": "qr_hash_abc123",
        "status": "Ativo",
        "data_emissao": datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_get_database(fake_db, monkeypatch):
    """Mock da função get_database."""
    def _get_database():
        return fake_db
    
    monkeypatch.setattr("app.config.database.get_database", _get_database)
    return fake_db


@pytest.fixture
def admin_token():
    """Fixture que fornece um token admin válido para testes."""
    return "Bearer valid_admin_token_123"


@pytest.fixture
def mock_verify_admin(monkeypatch):
    """Mock da verificação de admin."""
    async def _verify_admin(token: str = None):
        if token and "valid_admin_token" in token:
            return True
        raise Exception("Unauthorized")
    
    monkeypatch.setattr("app.config.auth.verify_admin_access", _verify_admin)


@pytest.fixture
def mock_verify_bilheteria(monkeypatch, sample_evento):
    """Mock da verificação de token de bilheteria."""
    async def _verify_bilheteria(token: str = None):
        if token and "bilheteria_token" in token:
            return str(sample_evento["_id"])
        raise Exception("Unauthorized")
    
    monkeypatch.setattr("app.config.auth.verify_token_bilheteria", _verify_bilheteria)


@pytest.fixture
def mock_verify_portaria(monkeypatch, sample_evento):
    """Mock da verificação de token de portaria."""
    async def _verify_portaria(token: str = None):
        if token and "portaria_token" in token:
            return str(sample_evento["_id"])
        raise Exception("Unauthorized")
    
    monkeypatch.setattr("app.config.auth.verify_token_portaria", _verify_portaria)
