"""
Testes abrangentes para os endpoints de bilheteria.
Cobre cadastro de participantes, busca, emissão e reimpressão de ingressos.
"""
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.routers import bilheteria
from tests.conftest import FakeDB


class TestParticipantesBilheteria:
    """Testes para endpoints de participantes."""
    
    @pytest.mark.asyncio
    async def test_create_participante_success(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa criação de novo participante."""
        from app.models.participante import ParticipanteCreate
        
        fake_db.eventos.docs.append(sample_evento)
        
        participante_data = ParticipanteCreate(
            nome="Maria Santos",
            email="maria@example.com",
            cpf="123.456.789-09",
            telefone="11988888888"
        )
        
        result = await bilheteria.create_participante(
            participante_data,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.nome == "Maria Santos"
        assert result.email == "maria@example.com"
        assert result.cpf == "12345678909"  # CPF normalizado
        assert len(fake_db.participantes.docs) == 1
    
    @pytest.mark.asyncio
    async def test_create_participante_invalid_cpf(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa criação de participante com CPF inválido."""
        from app.models.participante import ParticipanteCreate
        
        fake_db.eventos.docs.append(sample_evento)
        
        with pytest.raises(ValueError):
            participante_data = ParticipanteCreate(
                nome="Teste",
                email="teste@example.com",
                cpf="111.111.111-11",  # CPF inválido
                telefone="11999999999"
            )
    
    @pytest.mark.asyncio
    async def test_buscar_participantes_by_name(self, fake_db, mock_get_database, sample_evento, sample_participante, mock_verify_bilheteria):
        """Testa busca de participantes por nome."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.participantes.docs.append(sample_participante)
        
        result = await bilheteria.buscar_participantes(
            query="João",
            evento_id=str(sample_evento["_id"])
        )
        
        assert len(result) >= 1
        assert "João" in result[0].nome
    
    @pytest.mark.asyncio
    async def test_buscar_participantes_by_cpf(self, fake_db, mock_get_database, sample_evento, sample_participante, mock_verify_bilheteria):
        """Testa busca de participantes por CPF."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.participantes.docs.append(sample_participante)
        
        result = await bilheteria.buscar_participantes(
            query="529.982.247-25",
            evento_id=str(sample_evento["_id"])
        )
        
        assert len(result) >= 1
        assert result[0].cpf == "52998224725"
    
    @pytest.mark.asyncio
    async def test_buscar_participantes_by_email(self, fake_db, mock_get_database, sample_evento, sample_participante, mock_verify_bilheteria):
        """Testa busca de participantes por email."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.participantes.docs.append(sample_participante)
        
        result = await bilheteria.buscar_participantes(
            query="joao@example.com",
            evento_id=str(sample_evento["_id"])
        )
        
        assert len(result) >= 1
        assert result[0].email == "joao@example.com"
    
    @pytest.mark.asyncio
    async def test_buscar_participantes_empty_result(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa busca de participantes sem resultados."""
        fake_db.eventos.docs.append(sample_evento)
        
        result = await bilheteria.buscar_participantes(
            query="Inexistente",
            evento_id=str(sample_evento["_id"])
        )
        
        assert len(result) == 0


class TestListarParticipantesPaginado:
    """Testes para o endpoint de listagem paginada de participantes."""
    
    @pytest.mark.asyncio
    async def test_listar_participantes_default_pagination(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa listagem com paginação padrão."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 30 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(30):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf  # Usar mesmo CPF válido para todos
            }
            fake_db.participantes.docs.append(participante)
        
        result = await listar_participantes(
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.current_page == 1
        assert result.per_page == 20
        assert result.total_count == 30
        assert result.total_pages == 2
        assert len(result.participantes) == 20
    
    @pytest.mark.asyncio
    async def test_listar_participantes_custom_pagination(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa listagem com paginação customizada."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 50 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(50):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf
            }
            fake_db.participantes.docs.append(participante)
        
        # Página 2 com 10 itens por página
        result = await listar_participantes(
            page=2,
            per_page=10,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.current_page == 2
        assert result.per_page == 10
        assert result.total_count == 50
        assert result.total_pages == 5
        assert len(result.participantes) == 10
    
    @pytest.mark.asyncio
    async def test_listar_participantes_filter_by_name(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa listagem com filtro por nome."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona participantes com nomes diferentes e CPF válido
        base_cpf = "52998224725"
        participantes_data = [
            {"nome": "João Silva", "email": "joao@example.com", "cpf": base_cpf},
            {"nome": "Maria Santos", "email": "maria@example.com", "cpf": base_cpf},
            {"nome": "João Pedro", "email": "joaopedro@example.com", "cpf": base_cpf},
            {"nome": "Ana Costa", "email": "ana@example.com", "cpf": base_cpf},
            {"nome": "joão Carlos", "email": "joaocarlos@example.com", "cpf": base_cpf},
        ]
        
        for p_data in participantes_data:
            participante = {
                "_id": ObjectId(),
                **p_data
            }
            fake_db.participantes.docs.append(participante)
        
        # Busca por "joão" (case insensitive)
        result = await listar_participantes(
            nome="joão",
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.total_count == 3  # João Silva, João Pedro, joão Carlos
        assert len(result.participantes) == 3
        assert all("joão" in p.nome.lower() for p in result.participantes)
    
    @pytest.mark.asyncio
    async def test_listar_participantes_empty_filter(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa que filtro vazio retorna todos os participantes."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 5 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(5):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf
            }
            fake_db.participantes.docs.append(participante)
        
        # Filtro vazio ou apenas espaços deve retornar todos
        result = await listar_participantes(
            nome="",
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.total_count == 5
        assert len(result.participantes) == 5
    
    @pytest.mark.asyncio
    async def test_listar_participantes_no_results(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa listagem quando não há participantes."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        result = await listar_participantes(
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.total_count == 0
        assert result.total_pages == 1
        assert result.current_page == 1
        assert len(result.participantes) == 0
    
    @pytest.mark.asyncio
    async def test_listar_participantes_page_beyond_total(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa que página além do total é ajustada para última página."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 15 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(15):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf
            }
            fake_db.participantes.docs.append(participante)
        
        # Solicita página 10 (além do total)
        result = await listar_participantes(
            page=10,
            per_page=10,
            evento_id=str(sample_evento["_id"])
        )
        
        # Deve retornar a última página (2)
        assert result.current_page == 2
        assert result.total_pages == 2
        assert len(result.participantes) == 5  # Última página tem 5 itens
    
    @pytest.mark.asyncio
    async def test_listar_participantes_negative_page(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa que página negativa é ajustada para 1."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 5 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(5):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf
            }
            fake_db.participantes.docs.append(participante)
        
        result = await listar_participantes(
            page=-1,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.current_page == 1
    
    @pytest.mark.asyncio
    async def test_listar_participantes_per_page_exceeds_max(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa que per_page acima do máximo é limitado a 100."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 150 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(150):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf
            }
            fake_db.participantes.docs.append(participante)
        
        result = await listar_participantes(
            per_page=200,  # Acima do máximo de 100
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.per_page == 100
        assert len(result.participantes) == 100
    
    @pytest.mark.asyncio
    async def test_listar_participantes_per_page_below_min(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa que per_page abaixo do mínimo é ajustado para 1."""
        from app.routers.bilheteria import listar_participantes
        
        fake_db.eventos.docs.append(sample_evento)
        
        # Adiciona 25 participantes usando CPF válido
        base_cpf = "52998224725"
        for i in range(25):
            participante = {
                "_id": ObjectId(),
                "nome": f"Participante {i}",
                "email": f"participante{i}@example.com",
                "cpf": base_cpf
            }
            fake_db.participantes.docs.append(participante)
        
        result = await listar_participantes(
            per_page=0,  # Abaixo do mínimo
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.per_page == 1  # Ajustado para mínimo
        assert len(result.participantes) == 1


class TestEmissaoBilheteria:
    """Testes para emissão de ingressos."""
    
    @pytest.mark.asyncio
    async def test_emitir_ingresso_success(self, fake_db, mock_get_database, sample_evento, 
                                            sample_tipo_ingresso, sample_participante, mock_verify_bilheteria):
        """Testa emissão de ingresso com sucesso."""
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.participantes.docs.append(sample_participante)
        
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(sample_participante["_id"])
        )
        
        result = await bilheteria.emitir_ingresso(
            emissao_data,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result["participante_nome"] == "João Silva"
        assert result["tipo_ingresso"] == "VIP All Access"
        assert "qrcode_hash" in result
        assert len(fake_db.ingressos_emitidos.docs) == 1
    
    @pytest.mark.asyncio
    async def test_emitir_ingresso_tipo_inexistente(self, fake_db, mock_get_database, sample_evento, 
                                                      sample_participante, mock_verify_bilheteria):
        """Testa emissão de ingresso com tipo inexistente."""
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.participantes.docs.append(sample_participante)
        
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(ObjectId()),  # Tipo inexistente
            participante_id=str(sample_participante["_id"])
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await bilheteria.emitir_ingresso(
                emissao_data,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_emitir_ingresso_participante_inexistente(self, fake_db, mock_get_database, sample_evento, 
                                                             sample_tipo_ingresso, mock_verify_bilheteria):
        """Testa emissão de ingresso com participante inexistente."""
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(ObjectId())  # Participante inexistente
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await bilheteria.emitir_ingresso(
                emissao_data,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_emitir_ingresso_duplicado(self, fake_db, mock_get_database, sample_evento, 
                                               sample_tipo_ingresso, sample_participante, 
                                               sample_ingresso, mock_verify_bilheteria):
        """Testa emissão de ingresso duplicado para mesmo participante."""
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.participantes.docs.append(sample_participante)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(sample_participante["_id"])
        )
        
        # Dependendo da implementação, pode permitir múltiplos ingressos ou bloquear
        # Aqui testamos que a emissão funciona (múltiplos ingressos permitidos)
        result = await bilheteria.emitir_ingresso(
            emissao_data,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result is not None
        assert len(fake_db.ingressos_emitidos.docs) == 2


class TestReimpressaoBilheteria:
    """Testes para reimpressão de ingressos."""
    
    @pytest.mark.asyncio
    async def test_busca_credenciamento_success(self, fake_db, mock_get_database, sample_evento, 
                                                  sample_participante, sample_ingresso, mock_verify_bilheteria):
        """Testa busca para credenciamento/reimpressão."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.participantes.docs.append(sample_participante)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        result = await bilheteria.busca_credenciamento(
            query="João",
            evento_id=str(sample_evento["_id"])
        )
        
        assert len(result) >= 1
        assert result[0]["participante"]["nome"] == "João Silva"
        assert "ingressos" in result[0]
    
    @pytest.mark.asyncio
    async def test_reimprimir_ingresso_success(self, fake_db, mock_get_database, sample_evento, 
                                                 sample_ingresso, mock_verify_bilheteria):
        """Testa reimpressão de ingresso."""
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        result = await bilheteria.reimprimir_ingresso(
            str(sample_ingresso["_id"]),
            evento_id=str(sample_evento["_id"])
        )
        
        assert "layout_html" in result or "qrcode_hash" in result
    
    @pytest.mark.asyncio
    async def test_reimprimir_ingresso_inexistente(self, fake_db, mock_get_database, sample_evento, mock_verify_bilheteria):
        """Testa reimpressão de ingresso inexistente."""
        fake_db.eventos.docs.append(sample_evento)
        
        with pytest.raises(HTTPException) as exc_info:
            await bilheteria.reimprimir_ingresso(
                str(ObjectId()),
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_reimprimir_ingresso_evento_diferente(self, fake_db, mock_get_database, 
                                                         sample_evento, sample_ingresso, mock_verify_bilheteria):
        """Testa reimpressão de ingresso de outro evento."""
        outro_evento = sample_evento.copy()
        outro_evento["_id"] = ObjectId()
        
        fake_db.eventos.docs.append(outro_evento)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        with pytest.raises(HTTPException) as exc_info:
            await bilheteria.reimprimir_ingresso(
                str(sample_ingresso["_id"]),
                evento_id=str(outro_evento["_id"])
            )
        assert exc_info.value.status_code in [403, 404]


class TestQRCodeGeneration:
    """Testes para geração de QR codes."""
    
    @pytest.mark.asyncio
    async def test_qrcode_unique(self, fake_db, mock_get_database, sample_evento, 
                                  sample_tipo_ingresso, sample_participante, mock_verify_bilheteria):
        """Testa que QR codes são únicos."""
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.participantes.docs.append(sample_participante)
        
        # Cria outro participante
        outro_participante = sample_participante.copy()
        outro_participante["_id"] = ObjectId()
        outro_participante["email"] = "outro@example.com"
        outro_participante["cpf"] = "98765432100"
        fake_db.participantes.docs.append(outro_participante)
        
        emissao_data1 = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(sample_participante["_id"])
        )
        
        emissao_data2 = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(outro_participante["_id"])
        )
        
        result1 = await bilheteria.emitir_ingresso(
            emissao_data1,
            evento_id=str(sample_evento["_id"])
        )
        
        result2 = await bilheteria.emitir_ingresso(
            emissao_data2,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result1["qrcode_hash"] != result2["qrcode_hash"]
    
    @pytest.mark.asyncio
    async def test_qrcode_format(self, fake_db, mock_get_database, sample_evento, 
                                  sample_tipo_ingresso, sample_participante, mock_verify_bilheteria):
        """Testa formato do QR code."""
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.participantes.docs.append(sample_participante)
        
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(sample_participante["_id"])
        )
        
        result = await bilheteria.emitir_ingresso(
            emissao_data,
            evento_id=str(sample_evento["_id"])
        )
        
        qrcode_hash = result["qrcode_hash"]
        assert isinstance(qrcode_hash, str)
        assert len(qrcode_hash) > 0
