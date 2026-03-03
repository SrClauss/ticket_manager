"""
Testes abrangentes para os endpoints administrativos.
Cobre criação, leitura, atualização e exclusão de eventos, ilhas e tipos de ingresso.
"""
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.routers import admin
from tests.conftest import FakeDB


class TestEventosAdmin:
    """Testes para endpoints de eventos."""
    
    @pytest.mark.asyncio
    async def test_list_eventos_empty(self, fake_db, mock_get_database):
        """Testa listagem de eventos quando não há eventos."""
        result = await admin.list_eventos()
        assert result == []
    
    @pytest.mark.asyncio
    async def test_list_eventos_with_data(self, fake_db, mock_get_database, sample_evento):
        """Testa listagem de eventos com dados."""
        fake_db.eventos.docs.append(sample_evento)
        
        result = await admin.list_eventos()
        assert len(result) == 1
        assert result[0].nome == "Tech Conference 2024"
    
    @pytest.mark.asyncio
    async def test_list_eventos_pagination(self, fake_db, mock_get_database):
        """Testa paginação na listagem de eventos."""
        # Adiciona múltiplos eventos
        for i in range(15):
            fake_db.eventos.docs.append({
                "_id": ObjectId(),
                "nome": f"Evento {i}",
                "descricao": f"Descrição {i}",
                "data_evento": datetime.now(timezone.utc),
                "data_criacao": datetime.now(timezone.utc),
                "token_bilheteria": f"token_bil_{i}",
                "token_portaria": f"token_port_{i}",
                "layout_ingresso": {"canvas": {}, "elements": []}
            })
        
        result = await admin.list_eventos(skip=5, limit=5)
        assert len(result) == 5
    
    @pytest.mark.asyncio
    async def test_get_evento_success(self, fake_db, mock_get_database, sample_evento):
        """Testa busca de evento por ID."""
        fake_db.eventos.docs.append(sample_evento)
        
        result = await admin.get_evento(str(sample_evento["_id"]))
        assert result.nome == "Tech Conference 2024"
        assert result.descricao == "Conferência anual de tecnologia"
    
    @pytest.mark.asyncio
    async def test_get_evento_not_found(self, fake_db, mock_get_database):
        """Testa busca de evento inexistente."""
        with pytest.raises(HTTPException) as exc_info:
            await admin.get_evento(str(ObjectId()))
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_evento_invalid_id(self, fake_db, mock_get_database):
        """Testa busca com ID inválido."""
        with pytest.raises(HTTPException) as exc_info:
            await admin.get_evento("invalid_id")
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_create_evento_success(self, fake_db, mock_get_database):
        """Testa criação de novo evento."""
        from app.models.evento import EventoCreate
        
        evento_data = EventoCreate(
            nome="Novo Evento",
            descricao="Descrição do novo evento",
            data_evento=datetime(2024, 12, 25, 18, 0, 0, tzinfo=timezone.utc)
        )
        
        result = await admin.create_evento(evento_data)
        
        assert result.nome == "Novo Evento"
        assert result.token_bilheteria is not None
        assert result.token_portaria is not None
        assert result.nome_normalizado == "novo-evento"
        assert len(fake_db.eventos.docs) == 1
    
    @pytest.mark.asyncio
    async def test_update_evento_success(self, fake_db, mock_get_database, sample_evento):
        """Testa atualização de evento."""
        from app.models.evento import EventoUpdate
        
        fake_db.eventos.docs.append(sample_evento)
        
        update_data = EventoUpdate(
            nome="Evento Atualizado",
            descricao="Nova descrição"
        )
        
        result = await admin.update_evento(str(sample_evento["_id"]), update_data)
        
        assert result.nome == "Evento Atualizado"
        assert result.descricao == "Nova descrição"
    
    @pytest.mark.asyncio
    async def test_update_evento_not_found(self, fake_db, mock_get_database):
        """Testa atualização de evento inexistente."""
        from app.models.evento import EventoUpdate
        
        update_data = EventoUpdate(nome="Evento Atualizado")
        
        with pytest.raises(HTTPException) as exc_info:
            await admin.update_evento(str(ObjectId()), update_data)
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_evento_success(self, fake_db, mock_get_database, sample_evento):
        """Testa exclusão de evento."""
        fake_db.eventos.docs.append(sample_evento)
        
        result = await admin.delete_evento(str(sample_evento["_id"]))
        
        assert result["message"] == "Evento removido com sucesso"
        assert len(fake_db.eventos.docs) == 0
    
    @pytest.mark.asyncio
    async def test_delete_evento_not_found(self, fake_db, mock_get_database):
        """Testa exclusão de evento inexistente."""
        with pytest.raises(HTTPException) as exc_info:
            await admin.delete_evento(str(ObjectId()))
        assert exc_info.value.status_code == 404


class TestIlhasAdmin:
    """Testes para endpoints de ilhas/setores."""
    
    @pytest.mark.asyncio
    async def test_list_ilhas_by_evento(self, fake_db, mock_get_database, sample_evento, sample_ilha):
        """Testa listagem de ilhas por evento."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        
        result = await admin.list_ilhas(str(sample_evento["_id"]))
        
        assert len(result) == 1
        assert result[0].nome_setor == "VIP"
    
    @pytest.mark.asyncio
    async def test_create_ilha_success(self, fake_db, mock_get_database, sample_evento):
        """Testa criação de ilha."""
        from app.models.ilha import IlhaCreate
        
        fake_db.eventos.docs.append(sample_evento)
        
        ilha_data = IlhaCreate(
            evento_id=str(sample_evento["_id"]),
            nome_setor="Pista",
            capacidade_maxima=500
        )
        
        result = await admin.create_ilha(ilha_data)
        
        assert result.nome_setor == "Pista"
        assert result.capacidade_maxima == 500
        assert len(fake_db.ilhas.docs) == 1
    
    @pytest.mark.asyncio
    async def test_update_ilha_success(self, fake_db, mock_get_database, sample_ilha):
        """Testa atualização de ilha."""
        from app.models.ilha import IlhaUpdate
        
        fake_db.ilhas.docs.append(sample_ilha)
        
        update_data = IlhaUpdate(
            nome_setor="VIP Premium",
            capacidade_maxima=80
        )
        
        result = await admin.update_ilha(str(sample_ilha["_id"]), update_data)
        
        assert result.nome_setor == "VIP Premium"
        assert result.capacidade_maxima == 80
    
    @pytest.mark.asyncio
    async def test_delete_ilha_success(self, fake_db, mock_get_database, sample_ilha):
        """Testa exclusão de ilha."""
        fake_db.ilhas.docs.append(sample_ilha)
        
        result = await admin.delete_ilha(str(sample_ilha["_id"]))
        
        assert result["message"] == "Ilha removida com sucesso"
        assert len(fake_db.ilhas.docs) == 0


class TestTiposIngressoAdmin:
    """Testes para endpoints de tipos de ingresso."""
    
    @pytest.mark.asyncio
    async def test_list_tipos_by_evento(self, fake_db, mock_get_database, sample_evento, sample_tipo_ingresso):
        """Testa listagem de tipos de ingresso por evento."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        
        result = await admin.list_tipos_ingresso(str(sample_evento["_id"]))
        
        assert len(result) == 1
        assert result[0].descricao == "VIP All Access"
    
    @pytest.mark.asyncio
    async def test_create_tipo_ingresso_success(self, fake_db, mock_get_database, sample_evento, sample_ilha):
        """Testa criação de tipo de ingresso."""
        from app.models.tipo_ingresso import TipoIngressoCreate
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        
        tipo_data = TipoIngressoCreate(
            evento_id=str(sample_evento["_id"]),
            descricao="Pista",
            valor=50.0,
            permissoes=[str(sample_ilha["_id"])]
        )
        
        result = await admin.create_tipo_ingresso(tipo_data)
        
        assert result.descricao == "Pista"
        assert result.valor == 50.0
        assert len(fake_db.tipos_ingresso.docs) == 1
    
    @pytest.mark.asyncio
    async def test_update_tipo_ingresso_success(self, fake_db, mock_get_database, sample_tipo_ingresso):
        """Testa atualização de tipo de ingresso."""
        from app.models.tipo_ingresso import TipoIngressoUpdate
        
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        
        update_data = TipoIngressoUpdate(
            descricao="VIP Ultimate",
            valor=200.0
        )
        
        result = await admin.update_tipo_ingresso(str(sample_tipo_ingresso["_id"]), update_data)
        
        assert result.descricao == "VIP Ultimate"
        assert result.valor == 200.0
    
    @pytest.mark.asyncio
    async def test_delete_tipo_ingresso_success(self, fake_db, mock_get_database, sample_tipo_ingresso):
        """Testa exclusão de tipo de ingresso."""
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        
        result = await admin.delete_tipo_ingresso(str(sample_tipo_ingresso["_id"]))
        
        assert result["message"] == "Tipo de ingresso removido com sucesso"
        assert len(fake_db.tipos_ingresso.docs) == 0
    
    @pytest.mark.asyncio
    async def test_create_tipo_ingresso_with_invalid_permissoes(self, fake_db, mock_get_database, sample_evento):
        """Testa criação de tipo de ingresso com permissões inválidas."""
        from app.models.tipo_ingresso import TipoIngressoCreate
        
        fake_db.eventos.docs.append(sample_evento)
        
        tipo_data = TipoIngressoCreate(
            evento_id=str(sample_evento["_id"]),
            descricao="Teste",
            valor=100.0,
            permissoes=[str(ObjectId())]  # Ilha inexistente
        )
        
        # Deve criar mesmo com ilha inexistente (validação seria em camada superior)
        result = await admin.create_tipo_ingresso(tipo_data)
        assert result.descricao == "Teste"


class TestRelatoriosAdmin:
    """Testes para endpoints de relatórios."""
    
    @pytest.mark.asyncio
    async def test_relatorio_vendas_empty(self, fake_db, mock_get_database, sample_evento):
        """Testa relatório de vendas sem dados."""
        fake_db.eventos.docs.append(sample_evento)
        
        result = await admin.relatorio_vendas(str(sample_evento["_id"]))
        
        assert result["evento_id"] == str(sample_evento["_id"])
        assert result["total_ingressos"] == 0
        assert result["tipos"] == []
    
    @pytest.mark.asyncio
    async def test_relatorio_vendas_with_data(self, fake_db, mock_get_database, 
                                               sample_evento, sample_tipo_ingresso, sample_ingresso):
        """Testa relatório de vendas com dados."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        result = await admin.relatorio_vendas(str(sample_evento["_id"]))
        
        assert result["total_ingressos"] == 1
        assert len(result["tipos"]) == 1
        assert result["tipos"][0]["tipo"] == "VIP All Access"
        assert result["tipos"][0]["quantidade"] == 1
