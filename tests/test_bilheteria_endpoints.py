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
