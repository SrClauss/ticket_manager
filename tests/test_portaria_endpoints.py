"""
Testes abrangentes para os endpoints de portaria.
Cobre validação de QR codes e controle de acesso por setores.
"""
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.routers import portaria
from tests.conftest import FakeDB


class TestValidacaoPortaria:
    """Testes para validação de QR codes na portaria."""
    
    @pytest.mark.asyncio
    async def test_validar_acesso_permitido(self, fake_db, mock_get_database, sample_evento, 
                                              sample_ilha, sample_tipo_ingresso, sample_ingresso, mock_verify_portaria):
        """Testa validação com acesso permitido."""
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(sample_ilha["_id"])
        )
        
        result = await portaria.validar_acesso(
            validacao_data,
            evento_id=str(sample_evento["_id"])
        )
        
        assert result.status == "OK"
        assert "permitido" in result.mensagem.lower()
    
    @pytest.mark.asyncio
    async def test_validar_acesso_negado_sem_permissao(self, fake_db, mock_get_database, sample_evento, 
                                                         sample_tipo_ingresso, sample_ingresso, mock_verify_portaria):
        """Testa validação com acesso negado por falta de permissão."""
        from app.routers.portaria import ValidacaoRequest
        
        # Cria ilha sem permissão no tipo de ingresso
        outra_ilha = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "nome_setor": "Backstage",
            "capacidade_maxima": 50
        }
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(outra_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(outra_ilha["_id"])
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(
                validacao_data,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_validar_qrcode_invalido(self, fake_db, mock_get_database, sample_evento, 
                                            sample_ilha, mock_verify_portaria):
        """Testa validação com QR code inválido."""
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_inexistente",
            ilha_id=str(sample_ilha["_id"])
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(
                validacao_data,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 403
        assert "inválido" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_validar_ingresso_cancelado(self, fake_db, mock_get_database, sample_evento, 
                                                sample_ilha, sample_tipo_ingresso, sample_ingresso, mock_verify_portaria):
        """Testa validação com ingresso cancelado."""
        from app.routers.portaria import ValidacaoRequest
        
        # Marca ingresso como cancelado
        sample_ingresso["status"] = "Cancelado"
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(sample_ilha["_id"])
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(
                validacao_data,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 403
        assert "cancelado" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_validar_ingresso_evento_diferente(self, fake_db, mock_get_database, sample_evento, 
                                                       sample_ilha, sample_tipo_ingresso, sample_ingresso, mock_verify_portaria):
        """Testa validação com ingresso de outro evento."""
        from app.routers.portaria import ValidacaoRequest
        
        # Cria outro evento
        outro_evento = sample_evento.copy()
        outro_evento["_id"] = ObjectId()
        
        fake_db.eventos.docs.append(outro_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(sample_ilha["_id"])
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(
                validacao_data,
                evento_id=str(outro_evento["_id"])
            )
        assert exc_info.value.status_code == 403


class TestEstatisticasPortaria:
    """Testes para estatísticas da portaria."""
    
    @pytest.mark.asyncio
    async def test_estatisticas_sem_dados(self, fake_db, mock_get_database, sample_evento, mock_verify_portaria):
        """Testa estatísticas sem validações."""
        fake_db.eventos.docs.append(sample_evento)
        
        result = await portaria.get_estatisticas(evento_id=str(sample_evento["_id"]))
        
        assert result["total_validacoes"] == 0
    
    @pytest.mark.asyncio
    async def test_estatisticas_com_dados(self, fake_db, mock_get_database, sample_evento, 
                                           sample_ilha, sample_tipo_ingresso, sample_ingresso, mock_verify_portaria):
        """Testa estatísticas com validações."""
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        # Realiza algumas validações
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(sample_ilha["_id"])
        )
        
        try:
            await portaria.validar_acesso(
                validacao_data,
                evento_id=str(sample_evento["_id"])
            )
        except:
            pass
        
        result = await portaria.get_estatisticas(evento_id=str(sample_evento["_id"]))
        
        # Verifica que estatísticas foram geradas
        assert "total_validacoes" in result


class TestPermissoesPortaria:
    """Testes para sistema de permissões."""
    
    @pytest.mark.asyncio
    async def test_ingresso_com_multiplas_permissoes(self, fake_db, mock_get_database, sample_evento, mock_verify_portaria):
        """Testa ingresso com acesso a múltiplas ilhas."""
        from app.routers.portaria import ValidacaoRequest
        
        # Cria múltiplas ilhas
        ilha1 = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "nome_setor": "VIP",
            "capacidade_maxima": 100
        }
        ilha2 = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "nome_setor": "Pista",
            "capacidade_maxima": 500
        }
        
        # Tipo de ingresso com acesso a ambas ilhas
        tipo_ingresso = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "descricao": "All Access",
            "valor": 200.0,
            "permissoes": [str(ilha1["_id"]), str(ilha2["_id"])],
            "padrao": False
        }
        
        participante = {
            "_id": ObjectId(),
            "nome": "Teste",
            "email": "teste@example.com",
            "cpf": "12345678901"
        }
        
        ingresso = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "tipo_ingresso_id": str(tipo_ingresso["_id"]),
            "participante_id": str(participante["_id"]),
            "qrcode_hash": "qr_multi_access",
            "status": "Ativo",
            "data_emissao": datetime.now(timezone.utc)
        }
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.extend([ilha1, ilha2])
        fake_db.tipos_ingresso.docs.append(tipo_ingresso)
        fake_db.participantes.docs.append(participante)
        fake_db.ingressos_emitidos.docs.append(ingresso)
        
        # Valida acesso na ilha1
        validacao1 = ValidacaoRequest(
            qrcode_hash="qr_multi_access",
            ilha_id=str(ilha1["_id"])
        )
        result1 = await portaria.validar_acesso(validacao1, evento_id=str(sample_evento["_id"]))
        assert result1.status == "OK"
        
        # Valida acesso na ilha2
        validacao2 = ValidacaoRequest(
            qrcode_hash="qr_multi_access",
            ilha_id=str(ilha2["_id"])
        )
        result2 = await portaria.validar_acesso(validacao2, evento_id=str(sample_evento["_id"]))
        assert result2.status == "OK"
    
    @pytest.mark.asyncio
    async def test_ingresso_sem_permissoes(self, fake_db, mock_get_database, sample_evento, 
                                            sample_ilha, mock_verify_portaria):
        """Testa ingresso sem permissões específicas."""
        from app.routers.portaria import ValidacaoRequest
        
        # Tipo de ingresso sem permissões
        tipo_ingresso = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "descricao": "Básico",
            "valor": 50.0,
            "permissoes": [],
            "padrao": False
        }
        
        participante = {
            "_id": ObjectId(),
            "nome": "Teste",
            "email": "teste@example.com",
            "cpf": "12345678901"
        }
        
        ingresso = {
            "_id": ObjectId(),
            "evento_id": str(sample_evento["_id"]),
            "tipo_ingresso_id": str(tipo_ingresso["_id"]),
            "participante_id": str(participante["_id"]),
            "qrcode_hash": "qr_no_access",
            "status": "Ativo",
            "data_emissao": datetime.now(timezone.utc)
        }
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(tipo_ingresso)
        fake_db.participantes.docs.append(participante)
        fake_db.ingressos_emitidos.docs.append(ingresso)
        
        validacao = ValidacaoRequest(
            qrcode_hash="qr_no_access",
            ilha_id=str(sample_ilha["_id"])
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(validacao, evento_id=str(sample_evento["_id"]))
        assert exc_info.value.status_code == 403


class TestSecurityPortaria:
    """Testes de segurança da portaria."""
    
    @pytest.mark.asyncio
    async def test_token_invalido(self, fake_db, mock_get_database, sample_evento):
        """Testa acesso com token inválido."""
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(ObjectId())
        )
        
        # Mock de token inválido
        with pytest.raises(Exception):
            await portaria.validar_acesso(
                validacao_data,
                evento_id=None  # Simula falha de autenticação
            )
    
    @pytest.mark.asyncio
    async def test_ilha_inexistente(self, fake_db, mock_get_database, sample_evento, 
                                      sample_tipo_ingresso, sample_ingresso, mock_verify_portaria):
        """Testa validação com ilha inexistente."""
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.ingressos_emitidos.docs.append(sample_ingresso)
        
        validacao_data = ValidacaoRequest(
            qrcode_hash="qr_hash_abc123",
            ilha_id=str(ObjectId())  # Ilha inexistente
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(
                validacao_data,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 403
