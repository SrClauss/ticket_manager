"""
Testes de integração para fluxos completos do sistema.
Testa cenários end-to-end simulando uso real.
"""
import pytest
from datetime import datetime, timezone
from bson import ObjectId

from tests.conftest import FakeDB


class TestFluxoCompletoEvento:
    """Testes de integração para fluxo completo de evento."""
    
    @pytest.mark.asyncio
    async def test_fluxo_criar_evento_completo(self, fake_db, mock_get_database):
        """Testa criação completa de evento com ilhas e tipos de ingresso."""
        from app.routers import admin
        from app.models.evento import EventoCreate
        from app.models.ilha import IlhaCreate
        from app.models.tipo_ingresso import TipoIngressoCreate
        
        # 1. Criar evento
        evento_data = EventoCreate(
            nome="Conferência Tech 2024",
            descricao="Grande evento de tecnologia",
            data_evento=datetime(2024, 12, 15, 9, 0, 0, tzinfo=timezone.utc)
        )
        evento = await admin.create_evento(evento_data)
        assert evento.nome == "Conferência Tech 2024"
        
        # 2. Criar ilhas
        ilha_vip_data = IlhaCreate(
            evento_id=evento.id,
            nome_setor="VIP",
            capacidade_maxima=100
        )
        ilha_vip = await admin.create_ilha(ilha_vip_data)
        
        ilha_pista_data = IlhaCreate(
            evento_id=evento.id,
            nome_setor="Pista",
            capacidade_maxima=500
        )
        ilha_pista = await admin.create_ilha(ilha_pista_data)
        
        # 3. Criar tipos de ingresso
        tipo_vip_data = TipoIngressoCreate(
            evento_id=evento.id,
            descricao="VIP All Access",
            valor=200.0,
            permissoes=[ilha_vip.id, ilha_pista.id]
        )
        tipo_vip = await admin.create_tipo_ingresso(tipo_vip_data)
        
        tipo_pista_data = TipoIngressoCreate(
            evento_id=evento.id,
            descricao="Pista",
            valor=50.0,
            permissoes=[ilha_pista.id]
        )
        tipo_pista = await admin.create_tipo_ingresso(tipo_pista_data)
        
        # 4. Verificar estrutura completa
        evento_completo = await admin.get_evento(evento.id)
        assert evento_completo.nome == "Conferência Tech 2024"
        
        ilhas = await admin.list_ilhas(evento.id)
        assert len(ilhas) == 2
        
        tipos = await admin.list_tipos_ingresso(evento.id)
        assert len(tipos) == 2


class TestFluxoCompletoBilheteria:
    """Testes de integração para fluxo de bilheteria."""
    
    @pytest.mark.asyncio
    async def test_fluxo_credenciamento_completo(self, fake_db, mock_get_database, 
                                                   sample_evento, sample_ilha, 
                                                   sample_tipo_ingresso, mock_verify_bilheteria):
        """Testa fluxo completo de credenciamento."""
        from app.routers import bilheteria
        from app.models.participante import ParticipanteCreate
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        
        # 1. Cadastrar participante
        participante_data = ParticipanteCreate(
            nome="Carlos Silva",
            email="carlos@example.com",
            cpf="529.982.247-25",
            telefone="11999999999",
            empresa="Tech Corp"
        )
        participante = await bilheteria.create_participante(
            participante_data,
            evento_id=str(sample_evento["_id"])
        )
        
        # 2. Buscar participante
        resultados = await bilheteria.buscar_participantes(
            query="Carlos",
            evento_id=str(sample_evento["_id"])
        )
        assert len(resultados) >= 1
        assert resultados[0].nome == "Carlos Silva"
        
        # 3. Emitir ingresso
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=participante.id
        )
        ingresso = await bilheteria.emitir_ingresso(
            emissao_data,
            evento_id=str(sample_evento["_id"])
        )
        
        assert ingresso["participante_nome"] == "Carlos Silva"
        assert "qrcode_hash" in ingresso
        
        # 4. Buscar para reimpressão
        credenciados = await bilheteria.busca_credenciamento(
            query="Carlos",
            evento_id=str(sample_evento["_id"])
        )
        assert len(credenciados) >= 1
        assert len(credenciados[0]["ingressos"]) == 1


class TestFluxoCompletoPortaria:
    """Testes de integração para fluxo de portaria."""
    
    @pytest.mark.asyncio
    async def test_fluxo_validacao_completo(self, fake_db, mock_get_database, 
                                             sample_evento, sample_ilha, 
                                             sample_tipo_ingresso, sample_participante,
                                             mock_verify_bilheteria, mock_verify_portaria):
        """Testa fluxo completo de validação na portaria."""
        from app.routers import bilheteria, portaria
        from app.routers.bilheteria import EmissaoRequest
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        fake_db.participantes.docs.append(sample_participante)
        
        # 1. Emitir ingresso (bilheteria)
        emissao_data = EmissaoRequest(
            tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
            participante_id=str(sample_participante["_id"])
        )
        ingresso = await bilheteria.emitir_ingresso(
            emissao_data,
            evento_id=str(sample_evento["_id"])
        )
        qrcode_hash = ingresso["qrcode_hash"]
        
        # 2. Validar na portaria
        validacao_data = ValidacaoRequest(
            qrcode_hash=qrcode_hash,
            ilha_id=str(sample_ilha["_id"])
        )
        resultado = await portaria.validar_acesso(
            validacao_data,
            evento_id=str(sample_evento["_id"])
        )
        
        assert resultado.status == "OK"
        assert "João Silva" in resultado.participante_nome


class TestFluxoMultiplosParticipantes:
    """Testes de integração com múltiplos participantes."""
    
    @pytest.mark.asyncio
    async def test_emissao_multiplos_ingressos(self, fake_db, mock_get_database, 
                                                 sample_evento, sample_ilha, 
                                                 sample_tipo_ingresso, mock_verify_bilheteria):
        """Testa emissão de múltiplos ingressos."""
        from app.routers import bilheteria
        from app.models.participante import ParticipanteCreate
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        fake_db.tipos_ingresso.docs.append(sample_tipo_ingresso)
        
        participantes_data = [
            {"nome": "Participante 1", "email": "p1@example.com", "cpf": "529.982.247-25"},
            {"nome": "Participante 2", "email": "p2@example.com", "cpf": "123.456.789-09"},
            {"nome": "Participante 3", "email": "p3@example.com", "cpf": "987.654.321-00"},
        ]
        
        ingressos_emitidos = []
        
        for p_data in participantes_data:
            # Cadastrar participante
            participante = await bilheteria.create_participante(
                ParticipanteCreate(**p_data, telefone="11999999999"),
                evento_id=str(sample_evento["_id"])
            )
            
            # Emitir ingresso
            emissao = EmissaoRequest(
                tipo_ingresso_id=str(sample_tipo_ingresso["_id"]),
                participante_id=participante.id
            )
            ingresso = await bilheteria.emitir_ingresso(
                emissao,
                evento_id=str(sample_evento["_id"])
            )
            ingressos_emitidos.append(ingresso)
        
        # Verificar que todos os ingressos foram emitidos
        assert len(ingressos_emitidos) == 3
        
        # Verificar que QR codes são únicos
        qr_codes = [ing["qrcode_hash"] for ing in ingressos_emitidos]
        assert len(set(qr_codes)) == 3


class TestFluxoRelatorios:
    """Testes de integração para relatórios."""
    
    @pytest.mark.asyncio
    async def test_relatorio_apos_vendas(self, fake_db, mock_get_database, 
                                          sample_evento, sample_ilha, mock_verify_bilheteria):
        """Testa geração de relatório após vendas."""
        from app.routers import admin, bilheteria
        from app.models.tipo_ingresso import TipoIngressoCreate
        from app.models.participante import ParticipanteCreate
        from app.routers.bilheteria import EmissaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.ilhas.docs.append(sample_ilha)
        
        # Criar dois tipos de ingresso
        tipo1_data = TipoIngressoCreate(
            evento_id=str(sample_evento["_id"]),
            descricao="VIP",
            valor=200.0,
            permissoes=[str(sample_ilha["_id"])]
        )
        tipo1 = await admin.create_tipo_ingresso(tipo1_data)
        
        tipo2_data = TipoIngressoCreate(
            evento_id=str(sample_evento["_id"]),
            descricao="Pista",
            valor=50.0,
            permissoes=[str(sample_ilha["_id"])]
        )
        tipo2 = await admin.create_tipo_ingresso(tipo2_data)
        
        # Emitir ingressos (5 VIP, 10 Pista)
        for i in range(5):
            participante = await bilheteria.create_participante(
                ParticipanteCreate(
                    nome=f"VIP {i}",
                    email=f"vip{i}@example.com",
                    cpf=f"{100000000 + i:011d}",
                    telefone="11999999999"
                ),
                evento_id=str(sample_evento["_id"])
            )
            await bilheteria.emitir_ingresso(
                EmissaoRequest(
                    tipo_ingresso_id=tipo1.id,
                    participante_id=participante.id
                ),
                evento_id=str(sample_evento["_id"])
            )
        
        for i in range(10):
            participante = await bilheteria.create_participante(
                ParticipanteCreate(
                    nome=f"Pista {i}",
                    email=f"pista{i}@example.com",
                    cpf=f"{200000000 + i:011d}",
                    telefone="11999999999"
                ),
                evento_id=str(sample_evento["_id"])
            )
            await bilheteria.emitir_ingresso(
                EmissaoRequest(
                    tipo_ingresso_id=tipo2.id,
                    participante_id=participante.id
                ),
                evento_id=str(sample_evento["_id"])
            )
        
        # Gerar relatório
        relatorio = await admin.relatorio_vendas(str(sample_evento["_id"]))
        
        assert relatorio["total_ingressos"] == 15
        assert len(relatorio["tipos"]) == 2
        
        # Verificar quantidades por tipo
        vip_count = next((t["quantidade"] for t in relatorio["tipos"] if "VIP" in t["tipo"]), 0)
        pista_count = next((t["quantidade"] for t in relatorio["tipos"] if "Pista" in t["tipo"]), 0)
        
        assert vip_count == 5
        assert pista_count == 10


class TestFluxoErrorHandling:
    """Testes de integração para tratamento de erros."""
    
    @pytest.mark.asyncio
    async def test_emissao_com_tipo_sem_permissao(self, fake_db, mock_get_database, 
                                                    sample_evento, sample_participante, 
                                                    mock_verify_bilheteria, mock_verify_portaria):
        """Testa fluxo com tipo de ingresso sem permissão para ilha."""
        from app.routers import bilheteria, portaria, admin
        from app.models.ilha import IlhaCreate
        from app.models.tipo_ingresso import TipoIngressoCreate
        from app.routers.bilheteria import EmissaoRequest
        from app.routers.portaria import ValidacaoRequest
        
        fake_db.eventos.docs.append(sample_evento)
        fake_db.participantes.docs.append(sample_participante)
        
        # Criar ilha VIP
        ilha_vip = await admin.create_ilha(IlhaCreate(
            evento_id=str(sample_evento["_id"]),
            nome_setor="VIP",
            capacidade_maxima=100
        ))
        
        # Criar ilha Backstage
        ilha_backstage = await admin.create_ilha(IlhaCreate(
            evento_id=str(sample_evento["_id"]),
            nome_setor="Backstage",
            capacidade_maxima=50
        ))
        
        # Criar tipo de ingresso apenas para VIP
        tipo_ingresso = await admin.create_tipo_ingresso(TipoIngressoCreate(
            evento_id=str(sample_evento["_id"]),
            descricao="VIP Only",
            valor=150.0,
            permissoes=[ilha_vip.id]  # Apenas VIP
        ))
        
        # Emitir ingresso
        emissao = await bilheteria.emitir_ingresso(
            EmissaoRequest(
                tipo_ingresso_id=tipo_ingresso.id,
                participante_id=str(sample_participante["_id"])
            ),
            evento_id=str(sample_evento["_id"])
        )
        
        # Tentar validar na ilha VIP (deve funcionar)
        validacao_vip = ValidacaoRequest(
            qrcode_hash=emissao["qrcode_hash"],
            ilha_id=ilha_vip.id
        )
        resultado_vip = await portaria.validar_acesso(
            validacao_vip,
            evento_id=str(sample_evento["_id"])
        )
        assert resultado_vip.status == "OK"
        
        # Tentar validar na ilha Backstage (deve falhar)
        validacao_backstage = ValidacaoRequest(
            qrcode_hash=emissao["qrcode_hash"],
            ilha_id=ilha_backstage.id
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await portaria.validar_acesso(
                validacao_backstage,
                evento_id=str(sample_evento["_id"])
            )
        assert exc_info.value.status_code == 403
